"""Multi-Agent Orchestrator: coordinates analysis, synthesis, sandboxed execution, self-healing, and evaluation."""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from qualiagent.core.state import (
    CodebaseAnalysis,
    TestSuite,
    ExecutionResult,
    HealingStep,
    QualityScorecard,
    AgentTrace,
    QEPipelineOutput,
)
from qualiagent.agents.analyzer import CodebaseAnalyzerAgent
from qualiagent.agents.generator import TestSynthesisAgent
from qualiagent.agents.healer import SelfHealingAgent
from qualiagent.agents.evaluator import EvaluationJudgeAgent
from qualiagent.core.sandbox import TestSandbox
from qualiagent.rag.retriever import GuidelineRetriever
from qualiagent.config import settings


class QEOrchestrator:
    """
    Supervisor Agent orchestrating the end-to-end Autonomous Quality Engineering pipeline:
    1. Static AST Code Analysis & Risk Extraction
    2. RAG Guideline Retrieval (Enterprise Standards)
    3. LLM Test Synthesis (pytest)
    4. Sandboxed Isolated Execution
    5. Self-Healing Feedback Loop (if failures detected)
    6. LLM-as-a-Judge Evaluation & Executive Scorecard
    """

    def __init__(
        self,
        guidelines_path: Optional[str] = None,
        max_healing_iterations: Optional[int] = None,
    ):
        self.analyzer = CodebaseAnalyzerAgent()
        self.generator = TestSynthesisAgent()
        self.healer = SelfHealingAgent(max_iterations=max_healing_iterations)
        self.evaluator = EvaluationJudgeAgent()
        self.sandbox = TestSandbox()

        # Initialize RAG retriever
        self.retriever = GuidelineRetriever(top_k=settings.rag_top_k)
        if guidelines_path and Path(guidelines_path).exists():
            self.retriever.index_guidelines_file(guidelines_path)
        else:
            # Default internal enterprise guidelines
            self._seed_default_guidelines()

    def _seed_default_guidelines(self):
        """Seeds standard enterprise testing rules into RAG index."""
        default_rules = [
            {
                "title": "Idempotency and Fixture Isolation",
                "content": "Every test must isolate its state. Never rely on shared global state. Always use pytest fixtures for setting up instances and tearing them down.",
                "source": "Enterprise_Standard_QE_Rules",
            },
            {
                "title": "Boundary Testing and Edge Conditions",
                "content": "Always test edge conditions: empty strings, zero, negative integers, null/None values, invalid types, and max boundary numbers using @pytest.mark.parametrize.",
                "source": "Enterprise_Standard_QE_Rules",
            },
            {
                "title": "Explicit Exception Testing",
                "content": "Functions that raise explicit exceptions must be tested with pytest.raises(ExpectedError) and assert the message or error attributes.",
                "source": "Enterprise_Standard_QE_Rules",
            },
            {
                "title": "Mocking External I/O",
                "content": "Do not make real network calls, database queries, or write to arbitrary system paths. Use unittest.mock or pytest monkeypatch.",
                "source": "Enterprise_Standard_QE_Rules",
            },
        ]
        self.retriever.add_documents(default_rules)

    def run_pipeline(
        self,
        source_code: str,
        file_path: str = "source.py",
        module_name: Optional[str] = None,
    ) -> QEPipelineOutput:
        """Executes the complete multi-agent quality engineering workflow."""
        all_traces: List[AgentTrace] = []

        # 1. ANALYZE CODEBASE
        analysis, trace_analyze = self.analyzer.analyze(source_code, file_path=file_path)
        all_traces.append(trace_analyze)

        effective_module_name = module_name or analysis.module_name

        # 2. RAG GUIDELINE RETRIEVAL
        rag_query = f"{analysis.module_name} {' '.join(analysis.detected_risks)}"
        rag_context = self.retriever.format_as_context(rag_query)

        # 3. TEST SYNTHESIS
        initial_test_suite, trace_gen = self.generator.generate(
            source_code=source_code,
            analysis=analysis,
            rag_guidelines=rag_context,
        )
        all_traces.append(trace_gen)

        # 4. SANDBOX EXECUTION
        initial_execution = self.sandbox.execute_tests(
            source_code=source_code,
            test_code=initial_test_suite.code,
            module_name=effective_module_name,
        )

        # 5. SELF-HEALING REFLECTION LOOP
        if not initial_execution.success:
            final_test_suite, final_execution, healing_history, trace_heal = self.healer.heal_test_suite(
                source_code=source_code,
                initial_test_suite=initial_test_suite,
                initial_execution=initial_execution,
                module_name=effective_module_name,
            )
            all_traces.append(trace_heal)
        else:
            final_test_suite = initial_test_suite
            final_execution = initial_execution
            healing_history = []

        # 6. EVALUATION & LLM-AS-A-JUDGE SCORECARD
        scorecard, trace_eval = self.evaluator.evaluate(
            analysis=analysis,
            test_suite=final_test_suite,
            execution=final_execution,
        )
        all_traces.append(trace_eval)

        return QEPipelineOutput(
            source_file=file_path,
            analysis=analysis,
            initial_test_suite=initial_test_suite,
            healing_history=healing_history,
            final_test_suite=final_test_suite,
            final_execution=final_execution,
            scorecard=scorecard,
            agent_traces=all_traces,
        )
