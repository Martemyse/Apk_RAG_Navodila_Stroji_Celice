# Project Structure

Detailed overview of the RAG pipeline project structure.

## 📁 Directory Layout

```
2_Apk_RAG_Navodila_Stroji_Celice/
│
├── README.md                    # Main project documentation
├── QUICKSTART.md               # 5-minute quick start guide
├── SETUP_GUIDE.md              # Detailed setup instructions
├── DEPLOYMENT.md               # Production deployment guide
├── CONTRIBUTING.md             # Contribution guidelines
├── PROJECT_STRUCTURE.md        # This file
│
├── docker-compose.yml          # Docker Compose orchestration
├── env.example                 # Environment variables template
├── .gitignore                  # Git ignore rules
│
├── data_pdf/                   # Source PDF documents (input)
│   ├── Navodila_PTL007_V1_4.pdf
│   ├── Navodila_PTL008_V1_2.pdf
│   ├── Navodila_ROM27_V1_2.pdf
│   └── ... (12 PDF files)
│
├── data_processed/             # Processed documents (generated)
│   └── [doc_id]/
│       ├── parsed_document.json
│       ├── document.md
│       └── images/
│
├── ingestion/                  # Ingestion service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py              # Configuration
│   ├── main.py                # Main ingestion worker
│   ├── parsers.py             # PDF parsers (PyMuPDF4LLM, Unstructured)
│   ├── chunking.py            # Semantic chunking
│   ├── embeddings.py          # Embedding providers
│   └── weaviate_client.py     # Weaviate integration
│
├── retrieval/                  # Retrieval service (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py              # Configuration
│   ├── main.py                # FastAPI application
│   ├── weaviate_client.py     # Weaviate queries
│   ├── embeddings.py          # Query embeddings
│   ├── reranker.py            # Result reranking
│   ├── mcp_server.py          # MCP server for agents
│   └── MCP_SETUP.md           # MCP integration guide
│
└── dashapp/                    # Dash UI
    ├── Dockerfile
    ├── requirements.txt
    └── app.py                  # Dash application
```

## 🏗️ Component Breakdown

### Ingestion Service

**Purpose**: Parse PDFs, create embeddings, ingest to Weaviate

**Key Files:**
- `parsers.py`: PDF parsing with PyMuPDF4LLM and Unstructured
  - `PyMuPDFParser`: Layout-aware Markdown extraction
  - `UnstructuredParser`: Structured element extraction
  - `HybridParser`: Combined approach

- `chunking.py`: Semantic text chunking
  - `SemanticChunker`: Respects document structure
  - Preserves section paths, page numbers, bounding boxes

- `embeddings.py`: Text vectorization
  - `LocalEmbeddingProvider`: BGE models (CPU/GPU)
  - `OpenAIEmbeddingProvider`: OpenAI API

- `weaviate_client.py`: Vector DB operations
  - Schema management (Document, Chunk collections)
  - Batch ingestion with error handling
  - Duplicate detection

### Retrieval Service

**Purpose**: Query interface, hybrid search, reranking, MCP

**Key Files:**
- `main.py`: FastAPI application
  - `/query`: Hybrid search endpoint
  - `/documents`: List documents
  - `/doc/{id}/chunks`: Get document chunks
  - `/ws`: WebSocket streaming

- `weaviate_client.py`: Search operations
  - `hybrid_search()`: BM25 + vector search
  - `vector_search()`: Pure semantic search
  - Result mapping and scoring

- `reranker.py`: Result reranking
  - `LocalReranker`: BGE reranker
  - `CohereReranker`: Cohere API
  - Cross-encoder scoring

- `mcp_server.py`: Model Context Protocol
  - `search_docs`: Search tool for agents
  - `get_document`: Document retrieval
  - `list_documents`: Document listing
  - `get_document_page`: Page-specific content

### Dash UI

**Purpose**: Interactive web interface for queries

**Key Files:**
- `app.py`: Dash application
  - Query interface with advanced options
  - Result cards with citations
  - Real-time search
  - Copy/export functionality

## 🔄 Data Flow

### 1. Ingestion Flow

```
PDF Files (data_pdf/)
    ↓
PyMuPDF4LLM Parser
    ↓ (Markdown + metadata)
Semantic Chunker
    ↓ (Chunks with context)
Embedding Provider
    ↓ (Vectors)
Weaviate
    ↓
[Document & Chunk collections]
```

### 2. Query Flow

```
User Query (Dash UI / API)
    ↓
Embedding Provider
    ↓ (Query vector)
Weaviate Hybrid Search
    ↓ (Top K results)
Reranker (optional)
    ↓ (Reordered results)
Response with citations
```

### 3. MCP Flow

```
AI Agent (Claude, etc.)
    ↓
MCP Client
    ↓ (Tool call)
MCP Server (mcp_server.py)
    ↓
Retrieval Service
    ↓
Weaviate
    ↓
Results to Agent
```

## 🗄️ Data Models

### Weaviate Schema

**Document Collection:**
```python
{
    "doc_id": "string",          # Unique document identifier
    "title": "string",           # Document title
    "source_uri": "string",      # Path to original PDF
    "total_pages": int,          # Number of pages
    "created_at": "datetime",    # Ingestion timestamp
    "department": "string",      # Department tag
    "tags": ["string"]           # Document tags
}
```

