# Contributing to RAG Pipeline

Guidelines for contributing to the Manufacturing Documentation RAG Pipeline.

## 🤝 How to Contribute

### Reporting Issues

1. **Check existing issues** first
2. **Use issue template** for bug reports
3. **Include**:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Logs/screenshots

### Suggesting Features

1. **Open a discussion** first
2. **Explain use case** clearly
3. **Describe proposed solution**
4. **Consider alternatives**

### Code Contributions

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/your-feature`
3. **Follow code style** (see below)
4. **Write tests** for new features
5. **Update documentation**
6. **Submit pull request**

## 📝 Code Style

### Python

- **PEP 8** compliance
- **Type hints** for all functions
- **Docstrings** (Google style)
- **Line length**: 100 characters

**Example:**
```python
def search_documents(
    query: str,
    top_k: int = 5,
    rerank: bool = True
) -> List[SearchResult]:
    """
    Search documents using hybrid search.
    
    Args:
        query: Search query text
        top_k: Number of results to return
        rerank: Whether to rerank results
        
    Returns:
        List of SearchResult objects
        
    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    # Implementation...
```

### Imports

Order imports:
1. Standard library
2. Third-party packages
3. Local modules

```python
# Standard library
import sys
from typing import List, Dict

# Third-party
import weaviate
from loguru import logger

# Local
from config import get_settings
from models import SearchResult
```

### Git Commits

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

**Examples:**
```bash
feat(retrieval): add reranking support

Implement cross-encoder reranking for improved relevance.
Uses BAAI/bge-reranker-large model.

Closes #42

---

fix(ingestion): handle PDF parsing errors

Gracefully handle corrupted PDFs and continue processing.
Logs errors without stopping entire batch.

Fixes #38
```

## 🧪 Testing

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests
pytest

# With coverage
pytest --cov=.
```

### Writing Tests

```python
import pytest
from retrieval.weaviate_client import WeaviateRetrievalClient

def test_hybrid_search():
    """Test hybrid search returns results."""
    client = WeaviateRetrievalClient()
    
    results = client.hybrid_search(
        query="test query",
        limit=5
    )
    
    assert len(results) > 0
    assert results[0].score > 0
```

## 📚 Documentation

### Docstrings

Use Google-style docstrings:

```python
def process_document(
    doc_path: Path,
    chunk_size: int = 600
) -> List[Chunk]:
    """
    Process document into chunks.
    
    Parses PDF, extracts text, and creates semantic chunks
    while preserving document structure.
    
    Args:
        doc_path: Path to PDF document
        chunk_size: Target size for chunks in tokens
        
    Returns:
        List of Chunk objects with text and metadata
        
    Raises:
        FileNotFoundError: If document doesn't exist
        ParseError: If PDF is corrupted
        
    Example:
        >>> chunks = process_document(
        ...     Path("manual.pdf"),
        ...     chunk_size=500
        ... )
        >>> print(len(chunks))
        42
    """
    pass
```

### README Updates

When adding features:

1. **Update main README.md**
2. **Add to SETUP_GUIDE.md** if setup changes
3. **Update relevant service READMEs**
4. **Add examples** to documentation
5. **Document LLM providers** and required env vars (no secrets)

## 🔍 Code Review

### Review Checklist

- [ ] Code follows style guide
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No unnecessary dependencies
- [ ] Error handling implemented
- [ ] Logging added for key operations
- [ ] Performance considered
- [ ] Security implications reviewed

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new warnings
```

## 🏗️ Architecture Decisions

### When to Add New Service

Consider new service if:
- Functionality is independent
- Scales differently from existing services
- Has different dependencies
- Can fail independently

### When to Extend Existing Service

Extend existing service if:
- Tightly coupled to current logic
- Shares most dependencies
- Scaling requirements similar
- Small addition

### Technology Choices

Prefer:
- **Python** for main logic
- **Docker** for containerization
- **FastAPI** for APIs
- **Weaviate** for vector storage
- **PostgreSQL** for relational data

## 🚀 Release Process

### Versioning

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. **Update version** in all relevant files
2. **Update CHANGELOG.md**
3. **Run full test suite**
4. **Create release branch**: `release/v1.2.0`
5. **Tag release**: `git tag v1.2.0`
6. **Deploy to staging**
7. **Smoke test staging**
8. **Deploy to production**
9. **Monitor for issues**

## 📋 Development Setup

### Local Development

```bash
# Clone repository
git clone https://github.com/lth-apps/rag-pipeline.git
cd rag-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Pre-commit Hooks

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## 🎯 Performance Guidelines

### Optimization

- Profile before optimizing
- Cache expensive operations
- Use batch operations
- Async for I/O operations
- Connection pooling

### Benchmarking

```python
import time

def benchmark(func):
    start = time.time()
    result = func()
    duration = time.time() - start
    logger.info(f"{func.__name__} took {duration:.3f}s")
    return result
```

## 🔐 Security

### Security Checklist

- [ ] No secrets in code
- [ ] No API keys in examples (use placeholders)
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens (if applicable)
- [ ] Rate limiting
- [ ] Authentication/authorization
- [ ] Audit logging

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Email: security@lth-apps.com

## 📞 Contact

- **Team Lead**: [Name]
- **Slack**: #rag-pipeline
- **Email**: team@lth-apps.com

## 📄 License

Internal use only - LTH Apps

---
**Thank you for contributing to LTH Apps!**

