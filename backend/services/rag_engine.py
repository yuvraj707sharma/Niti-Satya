"""
RAG Engine - Orchestrates document Q&A
Uses document summaries directly with LLM (Azure OpenAI or Gemini)
No Azure Search dependency - answers are contextual to document content
"""

from typing import List, Dict, Any, Optional
import re

from config import settings
from services.azure_translator import get_translator_service
from services.document_store import get_document_store

# Document data for reliable Q&A - ensures answers stay within document context
DOCUMENT_CONTEXT = {
    "income-tax-2025": {
        "title": "The Income-tax Bill, 2025",
        "summary": "The Income-tax Bill, 2025 is a major update to how India collects taxes from citizens and businesses. The old tax law from 1961 was 63 years old and had become very confusing with 819 sections full of legal terms. This new bill rewrites everything in simple, easy-to-understand language with only 536 sections. The good news? Your tax rates remain the same - you will not pay more or less tax. The government simply made the rules easier to read so that ordinary people can understand their tax obligations without needing a lawyer or CA to explain everything.",
        "key_points": [
            "Replaces the 63-year-old Income-tax Act, 1961",
            "Number of sections reduced from 819 to 536",
            "No change in current tax rates",
            "Simplified language for better understanding",
            "Tables and formulas replace complex explanations",
            "New tax regime as default option",
            "Streamlined exemption claims process"
        ]
    },
    "income-tax-select-committee": {
        "title": "Select Committee Report - Income Tax Bill 2025",
        "summary": "After the Income Tax Bill 2025 was introduced, a Select Committee of senior MPs reviewed it for several months. They invited common people, business owners, tax experts, and CAs to share their concerns. This 1200+ page report contains all their suggestions, complaints, and the committee's recommendations for making the bill even better.",
        "key_points": [
            "Committee recommendations for amendments",
            "Stakeholder observations addressed",
            "Compliance simplification suggestions",
            "Implementation timeline recommendations"
        ]
    },
    "shiksha-bill-2025": {
        "title": "The Viksit Bharat Shiksha Adhishthan Bill, 2025",
        "summary": "This Bill creates a single body called 'Viksit Bharat Shiksha Adhishthan' to manage all higher education in India. Currently, if you want to start a college, you need approvals from UGC (for universities), AICTE (for engineering/technical colleges), and NCTE (for teacher training). This is confusing and time-consuming. Under this new law, there will be just ONE organization handling everything - making it easier to open quality institutions and ensuring all colleges follow the same standards.",
        "key_points": [
            "Creates single umbrella body for higher education",
            "Merges functions of UGC, AICTE, and NCTE",
            "Aims to simplify higher education governance",
            "Promotes research and innovation",
            "Implements National Education Policy 2020",
            "Accreditation Council for quality assurance",
            "Standards Council for curriculum"
        ]
    },
    "vb-gramg-bill-2025": {
        "title": "Viksit Bharat Rozgar Guarantee (Gramin) Bill, 2025",
        "summary": "This Bill strengthens job guarantee for rural families. Under MGNREGA, every rural household can get 100 days of paid work. This new bill adds skill training - so you can learn useful things like computer skills, tailoring, or modern farming while earning money. No more just manual labor! Payments will be faster through digital transfers.",
        "key_points": [
            "100 days guaranteed employment",
            "Skill development integration",
            "Livelihood support for rural areas",
            "Digital payment mechanism",
            "Links employment with local development",
            "Work certification system"
        ]
    },
    "securities-code-2025": {
        "title": "The Securities Markets Code, 2025",
        "summary": "This Bill simplifies the rules for the stock market and investments in India. Currently, there are 4 different laws governing the stock market (SEBI Act, Securities Contracts Act, etc.) which creates confusion for investors and companies. This new code combines everything into one simple rulebook. If you invest in stocks, mutual funds, or any securities, this law protects your money better.",
        "key_points": [
            "Consolidates 4 major securities laws",
            "Replaces SEBI Act, 1992",
            "Modernizes capital market regulations",
            "Strengthens investor protection",
            "Includes provisions for digital assets",
            "Unified securities regulation code"
        ]
    },
    "electricity-bill-2025": {
        "title": "Electricity (Amendment) Bill, 2025",
        "summary": "This Bill updates India's electricity laws to prepare for the future. It strongly promotes solar power, wind energy, and other renewable sources - meaning cleaner air and sustainable energy for your children. The bill also protects electricity consumers with better complaint processes and modernizes the power grid for smart meters and electric vehicles.",
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
        "summary": "The Viksit Bharat Bill is India's roadmap to become a developed nation by 2047 - exactly 100 years after independence. It covers everything: better roads and railways, world-class hospitals and schools, clean water for all, modern cities, strong farming sector, and jobs for everyone.",
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
    Document Q&A Engine
    
    Flow:
    1. User asks a question about a document
    2. Get document summary and key points from store or DOCUMENT_CONTEXT
    3. Pass document context to LLM (Azure OpenAI or Gemini)
    4. Generate contextual answer based ONLY on document content
    5. Optionally translate to user's language
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.translator = get_translator_service()
        self.llm_provider = settings.get_available_llm()
    
    def _get_document_context(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document context from store or fallback to DOCUMENT_CONTEXT"""
        # Try document store first
        try:
            store = get_document_store()
            doc = store.get(document_id)
            if doc and doc.get('summary'):
                return doc
        except Exception as e:
            print(f"⚠️ Document store error: {e}")
        
        # Fallback to hardcoded context
        if document_id in DOCUMENT_CONTEXT:
            return DOCUMENT_CONTEXT[document_id]
        
        return None
    
    async def ask(
        self,
        question: str,
        document_id: Optional[str] = None,
        language: str = "en",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a question based on document context
        Answers are strictly limited to information within the document
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
            
        # Sanitize input
        question = self._sanitize_input(question)
        
        # Get document context
        doc_context = None
        if document_id:
            doc_context = self._get_document_context(document_id)
        
        if not doc_context:
            return {
                "answer": "I couldn't find the document you're asking about. Please select a document first.",
                "citations": [],
                "confidence": 0.0,
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Build context text from document
        context_text = f"Document Title: {doc_context.get('title', 'Government Document')}\n\n"
        context_text += f"Document Summary:\n{doc_context.get('summary', '')}\n\n"
        if doc_context.get('key_points'):
            context_text += "Key Points:\n"
            for kp in doc_context['key_points']:
                context_text += f"- {kp}\n"
        
        document_title = doc_context.get('title', 'Government Document')
        
        # Generate answer using LLM
        try:
            result = await self.llm_client.answer_question(
                question=question,
                context_chunks=[context_text],
                document_title=document_title
            )
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return {
                "answer": f"Sorry, I encountered an error while processing your question. Please try again. Error: {str(e)}",
                "citations": [],
                "confidence": 0.0,
                "language": language,
                "llm_provider": self.llm_provider
            }
        
        # Build citations
        citations = [{
            "text": doc_context.get('summary', '')[:200] + "...",
            "page": None,
            "section": "Document Summary",
            "document_id": document_id,
            "relevance_score": 0.9
        }]
        
        # Get answer and confidence
        answer = result.get("answer", "I couldn't generate an answer.")
        confidence = result.get("confidence", 0.7)
        
        # Translate if needed
        if language != "en" and self.translator.is_configured():
            try:
                answer = await self.translator.translate(answer, language, "en")
            except Exception as e:
                print(f"Translation error: {e}")
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "language": language,
            "llm_provider": self.llm_provider
        }
    
    async def summarize_document(
        self,
        document_text: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate a citizen-friendly summary"""
        summary = await self.llm_client.generate_summary(document_text)
        key_points = await self.llm_client.extract_key_points(document_text)
        
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
        timeline = await self.llm_client.generate_timeline(
            document_text=document_text,
            previous_law_text=previous_law_text
        )
        
        # Translate if needed
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
        return text[:1000]


# Singleton instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
