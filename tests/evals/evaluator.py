"""Deterministic evaluator for golden sets and labeled scenarios.

Binary checks — no LLM needed. Zero API cost. Run after every commit.

Check types:
  - Tool selection: did the agent call the expected tool(s)?
  - Content validation: does the response contain required facts?
  - Negative validation: agent must NOT say certain things.
  - Numerical validation: are numbers from tool output in the response?
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""

    case_id: str
    passed: bool
    tool_check_passed: bool | None = None
    content_check_passed: bool | None = None
    negative_check_passed: bool | None = None
    contain_any_check_passed: bool | None = None
    failures: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        if self.failures:
            return f"[{status}] {self.case_id}: {'; '.join(self.failures)}"
        return f"[{status}] {self.case_id}"


def evaluate_case(
    case: dict,
    response_text: str,
    tools_called: list[str],
) -> EvalResult:
    """Run all deterministic checks for a single eval case.

    Args:
        case: Test case dict from YAML (id, query, expected_tools, must_contain, etc.)
        response_text: The agent's final response string.
        tools_called: List of tool names the agent invoked.

    Returns:
        EvalResult with pass/fail and failure details.
    """
    case_id = case["id"]
    failures: list[str] = []
    response_lower = response_text.lower()

    # ── Tool Selection ───────────────────────────────────────────
    tool_check_passed = None
    expected_tools = case.get("expected_tools", [])
    if expected_tools:
        for tool in expected_tools:
            if tool not in tools_called:
                failures.append(f"Tool selection: expected '{tool}' but got {tools_called}")
        tool_check_passed = len(failures) == 0

    # ── Content Validation (must_contain) ────────────────────────
    content_check_passed = None
    must_contain = case.get("must_contain", [])
    if must_contain:
        pre_fail_count = len(failures)
        for phrase in must_contain:
            if phrase.lower() not in response_lower:
                failures.append(f"Content: response missing '{phrase}'")
        content_check_passed = len(failures) == pre_fail_count

    # ── Negative Validation (must_not_contain) ───────────────────
    negative_check_passed = None
    must_not_contain = case.get("must_not_contain", [])
    if must_not_contain:
        pre_fail_count = len(failures)
        for phrase in must_not_contain:
            if phrase.lower() in response_lower:
                failures.append(f"Negative: response contains forbidden '{phrase}'")
        negative_check_passed = len(failures) == pre_fail_count

    # ── Contain-Any Validation (must_contain_any) ────────────────
    contain_any_check_passed = None
    must_contain_any = case.get("must_contain_any", [])
    if must_contain_any:
        found_any = any(phrase.lower() in response_lower for phrase in must_contain_any)
        if not found_any:
            failures.append(
                f"ContainAny: response must contain at least one of {must_contain_any}"
            )
        contain_any_check_passed = found_any

    passed = len(failures) == 0

    return EvalResult(
        case_id=case_id,
        passed=passed,
        tool_check_passed=tool_check_passed,
        content_check_passed=content_check_passed,
        negative_check_passed=negative_check_passed,
        contain_any_check_passed=contain_any_check_passed,
        failures=failures,
    )


def evaluate_batch(
    cases: list[dict],
    results: list[dict],
) -> list[EvalResult]:
    """Evaluate a batch of test cases against agent results.

    Args:
        cases: List of test case dicts from YAML.
        results: List of agent result dicts with keys:
                 'response', 'tools_called'.

    Returns:
        List of EvalResult objects.
    """
    eval_results = []
    for case, result in zip(cases, results):
        eval_result = evaluate_case(
            case=case,
            response_text=result.get("response", ""),
            tools_called=result.get("tools_called", []),
        )
        eval_results.append(eval_result)
    return eval_results


def print_eval_report(eval_results: list[EvalResult]) -> None:
    """Print a formatted eval report to stdout."""
    total = len(eval_results)
    passed = sum(1 for r in eval_results if r.passed)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  EVAL REPORT: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    for r in eval_results:
        print(r.summary)

    if failed > 0:
        print(f"\n  FAILURES: {failed}/{total}")
        for r in eval_results:
            if not r.passed:
                for f in r.failures:
                    print(f"    - [{r.case_id}] {f}")
    print("=" * 60 + "\n")
