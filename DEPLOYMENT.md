# Production Deployment Guide

Guide for deploying the RAG pipeline to production environments.

## 🎯 Production Checklist

### Security

- [ ] Enable Weaviate authentication
- [ ] Set up JWT authentication for FastAPI
- [ ] Configure HTTPS/TLS
- [ ] Use environment-specific secrets
- [ ] Enable CORS restrictions
- [ ] Set up firewall rules
- [ ] Use Docker secrets for sensitive data

### Performance

- [ ] Enable GPU acceleration (if available)
- [ ] Set up caching layer (Redis)
- [ ] Configure load balancing
- [ ] Optimize chunk sizes for your use case
- [ ] Enable connection pooling
- [ ] Set appropriate timeouts

### Monitoring

- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards
- [ ] Enable application logging
- [ ] Set up alerting (PagerDuty, etc.)
- [ ] Configure health check endpoints
- [ ] Track query performance

### Backup & Recovery

- [ ] Automated Weaviate backups
- [ ] Document backup procedures
- [ ] Test restore procedures
- [ ] Set up off-site backup storage
- [ ] Version control for configurations

## 🏭 Production Architecture

```
                        ┌─────────────────┐
                        │   Load Balancer │
                        │    (nginx)      │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
            ┌───────▼────────┐       ┌───────▼────────┐
            │  Dash UI       │       │  FastAPI       │
            │  (Replica 1)   │       │  (Replica 1-3) │
            └───────┬────────┘       └───────┬────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                        ┌────────▼─────────┐
                        │    Weaviate      │
                        │   (Clustered)    │
                        └──────────────────┘
```

## 🔐 Security Hardening

### 1. Weaviate Authentication

**weaviate.runtime.json:**
```json
{
  "config": {
    "authentication": {
      "anonymous_access_enabled": false,
      "apikey": {
        "enabled": true,
        "allowed_keys": ["${WEAVIATE_API_KEY}"],
        "users": ["rag_service"]
      },
      "oidc": {
        "enabled": true,
        "issuer": "https://auth.yourcompany.com",
        "client_id": "weaviate"
      }
    },
    "authorization": {
      "admin_list": {
        "enabled": true,
        "users": ["admin@yourcompany.com"]
      }
    }
  }
}
```

### 2. FastAPI JWT Authentication

**Add to retrieval/main.py:**
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/query")
async def query(request: QueryRequest, user=Depends(verify_token)):
    # ... existing code
```

### 3. HTTPS/TLS Configuration

**nginx.conf:**
```nginx
upstream fastapi_backend {
    least_conn;
    server retrieval1:8001;
    server retrieval2:8001;
    server retrieval3:8001;
}

server {
    listen 443 ssl http2;
    server_name rag.yourcompany.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Dash UI
    location / {
        proxy_pass http://dashapp:8050;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://fastapi_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
    }
}

# Rate limit zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

### 4. Docker Secrets

**docker-compose.prod.yml:**
```yaml
services:
  retrieval:
    environment:
      - WEAVIATE_API_KEY_FILE=/run/secrets/weaviate_key
      - JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret
    secrets:
      - weaviate_key
      - jwt_secret

secrets:
  weaviate_key:
    external: true
  jwt_secret:
    external: true
```

**Create secrets:**
```bash
echo "your-weaviate-key" | docker secret create weaviate_key -
echo "your-jwt-secret" | docker secret create jwt_secret -
```

## 📈 Scaling

### Horizontal Scaling (Multiple Replicas)

**docker-compose.prod.yml:**
```yaml
services:
  retrieval:
    image: rag_retrieval:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

### Weaviate Cluster

For high availability:

```yaml
services:
  weaviate-node1:
    image: semitechnologies/weaviate:1.32.0
    environment:
      - CLUSTER_HOSTNAME=node1
      - CLUSTER_GOSSIP_BIND_PORT=7102
      - CLUSTER_DATA_BIND_PORT=7103
      - CLUSTER_JOIN=node2:7102,node3:7102
  
  weaviate-node2:
    image: semitechnologies/weaviate:1.32.0
    environment:
      - CLUSTER_HOSTNAME=node2
      - CLUSTER_JOIN=node1:7102,node3:7102
  
  weaviate-node3:
    image: semitechnologies/weaviate:1.32.0
    environment:
      - CLUSTER_HOSTNAME=node3
      - CLUSTER_JOIN=node1:7102,node2:7102
```

## 📊 Monitoring & Observability

### 1. Prometheus Metrics

**Add to retrieval/main.py:**
```python
from prometheus_client import Counter, Histogram, make_asgi_app

