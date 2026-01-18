"""PDF parsers using PyMuPDF4LLM and Unstructured."""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
import pymupdf4llm
import pymupdf as fitz
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element
from config import get_settings

settings = get_settings()


@dataclass
class ParsedDocument:
    """Parsed document structure."""
    doc_id: str
    title: str
    source_uri: str
    total_pages: int
    markdown_content: str
    elements: List[Dict]
    images: List[Dict]
    tables: List[Dict]
    metadata: Dict


@dataclass
class DocumentChunk:
    """A chunk of document content."""
    chunk_id: str
    doc_id: str
    text: str
    page: int
    section_path: str
    bbox: Optional[str]
    token_count: int
    metadata: Dict


class PyMuPDFParser:
    """Parser using PyMuPDF4LLM for layout-aware extraction."""
    
    def __init__(self):
        self.settings = settings
    
    def parse(self, pdf_path: Path) -> ParsedDocument:
        """
        Parse PDF using PyMuPDF4LLM.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParsedDocument with markdown content and metadata
        """
        logger.info(f"Parsing {pdf_path.name} with PyMuPDF4LLM")
        
        doc_id = pdf_path.stem
        
        # Extract markdown with layout awareness
        try:
            # Use pymupdf4llm to extract markdown
            markdown_content = pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=None,  # All pages
                write_images=settings.extract_images,
                image_path=str(settings.processed_dir / doc_id / "images") if settings.extract_images else None,
                image_format="png",
                dpi=150
            )
        except Exception as e:
            logger.error(f"Error extracting markdown from {pdf_path.name}: {e}")
            markdown_content = ""
        
        # Open document for metadata and image extraction
        images = []
        tables = []
        total_pages = 0
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Extract images with coordinates
            if settings.extract_images:
                images = self._extract_images(doc, doc_id)
            
            # Extract tables (basic detection)
            if settings.extract_tables:
                tables = self._extract_tables(doc, doc_id)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error opening PDF {pdf_path.name}: {e}")
        
        # Create parsed document
        parsed_doc = ParsedDocument(
            doc_id=doc_id,
            title=pdf_path.stem.replace("_", " "),
            source_uri=str(pdf_path),
            total_pages=total_pages,
            markdown_content=markdown_content,
            elements=[],  # Will be populated by Unstructured if needed
            images=images,
            tables=tables,
            metadata={
                "filename": pdf_path.name,
                "parser": "pymupdf4llm",
                "file_size": pdf_path.stat().st_size,
            }
        )
        
        logger.info(
            f"Parsed {pdf_path.name}: {total_pages} pages, "
            f"{len(images)} images, {len(tables)} tables"
        )
        
        return parsed_doc
    
    def _extract_images(self, doc: fitz.Document, doc_id: str) -> List[Dict]:
        """Extract images with metadata."""
        images = []
        image_dir = settings.processed_dir / doc_id / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_idx, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Get image position
                    rects = page.get_image_rects(xref)
                    bbox = str(rects[0]) if rects else None
                    
                    # Save image
                    image_filename = f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
                    image_path = image_dir / image_filename
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    images.append({
                        "image_id": f"{doc_id}_p{page_num + 1}_i{img_idx + 1}",
                        "page": page_num + 1,
                        "bbox": bbox,
                        "image_uri": str(image_path),
                        "format": image_ext,
                        "caption": None  # To be filled by image captioning later
                    })
                    
                except Exception as e:
                    logger.warning(f"Error extracting image on page {page_num + 1}: {e}")
        
        return images
    
    def _extract_tables(self, doc: fitz.Document, doc_id: str) -> List[Dict]:
        """Extract tables (basic detection)."""
        tables = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Basic table detection using text blocks
            # This is a simplified approach; for production, consider using
            # dedicated table extraction libraries like camelot or tabula
            blocks = page.get_text("blocks")
            
            # Look for structured blocks (simplified heuristic)
            for block_idx, block in enumerate(blocks):
                # Check if block contains tab-separated or structured data
                text = block[4]
                if "\t" in text or text.count("\n") > 2:
                    tables.append({
                        "table_id": f"{doc_id}_p{page_num + 1}_t{block_idx}",
                        "page": page_num + 1,
                        "bbox": f"{block[:4]}",
                        "content": text,
                        "format": "text"
                    })
        
        return tables


class UnstructuredParser:
    """Parser using Unstructured for element extraction."""
    
    def __init__(self):
        self.settings = settings
    
    def parse(self, pdf_path: Path) -> List[Element]:
        """
        Parse PDF using Unstructured library.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of structured elements
        """
        logger.info(f"Parsing {pdf_path.name} with Unstructured")
        
        try:
            elements = partition_pdf(
                filename=str(pdf_path),
                strategy="hi_res" if settings.enable_ocr else "fast",
                infer_table_structure=settings.extract_tables,
                extract_images_in_pdf=settings.extract_images,
                languages=[settings.tesseract_lang.split("+")[0]] if settings.enable_ocr else None,
            )
            
            logger.info(f"Extracted {len(elements)} elements from {pdf_path.name}")
            return elements
            
        except Exception as e:
            logger.error(f"Error parsing with Unstructured: {e}")
            return []


class HybridParser:
    """Hybrid parser combining PyMuPDF4LLM and Unstructured."""
    
    def __init__(self):
        self.pymupdf_parser = PyMuPDFParser()
        self.unstructured_parser = UnstructuredParser()
        self.settings = settings
    
    def parse(self, pdf_path: Path, use_unstructured: bool = False) -> ParsedDocument:
        """
        Parse PDF with hybrid approach.
        
        Args:
            pdf_path: Path to PDF file
            use_unstructured: Whether to also use Unstructured for element extraction
            
        Returns:
            ParsedDocument with all extracted data
        """
        # Primary: PyMuPDF4LLM
        parsed_doc = self.pymupdf_parser.parse(pdf_path)
        
        # Optional: Unstructured for structured elements
        if use_unstructured:
            try:
                elements = self.unstructured_parser.parse(pdf_path)
                parsed_doc.elements = [
                    {
                        "type": el.category,
                        "text": str(el),
                        "metadata": el.metadata.to_dict() if hasattr(el, "metadata") else {}
                    }
                    for el in elements
                ]
            except Exception as e:
                logger.warning(f"Unstructured parsing failed: {e}")
        
        # Save parsed document
        self._save_parsed_doc(parsed_doc)
        
        return parsed_doc
    
    def _save_parsed_doc(self, parsed_doc: ParsedDocument):
        """Save parsed document to disk."""
        output_dir = settings.processed_dir / parsed_doc.doc_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        output_file = output_dir / "parsed_document.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asdict(parsed_doc), f, indent=2, ensure_ascii=False)
        
        # Save markdown separately
        md_file = output_dir / "document.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(parsed_doc.markdown_content)
        
        logger.info(f"Saved parsed document to {output_dir}")


def get_parser() -> HybridParser:
    """Get parser instance."""
    return HybridParser()

