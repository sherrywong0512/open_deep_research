"""Load shared pytest behavior from the legacy test package."""

from legacy.tests.pytest_plugin import pytest_addoption as _pytest_addoption
from legacy.tests.pytest_plugin import (
    pytest_collection_modifyitems as _pytest_collection_modifyitems,
)
from legacy.tests.pytest_plugin import pytest_configure as _pytest_configure


def pytest_addoption(parser: object) -> None:
    """Forward legacy CLI option registration."""
    _pytest_addoption(parser)  # type: ignore[arg-type]


def pytest_configure(config: object) -> None:
    """Forward legacy pytest configuration."""
    _pytest_configure(config)  # type: ignore[arg-type]


def pytest_collection_modifyitems(config: object, items: object) -> None:
    """Forward legacy integration-test selection."""
    _pytest_collection_modifyitems(config, items)  # type: ignore[arg-type]
