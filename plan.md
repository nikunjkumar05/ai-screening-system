# Project Plan: AI-Powered Candidate Screening System

**Assignment**: PGAGI AI/ML & Backend Intern Assignment
**Duration**: 48 Hours

---

## Objective

Build an AI-powered role-based candidate screening system that simulates a structured technical interview where questions are **dynamically generated** (not predefined) based on:
- The candidate's resume
- The selected job role
- A role-specific knowledge base (textbook/corpus)

---

## Current Status: Phase 1 - In Progress

### What Exists
- FastAPI app structure with CORS
- SQLAlchemy models (Candidate, InterviewSession, QuestionAnswer)
- Database configuration (SQLite)
- Environment variable handling (.env)
- Resume text extraction (pymupdf)
- Basic Gemini API integration
- Basic interview manager structure

### Critical Issues
| File | Issue |
|------|-------|
| `backend/app/schemas.py` | Contains duplicate SQLAlchemy models instead of Pydantic schemas |
| `backend/app/services/rag_engine.py` | No vector persistence, no retrieval method |
| `backend/app/services/interview_manager.py` | Doesn't use RAG for actual retrieval, just sends prompt directly |
| `backend/app/main.py` | Missing interview flow endpoints and resume upload |

---

## System Flow (per Assignment Section 3)

```
Resume Upload (PDF/text) → Role Selection (Backend/AI-ML Engineer)
         ↓
Resume Processing (parse, extract: skills, technologies, domain exposure)
         ↓
Context Construction (generate meaningful queries from resume + role → identify relevant topics)
         ↓
Knowledge Retrieval (RAG: query role-specific KB, retrieve relevant chunks)
         ↓
Question Generation (using retrieved context: role-relevant, background-influenced, depth/reflection)
         ↓
Interactive Interview (UI: answer questions, session continuity, optional adaptation)
         ↓
Response Handling (store Q&A in structured records)
         ↓
Final Output (structured summary + basic insights/analysis of session)
```

---

## Implementation Roadmap

### Phase 1: Backend Fixes & API (Hours 1-8) — CURRENT

**1.1 Fix `schemas.py`**
Replace SQLAlchemy duplicate with Pydantic schemas:
- `CandidateCreate` — name, email, phone, location, experience_years, education, skills, resume_path
- `CandidateResponse` — includes id
- `SessionCreate` — candidate_id, role
- `SessionResponse` — includes id, status, start_time
- `QuestionResponse` — question_text, question_number, total_questions
- `AnswerSubmit` — answer_text
- `AnswerResponse` — evaluation, score, next_question
- `SessionSummary` — overall_score, questions_asked, answers_given, insights

