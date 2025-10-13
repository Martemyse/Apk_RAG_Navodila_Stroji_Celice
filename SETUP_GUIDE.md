# RAG Pipeline Setup Guide

Complete setup guide for the Manufacturing Documentation RAG Pipeline.

## 📋 Prerequisites

### System Requirements

- **OS**: Linux, macOS, or Windows with WSL2
- **Docker**: 20.10+ with Docker Compose
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB free space
- **CPU**: Multi-core recommended for embeddings

### Software

```bash
# Verify installations
docker --version
docker-compose --version
```

## 🚀 Quick Start (5 Minutes)

### 1. Start Weaviate Infrastructure

```bash
cd ../1_Infrastructure_Weaviate
docker-compose up -d
```

Wait ~30 seconds for Weaviate to initialize.

**Verify:**
```bash
curl http://localhost:8080/v1/.well-known/ready
# Should return: {"status": "ready"}
```

### 2. Configure RAG Services

```bash
cd ../2_Apk_RAG_Navodila_Stroji_Celice

# Copy example environment file
cp env.example .env

# Edit .env with your preferences
nano .env  # or your preferred editor
```

**Minimal `.env` configuration:**
```bash
# Use local embeddings (no API keys needed)
EMBEDDING_PROVIDER=local
RERANKER_PROVIDER=local

# Weaviate connection
WEAVIATE_URL=http://weaviate:8080
```

### 3. Start RAG Services

```bash
docker-compose up -d
```

Services will start:
- **Ingestion**: Processes PDFs and creates embeddings
- **Retrieval**: FastAPI server for queries
- **Dash UI**: Web interface

**Monitor startup:**
```bash
docker-compose logs -f
```

### 4. Access Services

- **Dash UI**: http://localhost:8050
- **FastAPI Docs**: http://localhost:8001/docs
- **Weaviate Console**: http://localhost:8080/v1/console

### 5. Test Query

Visit http://localhost:8050 and search:
```
"How to calibrate PTL007?"
```

## 📖 Detailed Setup

### Configuration Options

#### Embedding Providers

**Local (Recommended for Development):**
```bash
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
```
- No API costs
- Runs on CPU
- ~30 seconds initial model download

**OpenAI (Faster, Requires API Key):**
```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

#### Reranker Options

**Local (Free):**
```bash
RERANKER_PROVIDER=local
RERANKER_MODEL=BAAI/bge-reranker-large
ENABLE_RERANK=true
```

**Cohere (Better Quality):**
```bash
RERANKER_PROVIDER=cohere
COHERE_API_KEY=...
ENABLE_RERANK=true
```

**Disabled:**
```bash
ENABLE_RERANK=false
```

#### Chunking Strategy

```bash
CHUNK_SIZE=600              # Target chunk size in tokens
CHUNK_OVERLAP=100           # Overlap between chunks
MIN_CHUNK_SIZE=100          # Minimum chunk size
MAX_CHUNK_SIZE=1000         # Maximum chunk size
```

### Adding Documents

#### Automatic Ingestion

PDFs in `data_pdf/` are automatically ingested on startup.

#### Manual Ingestion

```bash
# Re-ingest all documents (force)
docker exec rag_ingestion python main.py --force

# Ingest specific document
docker exec rag_ingestion python -c "
from pathlib import Path
from main import IngestionWorker

worker = IngestionWorker()
worker.process_pdf(Path('/app/data_pdf/Navodila_PTL007_V1_4.pdf'), force=True)
worker.close()
"
```

#### Via API

```bash
curl -X POST http://localhost:8001/ingest/all
```

## 🔧 Advanced Configuration

### GPU Acceleration

For faster embeddings, enable GPU support:

**1. Update Docker Compose:**
```yaml
# In retrieval/Dockerfile and ingestion/Dockerfile
services:
  ingestion:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**2. Update requirements:**
```bash
# Use GPU-enabled PyTorch
torch==2.2.0+cu121
```

### Multi-Tenancy

Enable department-level isolation:

```bash
ENABLE_MULTI_TENANCY=true
DEFAULT_TENANT=manufacturing
```

Then filter queries by tenant:
```python
response = requests.post("http://localhost:8001/query", json={
    "query": "safety procedures",
    "filters": {"tenant": "quality_control"}
})
```

### Authentication

#### JWT Authentication (FastAPI)

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
JWT_SECRET_KEY=your-generated-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

#### Weaviate Authentication

Update `1_Infrastructure_Weaviate/weaviate.runtime.json`:

