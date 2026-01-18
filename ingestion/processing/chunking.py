"""Chunking strategies for parsed documents."""
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
import tiktoken
from loguru import logger
from processing.parsers import ParsedDocument, DocumentChunk
from config import get_settings

settings = get_settings()


class SemanticChunker:
    """Semantic chunker that respects document structure."""
    
    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Initialize tokenizer (using GPT-2 as proxy for token counting)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
    
    def chunk(self, parsed_doc: ParsedDocument) -> List[DocumentChunk]:
        """
        Chunk document while preserving semantic boundaries.
        
        Args:
            parsed_doc: Parsed document
            
        Returns:
            List of document chunks
        """
        logger.info(f"Chunking document {parsed_doc.doc_id}")
        
        # Split markdown by headings
        sections = self._split_by_headings(parsed_doc.markdown_content)
        
        chunks = []
        for section_idx, (heading, content, level) in enumerate(sections):
            section_path = self._build_section_path(sections, section_idx)
            
            # Estimate page number from content position (rough approximation)
            page = self._estimate_page(section_idx, len(sections), parsed_doc.total_pages)
            
            # Split section into chunks
            section_chunks = self._split_section(
                content=content,
                doc_id=parsed_doc.doc_id,
                section_path=section_path,
                page=page,
                section_idx=section_idx
            )
            
            chunks.extend(section_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {parsed_doc.doc_id}")
        return chunks
    
    def _split_by_headings(self, markdown: str) -> List[Tuple[str, str, int]]:
        """
        Split markdown by headings.
        
        Returns:
            List of (heading, content, level) tuples
        """
        sections = []
        
        # Pattern to match markdown headings
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        # Find all headings
        matches = list(heading_pattern.finditer(markdown))
        
        if not matches:
            # No headings found, treat entire document as one section
            return [("Document", markdown, 0)]
        
        # Extract sections
        for i, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(2).strip()
            
            # Get content between this heading and next
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            content = markdown[start:end].strip()
            
            sections.append((heading, content, level))
        
        return sections
    
    def _build_section_path(
        self,
        sections: List[Tuple[str, str, int]],
        current_idx: int
    ) -> str:
        """Build hierarchical section path."""
        current_heading, _, current_level = sections[current_idx]
        
        # Build path by looking backwards for parent headings
        path_parts = [current_heading]
        
        for i in range(current_idx - 1, -1, -1):
            heading, _, level = sections[i]
            if level < current_level:
                path_parts.insert(0, heading)
                current_level = level
        
        return " > ".join(path_parts)
    
    def _split_section(
        self,
        content: str,
        doc_id: str,
        section_path: str,
        page: int,
        section_idx: int
    ) -> List[DocumentChunk]:
        """Split section into chunks."""
        chunks = []
        
        # Count tokens
        token_count = self._count_tokens(content)
        
        if token_count <= self.max_chunk_size:
            # Section fits in one chunk
            if token_count >= self.min_chunk_size:
                chunk_id = f"{doc_id}_s{section_idx}_c0"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        text=content,
                        page=page,
                        section_path=section_path,
                        bbox=None,  # TODO: Extract bbox from PDF
                        token_count=token_count,
                        metadata={"section_idx": section_idx}
                    )
                )
        else:
            # Split by paragraphs
            paragraphs = content.split("\n\n")
            current_chunk_text = ""
            current_token_count = 0
            chunk_idx = 0
            
            for para in paragraphs:
                para_tokens = self._count_tokens(para)
                
                if current_token_count + para_tokens <= self.chunk_size:
                    current_chunk_text += para + "\n\n"
                    current_token_count += para_tokens
                else:
                    # Save current chunk
                    if current_token_count >= self.min_chunk_size:
                        chunk_id = f"{doc_id}_s{section_idx}_c{chunk_idx}"
                        chunks.append(
                            DocumentChunk(
                                chunk_id=chunk_id,
                                doc_id=doc_id,
                                text=current_chunk_text.strip(),
                                page=page,
                                section_path=section_path,
                                bbox=None,
                                token_count=current_token_count,
                                metadata={"section_idx": section_idx, "chunk_idx": chunk_idx}
                            )
                        )
                        chunk_idx += 1
                    
                    # Start new chunk (with overlap)
                    # Take last paragraph as overlap
                    overlap_text = current_chunk_text.split("\n\n")[-1] if "\n\n" in current_chunk_text else ""
                    current_chunk_text = overlap_text + "\n\n" + para + "\n\n"
                    current_token_count = self._count_tokens(current_chunk_text)
            
            # Save last chunk
            if current_token_count >= self.min_chunk_size:
                chunk_id = f"{doc_id}_s{section_idx}_c{chunk_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        text=current_chunk_text.strip(),
                        page=page,
                        section_path=section_path,
                        bbox=None,
                        token_count=current_token_count,
                        metadata={"section_idx": section_idx, "chunk_idx": chunk_idx}
                    )
                )
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass
        
        # Fallback: rough approximation
        return len(text.split()) * 1.3
    
    def _estimate_page(self, section_idx: int, total_sections: int, total_pages: int) -> int:
        """Estimate page number from section position."""
        if total_sections == 0:
            return 1
        
        # Linear approximation
        page = int((section_idx / total_sections) * total_pages) + 1
        return min(page, total_pages)


def get_chunker() -> SemanticChunker:
    """Get chunker instance."""
    return SemanticChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        min_chunk_size=settings.min_chunk_size,
        max_chunk_size=settings.max_chunk_size,
    )

