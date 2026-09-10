"""
Policy Knowledge Base Service (Phase 13)

Manages loading, validation, and deterministic keyword/category retrieval of:
1. RBI Regulatory Requirements (source: RBI, is_simulated: False)
2. HDFC Bank Public Guidelines (source: HDFC_BANK, is_simulated: False)
3. Simulated HDFC Internal Demo Rules (source: HDFC_INTERNAL_DEMO, is_simulated: True)

Maintains strict separation between statutory regulatory mandates and bank underwriting rules.
Provides deterministic, structured facts without vector embeddings or FAISS.
"""

import os
import json
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.core.logging import logger
from app.schemas.policy import PolicyItemSchema, PolicyKnowledgeBaseSummary


class PolicyKnowledgeService:
    """
    Service for loading and querying the Phase 13 Policy Knowledge Base.
    Operates over structured JSON files in data/policies/.
    """

    _cached_policies: Optional[List[PolicyItemSchema]] = None

    @classmethod
    def get_policy_dir(cls) -> str:
        """Returns absolute path to the local policy directory."""
        # Check relative to settings.DATA_DIR or fallback to project root data/policies
        candidates = [
            os.path.join(settings.DATA_DIR, "policies"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "policies")),
            os.path.abspath(os.path.join(os.getcwd(), "data", "policies")),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        # Default to settings.DATA_DIR/policies
        default_path = os.path.join(settings.DATA_DIR, "policies")
        os.makedirs(default_path, exist_ok=True)
        return default_path

    @classmethod
    def load_policies(cls, force_reload: bool = False) -> List[PolicyItemSchema]:
        """
        Loads and validates policies from all JSON policy files in data/policies/.
        Caches result in memory unless force_reload=True.
        """
        if cls._cached_policies is not None and not force_reload:
            return cls._cached_policies

        policy_dir = cls.get_policy_dir()
        expected_files = [
            ("rbi_policies.json", "RBI", False),
            ("hdfc_public_policies.json", "HDFC_BANK", False),
            ("hdfc_internal_demo_policies.json", "HDFC_INTERNAL_DEMO", True),
        ]

        loaded: List[PolicyItemSchema] = []

        for filename, expected_source, expected_simulated in expected_files:
            file_path = os.path.join(policy_dir, filename)
            if not os.path.exists(file_path):
                logger.warning(f"Policy file not found: {file_path}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_items = json.load(f)

                for item in raw_items:
                    # Enforce source & is_simulated consistency
                    if item.get("source") != expected_source:
                        logger.warning(
                            f"Policy {item.get('policy_id')} source mismatch: "
                            f"expected {expected_source}, found {item.get('source')}"
                        )
                    if item.get("is_simulated") != expected_simulated:
                        logger.warning(
                            f"Policy {item.get('policy_id')} simulation flag mismatch: "
                            f"expected {expected_simulated}, found {item.get('is_simulated')}"
                        )

                    schema_item = PolicyItemSchema(**item)
                    loaded.append(schema_item)

            except Exception as e:
                logger.error(f"Error loading policies from {file_path}: {e}")
                raise

        cls._cached_policies = loaded
        logger.info(f"Loaded {len(loaded)} policies across {len(expected_files)} policy files.")
        return loaded

    @classmethod
    def get_all_policies(cls) -> List[PolicyItemSchema]:
        """Returns all policies currently registered in the knowledge base."""
        return cls.load_policies()

    @classmethod
    def get_policies_by_source(cls, source: str) -> List[PolicyItemSchema]:
        """
        Retrieves policies filtered strictly by source.
        Valid sources: 'RBI', 'HDFC_BANK', 'HDFC_INTERNAL_DEMO'.
        """
        all_policies = cls.load_policies()
        normalized_source = source.strip().upper()
        return [p for p in all_policies if p.source.upper() == normalized_source]

    @classmethod
    def get_policies_by_category(cls, category: str) -> List[PolicyItemSchema]:
        """
        Retrieves policies filtered by category.
        Categories: 'KYC', 'IDENTITY', 'CREDIT_ASSESSMENT', 'INCOME_VERIFICATION',
        'DOCUMENTATION', 'FAIR_PRACTICES', 'ESCALATION', 'DIGITAL_LENDING'.
        """
        all_policies = cls.load_policies()
        normalized_cat = category.strip().upper()
        return [p for p in all_policies if p.category.upper() == normalized_cat]

    @classmethod
    def get_policy_by_id(cls, policy_id: str) -> Optional[PolicyItemSchema]:
        """Retrieves a single policy by unique policy_id."""
        all_policies = cls.load_policies()
        for p in all_policies:
            if p.policy_id == policy_id:
                return p
        return None

    @classmethod
    def search_policies_keyword(
        cls,
        query: str,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[PolicyItemSchema]:
        """
        Simple deterministic keyword retrieval over title, text, description, and rule.
        Does NOT use embeddings, vector indexes, or FAISS (belongs to Phase 14).
        """
        candidates = cls.load_policies()
        if source:
            candidates = [p for p in candidates if p.source.upper() == source.strip().upper()]
        if category:
            candidates = [p for p in candidates if p.category.upper() == category.strip().upper()]

        if not query or not query.strip():
            return candidates

        terms = [t.lower() for t in query.strip().split()]
        matches = []

        for p in candidates:
            searchable_text = f"{p.title} {p.rule} {p.category} {p.description} {p.text}".lower()
            # Simple match score based on matching terms
            score = sum(1 for term in terms if term in searchable_text)
            if score > 0:
                matches.append((score, p))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matches]

    @classmethod
    def get_summary(cls) -> PolicyKnowledgeBaseSummary:
        """Returns aggregated summary metrics of the Policy Knowledge Base."""
        policies = cls.load_policies()
        sources = sorted(list({p.source for p in policies}))
        categories = sorted(list({p.category for p in policies}))

        return PolicyKnowledgeBaseSummary(
            total_policies=len(policies),
            rbi_policy_count=len([p for p in policies if p.source == "RBI"]),
            hdfc_public_policy_count=len([p for p in policies if p.source == "HDFC_BANK"]),
            hdfc_internal_demo_policy_count=len([p for p in policies if p.source == "HDFC_INTERNAL_DEMO"]),
            categories=categories,
            sources=sources,
        )