**1.2 Add Missing API Endpoints**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/upload-resume` | POST | Parse resume PDF, extract skills/technologies/domain exposure, store candidate |
| `/sessions/start` | POST | Initialize session with candidate_id + role, return first question |
| `/sessions/{id}/question` | GET | Get current question for session |
| `/sessions/{id}/answer` | POST | Submit answer, evaluate against context, return next question or completion |
| `/sessions/{id}/summary` | GET | Get final summary with score, Q&A history, insights |

**1.3 Fix `rag_engine.py`**
- Add `load_embeddings()` / `save_embeddings()` — persist NumPy arrays to disk
- Add `retrieve(query, role, top_k=5)` — embed query, cosine similarity search, return top chunks with metadata
- Add `retrieve_with_traceability()` — return chunks with source document references for traceability

**1.4 Fix `interview_manager.py`**
- Use RAG retrieval to get context for each question
- Generate questions based on retrieved chunks (not generic prompts)
- Track question provenance (which chunks generated this question)
- Implement difficulty scaling based on: candidate experience + previous answers

---

### Phase 2: RAG Knowledge Base (Hours 8-16)

**2.1 Knowledge Base Setup**
```
backend/knowledge_base/
├── ml/
│   ├── tom_mitchell_ml.txt        (from Machine Learning - Tom Mitchell)
│   ├── burkov_100page_ml.txt      (from The Hundred-Page ML Book)
│   └── ml_for_beginners.txt       (from ML for Absolute Beginners)
├── data_science/
│   ├── ml_with_python.txt         (from Introduction to ML with Python)
│   └── brownlee_algorithms.txt    (from Master ML Algorithms)
├── embeddings/
│   ├── ml_embeddings.npy
│   ├── ml_metadata.json
│   ├── ds_embeddings.npy
│   └── ds_metadata.json
└── ingest_kb.py                   (CLI script to process textbooks)
```

**2.2 Chunking Strategy**
- Chunk size: 500-1000 characters
- Overlap: 100-200 characters (preserve context across boundaries)
- Metadata per chunk: source document, chapter/section, page number, role relevance

**2.3 Embedding Generation**
- Model: `text-embedding-004` (Gemini)
- Store embeddings as NumPy arrays
- Store metadata as JSON for traceability

**2.4 Role-Based Filtering**
- When querying for ML role → search ml/ embeddings
- When querying for Data Science role → search data_science/ embeddings
- Metadata tags enable cross-role queries if needed

---

### Phase 3: Interview Flow & Session Management (Hours 16-24)

**3.1 Session State Machine**
```
INITIALIZED → IN_QUESTION → ANSWERED → IN_QUESTION → ... → COMPLETED
```

**3.2 Question Flow**
1. Start session → parse resume → extract profile → select knowledge base
2. Generate first question using resume context + role + retrieved chunks
3. Candidate answers → evaluate answer against retrieved context
4. Generate next question considering:
   - Candidate's experience level (from resume)
   - Previous answer scores (track performance trend)
   - Topic coverage (don't repeat same domain)
5. After 5 questions → end session, calculate overall score

**3.3 Answer Evaluation**
- Score: 0-100 based on accuracy, depth, relevance
- Feedback: specific to the answer
- Source reference: which chunks were used for evaluation

**3.4 Traceability**
- Each question must store: which chunks were retrieved, which chunk generated the question
- Final summary must show: question → source chunks → answer → evaluation chain

---

### Phase 4: Frontend (Hours 24-36)

**4.1 Tech Stack**
- React + Vite
- Tailwind CSS (glassmorphism dark-mode)
- shadcn/ui components
- lucide-react icons

**4.2 Page Structure**
```
frontend/src/
├── pages/
│   ├── HomePage.tsx        — Landing with role selection cards
│   ├── UploadPage.tsx      — Resume upload with drag-drop
│   ├── InterviewPage.tsx   — Live chat interface with step indicators
│   └── SummaryPage.tsx     — Results dashboard with charts
├── components/
│   ├── FileUpload.tsx
│   ├── ChatMessage.tsx
│   ├── QuestionCard.tsx
│   ├── ScoreChart.tsx
│   └── StepIndicator.tsx
├── services/
│   └── api.ts              — Backend API client (fetch/axios)
├── App.tsx
└── main.tsx
```

**4.3 UI Requirements**
- Resume upload interface (PDF/text)
- Role selection (Backend Engineer, AI/ML Engineer)
- Interview interaction flow (question → answer → next)
- Results/summary view with:
  - Overall score visualization
  - Per-question breakdown
  - Skill/technology assessment
  - Basic insights and analysis

**4.4 State Management**
- Track current session state
- Store question/answer history for current session
- Handle loading/error states

---

### Phase 5: Integration & Testing (Hours 36-42)

- End-to-end flow testing (upload → interview → summary)
- Error handling and validation
- API documentation (FastAPI auto-generated)
- Edge cases: empty resume, failed API calls, session timeout

---

### Phase 6: Polish & Deliverables (Hours 42-48)

**6.1 Final README.md**
- Setup instructions (backend + frontend)
- System architecture diagram
- Key design decisions and reasoning
- API endpoint documentation

**6.2 Demo Video (Mandatory)**
- Show complete system flow end-to-end
- Highlight key features
- Demonstrate component interaction

**6.3 Code Cleanup**
- Remove dead code
- Consistent formatting
- No console errors

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│  React + Vite + Tailwind + shadcn/ui                    │
│  - Resume Upload & Role Selection                       │
│  - Live Interview Chat Interface                        │
│  - Results Dashboard with Charts                        │
└───────────────────────────┬─────────────────────────────┘
                            │ API (JSON)
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     BACKEND                             │
│  FastAPI (Python)                                       │
│  ├── Resume Parser (pymupdf + Gemini)                   │
│  │   └── Extracts: skills, technologies, domain         │
│  ├── RAG Engine                                         │
│  │   ├── Knowledge Ingestion (chunking + embeddings)    │
│  │   └── Retrieval (cosine similarity + role filtering) │
│  ├── Interview Manager                                  │
│  │   ├── Question Generation (from retrieved context)   │
│  │   ├── Answer Evaluation (against source chunks)      │
│  │   └── Difficulty Adaptation (experience + performance)│
│  └── Session Manager (state machine + DB operations)    │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                           │
│  ├── SQLite                                             │
│  │   ├── candidates (profile, skills, resume)           │
│  │   ├── interview_sessions (status, score)             │
│  │   └── question_answers (Q, A, evaluation, score)     │
│  └── NumPy Files (.npy)                                 │
│      ├── {role}_embeddings.npy                          │
│      └── {role}_metadata.json                           │
└─────────────────────────────────────────────────────────┘
```

---

## Design Reasoning (per Assignment Requirement)

1. **NumPy over Vector DB** — No external dependencies, sufficient for single-user demo, easy to persist/load
2. **Gemini for both embeddings + generation** — Single API key, consistent model behavior
3. **Pydantic schemas separate from models** — Clean API contracts, validation at boundary
4. **Session state machine** — Reliable interview flow, easy to resume/debug
5. **Traceability chain** — Each question links to source chunks, enabling verification and debugging
6. **Role-based KB filtering** — Different question pools per role, avoids cross-contamination
7. **Difficulty adaptation** — Scales with candidate experience and performance (optional but valuable per assignment)

---

*Last Updated: 2026-07-03*
