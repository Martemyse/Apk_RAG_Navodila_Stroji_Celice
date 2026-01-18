"""Multimodal embeddings for text+image fusion."""
from typing import List, Optional
import numpy as np
from loguru import logger
from openai import OpenAI
from config import get_settings
from models import ContentUnit, UnitType

settings = get_settings()


class MultimodalEmbedder:
    """Generate embeddings for fused text+image content units."""
    
    def __init__(self):
        """Initialize multimodal embedder."""
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimension = settings.embedding_dimension
    
    def embed_content_unit(self, unit: ContentUnit) -> List[float]:
        """
        Generate embedding for a content unit.
        
        For IMAGE_WITH_CONTEXT units:
        - Option A: Use multimodal model (if available)
        - Option B: Use text-only embedding (current implementation)
        
        For TEXT_ONLY units:
        - Use text embedding
        
        Args:
            unit: ContentUnit to embed
            
        Returns:
            Embedding vector
        """
        if unit.unit_type == UnitType.IMAGE_WITH_CONTEXT:
            # For now, embed the fused text
            # TODO: Add vision model for true multimodal embeddings
            # OpenAI's vision API can be used here in the future
            return self._embed_text(unit.text)
        else:
            return self._embed_text(unit.text)
    
    def embed_batch(self, units: List[ContentUnit]) -> List[List[float]]:
        """Embed batch of content units."""
        texts = [unit.text for unit in units]
        return self._embed_texts(texts)
    
    def _embed_text(self, text: str) -> List[float]:
        """Embed single text."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            raise
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed batch of texts."""
        try:
            # OpenAI has batch size limit
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise
    
    def embed_with_image(
        self,
        text: str,
        image_path: Optional[str] = None
    ) -> List[float]:
        """
        Embed text with image (future multimodal support).
        
        For now, returns text embedding only.
        TODO: Integrate OpenAI Vision API or CLIP for true multimodal embeddings.
        """
        # Current implementation: text-only
        # Future: Use OpenAI Vision API or CLIP
        return self._embed_text(text)


def get_multimodal_embedder() -> MultimodalEmbedder:
    """Get multimodal embedder instance."""
    return MultimodalEmbedder()