query_counter = Counter('rag_queries_total', 'Total queries')
query_duration = Histogram('rag_query_duration_seconds', 'Query duration')

@app.post("/query")
@query_duration.time()
async def query(request: QueryRequest):
    query_counter.inc()
    # ... existing code

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### 2. Structured Logging

```python
import structlog

logger = structlog.get_logger()

@app.post("/query")
async def query(request: QueryRequest):
    logger.info(
        "query_received",
        query=request.query,
        top_k=request.top_k,
        user_id=user.id
    )
```

### 3. Grafana Dashboard

Create dashboard with:
- Query rate (queries/sec)
- Query latency (p50, p95, p99)
- Error rate
- Weaviate connection status
- Memory/CPU usage
- Cache hit rate

**Import dashboard JSON** from `monitoring/grafana-dashboard.json`

## 💾 Backup Strategy

### Automated Backups

**backup.sh:**
```bash
#!/bin/bash
set -e

BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Stop writes (optional)
# docker-compose pause ingestion

# Backup Weaviate
echo "Backing up Weaviate..."
docker exec weaviate_c tar czf - /var/lib/weaviate > \
  $BACKUP_DIR/weaviate_$DATE.tar.gz

# Backup processed data
echo "Backing up processed data..."
tar czf $BACKUP_DIR/processed_$DATE.tar.gz \
  2_Apk_RAG_Navodila_Stroji_Celice/data_processed/

# Resume writes
# docker-compose unpause ingestion

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/weaviate_$DATE.tar.gz \
  s3://your-bucket/backups/

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup complete: $DATE"
```

**Cron schedule:**
```bash
# Daily backups at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/rag-backup.log 2>&1
```

### Restore Procedure

```bash
#!/bin/bash
set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file>"
  exit 1
fi

# Stop services
docker-compose down

# Restore Weaviate data
cd 1_Infrastructure_Weaviate
rm -rf weaviate-data/
tar xzf $BACKUP_FILE -C .

# Restart
docker-compose up -d

echo "Restore complete"
```

## 🚀 Deployment Pipeline

### CI/CD with GitHub Actions

**.github/workflows/deploy.yml:**
```yaml
name: Deploy RAG Pipeline

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build images
        run: |
          docker-compose -f docker-compose.prod.yml build
      
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
      
      - name: Push to registry
        run: |
          docker tag rag_retrieval:latest registry.yourcompany.com/rag_retrieval:${{ github.sha }}
          docker push registry.yourcompany.com/rag_retrieval:${{ github.sha }}
      
      - name: Deploy to production
        run: |
          ssh deploy@prod-server "
            cd /opt/rag-pipeline &&
            docker-compose pull &&
            docker-compose up -d
          "
```

## 🧪 Testing in Production

### Smoke Tests

```bash
#!/bin/bash
set -e

API_URL="https://rag.yourcompany.com/api"

# Health check
curl -f $API_URL/health || exit 1

# Test query
RESPONSE=$(curl -s -X POST $API_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}')

if [ -z "$RESPONSE" ]; then
  echo "Query test failed"
  exit 1
fi

echo "All tests passed"
```

### Load Testing

```bash
# Install k6
brew install k6  # or apt-get install k6

# Run load test
k6 run load-test.js
```

**load-test.js:**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },  // Ramp up
    { duration: '5m', target: 50 },  // Peak load
    { duration: '2m', target: 0 },   // Ramp down
  ],
};

export default function() {
  let response = http.post(
    'https://rag.yourcompany.com/api/query',
    JSON.stringify({
      query: 'How to calibrate machine?',
      top_k: 5
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });
  
  sleep(1);
}
```

## 📋 Runbook

### Common Issues

**High Memory Usage**
```bash
# Check container stats
docker stats

# Restart service
docker-compose restart retrieval

# Scale down if needed
docker-compose up -d --scale retrieval=2
```

**Slow Queries**
```bash
# Check Weaviate status
curl http://localhost:8080/v1/nodes

# Disable reranking temporarily
docker exec rag_retrieval sh -c "echo 'ENABLE_RERANK=false' >> .env"
docker-compose restart retrieval
```

**Service Down**
```bash
# Check logs
docker-compose logs --tail=100 retrieval

# Restart
docker-compose up -d

# If persistent, rollback
docker-compose down
docker pull rag_retrieval:previous-tag
docker-compose up -d
```

## 📞 Support

### On-Call Procedures

1. Check health endpoints
2. Review Grafana dashboards
3. Check application logs
4. Restart affected services
5. Escalate if unresolved in 15 minutes

### Escalation Path

1. DevOps Team
2. Platform Engineering
3. CTO Office

---
**LTH Apps - Production Operations**

