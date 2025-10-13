"""Main FastAPI application for RAG retrieval."""
import sys
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from loguru import logger
import time

from config import get_settings
from weaviate_client import get_weaviate_client, SearchResult
from embeddings import get_embedding_provider
from reranker import get_reranker

settings = get_settings()

# Global instances
weaviate_client = None
embedding_provider = None
reranker = None


# Pydantic models
class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=25, description="Number of initial results")
    rerank: bool = Field(default=True, description="Whether to rerank results")
    rerank_top_k: int = Field(default=5, description="Number of results after reranking")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")
    alpha: float = Field(default=0.5, description="Hybrid search alpha (0=BM25, 1=vector)")


class QueryResponse(BaseModel):
    """Query response model."""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    reranked: bool
    processing_time: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    weaviate_connected: bool
    embedding_provider: str
    reranker_enabled: bool


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    global weaviate_client, embedding_provider, reranker
    
    # Startup
    logger.info("Starting up retrieval service")
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    
    # Initialize components
    try:
        logger.info("Initializing Weaviate client")
        weaviate_client = get_weaviate_client()
        
        logger.info("Initializing embedding provider")
        embedding_provider = get_embedding_provider()
        
        logger.info("Initializing reranker")
        reranker = get_reranker()
        
        logger.info("Retrieval service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down retrieval service")
    if weaviate_client:
        weaviate_client.close()


# Create FastAPI app
app = FastAPI(
    title="RAG Retrieval Service",
    description="Retrieval service for manufacturing documentation RAG pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RAG Retrieval Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    weaviate_ok = weaviate_client.health_check() if weaviate_client else False
    
    return HealthResponse(
        status="healthy" if weaviate_ok else "degraded",
        weaviate_connected=weaviate_ok,
        embedding_provider=settings.embedding_provider,
        reranker_enabled=settings.enable_rerank and reranker is not None
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query endpoint for document retrieval.
    
    Performs hybrid search (BM25 + vector) with optional reranking.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received query: {request.query}")
        
        # Generate query embedding
        query_vector = embedding_provider.embed(request.query)
        
        # Perform hybrid search
        results = weaviate_client.hybrid_search(
            query=request.query,
            query_vector=query_vector,
            limit=request.top_k,
            alpha=request.alpha,
            filters=request.filters
        )
        
        # Rerank if requested
        reranked = False
        if request.rerank and reranker and len(results) > 1:
            logger.info(f"Reranking {len(results)} results")
            
            # Extract texts
            texts = [r.text for r in results]
            
            # Rerank
            rerank_results = reranker.rerank(
                query=request.query,
                documents=texts,
                top_k=request.rerank_top_k
            )
            
            # Reorder results
            reranked_indices = [idx for idx, _ in rerank_results]
            results = [results[i] for i in reranked_indices]
            
            # Update scores with rerank scores
            for i, (_, score) in enumerate(rerank_results):
                results[i].score = score
            
            reranked = True
        
        # Convert to dict
        results_dict = [r.to_dict() for r in results]
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"Query processed in {processing_time:.3f}s, "
            f"returned {len(results_dict)} results"
        )
        
        return QueryResponse(
            query=request.query,
            results=results_dict,
            total_results=len(results_dict),
            reranked=reranked,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def get_documents():
    """Get all documents."""
    try:
        documents = weaviate_client.get_documents()
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/doc/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    """Get all chunks for a document."""
    try:
        chunks = weaviate_client.get_document_chunks(doc_id)
        chunks_dict = [c.to_dict() for c in chunks]
        return {"doc_id": doc_id, "chunks": chunks_dict, "total": len(chunks_dict)}
    except Exception as e:
        logger.error(f"Error retrieving document chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/doc/{doc_id}/page/{page}")
async def get_document_page(doc_id: str, page: int):
    """
    Get document page.
    
    TODO: Implement page serving (PDF snippet or PNG).
    For now, returns metadata about the page.
    """
    try:
        # Get chunks for this page
        all_chunks = weaviate_client.get_document_chunks(doc_id)
        page_chunks = [c for c in all_chunks if c.page == page]
        
        return {
            "doc_id": doc_id,
            "page": page,
            "chunks": [c.to_dict() for c in page_chunks],
            "message": "Page serving not yet implemented"
        }
    except Exception as e:
        logger.error(f"Error retrieving page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming queries.
    
    Client sends: {"query": "...", "top_k": 5}
    Server streams: {"type": "result", "data": {...}} or {"type": "done"}
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            query_text = data.get("query", "")
            top_k = data.get("top_k", 5)
            
            if not query_text:
                await websocket.send_json({"type": "error", "message": "Empty query"})
                continue
            
            logger.info(f"WebSocket query: {query_text}")
            
            # Generate embedding
            query_vector = embedding_provider.embed(query_text)
            
            # Search
            results = weaviate_client.hybrid_search(
                query=query_text,
                query_vector=query_vector,
                limit=top_k * 2,
                alpha=0.5
            )
            
            # Rerank if enabled
            if reranker and len(results) > 1:
                texts = [r.text for r in results]
                rerank_results = reranker.rerank(query_text, texts, top_k=top_k)
                reranked_indices = [idx for idx, _ in rerank_results]
                results = [results[i] for i in reranked_indices]
            
            # Stream results
            for result in results[:top_k]:
                await websocket.send_json({
                    "type": "result",
                    "data": result.to_dict()
                })
            
            # Send done signal
            await websocket.send_json({"type": "done"})
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload
    )

