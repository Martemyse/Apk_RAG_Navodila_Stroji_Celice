"""Data models for text-image fused content units."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class UnitType(str, Enum):
    """Content unit type."""
    TEXT_ONLY = "TEXT_ONLY"
    IMAGE_WITH_CONTEXT = "IMAGE_WITH_CONTEXT"


@dataclass
class Document:
    """Document metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""  # e.g., "Navodila_PTL007_V1_4"
    title: str = ""
    file_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    domain: Optional[str] = None
    total_pages: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageAsset:
    """Image asset extracted from PDF."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    doc_id: str = ""
    page_number: int = 0
    bbox: Dict[str, float] = field(default_factory=dict)  # {x1, y1, x2, y2}
    image_path: str = ""
    auto_caption: Optional[str] = None
    image_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentUnit:
    """Fused text+image content unit - the core semantic unit."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    doc_id: str = ""
    page_number: int = 0
    section_title: Optional[str] = None
    section_path: Optional[str] = None  # Hierarchical path
    text: str = ""
    unit_type: UnitType = UnitType.TEXT_ONLY
    image_id: Optional[str] = None  # Link to ImageAsset if fused
    token_count: int = 0
    bbox: Optional[Dict[str, float]] = None  # Text bounding box
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_image(self) -> bool:
        """Check if this unit has an associated image."""
        return self.image_id is not None and self.unit_type == UnitType.IMAGE_WITH_CONTEXT


@dataclass
class ParsedPDF:
    """Parsed PDF with layout information."""
    doc_id: str
    title: str
    file_path: str
    total_pages: int
    pages: List['PageLayout'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageLayout:
    """Layout information for a single page."""
    page_number: int
    text_blocks: List['TextBlock'] = field(default_factory=list)
    images: List['ImageBlock'] = field(default_factory=list)
    headings: List['Heading'] = field(default_factory=list)


@dataclass
class TextBlock:
    """Text block with position."""
    text: str
    bbox: Dict[str, float]  # {x1, y1, x2, y2}
    page_number: int
    block_type: str = "paragraph"  # paragraph, caption, list_item, etc.


@dataclass
class ImageBlock:
    """Image block with position and nearby text."""
    bbox: Dict[str, float]  # {x1, y1, x2, y2}
    page_number: int
    image_id: Optional[str] = None
    caption: Optional[str] = None
    nearby_text: List[str] = field(default_factory=list)  # Text blocks near image


@dataclass
class Heading:
    """Section heading."""
    text: str
    level: int  # 1-6 for h1-h6
    bbox: Dict[str, float]
    page_number: int

