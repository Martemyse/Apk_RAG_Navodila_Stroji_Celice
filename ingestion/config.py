"""Configuration for ingestion service."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Ingestion service configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Paths
    pdf_source_dir: Path = Field(default=Path("/app/data_pdf"))
    processed_dir: Path = Field(default=Path("/app/data_processed"))
    models_dir: Path = Field(default=Path("/app/models"))
    
    # Embedding configuration
    embedding_provider: str = Field(default="local")  # 'local' or 'openai'
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_device: str = Field(default="cpu")  # 'cpu', 'cuda', or 'auto'
    embedding_normalize: bool = Field(default=True)
    embedding_batch_size: int = Field(default=32)
    openai_api_key: str = Field(default="")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)  # text-embedding-3-small dimension
    
    # Weaviate configuration
    weaviate_url: str = Field(default="http://weaviate:8080")
    weaviate_api_key: str = Field(default="")
    weaviate_timeout: int = Field(default=120)
    
    # PostgreSQL configuration
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="postgres")
    postgres_url: Optional[str] = Field(default=None)
    postgres_schema_path: Path = Field(default=Path("/app/postgres/schema.sql"))
    
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
    
# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings

