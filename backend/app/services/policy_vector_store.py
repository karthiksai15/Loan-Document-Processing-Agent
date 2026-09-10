"""
Policy Vector Store Manager (Phase 14)

Manages FAISS index construction, disk persistence, metadata mapping,
manifest serialization, and vector similarity search.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import faiss

from app.core.config import settings
from app.core.logging import logger


class PolicyVectorStore:
    def __init__(self, vector_store_dir: str = settings.VECTOR_STORE_DIR):
        self.vector_store_dir = vector_store_dir
        self.index_file = os.path.join(self.vector_store_dir, "policy_index.faiss")
        self.manifest_file = os.path.join(self.vector_store_dir, "policy_index_manifest.json")
        
        self.index: Optional[faiss.Index] = None
        self.manifest: Optional[Dict[str, Any]] = None
        self.chunks_map: List[Dict[str, Any]] = []

    def ensure_directory_exists(self):
        """Ensures storage directory exists."""
        os.makedirs(self.vector_store_dir, exist_ok=True)

    def is_index_valid(self, expected_model_name: str) -> bool:
        """
        Checks whether index file and manifest exist on disk and are compatible with expected model.
        """
        if not os.path.exists(self.index_file) or not os.path.exists(self.manifest_file):
            return False

        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            if manifest_data.get("model_name") != expected_model_name:
                logger.warning(
                    f"Vector store model mismatch. Manifest model '{manifest_data.get('model_name')}' "
                    f"does not match expected model '{expected_model_name}'."
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating vector store manifest: {e}")
            return False

    def build_and_save_index(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray, model_name: str) -> Dict[str, Any]:
        """
        Builds FAISS IndexFlatIP from normalized float32 embeddings, maps metadata,
        and persists binary index and manifest to disk.
        """
        self.ensure_directory_exists()

        if embeddings is None or len(embeddings) == 0:
            dimension = 384
            index = faiss.IndexFlatIP(dimension)
            faiss.write_index(index, self.index_file)
            manifest_data = {
                "model_name": model_name,
                "embedding_dimension": dimension,
                "indexed_at": datetime.utcnow().isoformat(),
                "chunk_count": 0,
                "index_version": "1.0",
                "chunks": [],
            }
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            self.index = index
            self.manifest = manifest_data
            self.chunks_map = []
            return manifest_data

        num_vectors, dimension = embeddings.shape

        # FAISS Inner Product index (Cosine similarity for normalized vectors)
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        faiss.write_index(index, self.index_file)

        manifest_data = {
            "model_name": model_name,
            "embedding_dimension": dimension,
            "indexed_at": datetime.utcnow().isoformat(),
            "chunk_count": num_vectors,
            "index_version": "1.0",
            "chunks": chunks,
        }

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        self.index = index
        self.manifest = manifest_data
        self.chunks_map = chunks

        logger.info(f"FAISS policy index built successfully with {num_vectors} vectors ({dimension} dims).")
        return manifest_data

    def load_index(self) -> bool:
        """Loads FAISS index binary and metadata manifest from disk."""
        if not os.path.exists(self.index_file) or not os.path.exists(self.manifest_file):
            return False

        try:
            self.index = faiss.read_index(self.index_file)
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                self.manifest = json.load(f)
            self.chunks_map = self.manifest.get("chunks", [])
            logger.info(f"Loaded FAISS policy index with {len(self.chunks_map)} chunks.")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS index or manifest: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Executes vector similarity search against FAISS index.
        Returns list of (chunk_metadata, cosine_similarity_score) tuples.
        """
        if self.index is None or not self.chunks_map:
            if not self.load_index() or self.index is None or not self.chunks_map:
                return []

        # Prepare 2D float32 array for query vector
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        # Search index
        effective_k = min(top_k, self.index.ntotal)
        if effective_k <= 0:
            return []

        distances, indices = self.index.search(query_vector, effective_k)

        results = []
        for pos, sim_score in zip(indices[0], distances[0]):
            if pos < 0 or pos >= len(self.chunks_map):
                continue
            chunk_meta = self.chunks_map[pos]
            results.append((chunk_meta, float(sim_score)))

        return results
