# RAG Pipeline - Navodila Stroji Celice

Production-ready Retrieval-Augmented Generation (RAG) pipeline for manufacturing documentation with images, supporting multiple interfaces (Dash UI, FastAPI, MCP for AI agents).

## 🏗️ Architecture

```
[PDF Documents]
       │
[Ingestion Service]
  - PyMuPDF4LLM (layout-aware parsing)
  - Unstructured (element extraction)
  - OpenAI embeddings
  - Chunking with metadata
       │
[Weaviate Vector DB]
  - Hybrid search (BM25 + vectors)
  - Multi-tenancy ready
  - Collections: Document, Chunk, (Future: Figure, Table)
       │
[Retrieval Service - FastAPI]
  - /query (hybrid + rerank)
  - /doc/{id}/page/{n}
  - WebSocket streaming
  - MCP tools for agents
       │                   │
   [Dash UI]              [AI Agents via MCP]
   (Plotly, WS)           (Claude, ChatGPT)
```

## 📦 Components

### 1. Ingestion Service
- **Parser**: PyMuPDF4LLM for layout-aware Markdown extraction
- **Chunker**: Semantic chunking with heading preservation (300-800 tokens)
- **Embeddings**: BAAI/bge-large-en-v1.5 (local) or OpenAI
- **Storage**: Weaviate with metadata (doc_id, page, section_path, bbox)

### 2. Retrieval Service (FastAPI)
- **Endpoints**:
  - `POST /query` - Hybrid search with optional reranking
  - `GET /doc/{doc_id}/page/{page}` - Page retrieval
  - `GET /health` - Health check
  - `WS /stream` - Streaming answers
- **Search**: Weaviate hybrid (BM25 + vector)
- **Reranker**: None (simplified setup)
- **MCP**: Model Context Protocol tools for agent integration

### 3. Dash UI
- Interactive query interface
- Source citations with page/bbox highlighting
- Real-time streaming answers (WebSockets)
- Document viewer with deep-linking

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM for embeddings
- (Optional) OpenAI API key for embeddings/reranking

### 1. Start Infrastructure (Weaviate)
```bash
cd ../1_Infrastructure_Weaviate
docker-compose up -d
```

### 2. Start RAG Services
```bash
cd 2_Apk_RAG_Navodila_Stroji_Celice
docker-compose up -d
```

### 3. Ingest Documents
```bash
# Trigger ingestion via API
curl -X POST http://localhost:8001/ingest/all
```

### 4. Access Services
- **Dash UI**: http://localhost:8050
- **FastAPI**: http://localhost:8001/docs
- **Weaviate**: http://localhost:8080

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Embeddings (choose one)
EMBEDDING_PROVIDER=local  # or 'openai'
OPENAI_API_KEY=sk-...     # if using OpenAI

# Reranker (optional)
RERANKER_PROVIDER=local   # or 'cohere'
COHERE_API_KEY=...        # if using Cohere

# Weaviate
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=          # if auth enabled

# Chunking
CHUNK_SIZE=600
CHUNK_OVERLAP=100
```

## 📊 Data Model (Weaviate)

### Collections

#### Document
```json
{
  "doc_id": "string",
  "title": "string",
  "source_uri": "string",
  "created_at": "datetime",
  "department": "string",
  "tags": ["string"]
}
```

#### Chunk
```json
{
  "doc_id": "string (ref)",
  "chunk_id": "string",
  "text": "string",
  "page": "int",
  "section_path": "string",
  "bbox": "string",
  "token_count": "int",
  "vector": [...]
}
```

#### Figure (Future)
```json
{
  "doc_id": "string (ref)",
  "page": "int",
  "caption": "string",
  "image_uri": "string",
  "bbox": "string",
  "vector": [...]
}
```

## 🔍 Usage Examples

### Python Client
```python
import requests

# Query
response = requests.post("http://localhost:8001/query", json={
    "query": "How to calibrate PTL007?",
    "top_k": 5,
    "rerank": True
})

results = response.json()
for result in results["results"]:
    print(f"[Page {result['page']}] {result['text']}")
```

### Dash UI
Navigate to http://localhost:8050, enter your question, and get:
- Streaming answer generation
- Source citations with page numbers
- Click citations to view exact page/region

### MCP (AI Agents)
```json
{
  "tool": "search_docs",
  "arguments": {
    "query": "What safety procedures apply to ROM27?",
    "top_k": 3
  }
}
```

## 🧪 Evaluation & Monitoring

### Ragas Metrics
- Context Relevance
- Groundedness
- Answer Relevance

### Grafana Dashboards
- Query latency
- Retrieval accuracy
- Token usage

## 🔐 Security

- **API Authentication**: JWT tokens (configure in FastAPI)
- **Weaviate**: OIDC/API key auth + RBAC
- **Multi-tenancy**: Department-level isolation available

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] Text ingestion with PyMuPDF4LLM
- [x] Hybrid search (BM25 + vectors)
- [x] FastAPI retrieval service
- [x] Dash UI
- [x] MCP server for agents

### Phase 2 (Future)
- [ ] Image extraction and CLIP embeddings
- [ ] Table parsing with html/markdown output
- [ ] Florence-2 or BLIP-2 for image captioning
- [ ] Multi-modal retrieval UI

### Phase 3 (Future)
- [ ] Ragas/TruLens evaluation pipeline
- [ ] Prometheus metrics + Grafana dashboards
- [ ] Advanced filters (department, date range, tags)
- [ ] User feedback loop for continuous improvement

## 🛠️ Tech Stack

- **Vector DB**: Weaviate (hybrid search)
- **Embeddings**: BAAI/bge-large-en-v1.5 (local) or OpenAI
- **Parser**: PyMuPDF4LLM + Unstructured
- **Reranker**: BGE reranker or Cohere Rerank
- **API**: FastAPI + Uvicorn
- **UI**: Dash (Plotly)
- **Agent Protocol**: MCP (Model Context Protocol)

## 📚 Documentation Structure

```
docs/
├── architecture.md     - Detailed system design
├── ingestion.md       - Ingestion pipeline deep-dive
├── retrieval.md       - Retrieval strategies
├── mcp.md             - MCP integration guide
└── deployment.md      - Production deployment
```

## 🤝 Contributing

Internal team guidelines:
1. Follow PEP 8 style
2. Add type hints
3. Write docstrings
4. Test with sample PDFs before production
5. Update README for new features

## 📧 Support

Contact: LTH Apps Team
Environment: Die Casting & Machining Operations

---
**Built for production at LTH - Manufacturing Intelligence**

