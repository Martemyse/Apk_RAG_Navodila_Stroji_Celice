"""LLM client for answer generation."""
from typing import List, Dict, Any, Optional
from loguru import logger
from openai import OpenAI
from groq import Groq
from config import get_settings

settings = get_settings()


class LLMClient:
    """Wrapper for external LLM providers."""

    def __init__(self):
        """Initialize LLM client based on configuration."""
        provider = settings.llm_provider.lower()
        self.provider = provider
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=settings.openai_api_key)
        elif provider == "groq":
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY not set")
            self.client = Groq(api_key=settings.groq_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response from the configured provider."""
        logger.info(f"Generating LLM response via {self.provider}:{self.model}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()


def get_llm_client() -> Optional[LLMClient]:
    """Return LLM client if enabled, else None."""
    provider = settings.llm_provider.lower()
    if provider in {"", "none", "disabled"}:
        return None
    return LLMClient()
