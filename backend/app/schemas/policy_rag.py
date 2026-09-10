from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class PolicySearchRequest(BaseModel):
    query: str = Field(..., description="Semantic search query string", json_schema_extra={"example": "What policy applies to customer identity verification?"})
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of candidate chunks to return")
    source: Optional[str] = Field(None, description="Filter by RBI, HDFC_BANK, or HDFC_INTERNAL_DEMO")
    is_simulated: Optional[bool] = Field(None, description="Filter by simulation status (True/False)")
    policy_type: Optional[str] = Field(None, description="Filter by REGULATORY or INTERNAL_UNDERWRITING")
    authority: Optional[str] = Field(None, description="Filter by RBI, HDFC_BANK, or INTERNAL_RISK_COMMITTEE")
    category: Optional[str] = Field(None, description="Filter by policy category (e.g., KYC, DIGITAL_LENDING)")
    policy_id: Optional[str] = Field(None, description="Filter by specific policy document ID")


class PolicyCitation(BaseModel):
    policy_id: str
    policy_name: str
    authority: str          # RBI vs HDFC_BANK vs INTERNAL_RISK_COMMITTEE
    policy_type: str        # REGULATORY vs INTERNAL_UNDERWRITING
    section_id: str
    section_title: str
    section_reference: Optional[str] = None  # e.g., Section 16, Clause 5
    chapter_or_part: Optional[str] = None
    page_number: Optional[int] = None
    source_document: Optional[str] = None
    source_url: Optional[str] = None
    version: str
    reference_code: Optional[str] = None
    effective_date: Optional[str] = None
    source: Optional[str] = None
    rule: Optional[str] = None
    category: Optional[str] = None
    is_simulated: Optional[bool] = False
    applicability: Optional[str] = None
    description: Optional[str] = None


class PolicySearchResultItem(BaseModel):
    rank: int
    chunk_id: str
    content: str
    similarity_score: float
    score_type: str = "COSINE_SIMILARITY"
    citation: PolicyCitation


class PolicySearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[PolicySearchResultItem]
    filters_applied: Dict[str, Any] = {}


class PolicyIndexRebuildResponse(BaseModel):
    status: str
    chunks_indexed: int
    embedding_model: str
    dimension: int
    index_path: str
    manifest_path: str
    message: str
    source_counts: Optional[Dict[str, int]] = None
