# HackBase

Agentic AI-powered hackathon problem discovery and recommendation platform.
HackBase turns a natural-language query into ranked hackathon recommendations,
project roadmaps, and starter resources, via a multi-agent RAG pipeline.

## Tech Stack

- **Frontend:** React
- **Backend:** FastAPI
- **LLM Inference:** Gemini API
- **Vector Store:** ChromaDB / FAISS
- **Orchestration:** LangChain / LangGraph
- **Structured Data:** PostgreSQL
- **Experiment Tracking:** MLflow
- **CI/CD:** GitHub Actions
- **Containerization:** Docker (deferred until closer to deployment)

## Core Agents

| Agent | Responsibility |
|---|---|
| Search | Retrieve relevant hackathon/problem statements from the vector store |
| Ranking | Score and rank candidates against the user's query/profile |
| Planning | Generate a project roadmap for the selected problem |
| Resource | Surface starter resources, docs, and repos |

## Project Layout

```
hackbase/
├── backend/          # FastAPI app, agents, RAG pipeline, scrapers
├── frontend/         # React app
├── data/             # raw / processed / seed data (SIH, Devpost, etc.)
├── mlflow/           # local MLflow tracking store
├── docs/             # architecture notes, ADRs, presentation assets
└── .github/workflows # CI/CD
```

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in GEMINI_API_KEY, DATABASE_URL, etc.
uvicorn app.main:app --reload
```

Health check: http://localhost:8000/health

Schema is managed with Alembic (`backend/migrations/`) — `app/main.py` applies any pending migrations automatically on startup, so the command above is still all you need. After changing a model in `app/models/`, generate a migration for it:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
```

Review the generated file in `migrations/versions/` before committing — autogenerate is a good first draft, not always exactly right.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Build Order

1. Data foundation (scrapers + seed corpus from SIH releases)
2. RAG core (chunking, embeddings, ChromaDB/FAISS indexing)
3. Agents, one at a time (Search → Ranking → Planning → Resource)
4. Frontend integration

Docker/containerization is intentionally deferred — revisit closer to deployment.
