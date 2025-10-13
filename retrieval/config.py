"""Configuration for retrieval service."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Retrieval service configuration."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8001)
    api_workers: int = Field(default=4)
    api_reload: bool = Field(default=False)
    
    # Weaviate Configuration
    weaviate_url: str = Field(default="http://weaviate:8080")
    weaviate_api_key: str = Field(default="")
    weaviate_timeout: int = Field(default=120)
    
    # Embedding Configuration (cheapest model)
    embedding_provider: str = Field(default="openai")  # 'openai' only
    openai_api_key: str = Field(default="")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    
    # Reranker Configuration
    reranker_provider: str = Field(default="none")  # 'cohere' or 'none'
    cohere_api_key: str = Field(default="")
    
    # Retrieval Configuration (simplified)
    default_top_k: int = Field(default=10)
    hybrid_alpha: float = Field(default=0.5)
    enable_rerank: bool = Field(default=False)
    
    # Paths
    models_dir: Path = Field(default=Path("/app/models"))
    pdf_source_dir: Path = Field(default=Path("/app/data_pdf"))
    
    # JWT Authentication (optional)
    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=1440)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="text")
    
    # Monitoring
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    
    # MCP (temporarily disabled)
    mcp_enable: bool = Field(default=False)
    mcp_server_name: str = Field(default="rag-navodila")
    mcp_server_version: str = Field(default="1.0.0")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings

