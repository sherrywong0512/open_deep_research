"""Expose shared legacy test options when this directory is the test root."""

from legacy.tests.pytest_plugin import pytest_addoption as _pytest_addoption


def pytest_addoption(parser: object) -> None:
    """Register legacy integration-test options."""
    _pytest_addoption(parser)
