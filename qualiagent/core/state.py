"""Core state definitions and Pydantic models for QualiAgent."""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import datetime


class FunctionArg(BaseModel):
    name: str
    type_hint: Optional[str] = "Any"
    default_val: Optional[str] = None


class FunctionSpec(BaseModel):
    name: str
    args: List[FunctionArg] = Field(default_factory=list)
    return_type: Optional[str] = "Any"
    docstring: Optional[str] = None
    raised_exceptions: List[str] = Field(default_factory=list)
    is_async: bool = False
    cyclomatic_complexity: int = 1
    line_start: int = 0
    line_end: int = 0


class ClassSpec(BaseModel):
    name: str
    docstring: Optional[str] = None
    methods: List[FunctionSpec] = Field(default_factory=list)
    attributes: List[str] = Field(default_factory=list)
    line_start: int = 0
    line_end: int = 0


class CodebaseAnalysis(BaseModel):
    file_path: str
    module_name: str
    classes: List[ClassSpec] = Field(default_factory=list)
    functions: List[FunctionSpec] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    total_lines: int = 0
    estimated_complexity: str = "Low"  # Low, Medium, High
    detected_risks: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    test_name: str
    target_function: str
    description: str
    category: Literal["unit", "integration", "edge_case", "exception", "boundary"] = "unit"
    code: str


class TestSuite(BaseModel):
    framework: str = "pytest"
    code: str
    test_cases: List[TestCase] = Field(default_factory=list)


class FailedTestDetail(BaseModel):
    test_name: str
    error_type: str
    stack_trace: str
    line_number: Optional[int] = None


class ExecutionResult(BaseModel):
    success: bool
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    output: str = ""
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    failed_tests: List[FailedTestDetail] = Field(default_factory=list)


class HealingStep(BaseModel):
    iteration: int
    diagnosis: str
    root_cause: str
    proposed_fix: str
    previous_code: str
    new_code: str
    execution_result: Optional[ExecutionResult] = None


class QualityMetrics(BaseModel):
    executability_score: float = Field(
        default=0.0, description="Percentage of generated tests passing successfully (0-100)"
    )
    assertion_density: float = Field(
        default=0.0, description="Average number of assertions per test function"
    )
    estimated_coverage_pct: float = Field(
        default=0.0, description="Estimated branch/function coverage percentage (0-100)"
    )
    mocking_faithfulness_score: float = Field(
        default=0.0, description="Accuracy and cleanliness of external mocks (0-10)"
    )
    edge_case_coverage_score: float = Field(
        default=0.0, description="Coverage of boundary conditions, nulls, and exceptions (0-10)"
    )
    hallucination_penalty: float = Field(
        default=0.0, description="Penalty for testing non-existent methods/attributes (0-10)"
    )
    overall_qe_score: float = Field(
        default=0.0, description="Weighted composite Quality Engineering Score (0-100)"
    )
    grade: str = Field(default="N/A", description="Letter grade: A+, A, B, C, F")


class QualityScorecard(BaseModel):
    metrics: QualityMetrics
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


class AgentTrace(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    agent_name: str
    role: str
    action: str
    status: Literal["success", "in_progress", "failed"] = "success"
    latency_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class QEPipelineOutput(BaseModel):
    source_file: str
    analysis: CodebaseAnalysis
    initial_test_suite: TestSuite
    healing_history: List[HealingStep] = Field(default_factory=list)
    final_test_suite: TestSuite
    final_execution: ExecutionResult
    scorecard: QualityScorecard
    agent_traces: List[AgentTrace] = Field(default_factory=list)