**Chunk Collection:**
```python
{
    "chunk_id": "string",        # Unique chunk identifier
    "doc_id": "string",          # Reference to document
    "text": "string",            # Chunk text content
    "page": int,                 # Page number (1-indexed)
    "section_path": "string",    # Hierarchical section path
    "bbox": "string",            # Bounding box coordinates
    "token_count": int,          # Number of tokens
    "vector": [float]            # Embedding vector
}
```

### API Models

**QueryRequest:**
```python
{
    "query": "string",           # Query text (required)
    "top_k": int,                # Initial results (default: 25)
    "rerank": bool,              # Enable reranking (default: true)
    "rerank_top_k": int,         # Results after rerank (default: 5)
    "filters": dict,             # Optional filters
    "alpha": float               # Hybrid alpha (default: 0.5)
}
```

**QueryResponse:**
```python
{
    "query": "string",
    "results": [
        {
            "chunk_id": "string",
            "doc_id": "string",
            "text": "string",
            "page": int,
            "section_path": "string",
            "score": float
        }
    ],
    "total_results": int,
    "reranked": bool,
    "processing_time": float
}
```

## 🔌 Inter-Service Communication

### Network: `infrastructure_weaviate_network`

All services communicate via Docker internal DNS:

- **Weaviate**: `http://weaviate:8080`
- **Retrieval API**: `http://retrieval:8001`
- **Dash UI**: `http://dashapp:8050`

### Volume Mounts

- **Ingestion**:
  - `./data_pdf:/app/data_pdf:ro` (read-only source)
  - `./data_processed:/app/data_processed` (output)
  - `ingestion_models:/app/models` (model cache)

- **Retrieval**:
  - `./data_pdf:/app/data_pdf:ro` (for page serving)
  - `retrieval_models:/app/models` (model cache)

## 🛠️ Configuration

### Environment Variables

**Shared:**
- `LOG_LEVEL`: Logging verbosity
- `WEAVIATE_URL`: Weaviate connection
- `EMBEDDING_PROVIDER`: 'local' or 'openai'
- `RERANKER_PROVIDER`: 'local', 'cohere', or 'none'

**Ingestion-specific:**
- `CHUNK_SIZE`: Target chunk size
- `CHUNK_OVERLAP`: Chunk overlap
- `ENABLE_OCR`: OCR for scanned PDFs

**Retrieval-specific:**
- `API_PORT`: FastAPI port
- `DEFAULT_TOP_K`: Default result count
- `ENABLE_RERANK`: Enable reranking

**Dash-specific:**
- `DASH_PORT`: Dash server port
- `RETRIEVAL_API_URL`: Retrieval service URL

## 📦 Dependencies

### Core Technologies

- **Vector DB**: Weaviate 1.32.0
- **Web Framework**: FastAPI 0.109.2
- **UI Framework**: Dash 2.14.2
- **PDF Parsing**: PyMuPDF4LLM, Unstructured
- **Embeddings**: sentence-transformers, OpenAI
- **ML**: PyTorch 2.2.0

### Python Version

- Python 3.11 (all services)

## 🚀 Deployment Variants

### Development (Current)

- Local models (CPU)
- No authentication
- Debug logging
- Single replicas

### Production (See DEPLOYMENT.md)

- GPU acceleration (optional)
- JWT + Weaviate auth
- Structured logging
- Multiple replicas
- Load balancing
- Monitoring

## 🔍 Monitoring Points

### Health Checks

- Weaviate: `http://localhost:8080/v1/.well-known/ready`
- Retrieval: `http://localhost:8001/health`
- Dash: `http://localhost:8050` (200 OK)

### Metrics (If Enabled)

- Retrieval: `http://localhost:8001/metrics` (Prometheus)
- Weaviate: `http://localhost:8080/v1/metrics`

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f [ingestion|retrieval|dashapp]
```

## 🧪 Testing Structure (Future)

```
tests/
├── unit/
│   ├── test_parsers.py
│   ├── test_chunking.py
│   ├── test_embeddings.py
│   └── test_reranker.py
├── integration/
│   ├── test_ingestion_flow.py
│   ├── test_query_flow.py
│   └── test_mcp_server.py
└── e2e/
    └── test_full_pipeline.py
```

## 📝 Documentation Files

- `README.md`: Overview and architecture
- `QUICKSTART.md`: 5-minute setup
- `SETUP_GUIDE.md`: Detailed setup
- `DEPLOYMENT.md`: Production deployment
- `CONTRIBUTING.md`: Development guidelines
- `PROJECT_STRUCTURE.md`: This file
- `retrieval/MCP_SETUP.md`: MCP integration

## 🔄 Update Workflow

1. **Code changes**: Edit service files
2. **Rebuild**: `docker-compose build [service]`
3. **Restart**: `docker-compose up -d [service]`
4. **Test**: Verify functionality
5. **Document**: Update relevant docs

## 🎯 Extension Points

### Adding New Parser

1. Create parser class in `ingestion/parsers.py`
2. Implement `parse()` method
3. Return `ParsedDocument`
4. Update `HybridParser` to use it

### Adding New Reranker

1. Create reranker class in `retrieval/reranker.py`
2. Inherit from `Reranker` ABC
3. Implement `rerank()` method
4. Update `get_reranker()` factory

### Adding New Endpoint

1. Add route in `retrieval/main.py`
2. Create Pydantic models
3. Update OpenAPI docs
4. Test with `/docs` interface

### Adding MCP Tool

1. Add tool definition in `mcp_server.py`
2. Implement handler method
3. Update `MCP_SETUP.md`
4. Test with MCP client

---
**LTH Apps - Technical Documentation**

