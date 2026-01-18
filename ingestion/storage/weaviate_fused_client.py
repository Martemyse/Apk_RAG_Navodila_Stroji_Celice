"""Weaviate client for ContentUnit ingestion."""
import time
from typing import List, Tuple
from urllib.parse import urlparse
import weaviate
from loguru import logger
from config import get_settings
from models import ContentUnit

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

class WeaviateFusedClient:
    """Weaviate client for ContentUnit ingestion."""
    
    def __init__(self):
        """Initialize Weaviate client."""
        self.settings = settings
        self.client: weaviate.WeaviateClient = None
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
    
    def store_content_units(
        self,
        content_units: List[ContentUnit],
        embeddings: List[List[float]]
    ):
        """Store content units with embeddings in Weaviate."""
        collection = self.client.collections.get("ContentUnit")
        
        with self.client.batch.dynamic() as batch:
            for unit, embedding in zip(content_units, embeddings):
                # Weaviate doesn't allow 'id' in properties - it must be passed as uuid parameter
                batch.add_object(
                    collection="ContentUnit",
                    uuid=unit.id,  # Pass id as uuid parameter, not in properties
                    properties={
                        "document_id": unit.document_id,
                        "doc_id": unit.doc_id,
                        "page_number": unit.page_number,
                        "section_title": unit.section_title or "",
                        "section_path": unit.section_path or "",
                        "text": unit.text,
                        "unit_type": unit.unit_type.value,
                        "image_id": unit.image_id or "",
                        "token_count": unit.token_count,
                        "tags": unit.tags,
                    },
                    vector=embedding
                )
        
        logger.info(f"Stored {len(content_units)} content units in Weaviate")
    
    def close(self):
        """Close Weaviate connection."""
        if self.client:
            self.client.close()
            logger.info("Weaviate connection closed")


def get_weaviate_fused_client() -> WeaviateFusedClient:
    """Get Weaviate fused client instance."""
    return WeaviateFusedClient()

