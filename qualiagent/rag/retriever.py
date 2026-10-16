"""RAG Retriever using FAISS and LocalEmbeddingEngine for testing guidelines."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import faiss
import numpy as np
from qualiagent.rag.embeddings import LocalEmbeddingEngine
from qualiagent.config import settings


class GuidelineRetriever:
    """Retrieves enterprise QE testing guidelines to steer agentic test synthesis."""

    def __init__(self, top_k: int = 3):
        self.top_k = top_k
        self.engine = LocalEmbeddingEngine(dimension=128)
        self.index: Optional[faiss.IndexFlatIP] = None
        self.documents: List[Dict[str, Any]] = []

    def index_guidelines_file(self, file_path: str):
        """Reads a markdown or text guidelines file and indexes sections."""
        path = Path(file_path)
        if not path.exists():
            return

        content = path.read_text(encoding="utf-8")
        # Split by markdown headers
        sections = content.split("## ")
        docs_to_add = []

        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            lines = sec.splitlines()
            title = lines[0].replace("#", "").strip()
            body = "\n".join(lines[1:]).strip()
            if body:
                docs_to_add.append({
                    "title": title,
                    "content": body,
                    "source": str(path.name)
                })

        self.add_documents(docs_to_add)

    def add_documents(self, docs: List[Dict[str, Any]]):
        """Indexes an array of documents."""
        if not docs:
            return

        self.documents.extend(docs)
        corpus = [f"{d['title']}\n{d['content']}" for d in self.documents]

        embeddings = self.engine.fit_and_embed(corpus)
        dim = embeddings.shape[1]

        # Inner Product for cosine similarity on normalized vectors
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves top_k most relevant guideline documents."""
        k = top_k or self.top_k
        if not self.documents or self.index is None:
            return []

        q_vec = self.engine.embed_query(query)
        effective_k = min(k, len(self.documents))
        distances, indices = self.index.search(q_vec, effective_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(dist)
                results.append(doc)

        return results

    def format_as_context(self, query: str) -> str:
        """Formats retrieved guidelines as a prompt context block."""
        results = self.retrieve(query)
        if not results:
            return "No specific guidelines retrieved."

        formatted = ["### Enterprise Testing Guidelines (RAG Context):"]
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r['title']} (Source: {r.get('source', 'internal')}):")
            formatted.append(f"    {r['content']}")

        return "\n\n".join(formatted)
