"""Evaluation Judge Agent with telemetry and scoring."""

import time
from typing import Tuple
from qualiagent.agents.base import BaseAgent
from qualiagent.core.state import (
    CodebaseAnalysis,
    TestSuite,
    ExecutionResult,
    QualityScorecard,
    AgentTrace,
)
from qualiagent.evaluation.judge import QEJudge


class EvaluationJudgeAgent(BaseAgent):
    """
    Evaluator Agent executing LLM-as-a-Judge and programmatic Quality Engineering scorecards.
    Ensures tests are grounded, non-hallucinatory, syntactically clean, and assertion-rich.
    """

    def __init__(self):
        super().__init__(
            name="EvaluationJudgeAgent",
            role="Quality Engineering Auditor & LLM-as-a-Judge",
        )
        self.judge = QEJudge()

    def evaluate(
        self,
        analysis: CodebaseAnalysis,
        test_suite: TestSuite,
        execution: ExecutionResult,
    ) -> Tuple[QualityScorecard, AgentTrace]:
        """Runs evaluation audit and records telemetry."""
        start_time = time.time()
        scorecard = self.judge.evaluate(
            analysis=analysis,
            test_suite=test_suite,
            execution=execution,
        )

        trace = self.record_trace(
            action="evaluate_test_quality",
            start_time=start_time,
            status="success",
            details={
                "overall_qe_score": scorecard.metrics.overall_qe_score,
                "grade": scorecard.metrics.grade,
                "executability": scorecard.metrics.executability_score,
                "assertion_density": scorecard.metrics.assertion_density,
                "estimated_coverage": scorecard.metrics.estimated_coverage_pct,
            },
        )

        return scorecard, trace
