import os
import pandas as pd
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.llm import get_llm_provider
from app.api.v1.applications import router as applications_router
from app.api.v1.documents import router as documents_router
from app.api.v1.policies import router as policies_router
from app.api.v1.llm import router as llm_router
from app.api.v1.agent import router as agent_router
from app.api.v1.human_review import router as human_review_router

api_router = APIRouter()

# Include feature sub-routers
api_router.include_router(applications_router)
api_router.include_router(documents_router)
api_router.include_router(policies_router)
api_router.include_router(llm_router)
api_router.include_router(agent_router)
api_router.include_router(human_review_router)

@api_router.get("/health", tags=["Health"])
def health_check():
    """Returns application health status."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER
    }

@api_router.get("/system/info", tags=["System"])
def system_info():
    """Returns foundation system metadata and dataset statistics."""
    try:
        provider = get_llm_provider()
        provider_name = provider.name()
    except Exception as e:
        provider_name = f"Unavailable ({str(e)})"
        
    profiles_path = os.path.join(settings.DATA_DIR, "processed", "applicant_profiles.csv")
    manifest_path = os.path.join(settings.DATA_DIR, "processed", "document_manifest.csv")
    
    applicant_count = 0
    document_count = 0
    
    if os.path.exists(profiles_path):
        df_profiles = pd.read_csv(profiles_path)
        applicant_count = len(df_profiles)
        
    if os.path.exists(manifest_path):
        df_manifest = pd.read_csv(manifest_path)
        document_count = len(df_manifest)
        
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_llm_provider": provider_name,
        "configured_provider_type": settings.LLM_PROVIDER,
        "data_directory": settings.DATA_DIR,
        "dataset_statistics": {
            "total_demo_applicants": applicant_count,
            "total_synthetic_documents": document_count
        }
    }
