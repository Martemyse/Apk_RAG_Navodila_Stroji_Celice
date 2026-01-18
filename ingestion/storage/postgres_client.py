"""PostgreSQL client for storing document metadata and relationships."""
import asyncpg
import json
from typing import List, Optional, Dict, Any
from loguru import logger
from models import Document, ImageAsset, ContentUnit, UnitType
from config import get_settings

settings = get_settings()


class PostgresClient:
    """PostgreSQL client for metadata storage."""
    
    def __init__(self):
        """Initialize PostgreSQL client."""
        self.settings = settings
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool."""
        try:
            # Get PostgreSQL connection from environment or use defaults
            db_url = settings.postgres_url if settings.postgres_url else \
                f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            
            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10
            )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection closed")
    
    async def ensure_schema(self):
        """Ensure database schema exists."""
        try:
            # Read and execute schema SQL
            schema_path = settings.postgres_schema_path if hasattr(settings, 'postgres_schema_path') else \
                "/app/postgres/schema.sql"
            
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            
            async with self.pool.acquire() as conn:
                await conn.execute(schema_sql)
            
            logger.info("Database schema ensured")
        except Exception as e:
            logger.error(f"Error ensuring schema: {e}")
            raise
    
    async def insert_document(self, doc: Document) -> str:
        """Insert document and return ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO documents (id, doc_id, title, file_path, created_at, domain, total_pages, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        file_path = EXCLUDED.file_path,
                        total_pages = EXCLUDED.total_pages,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                    """,
                    doc.id, doc.doc_id, doc.title, doc.file_path,
                    doc.created_at, doc.domain, doc.total_pages, json.dumps(doc.metadata)
                )
                return str(row['id'])
        except Exception as e:
            # Safe logging - convert exception to string first to avoid formatting issues
            error_msg = str(e)
            logger.error(
                f"Error inserting document {doc.doc_id}: {error_msg}. "
                f"Values: id={doc.id}, doc_id={doc.doc_id}, "
                f"title={doc.title[:50] if doc.title else 'None'}, "
                f"file_path={doc.file_path}, created_at={doc.created_at}, "
                f"domain={doc.domain}, total_pages={doc.total_pages}"
            )
            logger.exception("Full exception details:")
            raise
    
    async def insert_image_asset(self, image: ImageAsset) -> str:
        """Insert image asset and return ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO image_assets 
                (id, document_id, doc_id, page_number, bbox, image_path, auto_caption, image_hash, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                image.id, image.document_id, image.doc_id, image.page_number,
                json.dumps(image.bbox), image.image_path, image.auto_caption,
                image.image_hash, json.dumps(image.metadata)
            )
            return str(row['id'])
    
    async def insert_content_unit(self, unit: ContentUnit) -> str:
        """Insert content unit and return ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO content_units
                (id, document_id, doc_id, page_number, section_title, section_path,
                 text, unit_type, image_id, token_count, bbox, tags, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
                """,
                unit.id, unit.document_id, unit.doc_id, unit.page_number,
                unit.section_title, unit.section_path, unit.text,
                unit.unit_type.value, unit.image_id, unit.token_count,
                json.dumps(unit.bbox) if unit.bbox else None, 
                unit.tags, json.dumps(unit.metadata)
            )
            return str(row['id'])
    
    async def batch_insert_content_units(self, units: List[ContentUnit]):
        """Batch insert content units."""
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO content_units
                (id, document_id, doc_id, page_number, section_title, section_path,
                 text, unit_type, image_id, token_count, bbox, tags, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                [
                    (
                        unit.id, unit.document_id, unit.doc_id, unit.page_number,
                        unit.section_title, unit.section_path, unit.text,
                        unit.unit_type.value, unit.image_id, unit.token_count,
                        json.dumps(unit.bbox) if unit.bbox else None,
                        unit.tags, json.dumps(unit.metadata)
                    )
                    for unit in units
                ]
            )
        logger.info(f"Inserted {len(units)} content units")
    
    async def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image asset by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, image_path, bbox, auto_caption, page_number, doc_id
                FROM image_assets
                WHERE id = $1
                """,
                image_id
            )
            if row:
                return dict(row)
            return None
    
    async def get_content_unit_with_image(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Get content unit with image info."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM content_units_with_images
                WHERE id = $1
                """,
                unit_id
            )
            if row:
                return dict(row)
            return None


def get_postgres_client() -> PostgresClient:
    """Get PostgreSQL client instance."""
    return PostgresClient()

