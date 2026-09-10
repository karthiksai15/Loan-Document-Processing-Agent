from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class EvidenceNodeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    application_id: str
    document_id: Optional[str] = None
    node_type: str  # APPLICATION, DOCUMENT, FIELD, VALIDATION_RESULT, VERIFICATION_FINDING
    title: str
    value: Optional[str] = None
    source_type: str = "SYSTEM"
    source_reference: Optional[str] = None
    confidence: float = 1.0
    node_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class EvidenceRelationshipSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    relationship_id: str
    application_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str  # HAS_DOCUMENT, CONTAINS_FIELD, HAS_VALIDATION, HAS_FINDING, DERIVED_FROM, SUPPORTS, COMPARED_WITH
    rel_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class ApplicationEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    total_nodes: int = 0
    total_relationships: int = 0
    nodes: List[EvidenceNodeSchema] = []
    relationships: List[EvidenceRelationshipSchema] = []
    graph_summary: Optional[Dict[str, Any]] = None
    generated_at: Optional[datetime] = None
