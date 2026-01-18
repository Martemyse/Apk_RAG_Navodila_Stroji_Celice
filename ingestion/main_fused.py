"""Main ingestion pipeline for text-image fused content units."""
import sys
import asyncio
from pathlib import Path
from typing import List
from loguru import logger
from tqdm import tqdm

from config import get_settings
from models import Document, ContentUnit, ImageAsset
from processing.layout_parser import get_layout_parser
from processing.content_unit_builder import get_content_unit_builder
from embeddings.multimodal_embeddings import get_multimodal_embedder
from storage.postgres_client import PostgresClient
from storage.weaviate_fused_client import get_weaviate_fused_client
from storage.weaviate_schema import create_content_unit_schema, create_document_schema

settings = get_settings()


class FusedIngestionWorker:
    """Ingestion worker for text-image fused content units."""
    
    def __init__(self):
        """Initialize ingestion worker."""
        logger.info("Initializing fused ingestion worker")
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        
        # Initialize components
        self.layout_parser = get_layout_parser()
        self.unit_builder = get_content_unit_builder()
        self.embedder = get_multimodal_embedder()
        self.postgres = PostgresClient()
        self.weaviate = None  # Will be initialized in initialize()
        
        logger.info("Fused ingestion worker initialized")
    
    async def initialize(self):
        """Initialize databases."""
        # Connect to Postgres
        await self.postgres.connect()
        await self.postgres.ensure_schema()
        
        # Initialize Weaviate client
        self.weaviate = get_weaviate_fused_client()
        
        # Ensure Weaviate schema
        create_content_unit_schema(self.weaviate.client)
        create_document_schema(self.weaviate.client)
    
    async def process_pdf(self, pdf_path: Path, force: bool = False) -> bool:
        """
        Process single PDF document.
        
        Args:
            pdf_path: Path to PDF file
            force: Force re-ingestion even if document exists
            
        Returns:
            True if successful, False otherwise
        """
        doc_id = pdf_path.stem
        
        logger.info(f"Processing {pdf_path.name}")
        
        try:
            # Check if already ingested
            # TODO: Add check in Postgres
            
            # 1. Parse PDF layout
            logger.info("Step 1/5: Parsing PDF layout")
            parsed_pdf = self.layout_parser.parse(pdf_path)
            
            # 2. Create document record
            logger.info("Step 2/5: Creating document record")
            document = Document(
                doc_id=parsed_pdf.doc_id,
                title=parsed_pdf.title,
                file_path=parsed_pdf.file_path,
                total_pages=parsed_pdf.total_pages
            )
            document.id = await self.postgres.insert_document(document)
            
            # 3. Build content units
            logger.info("Step 3/5: Building content units")
            content_units, image_assets = self.unit_builder.build_content_units(
                parsed_pdf, document
            )
            
            # 4. Store image assets
            logger.info(f"Step 4/5: Storing {len(image_assets)} image assets")
            for image_asset in image_assets:
                image_asset.document_id = document.id
                await self.postgres.insert_image_asset(image_asset)
            
            # 5. Generate embeddings and store
            logger.info(f"Step 5/5: Generating embeddings for {len(content_units)} units")
            
            # Generate embeddings
            embeddings = self.embedder.embed_batch(content_units)
            
            # Store content units in Postgres
            await self.postgres.batch_insert_content_units(content_units)
            
            # Store in Weaviate with embeddings
            self.weaviate.store_content_units(content_units, embeddings)
            
            logger.success(f"Successfully processed {pdf_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}", exc_info=True)
            return False
    
    
    async def process_directory(
        self,
        directory: Path,
        pattern: str = "*.pdf",
        force: bool = False
    ):
        """Process all PDFs in directory."""
        logger.info(f"Processing directory: {directory}")
        
        pdf_files = list(directory.glob(pattern))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Process each file
        success_count = 0
        fail_count = 0
        
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            success = await self.process_pdf(pdf_path, force=force)
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(
            f"Processing complete: {success_count} successful, {fail_count} failed"
        )
    
    async def run(self):
        """Run ingestion worker."""
        logger.info("Starting fused ingestion worker")
        
        # Initialize databases
        await self.initialize()
        
        # Process all PDFs
        pdf_dir = settings.pdf_source_dir
        
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return
        
        await self.process_directory(pdf_dir, force=False)
        
        logger.info("Ingestion complete")
    
    async def close(self):
        """Clean up resources."""
        await self.postgres.close()
        self.weaviate.close()


async def main():
    """Main entry point."""
    worker = FusedIngestionWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await worker.close()


if __name__ == "__main__":
    asyncio.run(main())

