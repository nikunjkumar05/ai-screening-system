# AI-Powered Candidate Screening System — Technical Documentation

**Built for:** PGAGI AI/ML & Backend Intern Assignment (48-hour window)
**Live:** http://135.235.217.253
**Repo:** https://github.com/nikunjkumar05/ai-screening-system

---

## What This Does

This is a technical interview simulator. A candidate uploads their resume, picks a job role, and gets grilled with dynamically generated questions. The questions aren't pulled from a question bank — they're generated on the fly using RAG (Retrieval-Augmented Generation) grounded in ML textbooks. The system evaluates each answer, scores it, and adapts the difficulty based on how the candidate is doing.

Think of it as: Resume In → RAG-powered Interview → Scored Report Out.

---

## Architecture

```
Browser (React 19)
    ↓ HTTP (port 80)
Nginx (reverse proxy)
    ├── / → serves React static files
    └── /api/* → proxies to FastAPI on port 8080
         ↓
FastAPI Backend
    ├── Auth (JWT + bcrypt)
    ├── Resume Parser (PyMuPDF + Mistral AI)
    ├── RAG Engine (LanceDB + Mistral embeddings)
    ├── Interview Manager (question gen + answer eval)
    └── SQLite (candidates, sessions, Q&A)
```

The whole thing runs in two Docker containers — nginx for the frontend and uvicorn for the backend. LanceDB is embedded (no separate service needed), and SQLite is file-based. One `docker compose up` and it's running.

---

## How the Interview Flow Works

### 1. Resume Upload

The candidate uploads a PDF or TXT resume. PyMuPDF extracts the raw text, then Mistral AI (`mistral-small-latest`) parses it into structured fields: name, email, skills, experience years, education, and a profile summary. This gets stored in the `candidates` table.

**Code:** `backend/app/services/resume_parser.py`

### 2. Session Start

When the candidate picks a role (AI/ML Engineer, Data Scientist, or Computer Vision Engineer) and starts the interview:

- A new `InterviewSession` row is created in SQLite
- A `RAGEngine` instance is created for that role
- An `InterviewManager` is created and stored in an in-memory dict (`active_sessions`)
- The interview is now live

**Code:** `backend/app/main.py:197-241`

### 3. Question Generation

Each question goes through this pipeline:

```
Candidate profile + Role + Previous Q&A history
    ↓
RAG Query string built
    ↓
Mistral embed query (1024-dim vector)
    ↓
LanceDB cosine similarity search (top-5 chunks)
    ↓
LLM prompt with: retrieved chunks + interview history + guardrails
    ↓
Mistral generates a question
```

The prompt has strict guardrails to prevent the LLM from asking generic trivia:
- Must test deep conceptual understanding, not definitions
- Must be 1-2 sentences max (no essays)
- Must maintain conversational flow (follow-up or smooth pivot, not random)
- Must be conceptual, not coding

**Code:** `backend/app/services/interview_manager.py:16-65`

### 4. Answer Evaluation

After the candidate answers:

```
Question + Answer + Reference chunks from knowledge base
    ↓
LLM evaluates: score (0-100), feedback (2-3 bullets), suggestions (1-2 bullets)
    ↓
Strict scoring guardrails: use full 0-100 scale, be brutally honest
    ↓
Result stored in question_answers table
```

If the candidate scores well, the next question adapts. If they score poorly, the system can pivot to a related but simpler topic.

**Code:** `backend/app/services/interview_manager.py:67-107`

### 5. Session Completion

After all questions (default 5), the system:
- Marks the session as completed
- Calculates the overall score (average of all question scores)
- Generates AI insights by analyzing the full transcript
- The dashboard shows everything: score, Q&A breakdown, source chunks used, and insights

---

## Knowledge Base (RAG)

The question quality depends entirely on the knowledge base. Right now it has:

