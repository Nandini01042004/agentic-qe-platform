"""Test Synthesis Agent: generates comprehensive pytest test suites."""

import time
import re
from typing import Tuple, List
from qualiagent.agents.base import BaseAgent
from qualiagent.core.state import CodebaseAnalysis, TestSuite, TestCase, AgentTrace
from qualiagent.core.llm import get_llm_client


class TestSynthesisAgent(BaseAgent):
    """
    Autonomous agent specializing in synthesizing high-coverage pytest test suites.
    Integrates AST structural signatures with enterprise testing guidelines retrieved via RAG.
    """

    def __init__(self):
        super().__init__(
            name="TestSynthesisAgent",
            role="Autonomous Pytest & Quality Synthesis Engineer",
        )
        self.llm = get_llm_client()

    def generate(
        self,
        source_code: str,
        analysis: CodebaseAnalysis,
        rag_guidelines: str = "",
    ) -> Tuple[TestSuite, AgentTrace]:
        """Synthesizes pytest test suite using LLM and context."""
        start_time = time.time()

        system_prompt = (
            "You are an Elite Agentic Quality Engineering (QE) Architect. "
            "Your objective is to generate production-ready, idempotent, robust pytest test suites. "
            "You must ensure complete coverage of: "
            "1. Happy path execution with fixtures. "
            "2. Edge cases and boundary conditions using @pytest.mark.parametrize. "
            "3. Explicit exceptions using `pytest.raises`. "
            "4. Mocks for external network, filesystem, or database I/O. "
            "Output ONLY valid Python code inside triple backticks: ```python ... ```"
        )

        # Prepare summary of functions and classes
        fn_summaries = []
        for fn in analysis.functions:
            fn_summaries.append(
                f"- Function `{fn.name}`(args: {[a.name for a in fn.args]}) -> {fn.return_type}. "
                f"Complexity: {fn.cyclomatic_complexity}. Raises: {fn.raised_exceptions}"
            )
        for cls in analysis.classes:
            fn_summaries.append(
                f"- Class `{cls.name}` with methods: {[m.name for m in cls.methods]}"
            )

        prompt = f"""
Module Name: {analysis.module_name}
Target File: {analysis.file_path}

SOURCE CODE TO TEST:
```python
{source_code}
```

STRUCTURAL ANALYSIS & RISKS:
{chr(10).join(fn_summaries)}
Identified Risks:
{chr(10).join(f"- {r}" for r in analysis.detected_risks) if analysis.detected_risks else "None identified."}

{rag_guidelines}

TASK:
Write a comprehensive pytest test suite named `test_{analysis.module_name}.py`.
Import everything needed from `{analysis.module_name}`.
Generate clean fixtures, thorough assertions, edge-case tests, and exception tests.
Return code in ```python ... ``` format.
"""

        response_text = self.llm.generate(prompt=prompt, system_prompt=system_prompt)
        test_code = self._extract_code(response_text)
        test_cases = self._extract_test_cases(test_code)

        test_suite = TestSuite(
            framework="pytest",
            code=test_code,
            test_cases=test_cases,
        )

        trace = self.record_trace(
            action="synthesize_test_suite",
            start_time=start_time,
            status="success",
            details={
                "tests_generated": len(test_cases),
                "code_chars": len(test_code),
            },
        )

        return test_suite, trace

    def _extract_code(self, response: str) -> str:
        """Extracts python code block from markdown."""
        code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        code_match = re.search(r"```(.*?)```", response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return response.strip()

    def _extract_test_cases(self, code: str) -> List[TestCase]:
        """Extracts individual test function definitions from the generated test code."""
        test_cases = []
        matches = re.finditer(r"def\s+(test_[a-zA-Z0-9_]+)\s*\((.*?)\):", code)
        for m in matches:
            t_name = m.group(1)
            category = "unit"
            if "exception" in t_name or "raise" in t_name:
                category = "exception"
            elif "boundary" in t_name or "edge" in t_name or "invalid" in t_name:
                category = "edge_case"
            elif "integration" in t_name or "workflow" in t_name:
                category = "integration"

            test_cases.append(
                TestCase(
                    test_name=t_name,
                    target_function=t_name.replace("test_", ""),
                    description=f"Automated test case: {t_name}",
                    category=category,
                    code="",
                )
            )
        return test_cases
