# Loan Document Processing Agent

An Agentic GenAI and Machine Learning solution designed for loan officers to review, validate, compare, and analyze loan applications and supporting documents (Payslips, Bank Statements, Tax Returns, KYC) with traceable evidence and human oversight.

---

## System Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Loan Officer Dashboard  │
                          └─────────────┬─────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │    FastAPI Backend API    │
                          └─────────────┬─────────────┘
                                        │
      ┌──────────────────┬──────────────┼──────────────┬──────────────────┐
      │                  │              │              │                  │
┌─────▼──────┐    ┌──────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐    ┌───────▼──────┐
│ Deterministic│   │ OCR / PDF  │  │  ML Risk  │  │ LLM Abstr.│    │  Evidence    │
│ Validation │   │ Extraction │  │ Analysis  │  │Gemini/Olla│    │    Graph     │
└────────────┘    └────────────┘  └───────────┘  └───────────┘    └──────────────┘
```

---

## Free-Resource & Local AI Stack

- **Primary LLM:** Gemini API (`google-genai` free tier)
- **Local Fallback LLM:** Ollama (`http://localhost:11434` - local zero-cost)
- **OCR & Document Extraction:** PyMuPDF / Direct PDF & Text Parser
- **ML Framework:** scikit-learn (Logistic Regression / Random Forest)
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy, SQLite/PostgreSQL
- **Vector Search / RAG:** FAISS / Sentence Transformers (Local)

---

## Project Structure

```
Loan Document Processing Agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # Health & V1 endpoints
│   │   ├── core/           # Config, Logging, LLM Provider Abstraction
│   │   ├── db/             # SQLAlchemy Base, Session, Models
│   │   └── main.py         # FastAPI App Entrypoint
│   ├── tests/              # Pytest Unit Tests
│   ├── Dockerfile
│   └── requirements.txt
├── data/
│   ├── raw/                # Kaggle loan_approval_dataset.csv
│   ├── processed/          # applicant_profiles.csv & document_manifest.csv
│   ├── applicants/         # A001..A010 synthetic document folders
│   └── policies/           # Policy RAG documents
├── frontend/               # React Dashboard (Phase 18)
├── scripts/                # Utility scripts (manifest generator, seeders)
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## How to Run & Test

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Run Tests
```bash
PYTHONPATH=backend venv/bin/pytest backend/tests
```

### 3. Run FastAPI Dev Server
```bash
PYTHONPATH=backend venv/bin/python backend/app/main.py
```
Or with Uvicorn:
```bash
PYTHONPATH=backend venv/bin/uvicorn app.main:app --reload
```

Interactive API documentation available at: `http://localhost:8000/docs`
