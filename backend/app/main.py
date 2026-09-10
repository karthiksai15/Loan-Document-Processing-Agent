from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base
from app.db.session import engine
from app.api.v1.router import api_router

# Initialize database tables
try:
    Base.metadata.create_all(bind=engine)
    # Check for missing Phase 17 columns in SQLite
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    if "agent_reviews" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("agent_reviews")}
        with engine.connect() as conn:
            if "evidence_sufficiency" not in columns:
                conn.execute(text("ALTER TABLE agent_reviews ADD COLUMN evidence_sufficiency VARCHAR(50) DEFAULT 'SUFFICIENT'"))
            if "claims_support_summary" not in columns:
                conn.execute(text("ALTER TABLE agent_reviews ADD COLUMN claims_support_summary TEXT"))
            if "retries_count" not in columns:
                conn.execute(text("ALTER TABLE agent_reviews ADD COLUMN retries_count INTEGER DEFAULT 0"))
            conn.commit()
    if "human_reviews" in inspector.get_table_names():
        hr_columns = {c["name"] for c in inspector.get_columns("human_reviews")}
        with engine.connect() as conn:
            if "decision_reason" not in hr_columns:
                conn.execute(text("ALTER TABLE human_reviews ADD COLUMN decision_reason TEXT"))
            if "officer_feedback" not in hr_columns:
                conn.execute(text("ALTER TABLE human_reviews ADD COLUMN officer_feedback TEXT"))
            conn.commit()
    if "review_assessments" in inspector.get_table_names():
        ra_columns = {c["name"] for c in inspector.get_columns("review_assessments")}
        with engine.connect() as conn:
            if "missing_documents" not in ra_columns:
                conn.execute(text("ALTER TABLE review_assessments ADD COLUMN missing_documents JSON"))
            if "missing_document" not in ra_columns:
                conn.execute(text("ALTER TABLE review_assessments ADD COLUMN missing_document VARCHAR(100)"))
            if "critical_issue" not in ra_columns:
                conn.execute(text("ALTER TABLE review_assessments ADD COLUMN critical_issue VARCHAR(100)"))
            if "verification_issue_type" not in ra_columns:
                conn.execute(text("ALTER TABLE review_assessments ADD COLUMN verification_issue_type VARCHAR(100)"))
            conn.commit()
    if not settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE evidence_nodes ALTER COLUMN node_id TYPE VARCHAR(255)"))
                conn.execute(text("ALTER TABLE evidence_relationships ALTER COLUMN relationship_id TYPE VARCHAR(500)"))
                conn.execute(text("ALTER TABLE evidence_relationships ALTER COLUMN source_node_id TYPE VARCHAR(255)"))
                conn.execute(text("ALTER TABLE evidence_relationships ALTER COLUMN target_node_id TYPE VARCHAR(255)"))
                conn.commit()
            except Exception as ex:
                logger.warning(f"Note on evidence column alter: {ex}")
    logger.info("Database tables initialized and migrated successfully.")
except Exception as e:
    logger.error(f"Error initializing database tables: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
cors_raw = getattr(settings, "CORS_ORIGINS", "*")
if cors_raw == "*" or not cors_raw:
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    """Root health check endpoint for Cloud monitoring (Render / load balancers)."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER
    }

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_v1": f"{settings.API_V1_STR}/health"
    }

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", getattr(settings, "PORT", 8000) or 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
