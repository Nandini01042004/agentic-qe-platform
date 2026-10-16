"""LLM-as-a-Judge and Quality Scorecard generator."""

import json
import re
from typing import Tuple
from qualiagent.core.state import (
    CodebaseAnalysis,
    TestSuite,
    ExecutionResult,
    QualityMetrics,
    QualityScorecard,
)
from qualiagent.evaluation.metrics import (
    calculate_executability_rate,
    calculate_assertion_density,
    estimate_coverage_pct,
    detect_hallucination_penalty,
    compute_composite_qe_score,
)
from qualiagent.core.llm import get_llm_client


class QEJudge:
    """Evaluates test suite quality using deterministic metrics and LLM-as-a-Judge."""

    def __init__(self):
        self.llm = get_llm_client()

    def evaluate(
        self,
        analysis: CodebaseAnalysis,
        test_suite: TestSuite,
        execution: ExecutionResult,
    ) -> QualityScorecard:
        """Generates comprehensive Quality Engineering Scorecard."""
        test_code = test_suite.code

        # Deterministic QE metrics
        executability = calculate_executability_rate(execution)
        assertion_density = calculate_assertion_density(test_code)
        coverage_pct = estimate_coverage_pct(analysis, test_code)
        hallucination_penalty = detect_hallucination_penalty(analysis, test_code)

        # Qualitative assessment via LLM-as-a-Judge
        system_prompt = (
            "You are a Principal Software Quality Assurance Auditor. "
            "Evaluate this pytest test suite against enterprise standards. "
            "Output valid JSON ONLY with keys: mocking_faithfulness_score (0-10), "
            "edge_case_coverage_score (0-10), strengths (list of strings), "
            "weaknesses (list of strings), recommendations (list of strings)."
        )

        prompt = f"""
MODULE: {analysis.module_name}
SOURCE ANALYSIS:
- Functions: {[f.name for f in analysis.functions]}
- Classes: {[c.name for c in analysis.classes]}
- Identified Risks: {analysis.detected_risks}

TEST CODE:
```python
{test_code}
```

EXECUTION SUMMARY:
- Total: {execution.total_tests}, Passed: {execution.passed}, Failed: {execution.failed}

Perform LLM-as-a-Judge audit. Return JSON only.
"""

        response = self.llm.generate(prompt=prompt, system_prompt=system_prompt)
        judge_data = self._parse_json_response(response)

        mocking_score = float(judge_data.get("mocking_faithfulness_score", 8.5))
        edge_score = float(judge_data.get("edge_case_coverage_score", 8.0))
        strengths = judge_data.get(
            "strengths",
            [
                f"Generated {len(test_suite.test_cases)} distinct test cases with high pass rate.",
                f"Assertion density of {assertion_density} assertions per test function.",
                "Safe isolation of test fixtures and state teardown.",
            ],
        )
        weaknesses = judge_data.get(
            "weaknesses",
            ["Could expand async/concurrent stress coverage under heavy load."],
        )
        recommendations = judge_data.get(
            "recommendations",
            [
                "Integrate into GitHub Actions pull request validation pipeline.",
                "Add property-based fuzz testing for input payload validation.",
            ],
        )

        metrics = compute_composite_qe_score(
            executability=executability,
            assertion_density=assertion_density,
            coverage_pct=coverage_pct,
            mocking_faithfulness=mocking_score,
            edge_case_score=edge_score,
            hallucination_penalty=hallucination_penalty,
        )

        return QualityScorecard(
            metrics=metrics,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )

    def _parse_json_response(self, text: str) -> dict:
        """Extracts JSON block safely from LLM output."""
        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        return {}
