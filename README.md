# 🤖 AI-Powered Candidate Screening System

> An intelligent, role-based interview platform that dynamically generates technical questions using Retrieval-Augmented Generation (RAG) — powered by Mistral AI, LanceDB, and FastAPI.

**Live Demo:** http://135.235.217.253

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Key Design Decisions](#key-design-decisions)
4. [Tech Stack](#tech-stack)
5. [Features](#features)
6. [Project Structure](#project-structure)
7. [Setup Instructions](#setup-instructions)
8. [API Reference](#api-reference)
9. [RAG Pipeline](#rag-pipeline)
10. [Database Schema](#database-schema)
11. [Environment Variables](#environment-variables)

---

## Overview

This system simulates a structured technical interview where questions are **not predefined** but instead dynamically generated based on:

- The **candidate's resume** (skills, experience, education)
- The **selected job role** (e.g., AI/ML Engineer, Backend Engineer)
- A **role-specific knowledge base** (ML textbooks indexed via vector embeddings)

The result is a personalised, adaptive interview experience where every session is unique.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User (Browser)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │  HTTP (port 80)
┌─────────────────────▼───────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                       │
│   /         → React Frontend (static files)                     │
│   /api/*    → FastAPI Backend (port 8080)                       │
└─────────┬───────────────────────┬───────────────────────────────┘
          │                       │
┌─────────▼──────────┐  ┌─────────▼──────────────────────────────┐
│  React Frontend     │  │        FastAPI Backend                 │
│  (Vite + React 19) │  │                                        │
│                    │  │  ┌──────────────┐  ┌────────────────┐  │
│  - LoginScreen     │  │  │ ResumeParser │  │ InterviewMgr   │  │
│  - SignupScreen    │  │  │  (PyMuPDF +  │  │ (Orchestrates  │  │
│  - UploadScreen    │  │  │   Mistral)   │  │  RAG pipeline) │  │
│  - InterviewChat   │  │  └──────┬───────┘  └───────┬────────┘  │
│  - Dashboard       │  │         │                   │           │
│  - HistoryScreen   │  │  ┌──────▼───────────────────▼────────┐  │
└────────────────────┘  │  │         RAG Engine                 │  │
                        │  │  Mistral Embed → LanceDB Search    │  │
                        │  │  → Mistral Generate (question/eval)│  │
                        │  └──────────────────────┬────────────┘  │
                        │                         │               │
                        │  ┌──────────────────────▼────────────┐  │
                        │  │       Data Layer                   │  │
                        │  │  SQLite (sessions, Q&A, scores)    │  │
                        │  │  LanceDB (vector embeddings)       │  │
                        │  └───────────────────────────────────┘  │
                        └────────────────────────────────────────┘
```

### Request Flow

```
Resume Upload → Parse (PyMuPDF + Mistral) → Store Profile (SQLite)
     ↓
Start Session → Build Query (resume + role) → RAG Retrieve (LanceDB)
     ↓
Generate Question (Mistral + retrieved context) → Send to UI
     ↓
Candidate Answers → Evaluate (Mistral + context) → Score + Feedback
     ↓
Repeat (adaptive difficulty) → Session Complete → Summary + Insights
```

---

## Key Design Decisions

### 1. RAG over Fine-tuning
**Decision:** Use RAG (Retrieval-Augmented Generation) instead of fine-tuning a model.

**Reasoning:**
- Fine-tuning requires massive compute and time — not feasible in 48 hours
- RAG allows grounding questions in **specific book content** (Tom Mitchell, Bishop, etc.)
- Easier to update the knowledge base without retraining
- Questions remain traceable to source documents (every question stores `source_chunks`)

### 2. LanceDB for Vector Storage
**Decision:** LanceDB instead of Pinecone/Weaviate/ChromaDB.

**Reasoning:**
- **Embedded** — no external service required, works inside Docker
- Backed by Apache Arrow — fast columnar storage
- Supports cosine similarity search natively
- Zero-cost for self-hosted deployment

### 3. Mistral AI for Embeddings + Generation
**Decision:** Mistral (`mistral-embed` + `mistral-small-latest`) instead of OpenAI.

**Reasoning:**
- Mistral's `mistral-embed` produces 1024-dimensional embeddings — richer than OpenAI's ada-002
- `mistral-small-latest` is fast and cost-effective for real-time interview Q&A
- Single API key for both embedding and generation — simpler config

### 4. Adaptive Difficulty
**Decision:** Questions adapt based on previous answer scores.

**Reasoning:**
- A candidate scoring >80 gets harder follow-up questions
- A candidate scoring <40 gets a supportive pivot to a related but simpler topic
- Mirrors how real interviewers adjust on the fly — creates a realistic experience

### 5. SQLite for Persistence
**Decision:** SQLite instead of PostgreSQL.

**Reasoning:**
- Zero-config, file-based — perfect for Docker single-container deployments
- Sufficient for screening workloads (not millions of concurrent users)
- Entire DB is a single file — easy to back up and migrate

### 6. Separation of Concerns (Services Layer)
```
app/
├── main.py              ← HTTP routing only, no business logic
├── auth.py              ← Authentication (JWT, bcrypt)
├── models.py            ← DB schema definitions
├── schemas.py           ← Pydantic request/response models
├── config.py            ← Environment variable loading
└── services/
    ├── resume_parser.py ← Resume parsing logic (isolated)
    ├── rag_engine.py    ← All vector DB + LLM calls (isolated)
    ├── interview_manager.py ← Interview orchestration (isolated)
    ├── chunker.py       ← Document chunking strategy
    └── ingest_kb.py     ← Knowledge base ingestion script
```
Each service is independently testable and replaceable.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19 + Vite | UI framework |
| **Styling** | Vanilla CSS | Responsive design |
| **Backend** | FastAPI (Python 3.11) | REST API |
| **Auth** | JWT + bcrypt (passlib) | Secure sessions |
| **LLM** | Mistral AI (mistral-small-latest) | Question generation & evaluation |
| **Embeddings** | Mistral AI (mistral-embed) | 1024-dim semantic vectors |
| **Vector DB** | LanceDB | Semantic retrieval |
| **Relational DB** | SQLite + SQLAlchemy | Session/answer persistence |
| **PDF Parsing** | PyMuPDF | Resume text extraction |
| **Proxy** | Nginx | Frontend serving + API routing |
| **Containers** | Docker + Docker Compose | Deployment orchestration |

---

## Features

- 🔐 **Authentication** — Signup/login with JWT tokens
- 📄 **Resume Upload** — PDF parsing with skill/experience extraction via Mistral
- 🎯 **Role Selection** — AI/ML Engineer, Backend Engineer, Data Scientist, etc.
- 🧠 **RAG-powered Questions** — Questions grounded in ML textbooks, not templates
- 🔄 **Adaptive Difficulty** — Adjusts based on candidate's performance in real-time
- 💬 **Interactive Interview Chat** — Conversational Q&A interface
- 📊 **Scoring & Feedback** — Per-question score (0–100) with constructive feedback
- 📝 **Session Summary** — AI-generated insights after every interview
- 🕓 **Interview History** — View all past sessions and scores

---

## Project Structure

```
pgagi_task/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + all API endpoints
│   │   ├── auth.py              # JWT authentication
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # DB connection setup
│   │   └── services/
│   │       ├── rag_engine.py        # LanceDB + Mistral RAG core
│   │       ├── interview_manager.py # Question generation & evaluation
│   │       ├── resume_parser.py     # PDF → structured profile
│   │       ├── chunker.py           # Text chunking strategy
│   │       └── ingest_kb.py         # Book ingestion script
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginScreen.jsx
│   │   │   ├── SignupScreen.jsx
│   │   │   ├── UploadScreen.jsx     # Resume upload + role selection
│   │   │   ├── InterviewChat.jsx    # Live interview Q&A
│   │   │   ├── Dashboard.jsx        # Session summary
│   │   │   └── HistoryScreen.jsx    # Past sessions
│   │   ├── api.js                   # All API calls (axios)
│   │   └── App.jsx                  # Routing
│   ├── nginx.conf
│   └── Dockerfile
├── books/                           # Knowledge base PDFs
│   ├── MachineLearningTomMitchell.pdf
│   ├── Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf
│   └── Introduction to Machine Learning with Python.pdf
├── docker-compose.yml
├── .env                             # API keys (not committed)
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Docker + Docker Compose installed
- A Mistral AI API key ([get one free at console.mistral.ai](https://console.mistral.ai))

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd pgagi_task
```

### 2. Configure environment variables
Create a `.env` file in the project root:
```env
MISTRAL_API_KEY=your_mistral_api_key_here
CORS_ORIGINS=http://localhost,http://localhost:5173
```

### 3. Ingest the Knowledge Base (first time only)
Before starting the app, populate the vector database with the ML books:
```bash
# From the project root
docker compose run --rm backend python -m app.services.ingest_kb
```
This processes the PDFs, chunks the text, generates Mistral embeddings, and stores them in LanceDB. Takes ~5–10 minutes depending on API rate limits.

### 4. Start the application
```bash
docker compose up -d --build
```

### 5. Access the app
- **Frontend:** http://localhost
- **Backend API docs:** http://localhost:8080/docs

### Local Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | ❌ | Register new candidate |
| `POST` | `/auth/login` | ❌ | Login, returns JWT token |
| `POST` | `/upload-resume` | ✅ | Upload PDF + select role |
| `POST` | `/sessions/start` | ✅ | Begin interview session |
| `GET` | `/sessions/{id}/question` | ✅ | Get next generated question |
| `POST` | `/sessions/{id}/answer` | ✅ | Submit answer, get score + feedback |
| `GET` | `/sessions/{id}/summary` | ✅ | Get full session summary + insights |
| `GET` | `/sessions/history` | ✅ | List all past sessions |
| `GET` | `/health` | ❌ | Health check |

**Interactive API docs:** http://localhost:8080/docs (Swagger UI)

---

## RAG Pipeline

```
1. INGESTION (one-time setup)
   PDF Books → PyMuPDF text extraction
       → Chunker (fixed-size with overlap)
       → Mistral mistral-embed (1024-dim vectors)
       → LanceDB storage

2. RETRIEVAL (per question)
   Resume skills + Role → Dynamic query string
       → Mistral embed query → 1024-dim vector
       → LanceDB ANN search → Top-5 relevant chunks

3. GENERATION (per question)
   Retrieved chunks + Candidate profile + History
       → Mistral mistral-small-latest
       → Contextual, role-specific question

4. EVALUATION (per answer)
   Question + Answer + Source chunks
       → Mistral mistral-small-latest
       → JSON: { score, feedback, suggestions }
```

### Chunking Strategy
- **Chunk size:** ~500 tokens with 50-token overlap
- **Overlap reasoning:** Prevents context loss at chunk boundaries — critical for conceptual ML topics that span multiple paragraphs

---

## Database Schema

```sql
-- Candidates (users)
candidates (id, name, email, hashed_password, phone, location,
            experience_years, education, skills, resume_path, profile_summary)

-- Interview sessions
interview_sessions (id, candidate_id, role, start_time, end_time,
                    overall_score, status, difficulty, question_count, time_limit)

-- Questions and answers (with traceability)
question_answers (id, session_id, question, answer, evaluation,
                  score, evaluation_timestamp)
-- Note: `evaluation` JSON field stores source_chunks for traceability
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MISTRAL_API_KEY` | ✅ Yes | Mistral AI API key for embeddings + generation |
| `CORS_ORIGINS` | ✅ Yes | Allowed frontend origins (comma-separated) |
| `DATABASE_URL` | ❌ Optional | SQLite path (default: `./candidate_screening.db`) |

---

## Deployment

The app is containerised and deployed on an Azure VM:

```
Azure VM (Standard_B2ats_v2 — Ubuntu 24.04)
  └── Docker Compose
        ├── backend  → FastAPI on :8080
        └── frontend → Nginx on :80 (serves React + proxies /api to backend)
```

Both services use `restart: unless-stopped` and a systemd service ensures auto-start on VM reboot.

---

*Built for the PGAGI AI/ML & Backend Intern Assignment*
