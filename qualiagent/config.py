"""Configuration settings for QualiAgent."""

import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # LLM Settings
    llm_provider: Literal["mock", "openai", "gemini", "anthropic"] = Field(
        default="mock",
        description="LLM provider: 'mock' for offline demo/free mode, 'openai', 'gemini', 'anthropic'"
    )
    llm_model: str = Field(default="gpt-4o", description="Model name to invoke")
    llm_temperature: float = Field(default=0.2, description="Sampling temperature")

    # API Keys
    openai_api_key: str = Field(default="", description="OpenAI API key")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Agent Execution Settings
    max_healing_iterations: int = Field(default=3, description="Maximum self-healing attempts")
    sandbox_timeout_seconds: int = Field(default=15, description="Timeout for test execution sandbox")
    enable_rag: bool = Field(default=True, description="Enable RAG retrieval for guidelines")
    rag_top_k: int = Field(default=3, description="Top K guideline chunks to retrieve")

    # Server Settings
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")
    dashboard_port: int = Field(default=8501, description="Streamlit dashboard port")

    # Governance & Telemetry
    log_level: str = Field(default="INFO", description="Logging level")
    enable_audit_log: bool = Field(default=True, description="Save full execution audit trail")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
