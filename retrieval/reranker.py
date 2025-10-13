"""Reranker for improving retrieval quality."""
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod
import numpy as np
from loguru import logger
from config import get_settings

settings = get_settings()


class Reranker(ABC):
    """Abstract base class for rerankers."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents.
        
        Args:
            query: Query text
            documents: List of document texts
            top_k: Number of top results to return
            
        Returns:
            List of (index, score) tuples sorted by score
        """
        pass


class LocalReranker(Reranker):
    """Local reranker using cross-encoder."""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        """Initialize local reranker."""
        self.model_name = model_name
        
        logger.info(f"Loading reranker model: {model_name}")
        
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(
                model_name,
                max_length=512,
                device=None,  # Auto-detect
            )
            logger.info("Reranker model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
        except Exception as e:
            logger.error(f"Error loading reranker model: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """Rerank documents using cross-encoder."""
        try:
            # Create query-document pairs
            pairs = [[query, doc] for doc in documents]
            
            # Get scores
            scores = self.model.predict(pairs)
            
            # Sort by score (descending)
            ranked_indices = np.argsort(scores)[::-1]
            
            # Create results
            results = [(int(idx), float(scores[idx])) for idx in ranked_indices]
            
            # Limit to top_k if specified
            if top_k:
                results = results[:top_k]
            
            logger.info(f"Reranked {len(documents)} documents, returning top {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Error reranking: {e}")
            raise


class CohereReranker(Reranker):
    """Cohere reranker using API."""
    
    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        """Initialize Cohere reranker."""
        self.model = model
        
        try:
            import cohere
            self.client = cohere.Client(api_key)
            logger.info(f"Cohere client initialized with model: {model}")
        except ImportError:
            logger.error("cohere package not installed")
            raise
        except Exception as e:
            logger.error(f"Error initializing Cohere client: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """Rerank documents using Cohere API."""
        try:
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_k if top_k else len(documents)
            )
            
            # Convert to list of (index, score) tuples
            results = [
                (result.index, result.relevance_score)
                for result in response.results
            ]
            
            logger.info(f"Reranked with Cohere, returning top {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Error reranking with Cohere: {e}")
            raise


class NoOpReranker(Reranker):
    """No-op reranker that returns original order."""
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """Return original order."""
        results = [(i, 1.0) for i in range(len(documents))]
        
        if top_k:
            results = results[:top_k]
        
        return results


def get_reranker() -> Optional[Reranker]:
    """Get reranker based on configuration."""
    provider = settings.reranker_provider.lower()
    
    if provider == "none" or not settings.enable_rerank:
        logger.info("Reranking disabled")
        return None
    elif provider == "local":
        return LocalReranker(model_name=settings.reranker_model)
    elif provider == "cohere":
        if not settings.cohere_api_key:
            raise ValueError("COHERE_API_KEY not set in environment")
        
        return CohereReranker(api_key=settings.cohere_api_key)
    else:
        raise ValueError(f"Unknown reranker provider: {provider}")

