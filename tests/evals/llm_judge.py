"""LLM-as-a-Judge evaluator for groundedness, faithfulness, and rubric scoring.

Use it right, or don't use it:
  - Binary claim-by-claim groundedness check
  - Rubric scoring with explicit anchors (no vague criteria)
  - Calibrate against human scores before trusting at scale

Reserve LLM judges for what can't be checked programmatically.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)

GROUNDEDNESS_PROMPT = """You are a fact-checking judge. Your job is to determine if the agent's
response is grounded in the tool output data.

TOOL OUTPUT (source of truth):
{tool_output}

AGENT RESPONSE (to verify):
{response}

For each factual claim in the agent's response, check if it is supported by the tool output.

Respond in JSON format:
{{
  "claims": [
    {{"claim": "...", "grounded": true/false, "reason": "..."}},
    ...
  ],
  "overall_grounded": true/false,
  "groundedness_score": 0.0-1.0
}}

Rules:
- A claim is grounded if the tool output supports it (exact numbers, correct relationships).
- Formatting differences (e.g., "$125,000.50" vs "125000.50") are acceptable.
- Rounding to 2 decimal places is acceptable.
- General financial disclaimers are always grounded (they don't need tool data).
- If the response fabricates ANY number not in the tool output, overall_grounded must be false.
"""

RUBRIC_PROMPT = """You are a quality judge evaluating an AI finance assistant's response.

USER QUERY: {query}
TOOL OUTPUT (ground truth): {tool_output}
AGENT RESPONSE: {response}

Score the response on these dimensions. Use ONLY the exact scores defined (0, 1, 3, or 5):

{rubric_text}

Respond in JSON format:
{{
  "scores": {{
    "relevance": {{"score": N, "reason": "..."}},
    "accuracy": {{"score": N, "reason": "..."}},
    "completeness": {{"score": N, "reason": "..."}},
    "clarity": {{"score": N, "reason": "..."}}
  }},
  "weighted_score": N.N,
  "quality_level": "excellent/good/acceptable/poor/critical"
}}

IMPORTANT:
- Score ONLY 0, 1, 3, or 5. No other values.
- Base accuracy ONLY on tool output data. If a number isn't in the tool output, it's fabricated.
- A disclaimer/boilerplate is always acceptable for completeness.
"""


@dataclass
class GroundednessResult:
    overall_grounded: bool
    groundedness_score: float
    claims: list[dict]
    raw_response: str


@dataclass
class RubricResult:
    scores: dict[str, dict]
    weighted_score: float
    quality_level: str
    raw_response: str


def _load_rubrics() -> dict:
    """Load rubric definitions from YAML."""
    import os

    rubric_path = os.path.join(os.path.dirname(__file__), "rubrics.yaml")
    with open(rubric_path) as f:
        return yaml.safe_load(f)


def _format_rubric_text(rubrics: dict) -> str:
    """Format rubric dimensions into a prompt-friendly string."""
    lines = []
    for dim_name, dim in rubrics["dimensions"].items():
        lines.append(f"\n{dim_name.upper()} (weight: {dim['weight']}):")
        lines.append(f"  Question: {dim['question']}")
        for score, desc in sorted(dim["scores"].items(), reverse=True):
            lines.append(f"  {score}: {desc}")
    return "\n".join(lines)


async def judge_groundedness(
    response: str,
    tool_outputs: list[str],
    llm=None,
) -> GroundednessResult:
    """Check if agent response is grounded in tool output data.

    Args:
        response: Agent's final response text.
        tool_outputs: Raw tool output strings.
        llm: LangChain LLM to use as judge. If None, uses Groq Llama.

    Returns:
        GroundednessResult with claim-level and overall assessment.
    """
    if llm is None:
        from langchain_groq import ChatGroq

        from app.config import settings

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=settings.groq_api_key,
        )

    combined_output = "\n---\n".join(tool_outputs) if tool_outputs else "(no tool output)"

    prompt = GROUNDEDNESS_PROMPT.format(
        tool_output=combined_output,
        response=response,
    )

    try:
        result = await llm.ainvoke(prompt)
        content = result.content

        # Parse JSON from response
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(content[json_start:json_end])
        else:
            parsed = {"overall_grounded": False, "groundedness_score": 0, "claims": []}

        return GroundednessResult(
            overall_grounded=parsed.get("overall_grounded", False),
            groundedness_score=parsed.get("groundedness_score", 0),
            claims=parsed.get("claims", []),
            raw_response=content,
        )
    except Exception as e:
        logger.error("LLM judge groundedness failed: %s", e)
        return GroundednessResult(
            overall_grounded=False,
            groundedness_score=0,
            claims=[],
            raw_response=str(e),
        )


async def judge_rubric(
    query: str,
    response: str,
    tool_outputs: list[str],
    llm=None,
) -> RubricResult:
    """Score agent response using weighted rubric dimensions.

    Args:
        query: User's original query.
        response: Agent's final response text.
        tool_outputs: Raw tool output strings.
        llm: LangChain LLM to use as judge.

    Returns:
        RubricResult with per-dimension scores and weighted total.
    """
    if llm is None:
        from langchain_groq import ChatGroq

        from app.config import settings

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=settings.groq_api_key,
        )

    rubrics = _load_rubrics()
    rubric_text = _format_rubric_text(rubrics)
    combined_output = "\n---\n".join(tool_outputs) if tool_outputs else "(no tool output)"

    prompt = RUBRIC_PROMPT.format(
        query=query,
        tool_output=combined_output,
        response=response,
        rubric_text=rubric_text,
    )

    try:
        result = await llm.ainvoke(prompt)
        content = result.content

        # Try to parse JSON, with fallback for malformed LLM output
        parsed = None
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            raw_json = content[json_start:json_end]
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                # Try fixing common LLM JSON issues (trailing commas, etc.)
                import re

                fixed = re.sub(r",\s*}", "}", raw_json)
                fixed = re.sub(r",\s*]", "]", fixed)
                try:
                    parsed = json.loads(fixed)
                except json.JSONDecodeError:
                    # Last resort: extract scores with regex
                    score_pattern = r'"(\w+)":\s*\{\s*"score":\s*(\d)'
                    matches = re.findall(score_pattern, raw_json)
                    if matches:
                        parsed = {
                            "scores": {
                                name: {"score": int(score), "reason": "extracted via regex"}
                                for name, score in matches
                            }
                        }
        if parsed is None:
            parsed = {"scores": {}, "weighted_score": 0, "quality_level": "critical"}

        # Calculate weighted score if not provided
        if "weighted_score" not in parsed or parsed["weighted_score"] == 0:
            total = 0
            for dim_name, dim_conf in rubrics["dimensions"].items():
                score_data = parsed.get("scores", {}).get(dim_name, {})
                score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
                total += score * dim_conf["weight"]
            parsed["weighted_score"] = round(total, 2)

        # Determine quality level from thresholds
        weighted = parsed["weighted_score"]
        quality = "critical"
        for level, conf in rubrics["thresholds"].items():
            if weighted >= conf["min"]:
                quality = level
                break
        parsed["quality_level"] = quality

        return RubricResult(
            scores=parsed.get("scores", {}),
            weighted_score=parsed["weighted_score"],
            quality_level=parsed["quality_level"],
            raw_response=content,
        )
    except Exception as e:
        logger.error("LLM judge rubric failed: %s", e)
        return RubricResult(
            scores={},
            weighted_score=0,
            quality_level="critical",
            raw_response=str(e),
        )
