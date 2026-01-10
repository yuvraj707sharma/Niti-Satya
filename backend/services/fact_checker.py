"""
Fact-Checker Service
Verifies claims against official government documents
Uses document summaries directly with LLM (no Azure Search dependency)
"""

from typing import List, Dict, Any, Optional
import re
import json

from config import settings
from services.azure_translator import get_translator_service
from services.document_store import get_document_store
from api.schemas import FactCheckVerdict


def get_llm_client():
    """Get the best available LLM client"""
    provider = settings.get_available_llm()
    
    if provider == "azure_openai":
        from services.azure_openai import get_azure_openai_client
        return get_azure_openai_client()
    elif provider == "gemini":
        from services.gemini_client import get_gemini_client
        return get_gemini_client()
    else:
        raise ValueError("No LLM provider configured")


class FactCheckerService:
    """
    Fact-checking service that verifies claims against official documents
    
    Flow:
    1. Sanitize and validate input
    2. Get all document summaries and key points
    3. Use LLM to compare claim against evidence
    4. Return verdict with citations
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.translator = get_translator_service()
        self.llm_provider = settings.get_available_llm()
    
    def _get_all_document_evidence(self) -> List[Dict[str, Any]]:
        """Get summaries and key points from all documents as evidence"""
        evidence = []
        
        try:
            store = get_document_store()
            result = store.get_all(page=1, page_size=100)
            
            for doc in result.get("documents", []):
                if doc.get("summary"):
                    evidence.append({
                        "document_id": doc.get("id", ""),
                        "document_title": doc.get("title", "Government Document"),
                        "text": f"Summary: {doc.get('summary', '')}\n\nKey Points: {', '.join(doc.get('key_points', []))}"
                    })
        except Exception as e:
            print(f"Error loading document evidence: {e}")
        
        # Add hardcoded documents if store is empty
        if not evidence:
            from services.rag_engine import DOCUMENT_CONTEXT
            for doc_id, doc_data in DOCUMENT_CONTEXT.items():
                evidence.append({
                    "document_id": doc_id,
                    "document_title": doc_data.get("title", ""),
                    "text": f"Summary: {doc_data.get('summary', '')}\n\nKey Points: {', '.join(doc_data.get('key_points', []))}"
                })
        
        return evidence
    
    async def check_claim(
        self,
        claim: str,
        language: str = "en",
        top_k: int = 8
    ) -> Dict[str, Any]:
        """
        Verify a claim against all indexed documents
        """
        # Input validation
        if not claim or len(claim.strip()) < 10:
            return {
                "claim": claim,
                "verdict": FactCheckVerdict.UNVERIFIABLE,
                "confidence": 0.0,
                "explanation": "Please provide a more detailed claim to verify.",
                "evidence": [],
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Sanitize input
        claim = self._sanitize_input(claim)
        
        # Translate claim to English if needed (for searching)
        search_claim = claim
        if language != "en" and self.translator.is_configured():
            try:
                detected = await self.translator.detect_language(claim)
                if detected["language"] != "en" and detected["confidence"] > 0.7:
                    search_claim = await self.translator.translate(claim, "en", detected["language"])
            except:
                pass  # Continue with original claim
        
        # Get all document evidence
        all_evidence = self._get_all_document_evidence()
        
        if not all_evidence:
            result = {
                "claim": claim,
                "verdict": FactCheckVerdict.UNVERIFIABLE,
                "confidence": 0.0,
                "explanation": "No government documents are available to verify this claim.",
                "evidence": [],
                "language": language,
                "llm_provider": self.llm_provider
            }
            return result
        
        # Use LLM to get verdict
        try:
            llm_result = await self.llm_client.fact_check(
                claim=search_claim,
                relevant_chunks=all_evidence
            )
        except Exception as e:
            print(f"LLM fact check error: {e}")
            return {
                "claim": claim,
                "verdict": FactCheckVerdict.UNVERIFIABLE,
                "confidence": 0.0,
                "explanation": f"Error during fact checking: {str(e)}",
                "evidence": [],
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Map verdict string to enum
        verdict_str = llm_result.get("verdict", "unverifiable").lower()
        verdict_map = {
            "true": FactCheckVerdict.TRUE,
            "false": FactCheckVerdict.FALSE,
            "partially_true": FactCheckVerdict.PARTIALLY_TRUE,
            "unverifiable": FactCheckVerdict.UNVERIFIABLE,
        }
        verdict = verdict_map.get(verdict_str, FactCheckVerdict.UNVERIFIABLE)
        
        # Build evidence list from LLM response
        evidence = []
        llm_evidence = llm_result.get("evidence", [])
        
        for ev in llm_evidence[:5]:  # Limit to 5 evidence items
            evidence.append({
                "document_id": ev.get("document_id", ""),
                "document_title": ev.get("source", ev.get("document_title", "Government Document")),
                "page": None,
                "section": "Document Summary",
                "quote": ev.get("quote", "")[:300],
                "supports_claim": ev.get("supports_claim", verdict == FactCheckVerdict.TRUE)
            })
        
        explanation = llm_result.get("explanation", "Unable to provide detailed explanation.")
        
        # Translate explanation if needed
        if language != "en" and self.translator.is_configured():
            try:
                explanation = await self.translator.translate(explanation, language, "en")
            except:
                pass
        
        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": llm_result.get("confidence", 0.5),
            "explanation": explanation,
            "evidence": evidence,
            "language": language,
            "llm_provider": self.llm_provider
        }
    
    async def extract_claims_from_text(self, text: str) -> List[str]:
        """Extract verifiable claims from a piece of text"""
        text = self._sanitize_input(text)
        
        prompt = f"""Extract all verifiable factual claims from this text. 
Only include claims that can be checked against official government documents.
Ignore opinions, predictions, and subjective statements.

Text:
{text[:2000]}

Return as a JSON array of claim strings:"""
        
        try:
            result = await self.llm_client._generate(prompt)
            claims = json.loads(result)
            if isinstance(claims, list):
                return claims[:10]  # Limit to 10 claims
        except:
            pass
        
        return []
    
    def _sanitize_input(self, text: str) -> str:
        """Basic input sanitization for security"""
        # Remove potential script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        # Limit length
        return text[:2000].strip()
    
    def get_verdict_explanation(self, verdict: FactCheckVerdict) -> str:
        """Get user-friendly explanation of verdict"""
        explanations = {
            FactCheckVerdict.TRUE: "This claim is supported by official government documents.",
            FactCheckVerdict.FALSE: "This claim contradicts what is stated in official government documents.",
            FactCheckVerdict.PARTIALLY_TRUE: "This claim is partially accurate but missing important context or contains some inaccuracies.",
            FactCheckVerdict.UNVERIFIABLE: "We cannot verify this claim with the available government documents.",
        }
        return explanations.get(verdict, "Unable to determine verdict.")


# Singleton instance
_fact_checker: Optional[FactCheckerService] = None


def get_fact_checker() -> FactCheckerService:
    """Get or create fact-checker instance"""
    global _fact_checker
    if _fact_checker is None:
        _fact_checker = FactCheckerService()
    return _fact_checker
