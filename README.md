# RAG Pipeline - Ask PDF (with images)

Production-ready Retrieval-Augmented Generation (RAG) pipeline for manufacturing documentation with **text and image embedding**. The system extracts and embeds both text content and images from PDFs, enabling retrieval of complete source information including PDF file, page number, and associated images.

## 🏗️ Architecture

```
[PDF Documents with Text + Images]
       │
[Ingestion Service]
  - PyMuPDF4LLM (layout-aware parsing)
  - Image extraction with bounding boxes
  - Text + Image fusion into ContentUnits
  - Embeddings (text + image context)
  - Storage: PostgreSQL + Weaviate
       │
[PostgreSQL]
  - Documents (PDF metadata)
  - ImageAssets (extracted images with page/bbox)
  - ContentUnits (fused text+image units)
       │
[Weaviate Vector DB]
  - Hybrid search (BM25 + vectors)
  - ContentUnit collection with embeddings
  - Multi-tenancy ready
       │
[Retrieval Service - FastAPI]
  - /query → Returns: PDF file, page, text, image_id
  - /image/{image_id} → Retrieve image asset
  - /pdf_section/{unit_id} → Get PDF source info
  - WebSocket streaming
  - MCP tools for agents
       │                   │
   [Dash UI]              [AI Agents via MCP]
   (Plotly, WS)           (Claude, ChatGPT)
```

## 📦 Components

### 1. Ingestion Service
- **Parser**: PyMuPDF4LLM for layout-aware Markdown extraction
- **Image Extractor**: Extracts images from PDFs with bounding boxes and page numbers
- **Content Unit Builder**: Creates fused text+image units (IMAGE_WITH_CONTEXT) and text-only units (TEXT_ONLY)
- **Embeddings**: BAAI/bge-large-en-v1.5 (local) or OpenAI for text embeddings
- **Storage**: 
  - **PostgreSQL**: Documents, ImageAssets, ContentUnits with full metadata
  - **Weaviate**: ContentUnit collection with embeddings for hybrid search

### 2. Retrieval Service (FastAPI)
- **Endpoints**:
  - `POST /query` - Hybrid search returning content units with **PDF file, page number, text, and image references**
  - `GET /image/{image_id}` - Retrieve image asset with path, bbox, caption, page number
  - `GET /pdf_section/{unit_id}` - Get complete PDF source information (file path, page, section)
  - `GET /content_unit/{unit_id}` - Get full content unit details
  - `GET /health` - Health check
- **Search**: Weaviate hybrid (BM25 + vector) on fused content units
- **Source Retrieval**: Every result includes `doc_id`, `page_number`, `image_id` for complete traceability
- **MCP**: Model Context Protocol tools for agent integration

### 3. Dash UI
- Interactive query interface
- **Source citations** with PDF file name, page numbers, and image references
- Real-time streaming answers (WebSockets)
- Document viewer with deep-linking to exact pages
- Image display from retrieved sources

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
# Run fused ingestion (text + images)
cd ingestion
python main_fused.py

# Or trigger via API if available
curl -X POST http://localhost:8001/ingest/all
```

The ingestion process:
1. Extracts text and images from PDFs
2. Creates fused content units (text + image context)
3. Stores images as ImageAssets with page numbers and bounding boxes
4. Generates embeddings for content units
5. Stores in PostgreSQL and Weaviate

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

## 📊 Data Model

### PostgreSQL Schema

#### Document
```json
{
  "id": "uuid",
  "doc_id": "string (unique)",
  "title": "string",
  "file_path": "string",
  "total_pages": "int",
  "created_at": "timestamp"
}
```

#### ImageAsset
```json
{
  "id": "uuid",
  "document_id": "uuid (ref)",
  "doc_id": "string",
  "page_number": "int",
  "bbox": {"x1": float, "y1": float, "x2": float, "y2": float},
  "image_path": "string",
  "auto_caption": "string (optional)",
  "image_hash": "string"
}
```

#### ContentUnit (Fused Text+Image)
```json
{
  "id": "uuid",
  "document_id": "uuid (ref)",
  "doc_id": "string",
  "page_number": "int",
  "section_title": "string",
  "section_path": "string",
  "text": "string",
  "unit_type": "TEXT_ONLY | IMAGE_WITH_CONTEXT",
  "image_id": "uuid (ref to ImageAsset, optional)",
  "token_count": "int",
  "bbox": {"x1": float, "y1": float, "x2": float, "y2": float},
  "tags": ["string"]
}
```

### Weaviate Collection

#### ContentUnit
- Stores ContentUnit objects with embeddings
- Properties: `doc_id`, `page_number`, `text`, `unit_type`, `image_id`, `section_path`
- Enables hybrid search (BM25 + vector) for retrieval

## 🔍 Usage Examples

### Python Client - Query with Source Retrieval
```python
import requests

