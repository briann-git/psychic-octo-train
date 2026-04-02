"""Package script entrypoints."""

from __future__ import annotations

import pytest


def run_tests() -> int:
    """Run the project's test suite via the Poetry script entrypoint."""
    return pytest.main([
        "betting/tests/",
        "-v",
        "--cov=betting",
        "--cov-report=term-missing",
    ])
