"""
Azure AI Document Intelligence Service
Extracts text and structure from PDF documents
Microsoft Imagine Cup Service #1
"""

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from typing import Optional, List, Dict, Any
import os

from config import settings


class AzureDocumentIntelligence:
    """
    Azure AI Document Intelligence for PDF extraction
    Handles both digital and scanned documents with OCR
    """
    
    def __init__(self):
        if not settings.azure_doc_intel_endpoint or not settings.azure_doc_intel_key:
            self.client = None
            print("⚠️ Azure Document Intelligence not configured - using fallback PDF parser")
            return
        
        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_intel_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key)
        )
    
    async def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and structure from a PDF file
        
        Returns:
            {
                "text": "full document text",
                "pages": [{"page_num": 1, "text": "...", "tables": [...]}],
                "tables": [...],
                "metadata": {...}
            }
        """
        if not self.client:
            return await self._fallback_extract(file_path)
        
        with open(file_path, "rb") as f:
            document_bytes = f.read()
        
        return await self._analyze_document(document_bytes)
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """Extract text from a document URL"""
        if not self.client:
            raise ValueError("Azure Document Intelligence not configured")
        
        poller = self.client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(url_source=url)
        )
        result: AnalyzeResult = poller.result()
        
        return self._process_result(result)
    
    async def _analyze_document(self, document_bytes: bytes) -> Dict[str, Any]:
        """Analyze document bytes using Azure"""
        try:
            poller = self.client.begin_analyze_document(
                "prebuilt-layout",
                document_bytes,
                content_type="application/pdf"
            )
            result: AnalyzeResult = poller.result()
            return self._process_result(result)
        except Exception as e:
            print(f"Azure Document Intelligence error: {e}")
            raise
    
    def _process_result(self, result: AnalyzeResult) -> Dict[str, Any]:
        """Process Azure analysis result into structured output"""
        
        # Extract full text
        full_text = result.content if result.content else ""
        
        # Process pages
        pages = []
        if result.pages:
            for page in result.pages:
                page_text = ""
                if page.lines:
                    page_text = "\n".join([line.content for line in page.lines])
                
                pages.append({
                    "page_num": page.page_number,
                    "text": page_text,
                    "width": page.width,
                    "height": page.height,
                })
        
        # Process tables
        tables = []
        if result.tables:
            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                if table.cells:
                    for cell in table.cells:
                        table_data["cells"].append({
                            "row": cell.row_index,
                            "column": cell.column_index,
                            "content": cell.content,
                        })
                tables.append(table_data)
        
        # Extract paragraphs
        paragraphs = []
        if result.paragraphs:
            for para in result.paragraphs:
                paragraphs.append({
                    "content": para.content,
                    "role": para.role if hasattr(para, 'role') else None
                })
        
        return {
            "text": full_text,
            "pages": pages,
            "tables": tables,
            "paragraphs": paragraphs,
            "page_count": len(pages),
            "metadata": {
                "model_id": result.model_id if hasattr(result, 'model_id') else None,
            }
        }
    
    async def _fallback_extract(self, file_path: str) -> Dict[str, Any]:
        """Fallback PDF extraction using PyPDF2 when Azure is not configured"""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            full_text = ""
            pages = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                full_text += page_text + "\n\n"
                pages.append({
                    "page_num": page_num,
                    "text": page_text,
                })
            
            return {
                "text": full_text.strip(),
                "pages": pages,
                "tables": [],
                "paragraphs": [],
                "page_count": len(pages),
                "metadata": {"model_id": "pypdf2-fallback"}
            }
        except Exception as e:
            raise ValueError(f"Could not extract PDF: {e}")


# Singleton instance
_doc_intel_client: Optional[AzureDocumentIntelligence] = None


def get_document_intelligence() -> AzureDocumentIntelligence:
    """Get or create Document Intelligence client"""
    global _doc_intel_client
    if _doc_intel_client is None:
        _doc_intel_client = AzureDocumentIntelligence()
    return _doc_intel_client
