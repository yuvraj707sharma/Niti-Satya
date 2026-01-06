"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============== Enums ==============

class DocumentCategory(str, Enum):
    BILL = "bill"
    ACT = "act"
    NOTIFICATION = "notification"
    REPORT = "report"
    JUDGMENT = "judgment"
    POLICY = "policy"


class FactCheckVerdict(str, Enum):
    TRUE = "true"
    FALSE = "false"
    PARTIALLY_TRUE = "partially_true"
    UNVERIFIABLE = "unverifiable"


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


# ============== Document Schemas ==============

class DocumentBase(BaseModel):
    """Base document information"""
    title: str
    category: DocumentCategory
    source_url: Optional[str] = None
    source_ministry: Optional[str] = None
    published_date: Optional[datetime] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    file_path: str


class DocumentSummary(BaseModel):
    """Summary information displayed in card views"""
    id: str
    title: str
    category: DocumentCategory
    summary: str = Field(..., max_length=300)
    source_ministry: Optional[str] = None
    published_date: Optional[datetime] = None
    thumbnail_gradient: int = Field(default=1, ge=1, le=4)


class TimelineSection(BaseModel):
    """A section of the Simply Put timeline"""
    title: str
    summary: str
    key_points: List[str]
    source_reference: Optional[str] = None  # e.g., "Article 324A, Clause 2"


class DocumentTimeline(BaseModel):
    """The 'Simply Put' before/change/result view"""
    before: TimelineSection = Field(..., description="How things were before this change")
    change: TimelineSection = Field(..., description="What this document changes")
    result: TimelineSection = Field(..., description="What will happen after implementation")


class DocumentDetail(DocumentBase):
    """Full document details for the article page"""
    id: str
    summary: str
    key_points: List[str]
    timeline: Optional[DocumentTimeline] = None
    full_text: Optional[str] = None
    page_count: Optional[int] = None
    pdf_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    documents: List[DocumentSummary]
    total: int
    page: int
    page_size: int


# ============== Q&A Schemas ==============

class AskRequest(BaseModel):
    """Request to ask a question about a document"""
    question: str = Field(..., min_length=5, max_length=500)
    language: Language = Language.ENGLISH


class SourceCitation(BaseModel):
    """Citation from the source document"""
    page: Optional[int] = None
    section: Optional[str] = None
    text: str
    relevance_score: float = Field(..., ge=0, le=1)


class AskResponse(BaseModel):
    """Response to a document question"""
    answer: str
    citations: List[SourceCitation]
    confidence: float = Field(..., ge=0, le=1)
    language: Language


# ============== Fact-Checker Schemas ==============

class FactCheckRequest(BaseModel):
    """Request to verify a claim"""
    claim: str = Field(..., min_length=10, max_length=1000)
    language: Language = Language.ENGLISH


class Evidence(BaseModel):
    """Evidence supporting a fact-check verdict"""
    document_id: str
    document_title: str
    page: Optional[int] = None
    section: Optional[str] = None
    quote: str
    supports_claim: bool


class FactCheckResponse(BaseModel):
    """Response from the fact-checker"""
    claim: str
    verdict: FactCheckVerdict
    confidence: float = Field(..., ge=0, le=1)
    explanation: str
    evidence: List[Evidence]
    language: Language


class URLFactCheckRequest(BaseModel):
    """Request to fact-check content from a URL"""
    url: str = Field(..., min_length=10, description="URL of article, video, or social media post")
    additional_context: Optional[str] = Field(None, max_length=1000, description="Optional additional context or specific claim to check")
    language: Language = Language.ENGLISH


class URLFactCheckResponse(BaseModel):
    """Response from URL-based fact-checking"""
    url: str
    source_type: str  # youtube, twitter, instagram, facebook, article
    is_govt_related: bool
    extracted_title: Optional[str] = None
    extracted_claims: List[str] = []
    fact_check_results: List[FactCheckResponse] = []
    govt_keywords_found: List[str] = []
    message: str  # User-friendly message about the result
    relevant_documents: List[str] = []  # Links to official documents


# ============== Translation Schemas ==============

class TranslateRequest(BaseModel):
    """Request to translate text"""
    text: str = Field(..., max_length=5000)
    target_language: Language
    source_language: Language = Language.ENGLISH


class TranslateResponse(BaseModel):
    """Translation response"""
    original_text: str
    translated_text: str
    source_language: Language
    target_language: Language


# ============== Health & Status ==============

class HealthStatus(BaseModel):
    """API health check response"""
    status: str = "healthy"
    version: str = "1.0.0"
    services: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
