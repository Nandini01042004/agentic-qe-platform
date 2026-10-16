"""Unit tests for FAISS-based Guideline Retriever."""

import pytest
from qualiagent.rag.retriever import GuidelineRetriever


def test_rag_retriever_indexing_and_search():
    retriever = GuidelineRetriever(top_k=2)
    docs = [
        {"title": "Boundary Rules", "content": "Always test zero, negative, and null bounds.", "source": "rules.md"},
        {"title": "Mocking Rules", "content": "Never make real HTTP calls, always patch requests.", "source": "rules.md"},
        {"title": "Fixture Rules", "content": "Use function-scoped fixtures for test isolation.", "source": "rules.md"},
    ]
    retriever.add_documents(docs)

    results = retriever.retrieve("How should I test null bounds and negative values?")
    assert len(results) > 0
    # Top result should be Boundary Rules
    assert "Boundary" in results[0]["title"]
