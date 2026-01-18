"""Main ingestion worker."""
import sys
import time
from pathlib import Path
from typing import List
from loguru import logger
from tqdm import tqdm

from config import get_settings
from processing.parsers import get_parser, ParsedDocument
from processing.chunking import get_chunker
from embeddings.embeddings import get_embedding_provider
from storage.weaviate_client import get_weaviate_client

settings = get_settings()


class IngestionWorker:
    """Main ingestion worker."""
    
    def __init__(self):
        """Initialize ingestion worker."""
        logger.info("Initializing ingestion worker")
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        
        # Initialize components
        self.parser = get_parser()
        self.chunker = get_chunker()
        self.embedding_provider = get_embedding_provider()
        self.weaviate_client = get_weaviate_client()
        
        # Ensure schema
        self.weaviate_client.ensure_schema()
        
        logger.info("Ingestion worker initialized")
    
    def process_pdf(self, pdf_path: Path, force: bool = False) -> bool:
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
            if not force and self.weaviate_client.document_exists(doc_id):
                logger.info(f"Document {doc_id} already exists, skipping")
                return True
            
            # If force, delete existing
            if force and self.weaviate_client.document_exists(doc_id):
                logger.info(f"Force flag set, deleting existing document {doc_id}")
                self.weaviate_client.delete_document(doc_id)
            
            # 1. Parse PDF
            logger.info("Step 1/4: Parsing PDF")
            parsed_doc = self.parser.parse(pdf_path, use_unstructured=False)
            
            # 2. Chunk document
            logger.info("Step 2/4: Chunking document")
            chunks = self.chunker.chunk(parsed_doc)
            
            if not chunks:
                logger.warning(f"No chunks generated for {doc_id}")
                return False
            
            # 3. Generate embeddings
            logger.info(f"Step 3/4: Generating embeddings for {len(chunks)} chunks")
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_provider.embed(texts)
            
            # Convert to list of lists for Weaviate
            embeddings_list = embeddings.tolist()
            
            # 4. Ingest to Weaviate
            logger.info("Step 4/4: Ingesting to Weaviate")
            self.weaviate_client.ingest_document(parsed_doc, chunks, embeddings_list)
            
            logger.success(f"Successfully processed {pdf_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}", exc_info=True)
            return False
    
    def process_directory(
        self,
        directory: Path,
        pattern: str = "*.pdf",
        force: bool = False
    ):
        """
        Process all PDFs in directory.
        
        Args:
            directory: Directory containing PDFs
            pattern: File pattern to match
            force: Force re-ingestion
        """
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
            success = self.process_pdf(pdf_path, force=force)
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(
            f"Processing complete: {success_count} successful, {fail_count} failed"
        )
    
    def run(self):
        """Run ingestion worker."""
        logger.info("Starting ingestion worker")
        
        # Wait for Weaviate to be ready
        logger.info("Waiting for Weaviate to be ready...")
        time.sleep(5)
        
        # Process all PDFs
        pdf_dir = settings.pdf_source_dir
        
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return
        
        self.process_directory(pdf_dir, force=False)
        
        logger.info("Ingestion complete")
    
    def close(self):
        """Clean up resources."""
        self.weaviate_client.close()


def main():
    """Main entry point."""
    worker = IngestionWorker()
    
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        worker.close()


if __name__ == "__main__":
    main()

