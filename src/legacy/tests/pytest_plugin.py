"""Shared registration for legacy integration-test command-line options."""


_OPTIONS_REGISTERED = False


def pytest_addoption(parser: object) -> None:
    """Add the options consumed by the legacy report-quality test."""
    global _OPTIONS_REGISTERED
    if _OPTIONS_REGISTERED:
        return
    parser.addoption("--research-agent", action="store")  # type: ignore[attr-defined]
    parser.addoption("--search-api", action="store")  # type: ignore[attr-defined]
    parser.addoption("--eval-model", action="store")  # type: ignore[attr-defined]
    parser.addoption("--supervisor-model", action="store")  # type: ignore[attr-defined]
    parser.addoption("--researcher-model", action="store")  # type: ignore[attr-defined]
    parser.addoption("--planner-provider", action="store")  # type: ignore[attr-defined]
    parser.addoption("--planner-model", action="store")  # type: ignore[attr-defined]
    parser.addoption("--writer-provider", action="store")  # type: ignore[attr-defined]
    parser.addoption("--writer-model", action="store")  # type: ignore[attr-defined]
    parser.addoption("--max-search-depth", action="store")  # type: ignore[attr-defined]
    _OPTIONS_REGISTERED = True
