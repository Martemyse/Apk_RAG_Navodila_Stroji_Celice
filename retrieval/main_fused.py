"""FastAPI application for fused text-image RAG retrieval."""
import sys
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger
import time
import asyncpg

from config import get_settings
from weaviate_fused_client import get_weaviate_fused_client, ContentUnitResult
from embeddings import get_embedding_provider
from mcp_tools import get_mcp_tools

settings = get_settings()

# Global instances
weaviate_client = None
embedding_provider = None
postgres_pool = None


# Pydantic models
class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=10, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")
    alpha: float = Field(default=0.5, description="Hybrid search alpha (0=BM25, 1=vector)")


class QueryResponse(BaseModel):
    """Query response model."""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    weaviate_connected: bool
    postgres_connected: bool


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    global weaviate_client, embedding_provider, postgres_pool
    
    # Startup
    logger.info("Starting up fused retrieval service")
    
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
        weaviate_client = get_weaviate_fused_client()
        
        logger.info("Initializing embedding provider")
        embedding_provider = get_embedding_provider()
        
        logger.info("Initializing PostgreSQL connection")
        db_url = getattr(settings, 'postgres_url',
            f"postgresql://{getattr(settings, 'postgres_user', 'postgres')}:"
            f"{getattr(settings, 'postgres_password', 'postgres')}@"
            f"{getattr(settings, 'postgres_host', 'postgres')}:"
            f"{getattr(settings, 'postgres_port', 5432)}/"
            f"{getattr(settings, 'postgres_db', 'postgres')}")
        
        postgres_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        
        logger.info("Fused retrieval service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down fused retrieval service")
    if weaviate_client:
        weaviate_client.close()
    if postgres_pool:
        await postgres_pool.close()


# Create FastAPI app
app = FastAPI(
    title="Fused RAG Retrieval Service",
    description="Retrieval service for text-image fused content units",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Fused RAG Retrieval Service",
        "version": "2.0.0",
        "status": "running",
        "architecture": "text-image fused content units"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    weaviate_ok = weaviate_client.health_check() if weaviate_client else False
    
    postgres_ok = False
    if postgres_pool:
        try:
            async with postgres_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            postgres_ok = True
        except Exception:
            pass
    
    return HealthResponse(
        status="healthy" if (weaviate_ok and postgres_ok) else "degraded",
        weaviate_connected=weaviate_ok,
        postgres_connected=postgres_ok
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query endpoint for content unit retrieval.
    
    Returns fused text+image content units with image references.
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
        
        # Convert to dict
        results_dict = [r.to_dict() for r in results]
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"Query processed in {processing_time:.3f}s, "
            f"returned {len(results_dict)} content units"
        )
        
        return QueryResponse(
            query=request.query,
            results=results_dict,
            total_results=len(results_dict),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content_unit/{unit_id}")
async def get_content_unit(unit_id: str):
    """Get content unit by ID."""
    try:
        unit = weaviate_client.get_content_unit(unit_id)
        
        if not unit:
            raise HTTPException(status_code=404, detail="Content unit not found")
        
        return unit.to_dict()
        
    except Exception as e:
        logger.error(f"Error retrieving content unit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/image/{image_id}")
async def get_image(image_id: str):
    """Get image asset by ID."""
    try:
        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, image_path, bbox, auto_caption, page_number, doc_id
                FROM image_assets
                WHERE id = $1
                """,
                image_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Image not found")
            
            return {
                "image_id": str(row['id']),
                "image_path": row['image_path'],
                "bbox": row['bbox'],
                "caption": row['auto_caption'],
                "page_number": row['page_number'],
                "doc_id": row['doc_id']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pdf_section/{unit_id}")
async def get_pdf_section(unit_id: str):
    """Get PDF section information for a content unit."""
    try:
        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    cu.doc_id,
                    d.title AS document_title,
                    d.file_path,
                    cu.page_number,
                    cu.section_title,
                    cu.section_path
                FROM content_units cu
                JOIN documents d ON cu.document_id = d.id
                WHERE cu.id = $1
                """,
                unit_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Content unit not found")
            
            return {
                "doc_id": row['doc_id'],
                "document_title": row['document_title'],
                "file_path": row['file_path'],
                "page_number": row['page_number'],
                "section_title": row['section_title'],
                "section_path": row['section_path']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving PDF section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_fused:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload
    )

