"""Base Agent definition with telemetry, tracing, and execution hooks."""

import time
from typing import Dict, Any, Optional
from qualiagent.core.state import AgentTrace


class BaseAgent:
    """Base class for all specialized agents in the QualiAgent ecosystem."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def record_trace(
        self,
        action: str,
        start_time: float,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> AgentTrace:
        """Records telemetry and latency for an agent action."""
        latency_ms = (time.time() - start_time) * 1000.0
        return AgentTrace(
            agent_name=self.name,
            role=self.role,
            action=action,
            status="success" if status == "success" else "failed",
            latency_ms=round(latency_ms, 2),
            details=details or {},
        )
