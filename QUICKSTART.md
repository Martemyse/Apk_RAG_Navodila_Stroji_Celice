# ⚡ Quick Start Guide

Get the RAG pipeline running in 5 minutes!

## 🎯 Prerequisites

- Docker & Docker Compose installed
- 8GB+ RAM available
- Internet connection (for initial model download)

## 🚀 3-Step Setup

### Step 1: Start Weaviate (30 seconds)

```bash
cd ../1_Infrastructure_Weaviate
docker-compose up -d

# Wait for ready status
curl http://localhost:8080/v1/.well-known/ready
```

### Step 2: Configure & Start RAG Services (1 minute)

```bash
cd ../2_Apk_RAG_Navodila_Stroji_Celice

# Copy environment file
cp env.example .env

# Start all services
docker-compose up -d

# Watch startup (optional)
docker-compose logs -f
```

### Step 3: Test It! (30 seconds)

Open your browser:
- **Dash UI**: http://localhost:8050
- **API Docs**: http://localhost:8001/docs

Try a search query in Dash UI:
```
"How to calibrate PTL007?"
```

## ✅ Verify Installation

```bash
# Check all services are running
docker ps

# Expected output:
# - weaviate_c
# - rag_ingestion
# - rag_retrieval
# - rag_dashapp
# - t2v_transformers_c

# Test API
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 3}'
```

## 📚 What Just Happened?

1. **Weaviate** started with local embeddings (CPU)
2. **Ingestion** processed PDFs from `data_pdf/` folder
3. **Retrieval** API started on port 8001
4. **Dash UI** started on port 8050

## 🎮 What's Next?

### Add Your Documents

```bash
# Copy PDFs to data folder
cp your_manual.pdf 2_Apk_RAG_Navodila_Stroji_Celice/data_pdf/

# Restart ingestion to process
docker-compose restart ingestion

# Watch processing
docker-compose logs -f ingestion
```

### Use the API

**Python:**
```python
import requests

response = requests.post("http://localhost:8001/query", json={
    "query": "How to maintain ROM27?",
    "top_k": 5,
    "rerank": True
})

results = response.json()
for result in results["results"]:
    print(f"[Page {result['page']}] {result['text']}")
```

**curl:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "safety procedures",
    "top_k": 5,
    "rerank": true
  }'
```

### Connect AI Agents (MCP)

See detailed guide: [retrieval/MCP_SETUP.md](retrieval/MCP_SETUP.md)

**Quick Claude Desktop setup:**
```json
{
  "mcpServers": {
    "rag-navodila": {
      "command": "docker",
      "args": ["exec", "-i", "rag_retrieval", "python", "mcp_server.py"]
    }
  }
}
```

## 🔧 Common Commands

```bash
# View logs
docker-compose logs -f [service_name]

# Restart service
docker-compose restart [service_name]

# Stop all
docker-compose down

# Stop all + remove volumes
docker-compose down -v

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

## 🐛 Troubleshooting

### Services won't start

```bash
# Check if ports are in use
netstat -an | grep 8050  # Dash
netstat -an | grep 8001  # API
netstat -an | grep 8080  # Weaviate

# Check Docker resources
docker system df
```

### No search results

```bash
# Check if documents ingested
curl http://localhost:8001/documents

# Re-run ingestion
docker-compose restart ingestion
```

### Slow performance

Edit `.env`:
```bash
# Disable reranking for speed
ENABLE_RERANK=false

# Or use smaller model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## 📖 Full Documentation

- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- **Architecture**: [README.md](README.md) - System overview
- **MCP Integration**: [retrieval/MCP_SETUP.md](retrieval/MCP_SETUP.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f`
2. Review [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Contact: LTH Apps Team

## 🎉 You're Ready!

Your RAG pipeline is now running. Start searching your documentation!

**Access Points:**
- 🖥️ **UI**: http://localhost:8050
- 🔌 **API**: http://localhost:8001/docs
- 🗄️ **Weaviate**: http://localhost:8080

---
**Happy Searching! 🚀**

