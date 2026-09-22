# HackBase Architecture

## Pipeline Overview

```
User query (NL)
      │
      ▼
 [Search Agent] ──uses──► RAG retriever ──uses──► ChromaDB/FAISS index
      │
      ▼
 [Ranking Agent] ── scores candidates against query/profile
      │
      ▼
 Ranked results ──► user selects a problem
      │
      ▼
 [Planning Agent] ── generates phased roadmap (Gemini)
      │
      ▼
 [Resource Agent] ── surfaces starter docs/repos/tutorials
      │
      ▼
 Roadmap + resources returned to frontend
```

## Data Flow

```
Scrapers (SIH / Devpost / Unstop / HackerEarth)
      │  graceful degradation — one source failing doesn't break the rest
      ▼
data/raw/*.json
      │  clean + chunk
      ▼
data/processed/*
      │  embed
      ▼
ChromaDB/FAISS index ──► used by Retriever at query time
```

## Notes

- SIH's structured problem-statement releases are the seed corpus — most reliable format.
- HackerEarth requires headless browsing (Playwright) since listings are JS-rendered.
- Docker is deferred; PostgreSQL runs natively on Windows for now.
- MLflow tracks experiments locally under `./mlflow`.
