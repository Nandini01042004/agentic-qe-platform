"""Integration tests for Agents and Orchestrator."""

import pytest
from qualiagent.agents.analyzer import CodebaseAnalyzerAgent
from qualiagent.agents.orchestrator import QEOrchestrator


SAMPLE_AUTH_CODE = """
class SimpleAuth:
    def __init__(self):
        self.users = {}

    def add_user(self, name: str):
        if not name:
            raise ValueError("Name cannot be empty")
        self.users[name] = True
        return True
"""


def test_analyzer_agent():
    analyzer = CodebaseAnalyzerAgent()
    analysis, trace = analyzer.analyze(SAMPLE_AUTH_CODE, file_path="auth.py")
    assert analysis.module_name == "auth"
    assert len(analysis.classes) == 1
    assert trace.status == "success"


def test_orchestrator_pipeline_end_to_end():
    orchestrator = QEOrchestrator()
    output = orchestrator.run_pipeline(
        source_code=SAMPLE_AUTH_CODE,
        file_path="auth.py",
        module_name="auth",
    )
    assert output.analysis is not None
    assert output.final_test_suite is not None
    assert output.scorecard is not None
    assert len(output.agent_traces) >= 3
