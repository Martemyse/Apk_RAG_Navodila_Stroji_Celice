"""Build fused text+image content units from parsed PDF."""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from loguru import logger
import tiktoken
from models import (
    ParsedPDF, PageLayout, ImageBlock, TextBlock, Heading,
    ContentUnit, ImageAsset, UnitType, Document
)
from processing.image_extractor import ImageExtractor
from config import get_settings

settings = get_settings()


class ContentUnitBuilder:
    """Build content units from parsed PDF layout."""
    
    def __init__(self):
        """Initialize content unit builder."""
        self.settings = settings
        self.image_extractor = ImageExtractor()
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
    
    def build_content_units(
        self,
        parsed_pdf: ParsedPDF,
        document: Document
    ) -> Tuple[List[ContentUnit], List[ImageAsset]]:
        """
        Build content units from parsed PDF.
        
        Returns:
            Tuple of (content_units, image_assets)
        """
        logger.info(f"Building content units for {parsed_pdf.doc_id}")
        
        content_units = []
        image_assets = []
        
        # Extract images first
        pdf_path = Path(parsed_pdf.file_path)
        image_blocks = self.image_extractor.extract_images_from_pdf(pdf_path, parsed_pdf.doc_id)
        
        # Create image assets
        image_map = {}  # Map image_path -> ImageAsset
        for img_block in image_blocks:
            image_path = getattr(img_block, 'image_path', '')
            # Calculate hash from image file if path exists
            image_hash = None
            if image_path and Path(image_path).exists():
                import hashlib
                with open(image_path, 'rb') as f:
                    image_hash = hashlib.sha256(f.read()).hexdigest()
            
            image_asset = ImageAsset(
                document_id=document.id,
                doc_id=parsed_pdf.doc_id,
                page_number=img_block.page_number,
                bbox=img_block.bbox,
                image_path=image_path,
                image_hash=image_hash
            )
            image_assets.append(image_asset)
            if image_path:
                image_map[image_path] = image_asset
        
        # Process each page
        for page_layout in parsed_pdf.pages:
            # Find images on this page
            page_images = [img for img in image_blocks if img.page_number == page_layout.page_number]
            
            # Build text blocks list
            text_blocks = page_layout.text_blocks
            
            # Process images first (create IMAGE_WITH_CONTEXT units)
            for img_block in page_images:
                # Find nearby text
                caption, nearby_text = self.image_extractor.find_nearby_text(
                    img_block, text_blocks, page_layout.page_number
                )
                
                # Build fused text
                fused_text_parts = []
                if caption:
                    fused_text_parts.append(caption)
                fused_text_parts.extend(nearby_text)
                
                # Get section context
                section_title = self._get_section_for_position(
                    page_layout.headings,
                    img_block.bbox["y1"]
                )
                
                # Create fused text
                fused_text = " ".join(fused_text_parts) if fused_text_parts else "Image"
                
                # Get corresponding image asset by path
                image_path = getattr(img_block, 'image_path', '')
                image_asset = image_map.get(image_path) if image_path else None
                
                # Create content unit
                unit = ContentUnit(
                    document_id=document.id,
                    doc_id=parsed_pdf.doc_id,
                    page_number=page_layout.page_number,
                    section_title=section_title,
                    section_path=self._build_section_path(page_layout.headings),
                    text=fused_text,
                    unit_type=UnitType.IMAGE_WITH_CONTEXT,
                    image_id=image_asset.id if image_asset else None,
                    token_count=self._count_tokens(fused_text),
                    tags=self._extract_tags(fused_text)
                )
                
                content_units.append(unit)
            
            # Process text-only sections (create TEXT_ONLY units)
            text_units = self._build_text_only_units(
                page_layout,
                document,
                parsed_pdf.doc_id,
                page_images  # Exclude text near images
            )
            content_units.extend(text_units)
        
        logger.info(
            f"Built {len(content_units)} content units "
            f"({sum(1 for u in content_units if u.unit_type == UnitType.IMAGE_WITH_CONTEXT)} with images)"
        )
        
        return content_units, image_assets
    
    def _build_text_only_units(
        self,
        page_layout: PageLayout,
        document: Document,
        doc_id: str,
        page_images: List[ImageBlock]
    ) -> List[ContentUnit]:
        """Build text-only content units, excluding text near images."""
        units = []
        
        # Get text blocks that aren't near images
        text_blocks = self._filter_text_away_from_images(
            page_layout.text_blocks,
            page_images
        )
        
        if not text_blocks:
            return units
        
        # Chunk text by sections
        current_section = self._get_section_for_position(
            page_layout.headings,
            text_blocks[0].bbox["y1"] if text_blocks else 0
        )
        
        current_chunk = []
        current_tokens = 0
        chunk_size = self.settings.chunk_size
        
        for text_block in text_blocks:
            block_tokens = self._count_tokens(text_block.text)
            
            # Check if we should start a new chunk
            if current_tokens + block_tokens > chunk_size and current_chunk:
                # Create unit from current chunk
                chunk_text = " ".join(current_chunk)
                unit = ContentUnit(
                    document_id=document.id,
                    doc_id=doc_id,
                    page_number=page_layout.page_number,
                    section_title=current_section,
                    section_path=self._build_section_path(page_layout.headings),
                    text=chunk_text,
                    unit_type=UnitType.TEXT_ONLY,
                    token_count=current_tokens,
                    tags=self._extract_tags(chunk_text)
                )
                units.append(unit)
                
                # Reset
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(text_block.text)
            current_tokens += block_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            unit = ContentUnit(
                document_id=document.id,
                doc_id=doc_id,
                page_number=page_layout.page_number,
                section_title=current_section,
                section_path=self._build_section_path(page_layout.headings),
                text=chunk_text,
                unit_type=UnitType.TEXT_ONLY,
                token_count=current_tokens,
                tags=self._extract_tags(chunk_text)
            )
            units.append(unit)
        
        return units
    
    def _filter_text_away_from_images(
        self,
        text_blocks: List[TextBlock],
        images: List[ImageBlock]
    ) -> List[TextBlock]:
        """Filter out text blocks that are too close to images."""
        if not images:
            return text_blocks
        
        filtered = []
        threshold = 50  # pixels
        
        for text_block in text_blocks:
            is_near_image = False
            
            for image in images:
                if image.page_number != text_block.page_number:
                    continue
                
                # Check distance
                text_y_center = (text_block.bbox["y1"] + text_block.bbox["y2"]) / 2
                img_y_center = (image.bbox["y1"] + image.bbox["y2"]) / 2
                distance = abs(text_y_center - img_y_center)
                
                if distance < threshold:
                    is_near_image = True
                    break
            
            if not is_near_image:
                filtered.append(text_block)
        
        return filtered
    
    def _get_section_for_position(self, headings: List[Heading], y_position: float) -> Optional[str]:
        """Get section title for a given Y position."""
        if not headings:
            return None
        
        # Find closest heading above this position
        closest = None
        min_distance = float('inf')
        
        for heading in headings:
            if heading.bbox["y2"] <= y_position:
                distance = y_position - heading.bbox["y2"]
                if distance < min_distance:
                    min_distance = distance
                    closest = heading
        
        return closest.text if closest else None
    
    def _build_section_path(self, headings: List[Heading]) -> Optional[str]:
        """Build hierarchical section path."""
        if not headings:
            return None
        
        # Sort by level and position
        sorted_headings = sorted(headings, key=lambda h: (h.page_number, h.bbox["y1"], h.level))
        
        # Build path from top-level headings
        path_parts = []
        for heading in sorted_headings:
            if heading.level == 1:
                path_parts = [heading.text]  # Reset at top level
            elif heading.level <= len(path_parts) + 1:
                path_parts = path_parts[:heading.level - 1] + [heading.text]
        
        return " > ".join(path_parts) if path_parts else None
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass
        
        # Fallback approximation
        return len(text.split()) * 1.3
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text (simple keyword-based)."""
        tags = []
        text_lower = text.lower()
        
        # Machine type tags
        machine_keywords = {
            "ptl007": "machine_ptl007",
            "ptl008": "machine_ptl008",
            "rom27": "machine_rom27",
            "rom28": "machine_rom28",
            "stgh": "machine_stgh"
        }
        
        for keyword, tag in machine_keywords.items():
            if keyword in text_lower:
                tags.append(tag)
        
        # Safety tags
        if any(word in text_lower for word in ["safety", "warning", "danger", "caution"]):
            tags.append("safety")
        
        # Procedure tags
        if any(word in text_lower for word in ["procedure", "step", "instruction", "how to"]):
            tags.append("procedure")
        
        return tags


def get_content_unit_builder() -> ContentUnitBuilder:
    """Get content unit builder instance."""
    return ContentUnitBuilder()

