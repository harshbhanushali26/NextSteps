"""
embedder.py
===========
Manages sentence-transformer model loading and embedding generation.

Loads the model once at module level and exposes a single encode function.
Reuses the EmbeddingManager pattern from ai-agent-engine, adapted for
CareerAgent's pure Python, no-Streamlit context.
"""

import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "all-MiniLM-L6-v2"


class EmbeddingManager:
    """
    Manages sentence-transformer model loading and embedding generation.

    Loads the model once at init and reuses across all encode() calls.
    Instantiated once at module level — never reloaded during a session.

    Attributes:
        model_name : str                  — model identifier
        model      : SentenceTransformer  — loaded model instance
    """


    def __init__(self):
        self.model_name = EMBED_MODEL
        self.model = None
        self._load_model()


    def _load_model(self) -> None:
        """
        Load the SentenceTransformer model from HuggingFace.

        Raises:
            RuntimeError: If model loading fails — fail fast at startup.
        """
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model '{self.model_name}': {e}")


    def generate_embeddings(self, texts: List[str]) -> tuple[np.ndarray, tuple, int]:
        """
        Generate dense vector embeddings for a list of text strings.

        Args:
            texts: List of strings to embed — skill names or CV text chunks.

        Returns:
            embeddings : np.ndarray of shape (n_texts, embedding_dim)
            shape      : tuple — (n_texts, embedding_dim) for logging
            count      : number of texts embedded

        Raises:
            ValueError: If model is not loaded or texts list is empty.
        """
        if not self.model:
            raise ValueError("Embedding model not loaded.")

        if not texts:
            raise ValueError("No texts provided for embedding.")

        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        return embeddings, embeddings.shape, len(texts)


    def embed_single(self, text: str) -> list[float]:
        """
        Embed a single text string and return a flat list.

        Convenience method for single queries (e.g. interview answer scoring).
        Returns a plain list instead of np.ndarray for direct ChromaDB usage.

        Args:
            text: Single text string to embed.

        Returns:
            Flat list of floats — the embedding vector.

        Raises:
            ValueError: If model is not loaded.
        """
        if not self.model:
            raise ValueError("Embedding model not loaded.")

        embedding = self.model.encode(text, show_progress_bar=False, convert_to_numpy=True)
        return embedding.tolist()


# Module-level singleton — loaded once, reused across all agents
embedder = EmbeddingManager()