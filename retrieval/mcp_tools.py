"""MCP tools for text-image fused RAG."""
from typing import List, Dict, Any, Optional
import asyncio
from loguru import logger
import asyncpg
from weaviate_client import WeaviateRetrievalClient
from embeddings import get_embedding_provider
from config import get_settings

settings = get_settings()


class RAGMCPTools:
    """MCP tools for RAG pipeline."""
    
    def __init__(self):
        """Initialize MCP tools."""
        self.settings = settings
        self.weaviate_client = None
        self.embedding_provider = None
        self.postgres_pool = None
    
    async def initialize(self):
        """Initialize connections."""
        self.weaviate_client = WeaviateRetrievalClient()
        self.embedding_provider = get_embedding_provider()
        
        # Connect to Postgres
        db_url = getattr(settings, 'postgres_url', 
            f"postgresql://{getattr(settings, 'postgres_user', 'postgres')}:"
            f"{getattr(settings, 'postgres_password', 'postgres')}@"
            f"{getattr(settings, 'postgres_host', 'postgres')}:"
            f"{getattr(settings, 'postgres_port', 5432)}/"
            f"{getattr(settings, 'postgres_db', 'postgres')}")
        
        self.postgres_pool = await asyncpg.create_pool(db_url)
        logger.info("MCP tools initialized")
    
    async def search_content_units(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search content units (fused text+image).
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of content units with image references
        """
        logger.info(f"Searching content units: {query}")
        
        # Generate query embedding
        query_vector = self.embedding_provider.embed(query)
        
        # Search Weaviate
        results = self.weaviate_client.hybrid_search(
            query=query,
            query_vector=query_vector,
            limit=top_k,
            alpha=0.5
        )
        
        # Convert to content units
        content_units = []
        for result in results:
            unit = {
                "id": result.chunk_id,  # Actually content unit id
                "doc_id": result.doc_id,
                "page_number": result.page,
                "section_title": result.section_path.split(" > ")[-1] if result.section_path else None,
                "section_path": result.section_path,
                "text": result.text,
                "score": result.score,
                "has_image": False,
                "image_id": None
            }
            
            # Get image_id from Weaviate properties
            # TODO: Update WeaviateRetrievalClient to return image_id
            # For now, fetch from Postgres
            if hasattr(result, 'properties') and result.properties.get('image_id'):
                unit["image_id"] = result.properties['image_id']
                unit["has_image"] = True
            
            content_units.append(unit)
        
        return content_units
    
    async def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image asset by ID.
        
        Args:
            image_id: Image asset UUID
            
        Returns:
            Image metadata with path/URL
        """
        logger.info(f"Getting image: {image_id}")
        
        async with self.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, image_path, bbox, auto_caption, page_number, doc_id
                FROM image_assets
                WHERE id = $1
                """,
                image_id
            )
            
            if not row:
                return None
            
            return {
                "image_id": str(row['id']),
                "image_path": row['image_path'],
                "bbox": row['bbox'],
                "caption": row['auto_caption'],
                "page_number": row['page_number'],
                "doc_id": row['doc_id']
            }
    
    async def get_pdf_section(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PDF section information for a content unit.
        
        Args:
            unit_id: Content unit UUID
            
        Returns:
            PDF section metadata
        """
        logger.info(f"Getting PDF section: {unit_id}")
        
        async with self.postgres_pool.acquire() as conn:
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
                return None
            
            return {
                "doc_id": row['doc_id'],
                "document_title": row['document_title'],
                "file_path": row['file_path'],
                "page_number": row['page_number'],
                "section_title": row['section_title'],
                "section_path": row['section_path']
            }
    
    async def close(self):
        """Close connections."""
        if self.postgres_pool:
            await self.postgres_pool.close()
        if self.weaviate_client:
            self.weaviate_client.close()


# Global instance
_mcp_tools: Optional[RAGMCPTools] = None


async def get_mcp_tools() -> RAGMCPTools:
    """Get MCP tools instance."""
    global _mcp_tools
    if _mcp_tools is None:
        _mcp_tools = RAGMCPTools()
        await _mcp_tools.initialize()
    return _mcp_tools

