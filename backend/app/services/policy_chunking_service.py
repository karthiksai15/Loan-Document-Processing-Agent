"""
Policy Chunking Service (Phase 14)

Splits policy sections into meaningful text chunks while preserving complete
provenance and source metadata for citation traceability.
"""

from typing import List, Dict, Any, Union
from app.core.config import settings
from app.schemas.policy import PolicyItemSchema


class PolicyChunkingService:
    @staticmethod
    def chunk_policy_item(
        policy: Union[PolicyItemSchema, Dict[str, Any]],
        chunk_size: int = settings.POLICY_CHUNK_SIZE,
        overlap: int = settings.POLICY_CHUNK_OVERLAP,
    ) -> List[Dict[str, Any]]:
        """
        Chunks a Phase 13 policy item (PolicyItemSchema or dict) into indexing units.
        Preserves all 14+ provenance fields required for Phase 14 RAG.
        """
        if isinstance(policy, PolicyItemSchema):
            p_data = policy.model_dump()
        else:
            p_data = policy

        policy_id = p_data.get("policy_id", "")
        title = p_data.get("title", "")
        rule = p_data.get("rule", "")
        section = p_data.get("section", "")
        category = p_data.get("category", "")
        description = p_data.get("description", "")
        text = p_data.get("text", "")
        applicability = p_data.get("applicability", "")
        source = p_data.get("source", "")
        authority = p_data.get("authority", "")
        is_simulated = p_data.get("is_simulated", False)
        reference_code = p_data.get("reference_code")
        official_url = p_data.get("official_url")
        version = p_data.get("version", "1.0")

        # Construct comprehensive, semantically rich searchable text
        full_content = (
            f"{title}. Category: {category}. Rule: {rule}. Section: {section}. "
            f"Applicability: {applicability}. Description: {description} "
            f"Policy Text: {text}"
        ).strip()

        if not full_content:
            return []

        text_length = len(full_content)
        if text_length <= chunk_size:
            text_slices = [full_content]
        else:
            text_slices = []
            start = 0
            while start < text_length:
                end = min(start + chunk_size, text_length)
                if end < text_length:
                    last_period = full_content.rfind(".", start, end)
                    if last_period > start + (chunk_size // 2):
                        end = last_period + 1
                slice_text = full_content[start:end].strip()
                if slice_text:
                    text_slices.append(slice_text)
                if end >= text_length:
                    break
                start = end - overlap if (end - overlap) > start else end

        chunks = []
        for idx, text_slice in enumerate(text_slices):
            chunk_id = f"CHK_{policy_id}_{idx + 1:02d}"
            policy_type = "REGULATORY" if source == "RBI" else "INTERNAL_UNDERWRITING"

            chunk_data = {
                "chunk_id": chunk_id,
                "chunk_index": idx + 1,
                "policy_id": policy_id,
                "source": source,
                "title": title,
                "category": category,
                "section": section,
                "rule": rule,
                "description": description,
                "text": text,
                "applicability": applicability,
                "is_simulated": is_simulated,
                "authority": authority,
                "reference_code": reference_code,
                "official_url": official_url,
                "version": version,
                "content": text_slice,
                "content_text": text_slice,
                # Backward-compatible fields:
                "policy_document_id": policy_id,
                "policy_name": title,
                "policy_type": policy_type,
                "source_authority": authority,
                "source_document": reference_code or title,
                "source_url": official_url,
                "section_id": policy_id,
                "section_title": title,
                "section_reference": section,
                "chapter_or_part": section,
                "page_number": None,
                "effective_date": version,
            }
            chunks.append(chunk_data)

        return chunks

    @classmethod
    def chunk_all_policies(
        cls,
        policies: List[Union[PolicyItemSchema, Dict[str, Any]]],
        chunk_size: int = settings.POLICY_CHUNK_SIZE,
        overlap: int = settings.POLICY_CHUNK_OVERLAP,
    ) -> List[Dict[str, Any]]:
        """Chunks a list of Phase 13 policies into RAG indexing chunks."""
        all_chunks = []
        for p in policies:
            all_chunks.extend(cls.chunk_policy_item(p, chunk_size=chunk_size, overlap=overlap))
        return all_chunks

    @staticmethod
    def chunk_section(section_payload: Dict[str, Any], chunk_size: int = settings.POLICY_CHUNK_SIZE, overlap: int = settings.POLICY_CHUNK_OVERLAP) -> List[Dict[str, Any]]:
        """
        Splits a single policy section payload into text chunks.
        If content length is within chunk_size, returns 1 chunk containing the full section text.
        Preserves all provenance metadata fields.
        """
        content_text = section_payload.get("content_text", "").strip()
        if not content_text:
            return []

        chunks = []
        text_length = len(content_text)

        if text_length <= chunk_size:
            text_slices = [content_text]
        else:
            text_slices = []
            start = 0
            while start < text_length:
                end = min(start + chunk_size, text_length)
                if end < text_length:
                    last_period = content_text.rfind(".", start, end)
                    if last_period > start + (chunk_size // 2):
                        end = last_period + 1
                slice_text = content_text[start:end].strip()
                if slice_text:
                    text_slices.append(slice_text)
                if end >= text_length:
                    break
                start = end - overlap if (end - overlap) > start else end

        for idx, text_slice in enumerate(text_slices):
            chunk_id = f"CHK_{section_payload['section_id']}_{idx + 1:02d}"
            
            chunk_data = {
                "chunk_id": chunk_id,
                "chunk_index": idx + 1,
                "policy_document_id": section_payload["policy_doc_id"],
                "policy_id": section_payload["policy_doc_id"],
                "section_id": section_payload["section_id"],
                "section_title": section_payload["section_title"],
                "policy_name": section_payload["policy_title"],
                "policy_type": section_payload["policy_type"],
                "source_authority": section_payload["authority"],
                "authority": section_payload["authority"],
                "source_document": section_payload.get("source_filename") or section_payload.get("reference_code") or section_payload["policy_title"],
                "source_url": section_payload.get("official_url"),
                "effective_date": section_payload.get("effective_date"),
                "page_number": section_payload.get("page_number"),
                "section_reference": section_payload.get("section_number") or section_payload.get("chapter_or_part"),
                "chapter_or_part": section_payload.get("chapter_or_part"),
                "category": section_payload.get("category"),
                "version": section_payload.get("version"),
                "reference_code": section_payload.get("reference_code"),
                "content": text_slice,
                "content_text": text_slice,
            }
            chunks.append(chunk_data)

        return chunks

    @classmethod
    def chunk_all_sections(cls, sections_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunks a list of policy sections."""
        all_chunks = []
        for sec in sections_payload:
            all_chunks.extend(cls.chunk_section(sec))
        return all_chunks
