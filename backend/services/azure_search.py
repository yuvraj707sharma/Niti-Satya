"""
Azure AI Search Service
Vector database for RAG retrieval
Microsoft Imagine Cup Service #2
"""

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from azure.core.credentials import AzureKeyCredential
from typing import Optional, List, Dict, Any
import hashlib
import numpy as np

from config import settings


class AzureSearchService:
    """
    Azure AI Search for document indexing and retrieval
    Supports both keyword and vector (semantic) search
    """
    
    VECTOR_DIMENSIONS = 384  # Using sentence-transformers all-MiniLM-L6-v2
    
    def __init__(self):
        if not settings.azure_search_endpoint or not settings.azure_search_key:
            self.search_client = None
            self.index_client = None
            print("⚠️ Azure AI Search not configured - using in-memory search")
            self._memory_store: List[Dict] = []
            return
        
        credential = AzureKeyCredential(settings.azure_search_key)
        
        self.index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=credential
        )
        
        self.search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=credential
        )
        
        self._embedding_model = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("⚠️ sentence-transformers not installed - embeddings disabled")
        return self._embedding_model
    
    async def create_index(self) -> bool:
        """Create the search index if it doesn't exist"""
        if not self.index_client:
            return False
        
        try:
            # Check if index exists
            self.index_client.get_index(settings.azure_search_index_name)
            print(f"Index '{settings.azure_search_index_name}' already exists")
            return True
        except Exception:
            pass  # Index doesn't exist, create it
        
        # Define index schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchableField(name="ministry", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.VECTOR_DIMENSIONS,
                vector_search_profile_name="myHnswProfile"
            ),
        ]
        
        # Vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="myHnsw"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw",
                ),
            ],
        )
        
        # Semantic search configuration
        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                title_field=SemanticField(field_name="title"),
            ),
        )
        
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # Create index
        index = SearchIndex(
            name=settings.azure_search_index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        self.index_client.create_or_update_index(index)
        print(f"Created index '{settings.azure_search_index_name}'")
        return True
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        model = self._get_embedding_model()
        if model is None:
            return [0.0] * self.VECTOR_DIMENSIONS
        
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique ID for a chunk"""
        raw = f"{document_id}_{chunk_index}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    async def index_document_chunks(
        self,
        document_id: str,
        title: str,
        chunks: List[Dict[str, Any]],
        category: str = "",
        ministry: str = ""
    ) -> int:
        """
        Index document chunks for search
        
        Args:
            document_id: Unique document identifier
            title: Document title
            chunks: List of {"text": str, "page": int} dicts
            category: Document category
            ministry: Source ministry
            
        Returns:
            Number of chunks indexed
        """
        documents = []
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get("text", "")
            page_num = chunk.get("page", 0)
            
            doc = {
                "id": self._generate_chunk_id(document_id, i),
                "content": chunk_text,
                "title": title,
                "document_id": document_id,
                "page_number": page_num,
                "chunk_index": i,
                "category": category,
                "ministry": ministry,
                "content_vector": self._generate_embedding(chunk_text),
            }
            documents.append(doc)
        
        if self.search_client:
            # Upload to Azure
            result = self.search_client.upload_documents(documents)
            return len([r for r in result if r.succeeded])
        else:
            # In-memory fallback
            self._memory_store.extend(documents)
            return len(documents)
    
    async def search(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        use_vector: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            document_id: Optional - limit to specific document
            top_k: Number of results to return
            use_vector: Whether to use vector search
            
        Returns:
            List of matching chunks with scores
        """
        if self.search_client:
            return await self._azure_search(query, document_id, top_k, use_vector)
        else:
            return await self._memory_search(query, document_id, top_k)
    
    async def _azure_search(
        self,
        query: str,
        document_id: Optional[str],
        top_k: int,
        use_vector: bool
    ) -> List[Dict[str, Any]]:
        """Search using Azure AI Search"""
        
        filter_expr = None
        if document_id:
            filter_expr = f"document_id eq '{document_id}'"
        
        vector_queries = None
        if use_vector:
            query_vector = self._generate_embedding(query)
            vector_queries = [
                VectorizedQuery(
                    vector=query_vector,
                    k_nearest_neighbors=top_k,
                    fields="content_vector"
                )
            ]
        
        results = self.search_client.search(
            search_text=query,
            vector_queries=vector_queries,
            filter=filter_expr,
            top=top_k,
            select=["id", "content", "title", "document_id", "page_number", "chunk_index"]
        )
        
        output = []
        for result in results:
            output.append({
                "id": result["id"],
                "text": result["content"],
                "document_title": result["title"],
                "document_id": result["document_id"],
                "page": result.get("page_number"),
                "chunk_index": result.get("chunk_index"),
                "score": result.get("@search.score", 0)
            })
        
        return output
    
    async def _memory_search(
        self,
        query: str,
        document_id: Optional[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback in-memory search using embeddings"""
        
        # Filter by document if specified
        candidates = self._memory_store
        if document_id:
            candidates = [c for c in candidates if c["document_id"] == document_id]
        
        if not candidates:
            return []
        
        # Compute query embedding
        query_embedding = np.array(self._generate_embedding(query))
        
        # Compute similarities
        scored = []
        for chunk in candidates:
            chunk_embedding = np.array(chunk["content_vector"])
            # Cosine similarity
            similarity = np.dot(query_embedding, chunk_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding) + 1e-8
            )
            scored.append((chunk, similarity))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k
        output = []
        for chunk, score in scored[:top_k]:
            output.append({
                "id": chunk["id"],
                "text": chunk["content"],
                "document_title": chunk["title"],
                "document_id": chunk["document_id"],
                "page": chunk.get("page_number"),
                "chunk_index": chunk.get("chunk_index"),
                "score": float(score)
            })
        
        return output
    
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document"""
        if self.search_client:
            # Search for all chunks
            results = self.search_client.search(
                search_text="*",
                filter=f"document_id eq '{document_id}'",
                select=["id"]
            )
            
            chunk_ids = [r["id"] for r in results]
            if chunk_ids:
                self.search_client.delete_documents([{"id": cid} for cid in chunk_ids])
            return len(chunk_ids)
        else:
            # In-memory fallback
            before = len(self._memory_store)
            self._memory_store = [c for c in self._memory_store if c["document_id"] != document_id]
            return before - len(self._memory_store)


# Singleton instance
_search_service: Optional[AzureSearchService] = None


def get_search_service() -> AzureSearchService:
    """Get or create search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = AzureSearchService()
    return _search_service
