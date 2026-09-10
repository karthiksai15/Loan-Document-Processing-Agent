"""
Policy Embedding Service (Phase 14)

Provides local SentenceTransformers embedding generation for policy chunks
and user query strings. Normalizes vectors for Cosine Similarity indexing.
"""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import logger


class PolicyEmbeddingService:
    _model_instance: SentenceTransformer = None
    _model_name: str = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazily loads and returns the configured SentenceTransformer model instance."""
        target_model = settings.POLICY_EMBEDDING_MODEL
        if cls._model_instance is None or cls._model_name != target_model:
            logger.info(f"Loading local SentenceTransformer model: {target_model}")
            try:
                # First try loading with local_files_only to prevent network retries
                cls._model_instance = SentenceTransformer(target_model, local_files_only=True)
            except Exception:
                # Fallback to standard loading if model not yet cached locally
                cls._model_instance = SentenceTransformer(target_model)
            cls._model_name = target_model
        return cls._model_instance

    @classmethod
    def embed_text(cls, text: str) -> np.ndarray:
        """
        Embeds a single query or text string into a normalized 1D float32 numpy array.
        """
        model = cls.get_model()
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)

    @classmethod
    def embed_batch(cls, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of texts into a 2D float32 numpy array of shape (N, dimension).
        """
        if not texts:
            dim = cls.get_embedding_dimension()
            return np.empty((0, dim), dtype=np.float32)

        model = cls.get_model()
        vecs = model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)

    @classmethod
    def get_model_name(cls) -> str:
        """Returns configured embedding model name."""
        return settings.POLICY_EMBEDDING_MODEL

    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Returns the embedding vector dimension for the active model (e.g. 384 for all-MiniLM-L6-v2)."""
        model = cls.get_model()
        if hasattr(model, "get_embedding_dimension"):
            dim = model.get_embedding_dimension()
        else:
            dim = model.get_sentence_embedding_dimension()
        return dim if dim is not None else 384
