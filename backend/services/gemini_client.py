"""
Gemini API Client for RAG and summarization
Uses Google AI Studio free tier (1500 requests/day)
"""

import google.generativeai as genai
from typing import List, Optional, Dict, Any
import json
import re

from config import settings


class GeminiClient:
    """Wrapper for Google Gemini API"""
    
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=settings.gemini_api_key)
        
        # Use Gemini 1.5 Flash for speed and cost efficiency
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Safety settings - allow all content for government docs
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    
    async def generate_summary(self, document_text: str, max_length: int = 800) -> str:
        """Generate a detailed, citizen-friendly summary of a document"""
        prompt = f"""You are a friendly government document explainer. Your job is to help common Indian citizens understand official documents in simple, everyday language.

Create a detailed summary of this official document.

IMPORTANT RULES:
1. Write 4-6 sentences that explain:
   - What is this document about?
   - Why does it matter to common people?
   - What will change for citizens?
   - Any benefits or things people should know?

2. Use SIMPLE language:
   - Avoid legal/technical terms
   - Use words a 10th standard student would understand
   - Give relatable examples where possible
   - Explain acronyms (UGC = University Grants Commission)

3. Be NEUTRAL and FACTUAL:
   - No political opinions
   - Only what the document actually says
   - Don't exaggerate benefits or problems

Document text:
{document_text[:15000]}

Write a helpful summary that a rickshaw driver, farmer, or shopkeeper could understand:"""
        
        response = await self._generate(prompt)
        return response[:max_length]
    
    async def extract_key_points(self, document_text: str, num_points: int = 5) -> List[str]:
        """Extract citizen-friendly key points from a document"""
        prompt = f"""Extract exactly {num_points} key points from this government document that would be most useful for common Indian citizens.

Focus on:
- How does this affect ordinary people's lives?
- What are the main benefits or changes?
- What should people know about this?

Rules:
- Each point should be one clear sentence in SIMPLE language
- Avoid legal jargon - explain like you're talking to your grandmother
- Focus on practical impact, not technical details
- Return as a JSON array of strings

Document:
{document_text[:15000]}

Example format:
["Your tax filing will become simpler with fewer forms", "Students can now get loans at lower interest rates"]

Key points (JSON array):"""
        
        response = await self._generate(prompt)
        try:
            # Parse JSON response
            points = json.loads(response)
            if isinstance(points, list):
                return points[:num_points]
        except json.JSONDecodeError:
            # Fallback: split by newlines
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            return lines[:num_points]
        
        return []
    
    async def generate_timeline(self, document_text: str, previous_law_text: Optional[str] = None) -> Dict[str, Any]:
        """Generate the 'Simply Put' timeline view"""
        
        context = ""
        if previous_law_text:
            context = f"""
Previous Law/Situation:
{previous_law_text[:5000]}

"""
        
        prompt = f"""Analyze this government document and create a "Simply Put" timeline.

{context}Current Document:
{document_text[:10000]}

Create a JSON response with this exact structure:
{{
    "before": {{
        "title": "How it was before",
        "summary": "2-3 sentence summary of the previous situation",
        "key_points": ["point 1", "point 2", "point 3"]
    }},
    "change": {{
        "title": "What this changes",
        "summary": "2-3 sentence summary of the new provisions",
        "key_points": ["change 1", "change 2", "change 3"]
    }},
    "result": {{
        "title": "What happens now",
        "summary": "2-3 sentence summary of the expected outcomes",
        "key_points": ["result 1", "result 2", "result 3"]
    }}
}}

Rules:
- Be strictly factual - only what the document says
- No political opinions or bias
- Use simple language
- If previous law context is not provided, infer from the document's references

JSON response:"""
        
        response = await self._generate(prompt)
        
        try:
            # Clean up response and parse JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Return default structure if parsing fails
        return {
            "before": {"title": "Previous Situation", "summary": "Information not available", "key_points": []},
            "change": {"title": "Current Changes", "summary": "Document analysis in progress", "key_points": []},
            "result": {"title": "Expected Outcome", "summary": "To be determined", "key_points": []}
        }
    
    async def answer_question(self, question: str, context_chunks: List[str], document_title: str) -> Dict[str, Any]:
        """Answer a question using RAG context"""
        
        context = "\n\n---\n\n".join(context_chunks)
        
        prompt = f"""You are a helpful government document assistant. Answer the user's question based ONLY on the provided document excerpts.

Document: {document_title}

Relevant excerpts:
{context}

Question: {question}

Rules:
- Answer ONLY based on the provided excerpts
- If the answer is not in the excerpts, say "This information is not available in the document"
- Be neutral and factual
- Cite specific sections when possible
- Use simple language

Provide your response as JSON:
{{
    "answer": "Your answer here",
    "confidence": 0.0 to 1.0,
    "citations": [
        {{"text": "quoted text from document", "section": "section reference if available"}}
    ]
}}

JSON response:"""
        
        response = await self._generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {
            "answer": response,
            "confidence": 0.5,
            "citations": []
        }
    
    async def fact_check(self, claim: str, relevant_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify a claim against document evidence"""
        
        evidence_text = ""
        for i, chunk in enumerate(relevant_chunks, 1):
            evidence_text += f"\n[Source {i}: {chunk.get('document_title', 'Unknown')}]\n{chunk.get('text', '')}\n"
        
        prompt = f"""You are a neutral fact-checker. Verify this claim against official government documents.

Claim to verify: "{claim}"

Official document excerpts:
{evidence_text}

Analyze the claim and provide a verdict. Response as JSON:
{{
    "verdict": "true" | "false" | "partially_true" | "unverifiable",
    "confidence": 0.0 to 1.0,
    "explanation": "2-3 sentence explanation of your verdict",
    "evidence": [
        {{
            "source": "document name",
            "quote": "relevant quote",
            "supports_claim": true/false
        }}
    ]
}}

Rules:
- Only use the provided document excerpts as evidence
- If no relevant evidence exists, verdict should be "unverifiable"
- Be strictly neutral and factual
- Explain clearly why the claim is true/false

JSON response:"""
        
        response = await self._generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {
            "verdict": "unverifiable",
            "confidence": 0.0,
            "explanation": "Unable to verify this claim with available documents.",
            "evidence": []
        }
    
    async def _generate(self, prompt: str) -> str:
        """Internal method to generate response"""
        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config={
                    "temperature": 0.3,  # Lower for more factual responses
                    "top_p": 0.8,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
