"""
Azure OpenAI Client - GPT-4 integration
Alternative LLM for Imagine Cup demo
"""

import os
from typing import Dict, Any, List, Optional
import json

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config import settings


class AzureOpenAIClient:
    """
    Azure OpenAI wrapper for GPT-4 integration
    Used as alternative to Gemini for Imagine Cup demo
    """
    
    def __init__(self):
        self.configured = False
        self.client = None
        
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI package not installed. Install with: pip install openai")
            return
            
        if settings.azure_openai_endpoint and settings.azure_openai_key:
            try:
                self.client = AzureOpenAI(
                    api_key=settings.azure_openai_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=settings.azure_openai_endpoint
                )
                self.deployment = settings.azure_openai_deployment
                self.configured = True
                print("✅ Azure OpenAI configured")
            except Exception as e:
                print(f"⚠️ Azure OpenAI configuration failed: {e}")
    
    def is_configured(self) -> bool:
        return self.configured and self.client is not None
    
    async def _generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using GPT-4"""
        if not self.is_configured():
            raise ValueError("Azure OpenAI not configured")
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are an AI assistant analyzing official Indian government documents. Be factual, unbiased, and cite sources when possible."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for factual accuracy
            )
            return response.choices[0].message.content
        except Exception as e:
            raise ValueError(f"Azure OpenAI generation failed: {e}")
    
    async def generate_summary(self, document_text: str, max_length: int = 300) -> str:
        """Generate document summary"""
        prompt = f"""Summarize this government document in simple terms for an average citizen.
Keep it under {max_length} words. Focus on:
- What the document is about
- Key changes or proposals
- How it affects citizens

Document:
{document_text[:8000]}

Summary:"""
        
        return await self._generate(prompt)
    
    async def extract_key_points(self, document_text: str, num_points: int = 5) -> List[str]:
        """Extract key points from document"""
        prompt = f"""Extract exactly {num_points} key points from this government document.
Format as a JSON array of strings.

Document:
{document_text[:8000]}

Key points (JSON array):"""
        
        result = await self._generate(prompt)
        try:
            points = json.loads(result)
            if isinstance(points, list):
                return points[:num_points]
        except:
            lines = [l.strip() for l in result.split('\n') if l.strip()]
            return lines[:num_points]
        
        return []
    
    async def generate_timeline(
        self,
        document_text: str,
        previous_law_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate before/change/result timeline"""
        context = ""
        if previous_law_text:
            context = f"Previous law/situation:\n{previous_law_text[:3000]}\n\n"
        
        prompt = f"""Analyze this government document and create a timeline showing:
1. BEFORE: The previous situation/law
2. CHANGE: What this document proposes to change
3. RESULT: Expected outcome if implemented

{context}Current Document:
{document_text[:6000]}

Respond in JSON format:
{{
    "before": {{"title": "...", "summary": "...", "key_points": ["..."]}},
    "change": {{"title": "...", "summary": "...", "key_points": ["..."]}},
    "result": {{"title": "...", "summary": "...", "key_points": ["..."]}}
}}"""
        
        result = await self._generate(prompt, max_tokens=1500)
        
        try:
            return json.loads(result)
        except:
            return {
                "before": {"title": "Previous State", "summary": "Unable to parse", "key_points": []},
                "change": {"title": "Proposed Changes", "summary": result[:300], "key_points": []},
                "result": {"title": "Expected Outcome", "summary": "See document for details", "key_points": []}
            }
    
    async def answer_question(
        self,
        question: str,
        context_chunks: List[str],
        document_title: str = "Government Document"
    ) -> Dict[str, Any]:
        """Answer question using RAG context - with Gemini fallback"""
        context = "\n\n---\n\n".join(context_chunks[:5])
        
        prompt = f"""Based ONLY on the following excerpts from "{document_title}", answer the question.
If the answer is not in the context, say "This information is not available in the document."
Be factual and cite specific parts when possible.

Context:
{context}

Question: {question}

Answer:"""
        
        # Try Azure OpenAI first
        try:
            answer = await self._generate(prompt)
            return {
                "answer": answer,
                "confidence": 0.85 if "not available" not in answer.lower() else 0.3
            }
        except Exception as e:
            print(f"⚠️ Azure OpenAI failed: {e}. Falling back to Gemini...")
            # Fallback to Gemini
            try:
                from services.gemini_client import get_gemini_client
                gemini = get_gemini_client()
                return await gemini.answer_question(question, context_chunks, document_title)
            except Exception as gemini_error:
                return {
                    "answer": f"Sorry, both Azure OpenAI and Gemini failed. Please check your API configuration. Error: {str(e)}",
                    "confidence": 0.0
                }
    
    async def fact_check(
        self,
        claim: str,
        relevant_chunks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Verify a claim against document evidence - with Gemini fallback"""
        evidence_text = "\n\n".join([
            f"From '{chunk.get('document_title', 'Document')}':\n{chunk.get('text', '')[:500]}"
            for chunk in relevant_chunks[:5]
        ])
        
        prompt = f"""Fact-check this claim against the official government documents provided.

Claim: "{claim}"

Evidence from official documents:
{evidence_text}

Respond in JSON format:
{{
    "verdict": "true" | "false" | "partially_true" | "unverifiable",
    "confidence": 0.0-1.0,
    "explanation": "detailed explanation",
    "evidence": [
        {{"supports_claim": true/false, "quote": "relevant quote"}}
    ]
}}

Be very careful: only mark as "true" if clearly supported, "false" if contradicted.
Mark "partially_true" if some aspects are correct but context is missing.
Mark "unverifiable" if documents don't contain relevant information."""
        
        # Try Azure OpenAI first
        try:
            result = await self._generate(prompt, max_tokens=1200)
            try:
                return json.loads(result)
            except:
                return {
                    "verdict": "unverifiable",
                    "confidence": 0.3,
                    "explanation": result[:500],
                    "evidence": []
                }
        except Exception as e:
            print(f"⚠️ Azure OpenAI failed for fact-check: {e}. Falling back to Gemini...")
            # Fallback to Gemini
            try:
                from services.gemini_client import get_gemini_client
                gemini = get_gemini_client()
                return await gemini.fact_check(claim, relevant_chunks)
            except Exception as gemini_error:
                return {
                    "verdict": "unverifiable",
                    "confidence": 0.0,
                    "explanation": f"Both Azure OpenAI and Gemini failed. Error: {str(e)}",
                    "evidence": []
                }


# Singleton instance
_azure_openai_client: Optional[AzureOpenAIClient] = None


def get_azure_openai_client() -> AzureOpenAIClient:
    """Get or create Azure OpenAI client"""
    global _azure_openai_client
    if _azure_openai_client is None:
        _azure_openai_client = AzureOpenAIClient()
    return _azure_openai_client
