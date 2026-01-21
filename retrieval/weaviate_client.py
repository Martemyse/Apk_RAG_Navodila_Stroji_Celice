"""Weaviate client for retrieval."""
import time
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import weaviate
import weaviate.classes.query as wq
from loguru import logger
from config import get_settings

settings = get_settings()

def _parse_host_port(url: str, default_port: int) -> Tuple[str, int]:
    """Parse host and port from a URL or host:port string."""
    if not url:
        return ("weaviate", default_port)
    if "://" not in url:
        url = f"http://{url}"
    parsed = urlparse(url)
    host = parsed.hostname or url
    port = parsed.port or default_port
    return host, port

class SearchResult:
    """Search result wrapper."""
    
    def __init__(self, obj: Any):
        """Initialize from Weaviate object."""
        self.chunk_id = getattr(obj, "uuid", "") or obj.properties.get("chunk_id", "")
        self.doc_id = obj.properties.get("doc_id", "")
        self.text = obj.properties.get("text", "")
        self.page = obj.properties.get("page_number", 0)
        self.section_path = obj.properties.get("section_path", "")
        self.bbox = obj.properties.get("bbox", "")
        self.token_count = obj.properties.get("token_count", 0)
        self.score = obj.metadata.score if hasattr(obj.metadata, 'score') else 0.0
        self.distance = obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "page": self.page,
            "section_path": self.section_path,
            "bbox": self.bbox,
            "token_count": self.token_count,
            "score": self.score,
        }


class WeaviateRetrievalClient:
    """Client for retrieval from Weaviate."""
    
    def __init__(self):
        """Initialize Weaviate client."""
        self.settings = settings
        self.client: Optional[weaviate.WeaviateClient] = None
        self._connect()
    
    def _connect(self):
        """Connect to Weaviate."""
        try:
            logger.info(f"Connecting to Weaviate at {settings.weaviate_url}")
            
            # Add retry logic
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    http_host, http_port = _parse_host_port(settings.weaviate_url, 8080)
                    grpc_url = getattr(settings, "weaviate_grpc_url", "")
                    grpc_host, grpc_port = _parse_host_port(grpc_url, 50051)
                    if not grpc_url:
                        grpc_host = http_host
                    if settings.weaviate_api_key:
                        self.client = weaviate.connect_to_custom(
                            http_host=http_host,
                            http_port=http_port,
                            http_secure=False,
                            grpc_host=grpc_host,
                            grpc_port=grpc_port,
                            grpc_secure=False,
                            auth_credentials=weaviate.auth.AuthApiKey(settings.weaviate_api_key),
                        )
                    else:
                        self.client = weaviate.connect_to_custom(
                            http_host=http_host,
                            http_port=http_port,
                            http_secure=False,
                            grpc_host=grpc_host,
                            grpc_port=grpc_port,
                            grpc_secure=False,
                        )
                    
                    # Test connection
                    self.client.collections.list_all()
                    logger.info("Successfully connected to Weaviate")
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def hybrid_search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        limit: int = 25,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search (BM25 + vector).
        
        Args:
            query: Query text
            query_vector: Query embedding (optional, will use text if None)
            limit: Number of results
            alpha: Hybrid search weight (0 = BM25 only, 1 = vector only)
            filters: Optional filters (e.g., {"doc_id": "..."}
            
        Returns:
            List of SearchResult objects
        """
        try:
            chunks = self.client.collections.get("ContentUnit")
            
            # Build filter if provided
            where_filter = None
            if filters:
                if "doc_id" in filters:
                    where_filter = wq.Filter.by_property("doc_id").equal(filters["doc_id"])
            
            # Perform hybrid search
            if query_vector:
                # Use provided vector
                response = chunks.query.hybrid(
                    query=query,
                    vector=query_vector,
                    limit=limit,
                    alpha=alpha,
                    filters=where_filter
                )
            else:
                # Use text only (Weaviate will vectorize if module configured)
                response = chunks.query.hybrid(
                    query=query,
                    limit=limit,
                    alpha=alpha,
                    filters=where_filter
                )
            
            # Convert to SearchResult objects
            results = [SearchResult(obj) for obj in response.objects]
            
            logger.info(f"Found {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            raise
    
    def vector_search(
        self,
        query_vector: List[float],
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform pure vector search.
        
        Args:
            query_vector: Query embedding
            limit: Number of results
            filters: Optional filters
            
        Returns:
            List of SearchResult objects
        """
        try:
            chunks = self.client.collections.get("ContentUnit")
            
            # Build filter if provided
            where_filter = None
            if filters:
                if "doc_id" in filters:
                    where_filter = wq.Filter.by_property("doc_id").equal(filters["doc_id"])
            
            # Perform vector search
            response = chunks.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                filters=where_filter
            )
            
            # Convert to SearchResult objects
            results = [SearchResult(obj) for obj in response.objects]
            
            logger.info(f"Found {len(results)} results for vector search")
            return results
            
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise
    
    def get_document_chunks(self, doc_id: str) -> List[SearchResult]:
        """
        Get all chunks for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            List of SearchResult objects
        """
        try:
            chunks = self.client.collections.get("ContentUnit")
            
            response = chunks.query.fetch_objects(
                filters=wq.Filter.by_property("doc_id").equal(doc_id),
                limit=1000
            )
            
            results = [SearchResult(obj) for obj in response.objects]
            
            logger.info(f"Retrieved {len(results)} chunks for document {doc_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving document chunks: {e}")
            raise
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """
        Get all documents.
        
        Returns:
            List of document dictionaries
        """
        try:
            documents = self.client.collections.get("Document")
            
            response = documents.query.fetch_objects(limit=1000)
            
            docs = [
                {
                    "doc_id": obj.properties.get("doc_id", ""),
                    "title": obj.properties.get("title", ""),
                    "total_pages": obj.properties.get("total_pages", 0),
                    "department": obj.properties.get("department", ""),
                    "tags": obj.properties.get("tags", []),
                }
                for obj in response.objects
            ]
            
            logger.info(f"Retrieved {len(docs)} documents")
            return docs
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check Weaviate health."""
        try:
            self.client.collections.list_all()
            return True
        except Exception:
            return False
    
    def close(self):
        """Close connection."""
        if self.client:
            self.client.close()
            logger.info("Weaviate connection closed")


def get_weaviate_client() -> WeaviateRetrievalClient:
    """Get Weaviate client instance."""
    return WeaviateRetrievalClient()