# Query - returns content units with full source information
response = requests.post("http://localhost:8001/query", json={
    "query": "How to calibrate PTL007?",
    "top_k": 5
})

results = response.json()
for result in results["results"]:
    print(f"PDF: {result['doc_id']}")
    print(f"Page: {result['page_number']}")
    print(f"Text: {result['text'][:200]}...")
    
    # Check if result has associated image
    if result.get('has_image') and result.get('image_id'):
        # Retrieve image details
        image_response = requests.get(
            f"http://localhost:8001/image/{result['image_id']}"
        )
        image_data = image_response.json()
        print(f"Image: {image_data['image_path']}")
        print(f"Image Page: {image_data['page_number']}")
        print(f"BBox: {image_data['bbox']}")
    
    # Get PDF section information
    pdf_section = requests.get(
        f"http://localhost:8001/pdf_section/{result['id']}"
    )
    section_data = pdf_section.json()
    print(f"Document: {section_data['document_title']}")
    print(f"Section: {section_data['section_path']}")
    print("---")
```

### Retrieval Response Format
Every query result includes complete source information:
```json
{
  "id": "content-unit-uuid",
  "doc_id": "machine_manual_ptl007",
  "page_number": 42,
  "text": "Calibration procedure...",
  "unit_type": "IMAGE_WITH_CONTEXT",
  "image_id": "image-asset-uuid",
  "has_image": true,
  "section_path": "Chapter 3 > Calibration",
  "score": 0.85
}
```

### Dash UI
Navigate to http://localhost:8050, enter your question, and get:
- Streaming answer generation
- **Source citations** showing:
  - PDF file name (`doc_id`)
  - Exact page number
  - Section path
  - Associated images (if available)
- Click citations to view exact page/region in PDF
- Display extracted images from sources

### MCP (AI Agents)
```json
{
  "tool": "search_content_units",
  "arguments": {
    "query": "What safety procedures apply to ROM27?",
    "top_k": 3
  }
}
```
Returns content units with full source traceability including PDF file, page, and image references.

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

### Phase 1 (Current) ✅
- [x] Text + Image extraction from PDFs
- [x] Fused content units (text + image context)
- [x] Image storage with page numbers and bounding boxes
- [x] Hybrid search (BM25 + vectors) on content units
- [x] FastAPI retrieval service with source information
- [x] Complete source retrieval (PDF file, page, images)
- [x] Dash UI with source citations
- [x] MCP server for agents

### Phase 2 (Future)
- [ ] CLIP or multimodal embeddings for images
- [ ] Table parsing with html/markdown output
- [ ] Florence-2 or BLIP-2 for automatic image captioning
- [ ] Image-based search (query by image similarity)
- [ ] Enhanced multi-modal retrieval UI

### Phase 3 (Future)
- [ ] Ragas/TruLens evaluation pipeline
- [ ] Prometheus metrics + Grafana dashboards
- [ ] Advanced filters (department, date range, tags)
- [ ] User feedback loop for continuous improvement

## 🛠️ Tech Stack

- **Vector DB**: Weaviate (hybrid search on fused content units)
- **Relational DB**: PostgreSQL (documents, images, content units)
- **Embeddings**: BAAI/bge-large-en-v1.5 (local) or OpenAI
- **Parser**: PyMuPDF4LLM (layout-aware text + image extraction)
- **Image Processing**: PyMuPDF (image extraction with bounding boxes)
- **API**: FastAPI + Uvicorn
- **UI**: Dash (Plotly) with source citations
- **Agent Protocol**: MCP (Model Context Protocol)

## 📍 Source Retrieval & Traceability

**Every retrieval result provides complete source information:**

1. **PDF File**: `doc_id` identifies the source document
2. **Page Number**: Exact page where content was found
3. **Section Path**: Hierarchical location (e.g., "Chapter 3 > Calibration")
4. **Image Assets**: If content includes images, `image_id` references the extracted image with:
   - Image file path
   - Bounding box coordinates on the page
   - Page number
   - Optional auto-generated caption

**Retrieval endpoints:**
- `/query` - Returns content units with all source metadata
- `/image/{image_id}` - Get full image asset details
- `/pdf_section/{unit_id}` - Get complete PDF source information

This enables full traceability: from query result → PDF file → exact page → associated images.

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

