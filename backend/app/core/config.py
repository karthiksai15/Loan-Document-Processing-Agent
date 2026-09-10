import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Loan Document Processing Agent API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    LLM_PROVIDER: Literal["gemini", "ollama", "grok", "groq"] = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Groq Settings — Phase 15
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Legacy Grok (xAI) Settings
    GROK_API_KEY: str = ""
    GROK_MODEL: str = "grok-3-mini"
    GROK_BASE_URL: str = "https://api.x.ai/v1"

    # AI Review Agent Settings — Phase 16 & 17
    MAX_AGENT_STEPS: int = 5
    AGENT_VERSION: str = "agent_v1"
    AGENT_INSTRUCTION_VERSION: str = "loan_review_agent_v1"
    MAX_LLM_RETRIES: int = 1
    LLM_RETRY_BACKOFF: float = 0.5

    # Confidence & Human Review Settings — Phase 18
    CONFIDENCE_HIGH_THRESHOLD: float = 80.0
    CONFIDENCE_MEDIUM_THRESHOLD: float = 50.0
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./loan_agent.db"
    
    # Storage Paths
    DATA_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
        "data"
    )
    UPLOADS_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
        "data", "uploads"
    )
    EXTRACTED_TEXT_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
        "data", "extracted_text"
    )
    
    # Document Upload Validation
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list[str] = [".txt", ".pdf"]
    ALLOWED_DOCUMENT_TYPES: list[str] = ["PAYSLIP", "BANK_STATEMENT", "TAX_RETURN", "KYC", "OTHER"]
    
    # Policy RAG Settings (Phase 14)
    POLICY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_STORE_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
        "data", "vector_store"
    )
    POLICY_CHUNK_SIZE: int = 500
    POLICY_CHUNK_OVERLAP: int = 50
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
