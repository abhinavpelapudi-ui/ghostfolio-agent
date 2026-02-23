"""Eval test configuration — skip if LangSmith API key is not set."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    if not os.environ.get("LANGCHAIN_API_KEY"):
        skip = pytest.mark.skip(reason="LANGCHAIN_API_KEY not set — skipping evals")
        for item in items:
            item.add_marker(skip)
