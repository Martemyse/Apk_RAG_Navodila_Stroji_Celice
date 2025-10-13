"""Embedding providers for text vectorization."""
from typing import List, Optional
import numpy as np
from abc import ABC, abstractmethod
from loguru import logger
from sentence_transformers import SentenceTransformer
from config import get_settings

settings = get_settings()


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of shape (len(texts), dimension)
        """
        pass
    
    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
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
        """
        Initialize local embedding provider.
        
        Args:
            model_name: Name of sentence-transformers model
            device: Device to run on ('cuda', 'cpu', or None for auto)
            normalize: Whether to normalize embeddings
        """
        self.model_name = model_name
        self.normalize = normalize
        
        logger.info(f"Loading embedding model: {model_name}")
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=str(settings.models_dir)
            )
            logger.info(f"Model loaded successfully on device: {self.model.device}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
        
        self._dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for batch of texts."""
        try:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=self.normalize,
                show_progress_bar=True,
                batch_size=32
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        return self.embed([text])[0]
    
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
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI embedding model name
        """
        self.model = model
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info(f"OpenAI client initialized with model: {model}")
        except ImportError:
            logger.error("OpenAI package not installed")
            raise
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
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for batch of texts."""
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
            
            return np.array(all_embeddings)
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            raise
    
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        return self.embed([text])[0]
    
    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension


def get_embedding_provider() -> EmbeddingProvider:
    """
    Get embedding provider based on configuration.
    
    Returns:
        EmbeddingProvider instance
    """
    provider = settings.embedding_provider.lower()
    
    if provider == "local":
        return LocalEmbeddingProvider(
            model_name=settings.embedding_model,
            normalize=True
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


# Batch embedding helper
def embed_batch(
    texts: List[str],
    provider: Optional[EmbeddingProvider] = None
) -> np.ndarray:
    """
    Embed batch of texts.
    
    Args:
        texts: List of text strings
        provider: Optional provider instance (will create if None)
        
    Returns:
        Numpy array of embeddings
    """
    if provider is None:
        provider = get_embedding_provider()
    
    return provider.embed(texts)