```json
{
  "config": {
    "authentication": {
      "anonymous_access_enabled": false,
      "apikey": {
        "enabled": true,
        "allowed_keys": ["your-secret-key"],
        "users": ["admin"]
      }
    }
  }
}
```

Then set in `.env`:
```bash
WEAVIATE_API_KEY=your-secret-key
```

### Custom Domain & HTTPS

**1. Update nginx configuration** (if using existing nginx):

```nginx
server {
    listen 443 ssl;
    server_name rag.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Dash UI
    location / {
        proxy_pass http://localhost:8050;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API
    location /api {
        proxy_pass http://localhost:8001;
    }
}
```

**2. Update environment:**
```bash
RETRIEVAL_API_URL=https://rag.yourcompany.com/api
```

## 🧪 Testing

### Health Checks

```bash
# Weaviate
curl http://localhost:8080/v1/.well-known/ready

# Retrieval API
curl http://localhost:8001/health

# Dash UI
curl http://localhost:8050
```

### Sample Queries

```bash
# Simple query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to maintain ROM27?",
    "top_k": 5,
    "rerank": true
  }'

# With filters
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "safety procedures",
    "top_k": 3,
    "filters": {"doc_id": "Navodila_ROM27_V1_2"}
  }'
```

### List Documents

```bash
curl http://localhost:8001/documents
```

## 📊 Monitoring

### Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f retrieval
docker-compose logs -f ingestion
docker-compose logs -f dashapp
```

### Resource Usage

```bash
docker stats
```

### Performance Metrics

Visit FastAPI docs for built-in metrics:
```
http://localhost:8001/docs
```

## 🐛 Troubleshooting

### Services Won't Start

**1. Check if ports are available:**
```bash
netstat -an | grep 8050  # Dash
netstat -an | grep 8001  # API
netstat -an | grep 8080  # Weaviate
```

**2. Check Docker resources:**
```bash
docker system df
docker system prune  # if needed
```

**3. View detailed logs:**
```bash
docker-compose logs retrieval
```

### No Results in Queries

**1. Check if documents are ingested:**
```bash
curl http://localhost:8001/documents
```

**2. Re-ingest documents:**
```bash
docker-compose restart ingestion
docker-compose logs -f ingestion
```

**3. Check Weaviate schema:**
```bash
curl http://localhost:8080/v1/schema
```

### Slow Performance

**1. Reduce reranking overhead:**
```bash
ENABLE_RERANK=false
```

**2. Use smaller embedding model:**
```bash
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

**3. Adjust chunk settings:**
```bash
CHUNK_SIZE=400  # Smaller chunks = faster
```

### Out of Memory

**1. Limit Docker memory:**
```yaml
# In docker-compose.yml
services:
  retrieval:
    mem_limit: 4g
```

**2. Use smaller models:**
```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKER_PROVIDER=none
```

## 🔄 Maintenance

### Backup

```bash
# Backup Weaviate data
cd ../1_Infrastructure_Weaviate
tar -czf weaviate-backup-$(date +%Y%m%d).tar.gz weaviate-data/

# Backup processed documents
cd ../2_Apk_RAG_Navodila_Stroji_Celice
tar -czf data-backup-$(date +%Y%m%d).tar.gz data_processed/
```

### Update

```bash
# Pull latest changes
git pull

# Rebuild containers
docker-compose build --no-cache

# Restart services
docker-compose up -d
```

### Clean Reset

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: destroys all data)
docker-compose down -v

# Remove Weaviate data
cd ../1_Infrastructure_Weaviate
rm -rf weaviate-data/

# Restart fresh
cd ../2_Apk_RAG_Navodila_Stroji_Celice
docker-compose up -d
```

## 📚 Next Steps

1. **Integrate with MCP**: See [MCP_SETUP.md](retrieval/MCP_SETUP.md)
2. **Add more documents**: Copy PDFs to `data_pdf/`
3. **Customize UI**: Edit `dashapp/app.py`
4. **Add evaluations**: Implement Ragas/TruLens (Phase 2)
5. **Scale up**: Add load balancing and caching

## 🆘 Support

- **Internal Issues**: Contact LTH Apps Team
- **Documentation**: Check README.md files in each service
- **Logs**: Always check `docker-compose logs` first

## 📖 Additional Resources

- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [Dash Documentation](https://dash.plotly.com/)
- [BGE Embeddings](https://huggingface.co/BAAI/bge-large-en-v1.5)

---
**Built for LTH Apps - Manufacturing Excellence**

