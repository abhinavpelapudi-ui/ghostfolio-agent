"""Tests for the memory bank store."""

import time

from app.memory.memory_store import MemoryStore


def _fresh_store() -> MemoryStore:
    return MemoryStore()


# ── Preferences ──────────────────────────────────────────────


def test_set_and_get_preference():
    store = _fresh_store()
    store.set_preference("user1", "preferred_time_range", "1y")
    assert store.get_preferences("user1") == {"preferred_time_range": "1y"}


def test_get_preferences_empty():
    store = _fresh_store()
    assert store.get_preferences("unknown_user") == {}


def test_overwrite_preference():
    store = _fresh_store()
    store.set_preference("user1", "risk_tolerance", "conservative")
    store.set_preference("user1", "risk_tolerance", "aggressive")
    assert store.get_preferences("user1")["risk_tolerance"] == "aggressive"


def test_multiple_preferences():
    store = _fresh_store()
    store.set_preference("user1", "risk_tolerance", "moderate")
    store.set_preference("user1", "preferred_time_range", "3m")
    prefs = store.get_preferences("user1")
    assert prefs == {"risk_tolerance": "moderate", "preferred_time_range": "3m"}


# ── Feedback Lessons ─────────────────────────────────────────


def test_add_and_retrieve_lesson():
    store = _fresh_store()
    store.add_lesson("user1", "show my portfolio performance", "Be more accurate with numbers")
    lessons = store.get_relevant_lessons("user1", "show portfolio performance chart")
    assert len(lessons) == 1
    assert "accurate" in lessons[0]


def test_lesson_no_match():
    store = _fresh_store()
    store.add_lesson("user1", "show my portfolio performance", "Be more accurate")
    lessons = store.get_relevant_lessons("user1", "search for Apple stock")
    assert len(lessons) == 0


def test_lesson_max_three_returned():
    store = _fresh_store()
    for i in range(5):
        store.add_lesson("user1", "portfolio risk analysis", f"Lesson {i}")
    lessons = store.get_relevant_lessons("user1", "portfolio risk check")
    assert len(lessons) <= 3


def test_lessons_per_user_isolated():
    store = _fresh_store()
    store.add_lesson("user1", "portfolio summary", "Lesson for user1")
    store.add_lesson("user2", "portfolio summary", "Lesson for user2")
    lessons1 = store.get_relevant_lessons("user1", "portfolio summary view")
    lessons2 = store.get_relevant_lessons("user2", "portfolio summary view")
    assert len(lessons1) == 1
    assert "user1" in lessons1[0]
    assert "user2" in lessons2[0]


# ── Fact Cache ───────────────────────────────────────────────


def test_cache_and_retrieve_fact():
    store = _fresh_store()
    store.cache_fact("user1", "portfolio_summary", '{"value": 100}')
    assert store.get_cached_fact("user1", "portfolio_summary") == '{"value": 100}'


def test_cache_miss():
    store = _fresh_store()
    assert store.get_cached_fact("user1", "portfolio_summary") is None


def test_cache_ttl_expiry():
    store = _fresh_store()
    store.FACT_TTL_SECONDS = 1
    store.cache_fact("user1", "portfolio_summary", '{"value": 100}')
    assert store.get_cached_fact("user1", "portfolio_summary") is not None
    time.sleep(1.1)
    assert store.get_cached_fact("user1", "portfolio_summary") is None


# ── Context Builder ──────────────────────────────────────────


def test_build_context_empty():
    store = _fresh_store()
    ctx = store.build_context("unknown_user", "hello")
    assert ctx == ""


def test_build_context_with_preferences():
    store = _fresh_store()
    store.set_preference("user1", "risk_tolerance", "conservative")
    ctx = store.build_context("user1", "show my portfolio")
    assert "conservative" in ctx
    assert "User Preferences" in ctx


def test_build_context_with_lessons():
    store = _fresh_store()
    store.add_lesson("user1", "portfolio risk analysis", "Include all risk flags")
    ctx = store.build_context("user1", "analyze my portfolio risk")
    assert "risk flags" in ctx
    assert "Lessons" in ctx


def test_build_context_with_cached_facts():
    store = _fresh_store()
    store.cache_fact("user1", "portfolio_summary", '{"value": 100}')
    ctx = store.build_context("user1", "show my portfolio")
    assert "portfolio_summary" in ctx
    assert "cached" in ctx.lower()


# ── Preference Extraction ────────────────────────────────────


def test_extract_time_range_preference():
    store = _fresh_store()
    store.extract_preferences("user1", "show me 1y performance", ["portfolio_performance"])
    assert store.get_preferences("user1").get("preferred_time_range") == "1y"


def test_extract_risk_tolerance():
    store = _fresh_store()
    store.extract_preferences("user1", "I am a conservative investor", [])
    assert store.get_preferences("user1").get("risk_tolerance") == "conservative"


def test_no_extraction_without_matching_tool():
    store = _fresh_store()
    store.extract_preferences("user1", "show me 1y data", ["symbol_search"])
    assert store.get_preferences("user1").get("preferred_time_range") is None
