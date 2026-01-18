"""Weaviate schema for ContentUnit (text-image fused)."""
import weaviate
import weaviate.classes.config as wc
from weaviate.classes.config import Property, DataType
from loguru import logger


def create_content_unit_schema(client: weaviate.WeaviateClient):
    """Create ContentUnit schema in Weaviate."""
    try:
        # Check if collection exists
        client.collections.get("ContentUnit")
        logger.info("ContentUnit collection already exists")
        return
    except Exception:
        pass
    
    logger.info("Creating ContentUnit collection")
    
    try:
        client.collections.create(
            name="ContentUnit",
            description="Fused text+image content units for semantic search",
            properties=[
                # Note: 'id' is reserved by Weaviate - use uuid parameter in batch.add_object()
                Property(name="document_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="doc_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="page_number", data_type=DataType.INT, skip_vectorization=True),
                Property(name="section_title", data_type=DataType.TEXT),
                Property(name="section_path", data_type=DataType.TEXT),
                Property(name="text", data_type=DataType.TEXT),
                Property(name="unit_type", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="image_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="token_count", data_type=DataType.INT, skip_vectorization=True),
                Property(name="tags", data_type=DataType.TEXT_ARRAY),
            ],
            vectorizer_config=wc.Configure.Vectorizer.none(),  # External embeddings
            # Enable hybrid search (BM25 + vector)
        )
        
        logger.info("ContentUnit collection created successfully")
        
    except Exception as e:
        logger.error(f"Error creating ContentUnit schema: {e}")
        raise


def create_document_schema(client: weaviate.WeaviateClient):
    """Create Document schema in Weaviate (optional, for metadata)."""
    try:
        client.collections.get("Document")
        logger.info("Document collection already exists")
        return
    except Exception:
        pass
    
    logger.info("Creating Document collection")
    
    try:
        client.collections.create(
            name="Document",
            description="Document metadata",
            properties=[
                # Note: 'id' is reserved by Weaviate - use uuid parameter in batch.add_object()
                Property(name="doc_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="file_path", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="domain", data_type=DataType.TEXT),
                Property(name="total_pages", data_type=DataType.INT, skip_vectorization=True),
            ],
            vectorizer_config=wc.Configure.Vectorizer.none(),
        )
        
        logger.info("Document collection created successfully")
        
    except Exception as e:
        logger.error(f"Error creating Document schema: {e}")
        raise

