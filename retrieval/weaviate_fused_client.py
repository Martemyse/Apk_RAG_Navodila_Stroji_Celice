"""Weaviate client for ContentUnit retrieval."""
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

class ContentUnitResult:
    """Content unit search result."""
    
    def __init__(self, obj: Any):
        """Initialize from Weaviate object."""
        props = obj.properties
        self.id = props.get("id", "")
        self.document_id = props.get("document_id", "")
        self.doc_id = props.get("doc_id", "")
        self.page_number = props.get("page_number", 0)
        self.section_title = props.get("section_title", "")
        self.section_path = props.get("section_path", "")
        self.text = props.get("text", "")
        self.unit_type = props.get("unit_type", "TEXT_ONLY")
        self.image_id = props.get("image_id", "")
        self.token_count = props.get("token_count", 0)
        self.tags = props.get("tags", [])
        self.score = obj.metadata.score if hasattr(obj.metadata, 'score') else 0.0
        self.distance = obj.metadata.distance if hasattr(obj.metadata, 'distance') else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "text": self.text,
            "unit_type": self.unit_type,
            "image_id": self.image_id if self.image_id else None,
            "has_image": bool(self.image_id),
            "token_count": self.token_count,
            "tags": self.tags,
            "score": self.score,
        }


class WeaviateFusedRetrievalClient:
    """Client for retrieving ContentUnits from Weaviate."""
    
    def __init__(self):
        """Initialize Weaviate client."""
        self.settings = settings
        self.client: Optional[weaviate.WeaviateClient] = None
        self._connect()
    
    def _connect(self):
        """Connect to Weaviate."""
        try:
            logger.info(f"Connecting to Weaviate at {settings.weaviate_url}")
            
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
        limit: int = 10,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContentUnitResult]:
        """
        Perform hybrid search on ContentUnit collection.
        
        Args:
            query: Query text
            query_vector: Query embedding (optional)
            limit: Number of results
            alpha: Hybrid search weight (0=BM25, 1=vector)
            filters: Optional filters
            
        Returns:
            List of ContentUnitResult objects
        """
        try:
            collection = self.client.collections.get("ContentUnit")
            
            # Build filter if provided
            where_filter = None
            if filters:
                if "doc_id" in filters:
                    where_filter = wq.Filter.by_property("doc_id").equal(filters["doc_id"])
                if "unit_type" in filters:
                    type_filter = wq.Filter.by_property("unit_type").equal(filters["unit_type"])
                    if where_filter:
                        where_filter = where_filter & type_filter
                    else:
                        where_filter = type_filter
            
            # Perform hybrid search
            if query_vector:
                response = collection.query.hybrid(
                    query=query,
                    vector=query_vector,
                    limit=limit,
                    alpha=alpha,
                    filters=where_filter
                )
            else:
                response = collection.query.hybrid(
                    query=query,
                    limit=limit,
                    alpha=alpha,
                    filters=where_filter
                )
            
            # Convert to ContentUnitResult objects
            results = [ContentUnitResult(obj) for obj in response.objects]
            
            logger.info(f"Found {len(results)} content units for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            raise
    
    def get_content_unit(self, unit_id: str) -> Optional[ContentUnitResult]:
        """Get content unit by ID."""
        try:
            collection = self.client.collections.get("ContentUnit")
            
            response = collection.query.fetch_objects(
                filters=wq.Filter.by_property("id").equal(unit_id),
                limit=1
            )
            
            if response.objects:
                return ContentUnitResult(response.objects[0])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving content unit: {e}")
            return None
    
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


def get_weaviate_fused_client() -> WeaviateFusedRetrievalClient:
    """Get Weaviate fused client instance."""
    return WeaviateFusedRetrievalClient()

