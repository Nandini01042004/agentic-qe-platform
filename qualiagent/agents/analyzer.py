"""Analyzer Agent: extracts AST structure, interface signatures, and risk metrics."""

import time
from typing import Tuple
from qualiagent.agents.base import BaseAgent
from qualiagent.core.ast_parser import analyze_python_source
from qualiagent.core.state import CodebaseAnalysis, AgentTrace


class CodebaseAnalyzerAgent(BaseAgent):
    """
    Specialized agent responsible for deep static inspection of source code,
    identifying public API contracts, cyclomatic complexity hotspots, and error branches.
    """

    def __init__(self):
        super().__init__(
            name="CodebaseAnalyzerAgent",
            role="AST & API Contract Structural Analyst",
        )

    def analyze(self, source_code: str, file_path: str = "source.py") -> Tuple[CodebaseAnalysis, AgentTrace]:
        """Performs static AST parsing, complexity scoring, and risk discovery."""
        start_time = time.time()
        analysis = analyze_python_source(source_code, file_path=file_path)

        details = {
            "file": file_path,
            "classes_found": len(analysis.classes),
            "functions_found": len(analysis.functions),
            "total_lines": analysis.total_lines,
            "complexity": analysis.estimated_complexity,
            "risks_identified": len(analysis.detected_risks),
        }

        trace = self.record_trace(
            action="ast_code_analysis",
            start_time=start_time,
            status="success",
            details=details,
        )

        return analysis, trace
