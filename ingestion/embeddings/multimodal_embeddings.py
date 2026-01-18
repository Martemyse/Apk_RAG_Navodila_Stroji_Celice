"""Multimodal embeddings for text+image fusion."""
from typing import List, Optional
import numpy as np
from loguru import logger
from config import get_settings
from models import ContentUnit, UnitType
from embeddings.embeddings import get_embedding_provider

settings = get_settings()


class MultimodalEmbedder:
    """Generate embeddings for fused text+image content units."""
    
    def __init__(self):
        """Initialize multimodal embedder."""
        self.settings = settings
        # Use the existing embedding provider infrastructure
        # This automatically respects EMBEDDING_PROVIDER setting (local/openai)
        self.embedding_provider = get_embedding_provider()
        self.dimension = self.embedding_provider.dimension
        logger.info(f"Multimodal embedder initialized with provider: {settings.embedding_provider}")
    
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
        # For now, embed the fused text (works for both TEXT_ONLY and IMAGE_WITH_CONTEXT)
        # TODO: Add vision model for true multimodal embeddings
        # OpenAI's vision API can be used here in the future
        embedding = self.embedding_provider.embed_single(unit.text)
        return embedding.tolist()
    
    def embed_batch(self, units: List[ContentUnit]) -> List[List[float]]:
        """Embed batch of content units."""
        texts = [unit.text for unit in units]
        # Use the embedding provider to generate embeddings
        embeddings = self.embedding_provider.embed(texts)
        # Convert numpy array to list of lists
        return embeddings.tolist()
    
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
        embedding = self.embedding_provider.embed_single(text)
        return embedding.tolist()


def get_multimodal_embedder() -> MultimodalEmbedder:
    """Get multimodal embedder instance."""
    return MultimodalEmbedder()

