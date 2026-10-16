"""Enterprise FastAPI Service for QualiAgent."""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from qualiagent.core.state import (
    CodebaseAnalysis,
    TestSuite,
    ExecutionResult,
    QualityScorecard,
    QEPipelineOutput,
)
from qualiagent.agents.orchestrator import QEOrchestrator
from qualiagent.agents.analyzer import CodebaseAnalyzerAgent
from qualiagent.agents.generator import TestSynthesisAgent
from qualiagent.agents.healer import SelfHealingAgent
from qualiagent.agents.evaluator import EvaluationJudgeAgent
from qualiagent.core.sandbox import TestSandbox
from qualiagent.rag.retriever import GuidelineRetriever
from qualiagent.config import settings

app = FastAPI(
    title="QualiAgent Enterprise QE API",
    version="1.0.0",
    description="Multi-Agent Quality Engineering & AI-Assisted Delivery Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared orchestrator instance
orchestrator = QEOrchestrator(
    guidelines_path="examples/test_guidelines/enterprise_testing_rules.md"
)


class CodeInputRequest(BaseModel):
    source_code: str = Field(..., description="Python source code to analyze and test")
    module_name: Optional[str] = Field("target_module", description="Module import identifier")
    file_path: Optional[str] = Field("source.py", description="Relative file path")


class TestExecutionRequest(BaseModel):
    source_code: str
    test_code: str
    module_name: Optional[str] = "target_module"


class HealRequest(BaseModel):
    source_code: str
    test_code: str
    failure_output: str
    module_name: Optional[str] = "target_module"


@app.get("/")
def root():
    return {
        "service": "QualiAgent Enterprise Platform",
        "version": "1.0.0",
        "status": "online",
        "active_roles": [
            "Agentic QE Engineer",
            "Agentic AI Engineer",
            "Enterprise AI Engineer",
        ],
        "active_agents": [
            "CodebaseAnalyzerAgent",
            "TestSynthesisAgent",
            "SelfHealingAgent",
            "EvaluationJudgeAgent",
            "QEOrchestrator",
        ],
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "provider": settings.llm_provider}


@app.post("/api/v1/analyze", response_model=CodebaseAnalysis)
def analyze_code(req: CodeInputRequest):
    """Analyzes AST interfaces, complexity, and detected risks in source code."""
    analyzer = CodebaseAnalyzerAgent()
    analysis, _ = analyzer.analyze(req.source_code, file_path=req.file_path or "source.py")
    return analysis


@app.post("/api/v1/generate-tests", response_model=TestSuite)
def generate_tests(req: CodeInputRequest):
    """Generates an initial pytest test suite grounded in AST & RAG rules."""
    analyzer = CodebaseAnalyzerAgent()
    analysis, _ = analyzer.analyze(req.source_code, file_path=req.file_path or "source.py")

    rag_context = orchestrator.retriever.format_as_context(req.source_code)
    generator = TestSynthesisAgent()
    test_suite, _ = generator.generate(req.source_code, analysis, rag_guidelines=rag_context)
    return test_suite


@app.post("/api/v1/execute-tests", response_model=ExecutionResult)
def execute_tests(req: TestExecutionRequest):
    """Executes test code against source code inside an isolated sandbox."""
    sandbox = TestSandbox()
    result = sandbox.execute_tests(
        source_code=req.source_code,
        test_code=req.test_code,
        module_name=req.module_name or "target_module",
    )
    return result


@app.post("/api/v1/pipeline", response_model=QEPipelineOutput)
def run_full_pipeline(req: CodeInputRequest):
    """Runs complete end-to-end multi-agent quality engineering pipeline."""
    try:
        output = orchestrator.run_pipeline(
            source_code=req.source_code,
            file_path=req.file_path or "source.py",
            module_name=req.module_name,
        )
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