| Role | Books |
|------|-------|
| AI/ML Engineer | Tom Mitchell's "Machine Learning", Bishop's "Pattern Recognition and Machine Learning" |
| Data Scientist | "Introduction to Machine Learning with Python" |

### How to Add More Content

```bash
# Ingest a new book for a role
docker compose run --rm backend python -m app.services.ingest_kb \
    --role "AI/ML Engineer" \
    --pdf books/NewBook.pdf

# Multiple books at once
docker compose run --rm backend python -m app.services.ingest_kb \
    --role "Data Scientist" \
    --pdf book1.pdf book2.pdf book3.pdf
```

### Chunking Strategy

- **Chunk size:** 800 characters
- **Overlap:** 150 characters
- **Break at sentence boundaries** when possible (looks back up to 200 chars for `.` or `\n`)
- **Embeddings:** Mistral `mistral-embed` (1024 dimensions), stored in LanceDB

**Code:** `backend/app/services/chunker.py`

---

## Database Schema

Three tables, all in SQLite:

### candidates
```
id (PK), name, email (unique), hashed_password, phone, location,
experience_years, education, skills (text), resume_path, profile_summary
```

### interview_sessions
```
id (PK), candidate_id (FK), role, start_time, end_time,
overall_score, status, difficulty, question_count, time_limit
```

### question_answers
```
id (PK), session_id (FK), question (text), answer (text),
evaluation (JSON text — stores source_chunks), score, evaluation_timestamp
```

The `evaluation` field on `question_answers` doubles as traceability storage. When a question is generated, the retrieved chunks are saved there so you can see exactly which parts of the knowledge base influenced each question.

---

## API Endpoints

| Method | Path | Auth | What It Does |
|--------|------|------|-------------|
| `POST` | `/auth/signup` | No | Register a new user |
| `POST` | `/auth/login` | No | Login, returns JWT |
| `POST` | `/upload-resume` | JWT | Upload resume PDF + select role |
| `POST` | `/sessions/start` | JWT | Begin interview session |
| `GET` | `/sessions/{id}/question` | JWT | Get next generated question |
| `POST` | `/sessions/{id}/answer` | JWT | Submit answer, get score + feedback |
| `GET` | `/sessions/{id}/summary` | JWT | Get full session summary + AI insights |
| `GET` | `/sessions/history` | JWT | List all past sessions for the user |
| `GET` | `/health` | No | Health check |

Interactive docs at: http://localhost:8080/docs

---

## Frontend

React 19 + Vite, no TypeScript. Six components, simple state machine in `App.jsx`:

```
LOGIN/SIGNUP → UPLOAD → INTERVIEW → DASHBOARD
                         ↓
                      HISTORY → DASHBOARD
```

### Key Components

- **UploadScreen** — Role/difficulty/count selection + resume drag-and-drop
- **InterviewChat** — Live Q&A with countdown timer, speech-to-text (Web Speech API), expandable history accordion per question
- **Dashboard** — Score visualization, candidate profile, AI executive summary, detailed Q&A breakdown with RAG source chunk traceability
- **HistoryScreen** — List of all past sessions with scores

### Styling

Glassmorphism dark mode. CSS custom properties for theming, `backdrop-filter: blur()` for glass panels, gradient accents. No Tailwind — just vanilla CSS. Framer-motion for page transitions and accordion animations.

---

## Running Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
# Create .env with MISTRAL_API_KEY=your_key_here
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on port 5173, proxies /api to localhost:8080
```

### With Docker

```bash
# First time: ingest knowledge base
docker compose run --rm backend python -m app.services.ingest_kb \
    --role "AI/ML Engineer" \
    --pdf books/MachineLearningTomMitchell.pdf

# Start everything
docker compose up -d --build

# Frontend: http://localhost
# Backend API docs: http://localhost:8080/docs
```

---

## Deployment (Azure VM)

The app runs on an Azure Standard_B2ats_v2 VM (Ubuntu 24.04).

```
Azure VM
└── Docker Compose
    ├── backend (uvicorn on :8080)
    └── frontend (nginx on :80)
