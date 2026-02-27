"""Per-user memory bank: preferences, feedback lessons, and fact caching."""

import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserPreference:
    key: str
    value: str
    updated_at: str


@dataclass
class FeedbackLesson:
    query_pattern: str
    lesson: str
    timestamp: str


@dataclass
class CachedFact:
    tool_name: str
    output: str
    cached_at: float


@dataclass
class MemoryStore:
    preferences: dict[str, dict[str, UserPreference]] = field(default_factory=dict)
    lessons: dict[str, deque] = field(default_factory=dict)
    fact_cache: dict[str, dict[str, CachedFact]] = field(default_factory=dict)

    FACT_TTL_SECONDS: int = 300  # 5 minutes

    # ── Preferences ──────────────────────────────────────────
    def set_preference(self, user_token: str, key: str, value: str) -> None:
        if user_token not in self.preferences:
            self.preferences[user_token] = {}
        self.preferences[user_token][key] = UserPreference(
            key=key,
            value=value,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_preferences(self, user_token: str) -> dict[str, str]:
        prefs = self.preferences.get(user_token, {})
        return {k: v.value for k, v in prefs.items()}

    # ── Feedback Lessons ─────────────────────────────────────
    def add_lesson(self, user_token: str, query_pattern: str, lesson: str) -> None:
        if user_token not in self.lessons:
            self.lessons[user_token] = deque(maxlen=50)
        self.lessons[user_token].append(FeedbackLesson(
            query_pattern=query_pattern,
            lesson=lesson,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    def get_relevant_lessons(self, user_token: str, query: str) -> list[str]:
        user_lessons = self.lessons.get(user_token, [])
        query_words = set(query.lower().split())
        relevant = []
        for lesson in user_lessons:
            pattern_words = set(lesson.query_pattern.lower().split())
            if len(query_words & pattern_words) >= 2:
                relevant.append(lesson.lesson)
        return relevant[-3:]

    # ── Fact Cache ───────────────────────────────────────────
    def cache_fact(self, user_token: str, tool_name: str, output: str) -> None:
        if user_token not in self.fact_cache:
            self.fact_cache[user_token] = {}
        self.fact_cache[user_token][tool_name] = CachedFact(
            tool_name=tool_name,
            output=output,
            cached_at=time.time(),
        )

    def get_cached_fact(self, user_token: str, tool_name: str) -> str | None:
        cache = self.fact_cache.get(user_token, {})
        fact = cache.get(tool_name)
        if fact and (time.time() - fact.cached_at) < self.FACT_TTL_SECONDS:
            return fact.output
        if fact:
            del cache[tool_name]
        return None

    # ── Context Builder ──────────────────────────────────────
    def build_context(self, user_token: str, query: str) -> str:
        parts = []

        prefs = self.get_preferences(user_token)
        if prefs:
            pref_lines = [f"- {k}: {v}" for k, v in prefs.items()]
            parts.append("User Preferences:\n" + "\n".join(pref_lines))

        lessons = self.get_relevant_lessons(user_token, query)
        if lessons:
            lesson_lines = [f"- {l}" for l in lessons]
            parts.append("Lessons from previous feedback:\n" + "\n".join(lesson_lines))

        cache = self.fact_cache.get(user_token, {})
        now = time.time()
        cached_tools = [
            name for name, fact in cache.items()
            if (now - fact.cached_at) < self.FACT_TTL_SECONDS
        ]
        if cached_tools:
            parts.append(
                f"Recent data available (cached): {', '.join(cached_tools)}. "
                "You may still call these tools if the user needs fresh data."
            )

        return "\n\n".join(parts)

    # ── Preference Extraction ────────────────────────────────
    def extract_preferences(self, user_token: str, query: str, tools_called: list[str]) -> None:
        query_lower = query.lower()

        range_match = re.search(r"\b(1d|1w|1m|3m|6m|ytd|1y|3y|5y)\b", query_lower)
        if range_match and "portfolio_performance" in tools_called:
            self.set_preference(user_token, "preferred_time_range", range_match.group(1))

        risk_match = re.search(r"\b(conservative|moderate|aggressive)\b", query_lower)
        if risk_match:
            self.set_preference(user_token, "risk_tolerance", risk_match.group(1))


memory_store = MemoryStore()
