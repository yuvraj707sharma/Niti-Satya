"""
Document Chunker Service
Splits documents into chunks for vector storage
"""

from typing import List, Dict, Any
import re


class DocumentChunker:
    """
    Splits documents into smaller chunks for vector embedding
    Uses semantic chunking to preserve meaning
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        respect_sentences: bool = True
    ):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target characters per chunk
            chunk_overlap: Overlap between chunks for context
            respect_sentences: Try to break at sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sentences = respect_sentences
    
    def chunk_text(self, text: str, page_numbers: List[int] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks
        
        Args:
            text: Full document text
            page_numbers: Optional list mapping character positions to pages
            
        Returns:
            List of {"text": str, "page": int, "start": int, "end": int}
        """
        if not text:
            return []
        
        # Clean text
        text = self._clean_text(text)
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunk_text = text[start:]
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text.strip(),
                        "page": self._get_page_number(start, page_numbers),
                        "start": start,
                        "end": len(text)
                    })
                break
            
            # Try to find a good break point
            if self.respect_sentences:
                # Look for sentence boundary
                break_point = self._find_sentence_boundary(text, end)
                if break_point > start:
                    end = break_point
            
            chunk_text = text[start:end]
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text.strip(),
                    "page": self._get_page_number(start, page_numbers),
                    "start": start,
                    "end": end
                })
            
            # Move start with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk document by pages
        
        Args:
            pages: List of {"page_num": int, "text": str}
            
        Returns:
            List of chunks with page numbers
        """
        all_chunks = []
        
        for page in pages:
            page_num = page.get("page_num", 0)
            page_text = page.get("text", "")
            
            # Chunk this page
            page_chunks = self.chunk_text(page_text)
            
            # Add page number to each chunk
            for chunk in page_chunks:
                chunk["page"] = page_num
                all_chunks.append(chunk)
        
        return all_chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def _find_sentence_boundary(self, text: str, position: int, window: int = 100) -> int:
        """
        Find the nearest sentence boundary near position
        
        Args:
            text: Full text
            position: Target position
            window: How far to look for boundary
            
        Returns:
            Position of sentence boundary, or original position if none found
        """
        # Look backwards for sentence ending
        search_start = max(0, position - window)
        search_text = text[search_start:position + window]
        
        # Find sentence endings (.!?)
        sentence_endings = []
        for match in re.finditer(r'[.!?]\s+', search_text):
            abs_pos = search_start + match.end()
            sentence_endings.append(abs_pos)
        
        if not sentence_endings:
            # Try paragraph breaks
            for match in re.finditer(r'\n\n', search_text):
                abs_pos = search_start + match.end()
                sentence_endings.append(abs_pos)
        
        if not sentence_endings:
            return position
        
        # Find the ending closest to target position
        best = min(sentence_endings, key=lambda x: abs(x - position))
        
        # Only use if reasonably close
        if abs(best - position) < window:
            return best
        
        return position
    
    def _get_page_number(self, position: int, page_map: List[int] = None) -> int:
        """Get page number for a character position"""
        if not page_map:
            return 0
        
        for i, page_start in enumerate(page_map):
            if position < page_start:
                return i
        
        return len(page_map)


# Default chunker instance
_chunker: DocumentChunker = None


def get_chunker(
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> DocumentChunker:
    """Get or create chunker instance"""
    global _chunker
    if _chunker is None:
        _chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return _chunker
