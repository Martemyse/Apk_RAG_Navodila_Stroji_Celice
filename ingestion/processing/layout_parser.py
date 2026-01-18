"""Layout-aware PDF parser for text-image fusion."""
from pathlib import Path
from typing import List, Dict
import pymupdf as fitz
import pymupdf4llm
from loguru import logger
from models import ParsedPDF, PageLayout, TextBlock, Heading
from config import get_settings

settings = get_settings()


class LayoutParser:
    """Parse PDF with layout information for text-image fusion."""
    
    def __init__(self):
        """Initialize layout parser."""
        self.settings = settings
    
    def parse(self, pdf_path: Path) -> ParsedPDF:
        """
        Parse PDF with full layout information.
        
        Returns:
            ParsedPDF with pages containing text blocks, headings, and image positions
        """
        logger.info(f"Parsing layout from {pdf_path.name}")
        
        doc_id = pdf_path.stem
        doc = fitz.open(pdf_path)
        
        try:
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text blocks with positions
                text_blocks = self._extract_text_blocks(page, page_num + 1)
                
                # Extract headings
                headings = self._extract_headings(page, page_num + 1)
                
                # Create page layout
                page_layout = PageLayout(
                    page_number=page_num + 1,
                    text_blocks=text_blocks,
                    headings=headings
                )
                
                pages.append(page_layout)
            
            parsed_pdf = ParsedPDF(
                doc_id=doc_id,
                title=doc_id.replace("_", " "),
                file_path=str(pdf_path),
                total_pages=len(doc),
                pages=pages
            )
            
            logger.info(
                f"Parsed {pdf_path.name}: {len(pages)} pages, "
                f"{sum(len(p.text_blocks) for p in pages)} text blocks, "
                f"{sum(len(p.headings) for p in pages)} headings"
            )
            
            return parsed_pdf
            
        finally:
            doc.close()
    
    def _extract_text_blocks(self, page: fitz.Page, page_number: int) -> List[TextBlock]:
        """Extract text blocks with bounding boxes."""
        blocks = []
        
        # Get text blocks with positions
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:  # Skip image blocks
                continue
            
            # Collect text from all lines
            text_parts = []
            for line in block["lines"]:
                for span in line.get("spans", []):
                    text_parts.append(span.get("text", ""))
            
            text = " ".join(text_parts).strip()
            if not text:
                continue
            
            # Get bounding box
            bbox = {
                "x1": block["bbox"][0],
                "y1": block["bbox"][1],
                "x2": block["bbox"][2],
                "y2": block["bbox"][3]
            }
            
            # Determine block type
            block_type = "paragraph"
            text_lower = text.lower()
            
            if any(keyword in text_lower for keyword in ["figure", "fig", "image", "diagram"]):
                block_type = "caption"
            elif text.startswith("-") or text.startswith("•"):
                block_type = "list_item"
            
            text_block = TextBlock(
                text=text,
                bbox=bbox,
                page_number=page_number,
                block_type=block_type
            )
            
            blocks.append(text_block)
        
        return blocks
    
    def _extract_headings(self, page: fitz.Page, page_number: int) -> List[Heading]:
        """Extract headings from page."""
        headings = []
        
        # Use PyMuPDF4LLM markdown to identify headings
        try:
            markdown = pymupdf4llm.to_markdown(
                page.parent,
                pages=[page_number - 1],  # 0-indexed
                write_images=False
            )
            
            # Parse markdown for headings
            lines = markdown.split("\n")
            current_level = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for markdown heading
                if line.startswith("#"):
                    level = len(line) - len(line.lstrip("#"))
                    heading_text = line.lstrip("#").strip()
                    
                    if heading_text and level <= 6:
                        # Estimate position (simplified)
                        bbox = {
                            "x1": 0,
                            "y1": current_level * 50,  # Rough estimate
                            "x2": 1000,
                            "y2": current_level * 50 + 30
                        }
                        
                        heading = Heading(
                            text=heading_text,
                            level=level,
                            bbox=bbox,
                            page_number=page_number
                        )
                        
                        headings.append(heading)
                        current_level += 1
            
        except Exception as e:
            logger.warning(f"Error extracting headings from page {page_number}: {e}")
        
        return headings


def get_layout_parser() -> LayoutParser:
    """Get layout parser instance."""
    return LayoutParser()

