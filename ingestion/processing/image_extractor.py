"""Image extraction and text-image fusion logic."""
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pymupdf as fitz
from loguru import logger
from models import ImageAsset, ImageBlock, TextBlock, PageLayout, ParsedPDF
from config import get_settings

settings = get_settings()


class ImageExtractor:
    """Extract images from PDFs and identify nearby text."""
    
    def __init__(self):
        """Initialize image extractor."""
        self.settings = settings
        self.image_output_dir = Path(settings.processed_dir) / "images"
        self.image_output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_images_from_pdf(self, pdf_path: Path, doc_id: str) -> List[ImageBlock]:
        """
        Extract images from PDF with bounding boxes.
        
        Returns:
            List of ImageBlock objects with position and metadata
        """
        logger.info(f"Extracting images from {pdf_path.name}")
        
        images = []
        doc = fitz.open(pdf_path)
        
        try:
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
                        if not rects:
                            continue
                        
                        rect = rects[0]
                        bbox = {
                            "x1": rect.x0,
                            "y1": rect.y0,
                            "x2": rect.x1,
                            "y2": rect.y1
                        }
                        
                        # Generate image hash for deduplication
                        image_hash = hashlib.sha256(image_bytes).hexdigest()
                        
                        # Save image
                        image_filename = f"{doc_id}_p{page_num + 1}_i{img_idx + 1}.{image_ext}"
                        image_dir = self.image_output_dir / doc_id
                        image_dir.mkdir(parents=True, exist_ok=True)
                        image_path = image_dir / image_filename
                        
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        
                        # Create image block with path
                        image_block = ImageBlock(
                            bbox=bbox,
                            page_number=page_num + 1,
                            image_hash=image_hash
                        )
                        image_block.image_path = str(image_path)
                        
                        images.append(image_block)
                        
                    except Exception as e:
                        logger.warning(f"Error extracting image on page {page_num + 1}: {e}")
                        continue
            
            logger.info(f"Extracted {len(images)} images from {pdf_path.name}")
            return images
            
        finally:
            doc.close()
    
    def find_nearby_text(
        self,
        image_block: ImageBlock,
        text_blocks: List[TextBlock],
        page_number: int
    ) -> Tuple[Optional[str], List[str]]:
        """
        Find caption and nearby text for an image.
        
        Args:
            image_block: Image block with bbox
            text_blocks: All text blocks on the page
            page_number: Page number
            
        Returns:
            Tuple of (caption, nearby_text_list)
        """
        if image_block.page_number != page_number:
            return None, []
        
        # Filter text blocks on same page
        page_text_blocks = [tb for tb in text_blocks if tb.page_number == page_number]
        
        if not page_text_blocks:
            return None, []
        
        # Find text blocks near image (within threshold)
        threshold = 50  # pixels
        nearby_blocks = []
        caption = None
        
        img_y_center = (image_block.bbox["y1"] + image_block.bbox["y2"]) / 2
        
        for text_block in page_text_blocks:
            text_y_center = (text_block.bbox["y1"] + text_block.bbox["y2"]) / 2
            distance = abs(text_y_center - img_y_center)
            
            # Check if text is above image (likely caption)
            if text_block.bbox["y2"] < image_block.bbox["y1"] and distance < threshold * 2:
                # Check if it looks like a caption
                text_lower = text_block.text.lower().strip()
                if any(keyword in text_lower for keyword in ["figure", "fig", "image", "diagram", "scheme"]):
                    caption = text_block.text
                else:
                    nearby_blocks.append(text_block.text)
            
            # Check if text is below image
            elif text_block.bbox["y1"] > image_block.bbox["y2"] and distance < threshold * 2:
                nearby_blocks.append(text_block.text)
            
            # Check if text overlaps horizontally with image
            elif (text_block.bbox["x1"] < image_block.bbox["x2"] and 
                  text_block.bbox["x2"] > image_block.bbox["x1"]):
                if distance < threshold:
                    nearby_blocks.append(text_block.text)
        
        return caption, nearby_blocks[:3]  # Limit to 3 nearby blocks


def get_image_extractor() -> ImageExtractor:
    """Get image extractor instance."""
    return ImageExtractor()

