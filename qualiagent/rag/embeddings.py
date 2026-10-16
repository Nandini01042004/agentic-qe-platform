"""Lightweight embedding representation for RAG and semantic guideline retrieval."""

import numpy as np
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer


class LocalEmbeddingEngine:
    """Fast, deterministic, dependency-light embedding engine using TF-IDF and dense projection."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=500,
            stop_words="english",
        )
        self.is_fitted = False
        # Fixed projection matrix for dimensional consistency
        rng = np.random.RandomState(42)
        self.projection = rng.normal(0, 1, (500, dimension))
        # Normalize projection matrix
        self.projection /= np.linalg.norm(self.projection, axis=1, keepdims=True)

    def fit_and_embed(self, documents: List[str]) -> np.ndarray:
        """Fits vocabulary on documents and returns normalized dense embeddings."""
        if not documents:
            return np.zeros((0, self.dimension), dtype=np.float32)

        tfidf_matrix = self.vectorizer.fit_transform(documents).toarray()
        self.is_fitted = True

        # Pad if features < 500
        n_samples, n_feats = tfidf_matrix.shape
        if n_feats < 500:
            padded = np.zeros((n_samples, 500))
            padded[:, :n_feats] = tfidf_matrix
            tfidf_matrix = padded

        dense = np.dot(tfidf_matrix, self.projection)
        # L2 Normalize
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        dense_norm = (dense / norms).astype(np.float32)
        return dense_norm

    def embed_query(self, query: str) -> np.ndarray:
        """Transforms a query into dense embedding."""
        if not self.is_fitted:
            # Quick fallback fit
            self.fit_and_embed([query, "testing guidelines", "pytest mock assertions"])

        tfidf = self.vectorizer.transform([query]).toarray()
        n_samples, n_feats = tfidf.shape
        if n_feats < 500:
            padded = np.zeros((n_samples, 500))
            padded[:, :n_feats] = tfidf
            tfidf = padded

        dense = np.dot(tfidf, self.projection)
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (dense / norms).astype(np.float32)
