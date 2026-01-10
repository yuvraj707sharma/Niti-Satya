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
from services.document_store import get_document_store

# DEMO MODE: Hardcoded document data for presentations when Azure Search is unavailable
DEMO_DOCUMENTS = {
    "income-tax-2025": {
        "title": "The Income-tax Bill, 2025",
        "summary": "The Income-tax Bill, 2025 is a major update to how India collects taxes from citizens and businesses. The old tax law from 1961 was 63 years old and had become very confusing with 819 sections full of legal terms. This new bill rewrites everything in simple, easy-to-understand language with only 536 sections. The good news? Your tax rates remain the same - you will not pay more or less tax. The government simply made the rules easier to read.",
        "key_points": [
            "Replaces the 63-year-old Income-tax Act, 1961",
            "Number of sections reduced from 819 to 536",
            "No change in current tax rates",
            "Simplified language for better understanding",
            "Tables and formulas replace complex explanations"
        ]
    },
    "shiksha-bill-2025": {
        "title": "The Viksit Bharat Shiksha Adhishthan Bill, 2025",
        "summary": "This Bill creates a single body called 'Viksit Bharat Shiksha Adhishthan' to manage all higher education in India. Currently, you need approvals from UGC, AICTE, and NCTE separately. Under this new law, there will be just ONE organization handling everything - making it easier to open quality institutions.",
        "key_points": [
            "Creates single umbrella body for higher education",
            "Merges functions of UGC, AICTE, and NCTE",
            "Aims to simplify higher education governance",
            "Promotes research and innovation",
            "Implements National Education Policy 2020"
        ]
    },
    "vb-gramg-bill-2025": {
        "title": "Viksit Bharat Rozgar Guarantee (Gramin) Bill, 2025",
        "summary": "This Bill strengthens job guarantee for rural families. Under MGNREGA, every rural household can get 100 days of paid work. This new bill adds skill training - so you can learn useful things like computer skills, tailoring, or modern farming while earning money.",
        "key_points": [
            "100 days guaranteed employment",
            "Skill development integration",
            "Livelihood support for rural areas",
            "Digital payment mechanism",
            "Links employment with local development"
        ]
    },
    "securities-code-2025": {
        "title": "The Securities Markets Code, 2025",
        "summary": "This Bill simplifies the rules for the stock market and investments in India. Currently, there are 4 different laws governing the stock market which creates confusion. This new code combines everything into one simple rulebook, making it easier for investors.",
        "key_points": [
            "Consolidates 4 major securities laws",
            "Replaces SEBI Act, 1992",
            "Modernizes capital market regulations",
            "Strengthens investor protection",
            "Includes provisions for digital assets"
        ]
    },
    "electricity-bill-2025": {
        "title": "Electricity (Amendment) Bill, 2025",
        "summary": "This Bill updates India's electricity laws to prepare for the future. It strongly promotes solar power, wind energy, and other renewable sources. The bill also protects electricity consumers with better complaint processes and modernizes the power grid for smart meters.",
        "key_points": [
            "Renewable energy promotion",
            "Distribution network improvements",
            "Consumer rights enhancement",
            "Smart grid provisions",
            "Subsidy reforms"
        ]
    },
    "vikasit-bharat-main": {
        "title": "Viksit Bharat Bill - Main Document",
        "summary": "The Viksit Bharat Bill is India's roadmap to become a developed nation by 2047. It covers everything: better roads, world-class hospitals, clean water, modern cities, and jobs for everyone.",
        "key_points": [
            "Vision 2047 development goals",
            "Sectoral development priorities",
            "Infrastructure modernization",
            "Human capital development",
            "Technology advancement"
        ]
    }
}


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
        Answer a question based on document context
        """
        # Validate inputs
        if not question or not question.strip():
            return {
                "answer": "Please ask a question.",
                "citations": [],
                "confidence": 0.0,
                "language": language,
                "llm_provider": self.llm_provider
            }
            
        # Sanitize input (basic XSS prevention)
        question = self._sanitize_input(question)
        
        # 1. Search for relevant chunks
        chunks = []
        try:
            chunks = await self.search_service.search(
                query=question,
                document_id=document_id,
                top_k=top_k,
                use_vector=True
            )
        except Exception as e:
            print(f"⚠️ Search error: {e}. Attempting fallback...")
            
        # FALLBACK CHAIN: If search failed or returned nothing
        if not chunks and document_id:
            # Try 1: Document store
            try:
                store = get_document_store()
                doc = store.get(document_id)
                if doc:
                    print(f"ℹ️ Using document store fallback for {document_id}")
                    fallback_text = f"Document Title: {doc.get('title', 'Government Document')}\n\n"
                    fallback_text += f"Summary: {doc.get('summary', '')}\n\n"
                    if doc.get('key_points'):
                        fallback_text += "Key Points:\n" + "\n".join([f"- {kp}" for kp in doc['key_points']])
                    chunks = [{"text": fallback_text, "score": 0.5, "document_title": doc.get('title')}]
            except Exception as fb_err:
                print(f"❌ Document store fallback failed: {fb_err}")
            
            # Try 2: DEMO_DOCUMENTS (hardcoded - always works)
            if not chunks and document_id in DEMO_DOCUMENTS:
                print(f"ℹ️ Using DEMO_DOCUMENTS fallback for {document_id}")
                demo_doc = DEMO_DOCUMENTS[document_id]
                fallback_text = f"Document Title: {demo_doc['title']}\n\n"
                fallback_text += f"Summary: {demo_doc['summary']}\n\n"
                fallback_text += "Key Points:\n" + "\n".join([f"- {kp}" for kp in demo_doc['key_points']])
                chunks = [{"text": fallback_text, "score": 0.5, "document_title": demo_doc['title']}]

        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the documents to answer your question. This may be because the search index is still being set up.",
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
