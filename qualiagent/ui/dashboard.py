"""Streamlit Interactive Web Dashboard for QualiAgent Enterprise."""

import streamlit as st
import json
import time
from pathlib import Path

from qualiagent.agents.orchestrator import QEOrchestrator
from qualiagent.agents.analyzer import CodebaseAnalyzerAgent
from qualiagent.core.state import QEPipelineOutput

st.set_page_config(
    page_title="QualiAgent Enterprise | Autonomous QE Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished enterprise look
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .score-badge {
        font-size: 2.4rem;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

# Sample Code Loader
SAMPLE_DIR = Path("examples/sample_code")
SAMPLE_FILES = {
    "Authentication Service (auth_service.py)": SAMPLE_DIR / "auth_service.py",
    "Payment Gateway (payment_gateway.py)": SAMPLE_DIR / "payment_gateway.py",
    "Data Pipeline ETL (data_pipeline.py)": SAMPLE_DIR / "data_pipeline.py",
}

# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
st.sidebar.title("QualiAgent Controls")
st.sidebar.markdown("**Platform**: Autonomous Quality Engineering")

selected_sample_name = st.sidebar.selectbox(
    "Select Target Service:",
    list(SAMPLE_FILES.keys()) + ["Custom Code Input"]
)

# Load selected code
if selected_sample_name != "Custom Code Input":
    target_path = SAMPLE_FILES[selected_sample_name]
    if target_path.exists():
        default_code = target_path.read_text(encoding="utf-8")
        default_module = target_path.stem
    else:
        default_code = "# Code not found"
        default_module = "target_module"
else:
    default_code = 'def calculate_discount(price: float, discount_pct: float) -> float:\n    if price < 0 or discount_pct < 0 or discount_pct > 100:\n        raise ValueError("Invalid price or discount")\n    return round(price * (1 - discount_pct / 100), 2)\n'
    default_module = "discount_service"

st.sidebar.divider()
st.sidebar.subheader("Engine Configuration")
llm_mode = st.sidebar.radio("LLM Execution Mode:", ["Offline Intelligent Mode (Free / Demo)", "Live Cloud API (OpenAI / Gemini)"])
max_heal = st.sidebar.slider("Max Self-Healing Iterations:", 1, 5, 3)
enable_rag = st.sidebar.checkbox("Enable Enterprise RAG Guidelines", value=True)

# Main Header
st.markdown('<div class="main-title">🛡️ QualiAgent Enterprise QE Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Agent Quality Engineering, Self-Healing Sandboxes, RAG-Grounded Test Synthesis & LLM-as-a-Judge Scorecards</div>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Autonomous QE Studio",
    "🩺 Self-Healing Sandbox",
    "📊 Quality Scorecard & Judge",
    "📚 Enterprise RAG Guidelines"
])

with tab1:
    col_code, col_test = st.columns(2)

    with col_code:
        st.subheader("Source Code Under Test")
        source_code_input = st.text_area(
            "Python Source Code:",
            value=default_code,
            height=380,
            key="source_code_area",
        )
        module_name_input = st.text_input("Module Name:", value=default_module)

    with col_test:
        st.subheader("Generated Pytest Suite")
        test_container = st.empty()
        test_container.info("Click 'Execute Autonomous QE Pipeline' below to launch the agent workflow.")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        run_btn = st.button("⚡ Run Autonomous QE Engine", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("🤖 Multi-Agent System Active: Analyzing AST -> Querying RAG -> Synthesizing Tests -> Executing Sandbox -> Evaluating..."):
            guidelines_file = "examples/test_guidelines/enterprise_testing_rules.md" if enable_rag else None
            orchestrator = QEOrchestrator(
                guidelines_path=guidelines_file,
                max_healing_iterations=max_heal,
            )

            start_t = time.time()
            output: QEPipelineOutput = orchestrator.run_pipeline(
                source_code=source_code_input,
                file_path=f"{module_name_input}.py",
                module_name=module_name_input,
            )
            duration = round(time.time() - start_t, 2)

            st.session_state["pipeline_output"] = output
            st.success(f"✓ Pipeline execution completed in {duration}s!")

    if "pipeline_output" in st.session_state:
        out: QEPipelineOutput = st.session_state["pipeline_output"]
        test_container.code(out.final_test_suite.code, language="python")

        # Agent execution timeline
        st.divider()
        st.subheader("Multi-Agent Execution Audit Trail")
        trace_cols = st.columns(len(out.agent_traces))
        for i, tr in enumerate(out.agent_traces):
            with trace_cols[i]:
                st.markdown(f"**{tr.agent_name}**")
                st.caption(f"Role: {tr.role}")
                st.success(f"✓ {tr.action} ({tr.latency_ms}ms)")

with tab2:
    st.subheader("🩺 Self-Healing Diagnostics & Sandboxed Reflection")
    if "pipeline_output" in st.session_state:
        out: QEPipelineOutput = st.session_state["pipeline_output"]
        if not out.healing_history:
            st.info("No healing required: Initial test suite passed execution on first iteration with 100% success!")
        else:
            for step in out.healing_history:
                with st.expander(f"Healing Iteration {step.iteration} — Root Cause Diagnosis", expanded=True):
                    st.markdown(f"**Root Cause**: `{step.root_cause}`")
                    st.markdown(f"**Proposed Fix**: {step.proposed_fix}")
                    col_prev, col_new = st.columns(2)
                    with col_prev:
                        st.caption("Failing Code")
                        st.code(step.previous_code, language="python")
                    with col_new:
                        st.caption("Healed Patch")
                        st.code(step.new_code, language="python")
    else:
        st.info("Run the pipeline in Tab 1 to observe self-healing telemetry.")

with tab3:
    st.subheader("📊 Enterprise Quality Scorecard (LLM-as-a-Judge)")
    if "pipeline_output" in st.session_state:
        out: QEPipelineOutput = st.session_state["pipeline_output"]
        metrics = out.scorecard.metrics

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall QE Score", f"{metrics.overall_qe_score} / 100", f"Grade: {metrics.grade}")
        c2.metric("Executability Rate", f"{metrics.executability_score}%", f"{out.final_execution.passed}/{out.final_execution.total_tests} passed")
        c3.metric("Assertion Density", f"{metrics.assertion_density}", "asserts / test")
        c4.metric("Estimated Coverage", f"{metrics.estimated_coverage_pct}%", "interface methods")

        st.divider()
        col_s, col_w = st.columns(2)
        with col_s:
            st.markdown("#### 🌟 Key Strengths")
            for s in out.scorecard.strengths:
                st.markdown(f"- {s}")
        with col_w:
            st.markdown("#### ⚠️ Identified Quality Gaps")
            for w in out.scorecard.weaknesses:
                st.markdown(f"- {w}")

        st.markdown("#### 💡 CI/CD Delivery Recommendations")
        for r in out.scorecard.recommendations:
            st.markdown(f"- {r}")
    else:
        st.info("Run the pipeline in Tab 1 to generate Quality Scorecard.")

with tab4:
    st.subheader("📚 Enterprise Testing Standards Knowledgebase (RAG)")
    st.markdown("These enterprise guidelines are indexed into FAISS and injected into agent prompts to eliminate hallucinations.")
    guideline_path = Path("examples/test_guidelines/enterprise_testing_rules.md")
    if guideline_path.exists():
        st.markdown(guideline_path.read_text(encoding="utf-8"))
    else:
        st.warning("Guidelines file not found.")