```

Both containers use `restart: unless-stopped`. A systemd service ensures auto-start on VM reboot.

### How I Deploy Updates

```bash
# Via Azure CLI from local machine
az vm run-command invoke -g PGAGI -n pgagi-deployment \
    --command-id RunShellScript --scripts deploy.sh
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | Yes | — | Mistral AI API key |
| `DATABASE_URL` | No | `sqlite:///./candidate_screening.db` | SQLite path |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins |

---

## Design Decisions (and Why)

### RAG over Fine-tuning
Fine-tuning needs massive compute and time. RAG lets me ground questions in actual textbook content, is easier to update, and every question is traceable to source documents.

### LanceDB over Pinecone/ChromaDB
Embedded — no external service. Backed by Apache Arrow. Zero-cost for self-hosted. Works perfectly inside Docker.

### Mistral over OpenAI
`mistral-embed` produces 1024-dim vectors (richer than ada-002). `mistral-small-latest` is fast and cheap for real-time Q&A. Single API key for both embedding and generation.

### SQLite over PostgreSQL
Zero-config, file-based. Sufficient for screening workloads. Entire DB is one file — easy to back up.

### In-Memory Session Store
`active_sessions` dict in `main.py` holds `(RAGEngine, InterviewManager, qa_history)` per session. If the server restarts, sessions recover from the DB on the next question request. Trade-off: faster than re-hydrating from DB every time, but not persistent. For a production system I'd use Redis.

---

## Known Limitations

1. **No HTTPS** — The Azure VM runs HTTP only. In production you'd put this behind a load balancer with TLS termination.

2. **Hardcoded JWT secret** — `auth.py` has a hardcoded `SECRET_KEY`. Should come from env vars.

3. **No rate limiting** — The Mistral API calls could be throttled. Added retry logic with exponential backoff, but no application-level rate limiting.

4. **Session recovery is partial** — If the server restarts mid-interview, the `InterviewManager` is recreated but the difficulty adaptation state is lost. The first question after recovery won't have the full history context.

5. **No HTTPS on the live demo** — The Azure VM runs plain HTTP.

6. **Speech-to-text is browser-dependent** — Only works in Chrome/Edge. Firefox and Safari don't support the Web Speech API.

7. **Single-node deployment** — No horizontal scaling. Fine for a screening tool, not for production traffic.

---

## What I'd Do Differently

- Move JWT secret and all secrets to env vars or a vault
- Add proper session persistence (Redis) instead of in-memory dict
- Add HTTPS via Let's Encrypt + nginx
- Add unit tests (there are none right now)
- Add a rate limiter middleware for the Mistral API calls
- Add more roles with corresponding knowledge bases
- Add a candidate dashboard showing performance trends across multiple sessions
- Switch from SQLite to PostgreSQL for production
- Add proper CI/CD pipeline

---

## File Structure

```
pgagi_task/
├── backend/
│   ├── app/
│   │   ├── main.py              # All API endpoints
│   │   ├── auth.py              # JWT + bcrypt authentication
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # ORM models (3 tables)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── services/
│   │       ├── rag_engine.py        # LanceDB + Mistral RAG core
│   │       ├── interview_manager.py # Question gen + answer eval
│   │       ├── resume_parser.py     # PDF → structured profile
│   │       ├── chunker.py           # Text chunking strategy
│   │       └── ingest_kb.py         # CLI tool for KB ingestion
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginScreen.jsx
│   │   │   ├── SignupScreen.jsx
│   │   │   ├── UploadScreen.jsx
│   │   │   ├── InterviewChat.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   └── HistoryScreen.jsx
│   │   ├── api.js               # All API calls (axios)
│   │   └── App.jsx              # Screen state machine
│   ├── nginx.conf
│   └── Dockerfile
├── books/                       # Knowledge base PDFs
├── docker-compose.yml
└── .env
```
