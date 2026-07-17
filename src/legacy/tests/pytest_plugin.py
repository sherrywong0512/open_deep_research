"""Shared configuration for local and opt-in LangSmith legacy tests."""

import pytest  # noqa: I001


_OPTIONS_REGISTERED = False
_CONFIGURED = False
_COLLECTION_SELECTION_APPLIED = False


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add options used by the legacy LangSmith integration test."""
    global _OPTIONS_REGISTERED
    if _OPTIONS_REGISTERED:
        return

    parser.addoption("--run-langsmith", action="store_true", default=False)
    parser.addoption("--research-agent", action="store")
    parser.addoption("--search-api", action="store")
    parser.addoption("--eval-model", action="store")
    parser.addoption("--supervisor-model", action="store")
    parser.addoption("--researcher-model", action="store")
    parser.addoption("--planner-provider", action="store")
    parser.addoption("--planner-model", action="store")
    parser.addoption("--writer-provider", action="store")
    parser.addoption("--writer-model", action="store")
    parser.addoption("--max-search-depth", action="store")
    _OPTIONS_REGISTERED = True


def pytest_configure(config: pytest.Config) -> None:
    """Register the external integration marker."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    config.addinivalue_line(
        "markers",
        "langsmith: requires configured remote models, search, and LangSmith access",
    )
    _CONFIGURED = True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip external LangSmith tests unless a caller explicitly opts in."""
    global _COLLECTION_SELECTION_APPLIED
    if _COLLECTION_SELECTION_APPLIED:
        return
    if config.getoption("--run-langsmith"):
        return

    skip_langsmith = pytest.mark.skip(
        reason="requires --run-langsmith plus configured remote model, search, and LangSmith access"
    )
    for item in items:
        if "langsmith" in item.keywords:
            item.add_marker(skip_langsmith)
    _COLLECTION_SELECTION_APPLIED = True
