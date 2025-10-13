"""Configuration for ingestion service."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Ingestion service configuration."""
    
    # Paths
    pdf_source_dir: Path = Field(default=Path("/app/data_pdf"))
    processed_dir: Path = Field(default=Path("/app/data_processed"))
    models_dir: Path = Field(default=Path("/app/models"))
    
    # Embedding configuration (cheapest model)
    embedding_provider: str = Field(default="openai")  # 'openai' only
    openai_api_key: str = Field(default="")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)  # text-embedding-3-small dimension
    
    # Weaviate configuration
    weaviate_url: str = Field(default="http://weaviate:8080")
    weaviate_api_key: str = Field(default="")
    weaviate_timeout: int = Field(default=120)
    
    # Chunking configuration
    chunk_size: int = Field(default=600)
    chunk_overlap: int = Field(default=100)
    min_chunk_size: int = Field(default=100)
    max_chunk_size: int = Field(default=1000)
    
    # Ingestion configuration
    ingestion_batch_size: int = Field(default=100)
    ingestion_parallel_workers: int = Field(default=4)
    
    # OCR configuration
    enable_ocr: bool = Field(default=False)
    tesseract_lang: str = Field(default="slv+eng")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="text")
    
    # Processing options
    extract_images: bool = Field(default=True)
    extract_tables: bool = Field(default=True)
    preserve_layout: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings

