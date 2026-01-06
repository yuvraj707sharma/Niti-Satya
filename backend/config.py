"""
Configuration management for Government Truth Portal
Loads environment variables and provides typed settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Google Gemini API
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    
    # Azure Document Intelligence
    azure_doc_intel_endpoint: str = Field(default="", env="AZURE_DOC_INTEL_ENDPOINT")
    azure_doc_intel_key: str = Field(default="", env="AZURE_DOC_INTEL_KEY")
    
    # Azure AI Search
    azure_search_endpoint: str = Field(default="", env="AZURE_SEARCH_ENDPOINT")
    azure_search_key: str = Field(default="", env="AZURE_SEARCH_KEY")
    azure_search_index_name: str = Field(default="govt-documents", env="AZURE_SEARCH_INDEX_NAME")
    
    # Azure Translator
    azure_translator_key: str = Field(default="", env="AZURE_TRANSLATOR_KEY")
    azure_translator_region: str = Field(default="eastus", env="AZURE_TRANSLATOR_REGION")
    
    # Optional: Azure OpenAI
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_KEY")
    azure_openai_deployment: str = Field(default="gpt-4", env="AZURE_OPENAI_DEPLOYMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Data paths
    documents_dir: str = Field(default="data/documents")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def _is_valid_key(self, key: str) -> bool:
        """Check if a key is actually valid (not a placeholder)"""
        if not key:
            return False
        placeholders = ["PASTE_YOUR", "YOUR_", "_HERE", "your_key", "your-key", "xxx", "placeholder"]
        return not any(p.lower() in key.lower() for p in placeholders)
    
    def validate_required_keys(self) -> dict:
        """Check which API keys are configured (not placeholders)"""
        return {
            "gemini": self._is_valid_key(self.gemini_api_key),
            "azure_doc_intel": bool(self.azure_doc_intel_endpoint) and self._is_valid_key(self.azure_doc_intel_key),
            "azure_search": bool(self.azure_search_endpoint) and self._is_valid_key(self.azure_search_key),
            "azure_translator": self._is_valid_key(self.azure_translator_key),
            "azure_openai": bool(self.azure_openai_endpoint) and self._is_valid_key(self.azure_openai_key),
        }
    
    def get_available_llm(self) -> str:
        """Return the best available LLM provider - prefers Azure OpenAI for Imagine Cup"""
        # Prefer Azure OpenAI for Imagine Cup demo
        if self.azure_openai_endpoint and self.azure_openai_key:
            return "azure_openai"
        elif self.gemini_api_key:
            return "gemini"
        else:
            return "none"


# Global settings instance
settings = Settings()
