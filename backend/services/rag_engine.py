"""
RAG Engine - Orchestrates document Q&A
Combines Azure AI Search retrieval with LLM generation
Supports both Azure OpenAI and Gemini
"""

from typing import List, Dict, Any, Optional
import re

from config import settings
from services.azure_search import get_search_service
from services.azure_translator import get_translator_service


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
        raise ValueError("No LLM provider configured. Set GEMINI_API_KEY or AZURE_OPENAI_* in .env")


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine
    
    Flow:
    1. User asks a question
    2. Search for relevant document chunks (Azure AI Search)
    3. Pass chunks as context to LLM (Azure OpenAI or Gemini)
    4. Generate grounded answer
    5. Optionally translate to user's language
    """
    
    def __init__(self):
        self.search_service = get_search_service()
        self.llm_client = get_llm_client()
        self.translator = get_translator_service()
        self.llm_provider = settings.get_available_llm()
    
    async def ask(
        self,
        question: str,
        document_id: Optional[str] = None,
        language: str = "en",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG
        
        Args:
            question: User's question
            document_id: Limit search to specific document
            language: Response language code
            top_k: Number of chunks to retrieve
            
        Returns:
            {
                "answer": str,
                "citations": [...],
                "confidence": float,
                "language": str,
                "llm_provider": str
            }
        """
        # Input validation
        if not question or len(question.strip()) < 3:
            return {
                "answer": "Please provide a valid question.",
                "citations": [],
                "confidence": 0.0,
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Sanitize input (basic XSS prevention)
        question = self._sanitize_input(question)
        
        # Step 1: Retrieve relevant chunks
        chunks = await self.search_service.search(
            query=question,
            document_id=document_id,
            top_k=top_k,
            use_vector=True
        )
        
        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the documents to answer your question.",
                "citations": [],
                "confidence": 0.0,
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Step 2: Prepare context
        context_texts = [chunk["text"] for chunk in chunks]
        document_title = chunks[0].get("document_title", "Government Document")
        
        # Step 3: Generate answer using LLM
        result = await self.llm_client.answer_question(
            question=question,
            context_chunks=context_texts,
            document_title=document_title
        )
        
        # Step 4: Build citations
        citations = []
        for i, chunk in enumerate(chunks):
            citation = {
                "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "page": chunk.get("page"),
                "section": f"Chunk {chunk.get('chunk_index', i)}",
                "document_id": chunk.get("document_id"),
                "relevance_score": chunk.get("score", 0)
            }
            citations.append(citation)
        
        answer = result.get("answer", "Unable to generate answer.")
        confidence = result.get("confidence", 0.5)
        
        # Step 5: Translate if needed
        if language != "en" and self.translator.is_configured():
            answer = await self.translator.translate(answer, language, "en")
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "language": language,
            "llm_provider": self.llm_provider
        }
    
    async def generate_document_summary(
        self,
        document_text: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate a summary of a document"""
        # Generate summary
        summary = await self.llm_client.generate_summary(document_text, max_length=300)
        
        # Extract key points
        key_points = await self.llm_client.extract_key_points(document_text, num_points=5)
        
        # Translate if needed
        if language != "en" and self.translator.is_configured():
            summary = await self.translator.translate(summary, language, "en")
            key_points = await self.translator.translate_batch(key_points, language, "en")
        
        return {
            "summary": summary,
            "key_points": key_points,
            "language": language
        }
    
    async def generate_timeline(
        self,
        document_text: str,
        previous_law_text: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate the 'Simply Put' timeline view"""
        # Generate timeline using LLM
        timeline = await self.llm_client.generate_timeline(
            document_text=document_text,
            previous_law_text=previous_law_text
        )
        
        # Translate all text fields if needed
        if language != "en" and self.translator.is_configured():
            for section in ["before", "change", "result"]:
                if section in timeline:
                    if "summary" in timeline[section]:
                        timeline[section]["summary"] = await self.translator.translate(
                            timeline[section]["summary"], language, "en"
                        )
                    if "key_points" in timeline[section]:
                        timeline[section]["key_points"] = await self.translator.translate_batch(
                            timeline[section]["key_points"], language, "en"
                        )
                    if "title" in timeline[section]:
                        timeline[section]["title"] = await self.translator.translate(
                            timeline[section]["title"], language, "en"
                        )
        
        return timeline
    
    def _sanitize_input(self, text: str) -> str:
        """Basic input sanitization"""
        # Remove potential script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Limit length
        return text[:2000].strip()


# Singleton instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
