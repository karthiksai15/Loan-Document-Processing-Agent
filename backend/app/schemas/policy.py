from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class PolicyRuleBase(BaseModel):
    rule_code: str
    rule_name: str
    field_name: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[Any] = None
    description: Optional[str] = None
    is_regulatory: bool = False


class PolicyRuleCreate(PolicyRuleBase):
    rule_id: str
    policy_doc_id: str
    section_id: Optional[str] = None


class PolicyRuleRead(PolicyRuleBase):
    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    policy_doc_id: str
    section_id: Optional[str] = None
    created_at: datetime


class PolicySectionBase(BaseModel):
    chapter_or_part: Optional[str] = None
    section_number: Optional[str] = None
    section_title: str
    page_number: Optional[int] = None
    content_text: str
    summary: Optional[str] = None


class PolicySectionCreate(PolicySectionBase):
    section_id: str
    policy_doc_id: str


class PolicySectionRead(PolicySectionBase):
    model_config = ConfigDict(from_attributes=True)

    section_id: str
    policy_doc_id: str
    created_at: datetime
    rules: List[PolicyRuleRead] = []


class PolicySectionTraceability(PolicySectionRead):
    policy_title: str
    policy_type: str
    authority: str
    category: str
    version: str
    reference_code: Optional[str] = None
    official_url: Optional[str] = None


class PolicyDocumentBase(BaseModel):
    title: str
    policy_type: str  # REGULATORY, INTERNAL_UNDERWRITING
    authority: str    # RBI, INTERNAL_BANK
    category: str     # KYC, DIGITAL_LENDING, CREDIT_REPORTING, FAIR_PRACTICES, UNDERWRITING_METRICS
    version: str
    reference_code: Optional[str] = None
    official_url: Optional[str] = None
    source_filename: Optional[str] = None
    effective_date: Optional[str] = None
    description: Optional[str] = None
    status: str = "ACTIVE"


class PolicyDocumentCreate(PolicyDocumentBase):
    policy_doc_id: str
    sections: List[PolicySectionCreate] = []
    rules: List[PolicyRuleCreate] = []


class PolicyDocumentRead(PolicyDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    policy_doc_id: str
    created_at: datetime
    updated_at: datetime
    section_count: int = 0
    rule_count: int = 0


class PolicyDocumentDetailRead(PolicyDocumentRead):
    sections: List[PolicySectionRead] = []
    rules: List[PolicyRuleRead] = []


class PolicyIngestionResult(BaseModel):
    status: str
    documents_ingested: int
    sections_ingested: int
    rules_ingested: int
    message: str


class PolicyItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: str
    source: str  # RBI, HDFC_BANK, HDFC_INTERNAL_DEMO
    title: str
    category: str  # KYC, IDENTITY, CREDIT_ASSESSMENT, INCOME_VERIFICATION, DOCUMENTATION, FAIR_PRACTICES, ESCALATION, DIGITAL_LENDING
    section: str
    rule: str
    description: str
    text: str
    applicability: str
    is_simulated: bool = False
    authority: Optional[str] = None
    reference_code: Optional[str] = None
    official_url: Optional[str] = None
    version: Optional[str] = None


class PolicyKnowledgeBaseSummary(BaseModel):
    total_policies: int
    rbi_policy_count: int
    hdfc_public_policy_count: int
    hdfc_internal_demo_policy_count: int
    categories: List[str]
    sources: List[str]
