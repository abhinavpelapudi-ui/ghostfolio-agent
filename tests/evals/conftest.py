"""Eval test configuration.

Golden sets and labeled scenarios run deterministically (no API keys needed).
LLM judge tests skip automatically if GROQ_API_KEY is not set (via pytestmark).
"""
