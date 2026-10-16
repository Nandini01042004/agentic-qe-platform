"""Unit tests for Evaluation Metrics and Judge."""

import pytest
from qualiagent.core.state import CodebaseAnalysis, ExecutionResult
from qualiagent.evaluation.metrics import (
    calculate_executability_rate,
    calculate_assertion_density,
    estimate_coverage_pct,
    compute_composite_qe_score,
)


def test_calculate_executability_rate():
    exec_res = ExecutionResult(success=True, total_tests=10, passed=8, failed=2)
    assert calculate_executability_rate(exec_res) == 80.0


def test_calculate_assertion_density():
    code = """
def test_one():
    assert 1 == 1
    assert 2 == 2

def test_two():
    assert "a" in "abc"
"""
    density = calculate_assertion_density(code)
    assert density == 1.5


def test_composite_score_grade():
    metrics = compute_composite_qe_score(
        executability=95.0,
        assertion_density=3.5,
        coverage_pct=90.0,
        mocking_faithfulness=9.0,
        edge_case_score=8.5,
        hallucination_penalty=0.0,
    )
    assert metrics.overall_qe_score >= 85.0
    assert metrics.grade in ("A+", "A")
