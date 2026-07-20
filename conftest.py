"""Expose legacy test options when pytest is invoked from the repository root."""

from legacy.tests.pytest_plugin import pytest_addoption as _pytest_addoption


def pytest_addoption(parser: object) -> None:
    """Register the legacy integration-test options before test collection."""
    _pytest_addoption(parser)
