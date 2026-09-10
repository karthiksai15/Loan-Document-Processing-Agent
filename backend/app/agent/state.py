"""
Agent State — Phase 16 & 17 Hardening

Defines the LangGraph TypedDict state for the AI Loan Review Agent.
Each application investigation gets its own isolated state instance.

Hardened in Phase 17:
  - evidence_sufficiency (SUFFICIENT, PARTIAL, INSUFFICIENT)
  - investigation_status (COMPLETED, ESCALATED, DEGRADED, FAILED)
  - retries_count (transient retry tracking)
  - claims_support_summary (SUPPORTED, UNSUPPORTED, UNKNOWN claim mapping)
  - security_flags (prompt injection & tool abuse tracking)
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal


class InvestigationStep(TypedDict):
    """A single recorded step in the agent investigation trace."""
    step_number: int
    action: str                         # e.g., LOAD_CONTEXT, TOOL_CALL, BUILD_REVIEW, LLM_RETRY
    tool_name: Optional[str]            # tool used (if any)
    tool_input_summary: Optional[str]   # brief description of what was asked
    result_summary: str                 # brief description of what was found
    reason: str                         # why this action was taken
    evidence_ids: List[str]             # evidence node IDs referenced in this step
    policy_ids: List[str]               # policy section IDs referenced in this step


class AgentState(TypedDict):
    """
    Complete LangGraph state for one AI Loan Review Agent investigation.

    Isolation: Each investigation receives a fresh AgentState.
    No data from one investigation persists into another.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    application_id: str
    agent_version: str
    instruction_version: str

    # ── Initial context (loaded once at LOAD_CONTEXT) ────────────────────────
    initial_context: Dict[str, Any]          # Output of build_llm_context()
    injection_check_status: str              # CLEAN or FLAGGED
    security_flags: List[str]                # Matched injection/abuse patterns

    # ── Investigation accumulation ───────────────────────────────────────────
    current_findings: List[str]              # Bullet-point findings so far
    evidence_references: List[Dict[str, Any]]  # Accumulated evidence citations
    policy_references: List[Dict[str, Any]]    # Accumulated policy citations
    risk_information: Dict[str, Any]           # ML risk result snapshot
    review_information: Dict[str, Any]         # Review score result snapshot
    unresolved_questions: List[str]            # Things the agent cannot confirm

    # ── Tool tracking (loop protection) ──────────────────────────────────────
    tools_used: List[str]                    # List of tool names already called
    tool_call_history: List[str]             # Normalized "tool:key" strings
    investigation_steps: List[InvestigationStep]

    # ── Control flow & safety limits ─────────────────────────────────────────
    step_count: int
    retries_count: int                       # Count of transient LLM retries
    llm_unavailable: Optional[bool]          # True if LLM provider has failed fatally or exhausted quota
    next_tool: Optional[str]                 # Tool the agent decided to call next
    next_tool_query: Optional[str]           # Query/argument for next tool
    planned_tools: Optional[List[Any]]       # Planned tool queue to avoid repeated LLM decision round-trips
    sufficient_evidence: bool                # Agent declared it has enough info
    needs_more_investigation: bool           # Agent needs another tool call
    investigation_complete: bool             # Loop has finished

    # ── Evidence sufficiency (Phase 17 Guard) ────────────────────────────────
    evidence_sufficiency: Literal["SUFFICIENT", "PARTIAL", "INSUFFICIENT"]

    # ── Claim grounding audit (Phase 17 Support Map) ─────────────────────────
    claims_support_summary: Dict[str, str]

    # ── Reasoning summary (concise, not chain-of-thought) ────────────────────
    current_reasoning_summary: str

    # ── Escalation & Terminal Status ─────────────────────────────────────────
    escalation_required: bool
    escalation_reason: Optional[str]
    investigation_status: Literal["COMPLETED", "ESCALATED", "DEGRADED", "FAILED"]

    # ── Final review (produced by BUILD_REVIEW node) ─────────────────────────
    final_review: Optional[Dict[str, Any]]

    # ── Output confidence ────────────────────────────────────────────────────
    confidence: float
    confidence_level: str                    # LOW, MEDIUM, HIGH
