"""Weaviate client for ingestion."""
import time
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import weaviate
import weaviate.classes.config as wc
from weaviate.classes.config import Property, DataType
from loguru import logger
from parsers import ParsedDocument, DocumentChunk
from config import get_settings

settings = get_settings()


class WeaviateIngestionClient:
    """Client for ingesting documents into Weaviate."""
    
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
                    if settings.weaviate_api_key:
                        self.client = weaviate.connect_to_custom(
                            http_host=settings.weaviate_url.replace("http://", "").replace("https://", ""),
                            http_port=8080,
                            http_secure=False,
                            grpc_host=settings.weaviate_url.replace("http://", "").replace("https://", ""),
                            grpc_port=50051,
                            grpc_secure=False,
                            auth_credentials=weaviate.auth.AuthApiKey(settings.weaviate_api_key),
                            timeout=weaviate.config.Timeout(query=settings.weaviate_timeout)
                        )
                    else:
                        self.client = weaviate.connect_to_custom(
                            http_host=settings.weaviate_url.replace("http://", "").replace("https://", ""),
                            http_port=8080,
                            http_secure=False,
                            grpc_host=settings.weaviate_url.replace("http://", "").replace("https://", ""),
                            grpc_port=50051,
                            grpc_secure=False,
                            timeout=weaviate.config.Timeout(query=settings.weaviate_timeout)
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
    
    def ensure_schema(self):
        """Ensure Weaviate schema exists."""
        logger.info("Ensuring Weaviate schema")
        
        try:
            # Create Document collection
            self._create_document_collection()
            
            # Create Chunk collection
            self._create_chunk_collection()
            
            # Future: Create Figure and Table collections
            
            logger.info("Schema ensured successfully")
            
        except Exception as e:
            logger.error(f"Error ensuring schema: {e}")
            raise
    
    def _create_document_collection(self):
        """Create Document collection if not exists."""
        try:
            self.client.collections.get("Document")
            logger.info("Document collection already exists")
        except Exception:
            logger.info("Creating Document collection")
            
            self.client.collections.create(
                name="Document",
                description="Document metadata",
                properties=[
                    Property(name="doc_id", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="source_uri", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="total_pages", data_type=DataType.INT, skip_vectorization=True),
                    Property(name="created_at", data_type=DataType.DATE, skip_vectorization=True),
                    Property(name="department", data_type=DataType.TEXT),
                    Property(name="tags", data_type=DataType.TEXT_ARRAY),
                ],
                vectorizer_config=wc.Configure.Vectorizer.none(),  # Using external vectors
            )
            
            logger.info("Document collection created")
    
    def _create_chunk_collection(self):
        """Create Chunk collection if not exists."""
        try:
            self.client.collections.get("Chunk")
            logger.info("Chunk collection already exists")
        except Exception:
            logger.info("Creating Chunk collection")
            
            self.client.collections.create(
                name="Chunk",
                description="Document chunks with embeddings",
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="doc_id", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="page", data_type=DataType.INT, skip_vectorization=True),
                    Property(name="section_path", data_type=DataType.TEXT),
                    Property(name="bbox", data_type=DataType.TEXT, skip_vectorization=True),
                    Property(name="token_count", data_type=DataType.INT, skip_vectorization=True),
                ],
                vectorizer_config=wc.Configure.Vectorizer.none(),  # Using external vectors
                # Enable inverted index for hybrid search (BM25)
            )
            
            logger.info("Chunk collection created")
    
    def ingest_document(
        self,
        parsed_doc: ParsedDocument,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ):
        """
        Ingest document and chunks into Weaviate.
        
        Args:
            parsed_doc: Parsed document metadata
            chunks: List of document chunks
            embeddings: List of embeddings for each chunk
        """
        logger.info(f"Ingesting document {parsed_doc.doc_id} with {len(chunks)} chunks")
        
        try:
            # 1. Insert document metadata
            self._insert_document(parsed_doc)
            
            # 2. Batch insert chunks with embeddings
            self._batch_insert_chunks(chunks, embeddings)
            
            logger.info(f"Successfully ingested {parsed_doc.doc_id}")
            
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            raise
    
    def _insert_document(self, parsed_doc: ParsedDocument):
        """Insert document metadata."""
        documents = self.client.collections.get("Document")
        
        from datetime import datetime
        
        documents.data.insert(
            properties={
                "doc_id": parsed_doc.doc_id,
                "title": parsed_doc.title,
                "source_uri": parsed_doc.source_uri,
                "total_pages": parsed_doc.total_pages,
                "created_at": datetime.now().isoformat(),
                "department": "manufacturing",  # TODO: Extract from metadata
                "tags": ["manual", "equipment"],  # TODO: Extract tags
            }
        )
    
    def _batch_insert_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ):
        """Batch insert chunks with embeddings."""
        chunks_collection = self.client.collections.get("Chunk")
        
        # Use Weaviate's batch API
        with self.client.batch.dynamic() as batch:
            for chunk, embedding in zip(chunks, embeddings):
                batch.add_object(
                    collection="Chunk",
                    properties={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "text": chunk.text,
                        "page": chunk.page,
                        "section_path": chunk.section_path,
                        "bbox": chunk.bbox or "",
                        "token_count": chunk.token_count,
                    },
                    vector=embedding
                )
        
        logger.info(f"Inserted {len(chunks)} chunks")
    
    def document_exists(self, doc_id: str) -> bool:
        """Check if document already exists."""
        try:
            documents = self.client.collections.get("Document")
            response = documents.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("doc_id").equal(doc_id),
                limit=1
            )
            return len(response.objects) > 0
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False
    
    def delete_document(self, doc_id: str):
        """Delete document and all its chunks."""
        logger.info(f"Deleting document {doc_id}")
        
        try:
            # Delete document
            documents = self.client.collections.get("Document")
            documents.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("doc_id").equal(doc_id)
            )
            
            # Delete chunks
            chunks = self.client.collections.get("Chunk")
            chunks.data.delete_many(
                where=weaviate.classes.query.Filter.by_property("doc_id").equal(doc_id)
            )
            
            logger.info(f"Deleted document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    def close(self):
        """Close Weaviate connection."""
        if self.client:
            self.client.close()
            logger.info("Weaviate connection closed")


def get_weaviate_client() -> WeaviateIngestionClient:
    """Get Weaviate client instance."""
    return WeaviateIngestionClient()

