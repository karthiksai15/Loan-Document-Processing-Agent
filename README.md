# Loan Document Processing Agent

A GenAI-powered loan document processing and decision-support system that assists loan officers in reviewing applications, identifying missing documents, detecting inconsistencies, retrieving relevant policies, and generating evidence-grounded review summaries.

## Live Demo

**Application:**
https://loan-document-processing-agent.vercel.app

**Backend API:**
https://loan-document-processing-backend.onrender.com

**API Documentation (Swagger):**
https://loan-document-processing-backend.onrender.com/docs

### Deployment

```text
Frontend
    |
    | Vercel
    v
Loan Document Processing Agent
    |
    | HTTPS / REST API
    v
Backend
    |
    | Render
    v
FastAPI Application
    |
    +-------------------+
    |                   |
    v                   v
Neon PostgreSQL       Gemini
    |                   |
    |                   +-- LLM
    |                   |
    |                   +-- Embeddings
    |
    v
Application Data

Policy Retrieval
    |
    v
FAISS Vector Store
```

| Component           | Technology / Platform       |
| ------------------- | --------------------------- |
| Frontend            | Vercel                      |
| Backend             | FastAPI on Render           |
| Database            | Neon PostgreSQL             |
| Agent Orchestration | LangGraph                   |
| LLM                 | Gemini                      |
| Embeddings          | Gemini Embeddings           |
| Vector Search       | FAISS                       |
| Machine Learning    | Scikit-learn / RandomForest |

---

## Project Overview

Loan processing requires reviewing multiple documents such as payslips, bank statements, tax returns, and KYC documents. Manual review requires repeatedly checking documents, comparing information, identifying missing documents, and referring to applicable policies.

The Loan Document Processing Agent automates these information-processing and investigation tasks while keeping the final lending decision with the human loan officer.

---

## Problem

The system addresses the following problems:

| Problem                     | How the System Addresses It                    |
| --------------------------- | ---------------------------------------------- |
| Manual document review      | Structured document processing                 |
| Missing documents           | Automated document completeness checks         |
| Information inconsistencies | Cross-document verification                    |
| Risk assessment             | RandomForest-based statistical risk estimation |
| Policy lookup               | RAG-based policy retrieval                     |
| Unsupported AI responses    | Evidence and policy grounding                  |
| Repetitive investigation    | LangGraph-based agent workflow                 |
| Autonomous AI decisions     | Human-in-the-loop decision boundary            |

---

## Solution

```text
Loan Application
       |
       v
Document Processing
       |
       v
Data Extraction
       |
       v
Validation
       |
       v
Cross-Document Verification
       |
       +-------------------+
       |                   |
       v                   v
  RandomForest          Policy RAG
  Risk Assessment       FAISS + Gemini
       |                   |
       +---------+---------+
                 |
                 v
            LangGraph Agent
                 |
                 v
             Gemini LLM
                 |
                 v
          Grounded AI Review
                 |
                 v
          Human Loan Officer
                 |
                 v
          Final Decision
```

---

## Architecture

```text
                         USER
                          |
                          v
                +-------------------+
                | Vercel Frontend   |
                +---------+---------+
                          |
                       HTTPS
                          |
                          v
                +-------------------+
                | FastAPI Backend   |
                |      Render       |
                +---------+---------+
                          |
                          v
                +-------------------+
                | LangGraph Agent   |
                +---------+---------+
                          |
        +-----------------+------------------+
        |                 |                  |
        v                 v                  v
+---------------+  +-------------+  +----------------+
| Document      |  | RandomForest|  | Policy RAG     |
| Processing    |  | ML Model   |  |                |
+-------+-------+  +------+------+  +-------+--------+
        |                 |                 |
        |                 |          +------+------+
        |                 |          |             |
        |                 |          v             v
        |                 |       Gemini         FAISS
        |                 |     Embeddings
        |                 |          |
        +-----------------+----------+
                          |
                          v
                    Gemini LLM
                          |
                          v
                   AI Review Result
                          |
                          v
                   Loan Officer
```

---

## Key Technologies

### FastAPI

Backend API layer responsible for communication between the frontend and the processing system.

### LangGraph

Orchestrates the investigation workflow and controls the sequence of agent operations.

### RandomForest

Provides a statistical estimate of historical rejection risk from application features.

### Gemini

Generates the natural-language review and synthesizes application evidence, ML results, and retrieved policy context.

### Gemini Embeddings

Converts policy text and search queries into vector representations for semantic retrieval.

### FAISS

Performs similarity search over the policy knowledge base.

### PostgreSQL

Stores persistent application, document, review, and related processing data.

---

## AI Processing Flow

```text
Application
    |
    v
Collect Evidence
    |
    +---- Documents
    |
    +---- Verification Results
    |
    +---- ML Risk
    |
    +---- Retrieved Policies
    |
    v
LangGraph Agent
    |
    v
Gemini LLM
    |
    v
Structured AI Review
    |
    v
Grounding Check
    |
    v
Loan Officer
```

---

## Example Scenarios

### A003 — Missing Tax Return

The system identifies that the Tax Return is missing and retrieves the applicable policy.

```text
Payslip          Available
Bank Statement   Available
Tax Return       Missing
KYC              Available
```

Result:

```text
DOCUMENT_FOLLOWUP
```

### A004 — Income Discrepancy

The system detects a mismatch between income-related information in the payslip and bank statement.

Result:

```text
OFFICER_INVESTIGATION
```

### A006 — Identity Mismatch

The system identifies an inconsistency between applicant identity information and the KYC document.

Result:

```text
OFFICER_INVESTIGATION
```

---

## Human-in-the-Loop

The AI system provides analysis and recommendations but does not make the final lending decision.

```text
AI Analysis
     |
     v
Evidence
     +
ML Risk
     +
Policy
     +
LLM Review
     |
     v
Recommendation
     |
     v
Human Loan Officer
     |
     v
Final Lending Decision
```

---

## Validation

The implementation was validated through both automated tests and production testing.

```text
Backend Tests
245 passed
```

Production scenarios:

```text
A003  Missing Tax Return    PASS
A004  Income Discrepancy    PASS
A006  Identity Mismatch     PASS
```

The deployed system was also verified for Gemini embeddings, FAISS retrieval, AI grounding, frontend-backend integration, and Render runtime stability.

---

## Repository

The complete source code, backend, frontend, policy knowledge base, vector index, tests, and deployment configuration are maintained in the GitHub repository.

**GitHub:**
https://github.com/karthiksai15/Loan-Document-Processing-Agent

---

## Limitations

* Demonstration documents are synthetic.
* The policy knowledge base contains configured demonstration policies.
* ML output represents statistical risk estimation and is not a lending decision.
* The system is designed for decision support and human review.

---

## Future Scope

* Improved OCR and document extraction
* Additional document types
* Larger policy knowledge base
* More advanced risk models
* Enhanced agent planning
* Authentication and role-based access
* Detailed audit logging
* Production monitoring
* CI/CD automation

