"""Embedding provider for query vectorization."""
from typing import List, Optional
import numpy as np
from abc import ABC, abstractmethod
from loguru import logger
from sentence_transformers import SentenceTransformer
from config import get_settings
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

settings = get_settings()


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        device: Optional[str] = None,
        normalize: bool = True
    ):
        """Initialize local embedding provider."""
        self.model_name = model_name
        self.normalize = normalize
        
        logger.info(f"Loading embedding model: {model_name}")
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=str(settings.models_dir)
            )
            logger.info(f"Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
        
        self._dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            embedding = self.model.encode(text, normalize_embeddings=self.normalize)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-large"
    ):
        """Initialize OpenAI embedding provider."""
        self.model = model
        
        if OpenAI is None:
            logger.error("OpenAI package not installed")
            raise ImportError("openai package is required for OpenAI embeddings")
        
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info(f"OpenAI client initialized with model: {model}")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            raise
        
        # Set dimension based on model
        self._dimension = self._get_model_dimension(model)
    
    def _get_model_dimension(self, model: str) -> int:
        """Get embedding dimension for model."""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(model, 1536)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension


def get_embedding_provider() -> EmbeddingProvider:
    """Get embedding provider based on configuration."""
    provider = settings.embedding_provider.lower()
    
    if provider == "local":
        device = None if settings.embedding_device.lower() == "auto" else settings.embedding_device
        return LocalEmbeddingProvider(
            model_name=settings.embedding_model,
            device=device,
            normalize=settings.embedding_normalize
        )
    elif provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

