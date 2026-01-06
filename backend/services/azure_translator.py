"""
Azure Translator Service
Multi-language support for Indian languages
Microsoft Imagine Cup Service #3
"""

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from typing import Optional, List, Dict
import httpx

from config import settings


class AzureTranslatorService:
    """
    Azure Translator for multi-language support
    Supports all major Indian languages
    """
    
    # Supported Indian languages
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "ur": "Urdu",
        "or": "Odia",
        "as": "Assamese",
    }
    
    def __init__(self):
        self.api_key = settings.azure_translator_key
        self.region = settings.azure_translator_region
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        
        if not self.api_key:
            print("⚠️ Azure Translator not configured - translation disabled")
    
    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en"
    ) -> str:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'hi' for Hindi)
            source_language: Source language code (default: 'en')
            
        Returns:
            Translated text
        """
        if not self.api_key:
            return text  # Return original if not configured
        
        if target_language == source_language:
            return text
        
        if target_language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_language}")
        
        url = f"{self.endpoint}/translate"
        
        params = {
            "api-version": "3.0",
            "from": source_language,
            "to": target_language
        }
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json"
        }
        
        body = [{"text": text}]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params, headers=headers, json=body)
                response.raise_for_status()
                
                result = response.json()
                if result and len(result) > 0:
                    translations = result[0].get("translations", [])
                    if translations:
                        return translations[0].get("text", text)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                raise ValueError("Azure Translator API key is invalid or expired. Please update AZURE_TRANSLATOR_KEY in .env")
            raise ValueError(f"Translation failed: {e}")
        except Exception as e:
            raise ValueError(f"Translation error: {e}")
        
        return text
    
    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: str = "en"
    ) -> List[str]:
        """
        Translate multiple texts at once
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code
            
        Returns:
            List of translated texts
        """
        if not self.api_key:
            return texts
        
        if target_language == source_language:
            return texts
        
        url = f"{self.endpoint}/translate"
        
        params = {
            "api-version": "3.0",
            "from": source_language,
            "to": target_language
        }
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json"
        }
        
        # Azure Translator has a limit of 100 texts per request
        translated = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            body = [{"text": t} for t in batch]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params, headers=headers, json=body)
                response.raise_for_status()
                
                result = response.json()
                for item in result:
                    translations = item.get("translations", [])
                    if translations:
                        translated.append(translations[0].get("text", ""))
                    else:
                        translated.append("")
        
        return translated
    
    async def detect_language(self, text: str) -> Dict[str, any]:
        """
        Detect the language of input text
        
        Returns:
            {"language": "en", "confidence": 0.95}
        """
        if not self.api_key:
            return {"language": "en", "confidence": 0.0}
        
        url = f"{self.endpoint}/detect"
        
        params = {"api-version": "3.0"}
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json"
        }
        
        body = [{"text": text[:500]}]  # Limit text length
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, headers=headers, json=body)
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0:
                return {
                    "language": result[0].get("language", "en"),
                    "confidence": result[0].get("score", 0.0)
                }
        
        return {"language": "en", "confidence": 0.0}
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages"""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def is_configured(self) -> bool:
        """Check if the translator is configured"""
        return bool(self.api_key)


# Singleton instance
_translator_service: Optional[AzureTranslatorService] = None


def get_translator_service() -> AzureTranslatorService:
    """Get or create translator service instance"""
    global _translator_service
    if _translator_service is None:
        _translator_service = AzureTranslatorService()
    return _translator_service
