# Project Overview & Structure

Single-source config: use `.env` (copy from `env.example`). No other config files are needed.

## 📁 Directory Layout (concise)

```
.
├── docker-compose.yml        # Orchestration
├── env.example               # Env template (copy to .env)
├── data_pdf/                 # Input PDFs
├── data_processed/           # Parsed outputs and images
├── ingestion/                # Ingestion service
├── retrieval/                # Retrieval API + MCP
└── dashapp/                  # Dash UI
```

## 🔧 Components (what lives where)

**Ingestion (`ingestion/`)**
- `main.py`, `main_fused.py`: workers
- `processing/`: parsing, chunking, layout, image extraction, fused unit builder
- `embeddings/`: local/OpenAI embeddings + multimodal embedding helper
- `storage/`: Weaviate/Postgres clients + Weaviate schema helpers
- `models.py`, `config.py`: shared models and settings

**Retrieval (`retrieval/`)**
- `main.py`: FastAPI app (`/query`, `/documents`, etc.)
- `weaviate_client.py`: hybrid/vector search
- `embeddings.py`: query embeddings (local/OpenAI)
- `reranker.py`: optional reranking
- `mcp_server.py`, `mcp_tools.py`: agent-facing MCP tools

**Dash UI (`dashapp/`)**
- `app.py`: user UI for querying

**Database / Schema**
- `postgres/schema.sql`: tables for documents, images, content units

## ⚙️ Configuration (one place)
- Copy `env.example` → `.env` and edit.
- Modes: 
  - CPU default: `EMBEDDING_PROVIDER=local`, `EMBEDDING_DEVICE=cpu`
  - GPU: `EMBEDDING_DEVICE=cuda`
  - External API: `EMBEDDING_PROVIDER=openai` + `OPENAI_API_KEY`
- DB/Vector: `POSTGRES_*`, `WEAVIATE_*`
- Rerank optional: `RERANKER_PROVIDER`, `ENABLE_RERANK`

## 🔄 Data Flow (brief)
- Ingestion: PDF → parse/layout → chunk → embed → Weaviate vectors (+ Postgres links for fused units).
- Retrieval: query → embed → hybrid search (BM25+vector) → optional rerank → results with citations (and image refs if fused).
- MCP: agents call MCP server → retrieval API → Weaviate/Postgres.

## 🚀 Operations Quick Reference
- Start: `cp env.example .env && docker-compose up -d`
- Logs: `docker-compose logs -f [service]`
- Rebuild: `docker-compose build --no-cache [service] && docker-compose up -d [service]`
- Fused extras: run `postgres/schema.sql`, then `docker exec -it rag_ingestion python main_fused.py`

## 🌟 Key Features
- CPU-first defaults, GPU optional, or external embeddings via API.
- Text-image fused units with Postgres relationships + Weaviate vectors.
- Hybrid search with optional reranking.
- MCP tools for agent access.

## 🔮 Future Enhancements (high level)
- True multimodal embeddings (vision), auto-captioning, table extraction, visual search.