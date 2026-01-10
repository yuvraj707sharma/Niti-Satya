"""
API Routes for Government Truth Portal
All endpoints for documents, Q&A, fact-checking, and translation
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import shutil

from api.schemas import (
    DocumentListResponse, DocumentDetail, DocumentSummary, DocumentTimeline,
    AskRequest, AskResponse, SourceCitation,
    FactCheckRequest, FactCheckResponse, Evidence,
    URLFactCheckRequest, URLFactCheckResponse,
    TranslateRequest, TranslateResponse,
    HealthStatus, ErrorResponse,
    DocumentCategory, Language, FactCheckVerdict
)
from services.document_store import get_document_store
from services.azure_doc_intel import get_document_intelligence
from services.rag_engine import get_rag_engine
from services.fact_checker import get_fact_checker
from services.azure_translator import get_translator_service
from services.gemini_client import get_gemini_client
from services.url_extractor import get_url_extractor
from config import settings


router = APIRouter()


# ============== Health Check ==============

@router.get("/health", response_model=HealthStatus, tags=["System"])
async def health_check():
    """Check API health and service availability"""
    services = settings.validate_required_keys()
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        services=services
    )


# ============== Documents ==============

@router.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get list of all documents"""
    store = get_document_store()
    result = store.get_all(category=category, page=page, page_size=page_size)
    
    # Convert to response model
    documents = []
    for doc in result["documents"]:
        documents.append(DocumentSummary(
            id=doc["id"],
            title=doc["title"],
            category=doc.get("category", "report"),
            summary=doc.get("summary", "")[:300],
            source_ministry=doc.get("source_ministry"),
            published_date=doc.get("published_date"),
            thumbnail_gradient=(hash(doc["id"]) % 4) + 1
        ))
    
    return DocumentListResponse(
        documents=documents,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.get("/documents/{doc_id}", tags=["Documents"])
async def get_document(doc_id: str):
    """Get full document details"""
    store = get_document_store()
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc


@router.get("/documents/{doc_id}/timeline", tags=["Documents"])
async def get_document_timeline(
    doc_id: str,
    language: Language = Language.ENGLISH
):
    """Get the 'Simply Put' timeline for a document"""
    store = get_document_store()
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if timeline is already cached
    if doc.get("timeline"):
        timeline = doc["timeline"]
    else:
        # Generate timeline
        rag = get_rag_engine()
        full_text = doc.get("full_text", "")
        
        if not full_text:
            raise HTTPException(status_code=400, detail="Document text not available")
        
        timeline = await rag.generate_timeline(
            document_text=full_text,
            language=language.value
        )
        
        # Cache the timeline
        store.update(doc_id, {"timeline": timeline})
    
    return timeline


@router.post("/documents/{doc_id}/ask", response_model=AskResponse, tags=["Q&A"])
async def ask_document(doc_id: str, request: AskRequest):
    """Ask a question about a specific document"""
    store = get_document_store()
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    rag = get_rag_engine()
    result = await rag.ask(
        question=request.question,
        document_id=doc_id,
        language=request.language.value
    )
    
    # Convert to response model
    citations = [
        SourceCitation(
            page=c.get("page"),
            section=c.get("section"),
            text=c.get("text", ""),
            relevance_score=c.get("relevance_score", 0)
        )
        for c in result.get("citations", [])
    ]
    
    return AskResponse(
        answer=result["answer"],
        citations=citations,
        confidence=result["confidence"],
        language=request.language
    )


@router.post("/documents/upload", tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("report"),
    source_ministry: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None)
):
    """
    Upload and process a new document (PDF, DOC, DOCX)
    
    This endpoint:
    1. Saves the file
    2. Extracts text using Azure Document Intelligence
    3. Chunks the document
    4. Generates summary and key points
    5. Indexes chunks in Azure AI Search
    """
    # Security: File size limit (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Check file size - read first to get actual size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Support PDF, DOC, and DOCX
    allowed_extensions = ['.pdf', '.doc', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOC, DOCX")
    
    # Security: Sanitize filename to prevent path traversal
    import re
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    if not safe_filename:
        safe_filename = f"document_{hash(file.filename)}{file_ext}"
    
    # Save file
    os.makedirs(settings.documents_dir, exist_ok=True)
    file_path = os.path.join(settings.documents_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    try:
        # Extract text
        doc_intel = get_document_intelligence()
        extracted = await doc_intel.extract_from_file(file_path)
        
        full_text = extracted.get("text", "")
        pages = extracted.get("pages", [])
        page_count = extracted.get("page_count", 0)
        
        if not full_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Generate summary
        try:
            gemini = get_gemini_client()
            summary = await gemini.generate_summary(full_text)
            key_points = await gemini.extract_key_points(full_text)
        except Exception as e:
            print(f"Summary generation failed: {e}")
            summary = full_text[:300] + "..."
            key_points = []
        
        # Store document (no chunking/indexing needed - we use summaries directly)
        store = get_document_store()
        doc_id = store.create(
            title=title,
            category=DocumentCategory(category),
            file_path=file_path,
            source_url=source_url,
            source_ministry=source_ministry,
            summary=summary,
            key_points=key_points,
            full_text=full_text,
            page_count=page_count
        )
        
        return {
            "success": True,
            "document_id": doc_id,
            "title": title,
            "page_count": page_count,
            "summary": summary
        }
        
    except Exception as e:
        # Clean up on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """Delete a document"""
    store = get_document_store()
    doc = store.get(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from store
    store.delete(doc_id)
    
    return {
        "success": True
    }


# ============== Fact-Checking ==============

@router.post("/fact-check", response_model=FactCheckResponse, tags=["Fact-Check"])
async def fact_check(request: FactCheckRequest):
    """
    Verify a claim against all indexed government documents
    
    Returns:
    - verdict: true, false, partially_true, or unverifiable
    - confidence: 0-1 score
    - explanation: Why the claim is true/false
    - evidence: Supporting quotes from documents
    """
    checker = get_fact_checker()
    result = await checker.check_claim(
        claim=request.claim,
        language=request.language.value
    )
    
    # Convert to response model
    evidence = [
        Evidence(
            document_id=e.get("document_id", ""),
            document_title=e.get("document_title", ""),
            page=e.get("page"),
            section=e.get("section"),
            quote=e.get("quote", ""),
            supports_claim=e.get("supports_claim", False)
        )
        for e in result.get("evidence", [])
    ]
    
    return FactCheckResponse(
        claim=result["claim"],
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        evidence=evidence,
        language=request.language
    )


@router.post("/fact-check-url", response_model=URLFactCheckResponse, tags=["Fact-Check"])
async def fact_check_url(request: URLFactCheckRequest):
    """
    Fact-check content from a URL (YouTube, Twitter, Instagram, Facebook, Articles)
    
    This endpoint:
    1. Extracts content from the provided URL
    2. Checks if content is related to Indian government policies/bills
    3. If related, fact-checks claims against indexed official documents
    4. Returns verdict with evidence and links to relevant official docs
    
    If content is NOT government-related, returns a message explaining this.
    """
    extractor = get_url_extractor()
    checker = get_fact_checker()
    
    # Extract content from URL
    extracted = await extractor.extract_from_url(request.url)
    
    if not extracted.get("success"):
        return URLFactCheckResponse(
            url=request.url,
            source_type=extracted.get("source_type", "unknown"),
            is_govt_related=False,
            extracted_title=None,
            extracted_claims=[],
            fact_check_results=[],
            govt_keywords_found=[],
            message=f"Could not extract content from this URL. Error: {extracted.get('error', 'Unknown error')}",
            relevant_documents=[]
        )
    
    # Check if government-related
    if not extracted.get("is_govt_related"):
        return URLFactCheckResponse(
            url=request.url,
            source_type=extracted.get("source_type", "unknown"),
            is_govt_related=False,
            extracted_title=extracted.get("title"),
            extracted_claims=[],
            fact_check_results=[],
            govt_keywords_found=extracted.get("govt_keywords_found", []),
            message="This content does not appear to be related to Indian government policies, bills, or official matters. Our fact-checker only verifies claims about government-related information. Please share content that mentions government policies, bills, schemes, or official decisions.",
            relevant_documents=[]
        )
    
    # Extract claims from the content
    content = f"{extracted.get('title', '')} {extracted.get('content', '')}"
    
    # If additional context provided, prioritize that
    if request.additional_context:
        claims_to_check = [request.additional_context]
    else:
        # Use LLM to extract claims (simplified - just take main content)
        # In production, would use the gemini client to extract specific claims
        claims_to_check = [content[:500]]  # First 500 chars as claim
    
    # Fact-check each claim
    fact_results = []
    for claim in claims_to_check[:3]:  # Limit to 3 claims
        result = await checker.check_claim(
            claim=claim,
            language=request.language.value
        )
        
        evidence = [
            Evidence(
                document_id=e.get("document_id", ""),
                document_title=e.get("document_title", ""),
                page=e.get("page"),
                section=e.get("section"),
                quote=e.get("quote", ""),
                supports_claim=e.get("supports_claim", False)
            )
            for e in result.get("evidence", [])
        ]
        
        fact_results.append(FactCheckResponse(
            claim=result["claim"],
            verdict=result["verdict"],
            confidence=result["confidence"],
            explanation=result["explanation"],
            evidence=evidence,
            language=request.language
        ))
    
    # Get relevant document titles
    relevant_docs = []
    for fr in fact_results:
        for ev in fr.evidence:
            if ev.document_title and ev.document_title not in relevant_docs:
                relevant_docs.append(ev.document_title)
    
    # Create user-friendly message
    if fact_results and fact_results[0].verdict.value in ["true", "partially_true"]:
        message = f"✅ We found official documents that support the claims in this {extracted.get('source_type', 'content')}. See the evidence below."
    elif fact_results and fact_results[0].verdict.value == "false":
        message = f"❌ The claims in this {extracted.get('source_type', 'content')} contradict official government documents. See the correct information below."
    else:
        message = f"⚠️ We could not find official documents to verify the claims in this {extracted.get('source_type', 'content')}. This doesn't mean it's false - we may not have the relevant documents indexed."
    
    return URLFactCheckResponse(
        url=request.url,
        source_type=extracted.get("source_type", "unknown"),
        is_govt_related=True,
        extracted_title=extracted.get("title"),
        extracted_claims=claims_to_check,
        fact_check_results=fact_results,
        govt_keywords_found=extracted.get("govt_keywords_found", []),
        message=message,
        relevant_documents=relevant_docs
    )


# ============== Translation ==============

@router.post("/translate", response_model=TranslateResponse, tags=["Translation"])
async def translate_text(request: TranslateRequest):
    """Translate text to target language"""
    translator = get_translator_service()
    
    if not translator.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Translation service not configured"
        )
    
    translated = await translator.translate(
        text=request.text,
        target_language=request.target_language.value,
        source_language=request.source_language.value
    )
    
    return TranslateResponse(
        original_text=request.text,
        translated_text=translated,
        source_language=request.source_language,
        target_language=request.target_language
    )


@router.get("/languages", tags=["Translation"])
async def get_supported_languages():
    """Get list of supported languages"""
    translator = get_translator_service()
    return {
        "languages": translator.get_supported_languages(),
        "configured": translator.is_configured()
    }


# ============== General Q&A ==============

@router.post("/ask", response_model=AskResponse, tags=["Q&A"])
async def ask_general(request: AskRequest):
    """Ask a question across all indexed documents"""
    rag = get_rag_engine()
    result = await rag.ask(
        question=request.question,
        document_id=None,  # Search all documents
        language=request.language.value
    )
    
    citations = [
        SourceCitation(
            page=c.get("page"),
            section=c.get("section"),
            text=c.get("text", ""),
            relevance_score=c.get("relevance_score", 0)
        )
        for c in result.get("citations", [])
    ]
    
    return AskResponse(
        answer=result["answer"],
        citations=citations,
        confidence=result["confidence"],
        language=request.language
    )
