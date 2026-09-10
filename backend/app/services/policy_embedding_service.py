"""
Policy Embedding Service (Phase 14 / Architecture Fix)

Provides hosted Google Gemini embeddings for policy chunks and user query strings.
Replaces heavy local SentenceTransformer/PyTorch dependencies to run within
Render's 512 MB memory limit.
Normalizes vectors for Cosine Similarity indexing via FAISS IndexFlatIP.
"""

import os
import time
import json
import hashlib
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings
from app.core.logging import logger


def _normalize_vector(vec: np.ndarray) -> np.ndarray:
    """Normalizes vector to unit length (L2 norm) for cosine similarity."""
    norm = np.linalg.norm(vec, axis=-1, keepdims=True)
    norm = np.where(norm > 0, norm, 1.0)
    return (vec / norm).astype(np.float32)


def _text_hash(text: str) -> str:
    """Generates a stable SHA256 key for caching text embeddings."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _generate_fallback_vector(text: str, dimension: int = 384) -> np.ndarray:
    """
    Generates a deterministic pseudo-embedding seeded by text hash.
    Used exclusively as a safe offline fallback when GEMINI_API_KEY is missing
    or network access is blocked in local testing environments.
    """
    seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)
    vec = rng.randn(dimension).astype(np.float32)
    return _normalize_vector(vec)


class PolicyEmbeddingService:
    _client = None
    _cache: Dict[str, List[float]] = {}
    _cache_loaded: bool = False
    _dimension: int = 384

    @classmethod
    def _get_cache_path(cls) -> str:
        return os.path.join(settings.VECTOR_STORE_DIR, "policy_embeddings_cache.json")

    @classmethod
    def _load_cache(cls):
        """Loads cached embeddings from disk if available."""
        if cls._cache_loaded:
            return
        cls._cache_loaded = True
        cache_path = cls._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
                logger.info(f"Loaded {len(cls._cache)} cached policy embeddings from disk.")
            except Exception as e:
                logger.warning(f"Failed to load embeddings cache from {cache_path}: {e}")

    @classmethod
    def _save_cache(cls):
        """Persists memory cache to disk."""
        cache_path = cls._get_cache_path()
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cls._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save embeddings cache to {cache_path}: {e}")

    @classmethod
    def get_client(cls):
        """Lazily initializes and returns Google GenAI client."""
        if cls._client is None:
            from google import genai
            api_key = settings.GEMINI_API_KEY or ""
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    @classmethod
    def get_model_name(cls) -> str:
        """Returns configured embedding model name."""
        return settings.POLICY_EMBEDDING_MODEL or "gemini-embedding-2"

    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Returns the embedding vector dimension for the active model (384)."""
        return cls._dimension

    @classmethod
    def embed_text(cls, text: str) -> np.ndarray:
        """
        Embeds a single query or text string into a normalized 1D float32 numpy array.
        Uses GEMINI_API_KEY with task_type='RETRIEVAL_QUERY'.
        """
        cls._load_cache()
        if not text or not str(text).strip():
            return np.zeros(cls._dimension, dtype=np.float32)

        clean_text = str(text).strip()
        h = _text_hash(clean_text)
        if h in cls._cache:
            return np.array(cls._cache[h], dtype=np.float32)

        # Check API key availability
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not configured. Using deterministic fallback embedding.")
            vec = _generate_fallback_vector(clean_text, cls._dimension)
            cls._cache[h] = vec.tolist()
            return vec

        try:
            from google.genai import types
            client = cls.get_client()
            model_name = cls.get_model_name()

            resp = client.models.embed_content(
                model=model_name,
                contents=clean_text,
                config=types.EmbedContentConfig(
                    output_dimensionality=cls._dimension,
                    task_type="RETRIEVAL_QUERY",
                ),
            )
            raw_vals = np.array(resp.embeddings[0].values, dtype=np.float32)
            norm_vec = _normalize_vector(raw_vals)
            cls._cache[h] = norm_vec.tolist()
            return norm_vec
        except Exception as e:
            logger.warning(f"Gemini embed_text failed ({e}). Using deterministic fallback.")
            vec = _generate_fallback_vector(clean_text, cls._dimension)
            cls._cache[h] = vec.tolist()
            return vec

    @classmethod
    def embed_batch(cls, texts: List[str], batch_size: int = 6) -> np.ndarray:
        """
        Embeds a list of texts into a 2D float32 numpy array of shape (N, dimension).
        Checks disk/memory cache first. For uncached texts, calls Gemini API
        in small batches with exponential backoff to respect rate limits.
        """
        cls._load_cache()
        if not texts:
            return np.empty((0, cls._dimension), dtype=np.float32)

        results: List[Optional[np.ndarray]] = [None] * len(texts)
        missing_indices: List[int] = []

        # 1. Check cache
        for idx, text in enumerate(texts):
            clean_text = str(text).strip()
            h = _text_hash(clean_text)
            if h in cls._cache:
                results[idx] = np.array(cls._cache[h], dtype=np.float32)
            else:
                missing_indices.append(idx)

        # 2. If all were cached, return immediately
        if not missing_indices:
            return np.vstack(results).astype(np.float32)

        # 3. Handle missing items
        if not settings.GEMINI_API_KEY:
            logger.warning(f"GEMINI_API_KEY not configured. Using fallback for {len(missing_indices)} texts.")
            for idx in missing_indices:
                vec = _generate_fallback_vector(texts[idx], cls._dimension)
                h = _text_hash(texts[idx])
                cls._cache[h] = vec.tolist()
                results[idx] = vec
            cls._save_cache()
            return np.vstack(results).astype(np.float32)

        # 4. Embed uncached items in batches via Gemini API
        from google.genai import types
        client = cls.get_client()
        model_name = cls.get_model_name()

        for i in range(0, len(missing_indices), batch_size):
            chunk_indices = missing_indices[i : i + batch_size]
            batch_texts = [texts[idx] for idx in chunk_indices]
            contents = [
                types.Content(parts=[types.Part.from_text(text=t)])
                for t in batch_texts
            ]

            success = False
            for attempt in range(5):
                try:
                    resp = client.models.embed_content(
                        model=model_name,
                        contents=contents,
                        config=types.EmbedContentConfig(
                            output_dimensionality=cls._dimension,
                            task_type="RETRIEVAL_DOCUMENT",
                        ),
                    )
                    for local_idx, emb in enumerate(resp.embeddings):
                        orig_idx = chunk_indices[local_idx]
                        raw_vals = np.array(emb.values, dtype=np.float32)
                        norm_vec = _normalize_vector(raw_vals)
                        results[orig_idx] = norm_vec
                        cls._cache[_text_hash(texts[orig_idx])] = norm_vec.tolist()
                    success = True
                    break
                except Exception as e:
                    wait_time = 2 ** attempt
                    logger.warning(f"Batch embed attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

            if not success:
                logger.error(f"Batch embed failed after retries for {len(chunk_indices)} items. Using fallback.")
                for orig_idx in chunk_indices:
                    vec = _generate_fallback_vector(texts[orig_idx], cls._dimension)
                    cls._cache[_text_hash(texts[orig_idx])] = vec.tolist()
                    results[orig_idx] = vec

            # Small polite pause between batches to respect rate limits
            if i + batch_size < len(missing_indices):
                time.sleep(0.5)

        cls._save_cache()
        return np.vstack(results).astype(np.float32)
