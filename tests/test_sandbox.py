"""Unit tests for the Test Sandbox execution engine."""

import pytest
from qualiagent.core.sandbox import TestSandbox


def test_sandbox_runs_passing_tests():
    sandbox = TestSandbox(timeout_seconds=10)
    source = "def add(a, b): return a + b\n"
    test_code = "from target_module import add\ndef test_add(): assert add(2, 3) == 5\n"

    result = sandbox.execute_tests(source, test_code, module_name="target_module")
    assert result.success is True
    assert result.passed == 1
    assert result.failed == 0


def test_sandbox_captures_failing_tests():
    sandbox = TestSandbox(timeout_seconds=10)
    source = "def sub(a, b): return a - b\n"
    test_code = "from target_module import sub\ndef test_sub(): assert sub(5, 2) == 10\n"

    result = sandbox.execute_tests(source, test_code, module_name="target_module")
    assert result.success is False
    assert result.failed == 1
    assert len(result.failed_tests) > 0
    assert "AssertionError" in result.failed_tests[0].error_type
