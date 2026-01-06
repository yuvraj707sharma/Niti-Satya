"""
Document Store - In-memory document metadata storage
For MVP, this stores document metadata. Can be upgraded to Cosmos DB later.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import uuid

from config import settings
from api.schemas import DocumentCategory


class DocumentStore:
    """
    Simple document metadata store
    Stores document info in a JSON file for persistence
    """
    
    def __init__(self):
        self.data_dir = settings.documents_dir
        self.metadata_file = os.path.join(self.data_dir, "metadata.json")
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        # Create data directory if needed
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing metadata
        self._load()
    
    def _load(self):
        """Load documents from metadata file"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.documents = {}
    
    def _save(self):
        """Save documents to metadata file"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, default=str)
    
    def create(
        self,
        title: str,
        category: DocumentCategory,
        file_path: str,
        source_url: Optional[str] = None,
        source_ministry: Optional[str] = None,
        published_date: Optional[datetime] = None,
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        full_text: Optional[str] = None,
        page_count: Optional[int] = None,
        timeline: Optional[Dict] = None,
    ) -> str:
        """Create a new document record"""
        doc_id = str(uuid.uuid4())[:8]  # Short ID for readability
        
        now = datetime.utcnow()
        
        self.documents[doc_id] = {
            "id": doc_id,
            "title": title,
            "category": category.value if isinstance(category, DocumentCategory) else category,
            "file_path": file_path,
            "source_url": source_url,
            "source_ministry": source_ministry,
            "published_date": published_date.isoformat() if published_date else None,
            "summary": summary or "",
            "key_points": key_points or [],
            "full_text": full_text,
            "page_count": page_count,
            "timeline": timeline,
            "pdf_url": f"/documents/{os.path.basename(file_path)}" if file_path else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        self._save()
        return doc_id
    
    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        return self.documents.get(doc_id)
    
    def get_all(
        self,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get all documents with optional filtering"""
        docs = list(self.documents.values())
        
        # Filter by category
        if category:
            docs = [d for d in docs if d.get("category") == category]
        
        # Sort by created_at descending
        docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Paginate
        total = len(docs)
        start = (page - 1) * page_size
        end = start + page_size
        docs = docs[start:end]
        
        return {
            "documents": docs,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    def update(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update a document"""
        if doc_id not in self.documents:
            return False
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        self.documents[doc_id].update(updates)
        self._save()
        return True
    
    def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        if doc_id not in self.documents:
            return False
        
        del self.documents[doc_id]
        self._save()
        return True
    
    def get_document_text(self, doc_id: str) -> Optional[str]:
        """Get the full text of a document"""
        doc = self.documents.get(doc_id)
        if doc:
            return doc.get("full_text")
        return None


# Singleton instance
_document_store: Optional[DocumentStore] = None


def get_document_store() -> DocumentStore:
    """Get or create document store instance"""
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store
