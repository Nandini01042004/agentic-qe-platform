"""Programmatic Quality Engineering (QE) Metrics calculation."""

import re
from typing import Dict, Any, List
from qualiagent.core.state import (
    CodebaseAnalysis,
    ExecutionResult,
    QualityMetrics,
)


def calculate_executability_rate(execution: ExecutionResult) -> float:
    """Calculates percentage of tests successfully passing in sandbox."""
    if execution.total_tests == 0:
        return 0.0
    return round((execution.passed / execution.total_tests) * 100.0, 1)


def calculate_assertion_density(test_code: str) -> float:
    """Calculates the average number of assertions per test function."""
    test_functions = re.findall(r"def\s+(test_[a-zA-Z0-9_]+)\s*\(", test_code)
    if not test_functions:
        return 0.0

    # Count assert statements, pytest.raises, and mock asserts
    assert_count = len(re.findall(r"\bassert\b", test_code))
    raises_count = len(re.findall(r"pytest\.raises", test_code))
    mock_assert_count = len(re.findall(r"assert_called|assert_has_calls", test_code))

    total_assertions = assert_count + raises_count + mock_assert_count
    return round(total_assertions / len(test_functions), 2)


def estimate_coverage_pct(analysis: CodebaseAnalysis, test_code: str) -> float:
    """
    Estimates code coverage percentage based on test calls to declared functions & methods.
    """
    all_targets = set()
    for fn in analysis.functions:
        all_targets.add(fn.name)
    for cls in analysis.classes:
        all_targets.add(cls.name)
        for m in cls.methods:
            all_targets.add(m.name)

    if not all_targets:
        return 100.0

    matched = 0
    for target in all_targets:
        if re.search(rf"\b{re.escape(target)}\b", test_code):
            matched += 1

    return round((matched / len(all_targets)) * 100.0, 1)


def detect_hallucination_penalty(analysis: CodebaseAnalysis, test_code: str) -> float:
    """
    Detects if the generated test suite attempts to invoke non-existent methods
    on the declared classes (hallucination penalty).
    """
    known_methods = set()
    for cls in analysis.classes:
        for m in cls.methods:
            known_methods.add(m.name)

    # If there are no classes with methods, penalty is zero
    if not known_methods:
        return 0.0

    # Check for calls like service.non_existent_method()
    # Simple heuristic: find attribute accesses on common instance names
    potential_calls = re.findall(r"\.(?:[a-zA-Z0-9_]+)\(", test_code)
    non_existent = 0
    total_calls = 0

    for call in potential_calls:
        method_name = call[1:-1]
        # Ignore standard python / pytest builtins
        if method_name in ("raises", "fixture", "parametrize", "append", "get", "set", "keys", "values", "items"):
            continue
        total_calls += 1
        # If method_name is not known in any class methods or builtins
        # Check against known
        if method_name not in known_methods:
            # We don't penalize too aggressively for mock helpers
            if not method_name.startswith("mock_") and not method_name.startswith("assert_"):
                non_existent += 1

    if total_calls == 0:
        return 0.0

    ratio = non_existent / total_calls
    return round(min(10.0, ratio * 10.0), 1)


def compute_composite_qe_score(
    executability: float,
    assertion_density: float,
    coverage_pct: float,
    mocking_faithfulness: float,
    edge_case_score: float,
    hallucination_penalty: float,
) -> QualityMetrics:
    """
    Calculates weighted composite Quality Engineering score (0-100) and letter grade.
    Weights:
    - Executability: 35%
    - Coverage Estimate: 25%
    - Assertion Density: 15% (normalized to 5.0 assertions/test)
    - Edge Case Coverage: 15% (scaled 0-10)
    - Mocking Faithfulness: 10% (scaled 0-10)
    - Minus Hallucination Penalty
    """
    norm_assertion = min(100.0, (assertion_density / 4.0) * 100.0)
    norm_edge = (edge_case_score / 10.0) * 100.0
    norm_mock = (mocking_faithfulness / 10.0) * 100.0

    raw_score = (
        (0.35 * executability)
        + (0.25 * coverage_pct)
        + (0.15 * norm_assertion)
        + (0.15 * norm_edge)
        + (0.10 * norm_mock)
        - (hallucination_penalty * 2.0)
    )

    final_score = max(0.0, min(100.0, round(raw_score, 1)))

    if final_score >= 90.0:
        grade = "A+"
    elif final_score >= 80.0:
        grade = "A"
    elif final_score >= 70.0:
        grade = "B"
    elif final_score >= 60.0:
        grade = "C"
    else:
        grade = "F"

    return QualityMetrics(
        executability_score=executability,
        assertion_density=assertion_density,
        estimated_coverage_pct=coverage_pct,
        mocking_faithfulness_score=mocking_faithfulness,
        edge_case_coverage_score=edge_case_score,
        hallucination_penalty=hallucination_penalty,
        overall_qe_score=final_score,
        grade=grade,
    )
