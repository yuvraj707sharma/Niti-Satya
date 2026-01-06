"""
Government Truth Portal - Backend API
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from api.routes import router
from config import settings


# Create FastAPI app
app = FastAPI(
    title="Government Truth Portal API",
    description="""
    ## 🏛️ Government Truth Portal
    
    An AI-powered platform to combat misinformation about government policies.
    
    ### Features:
    - **Document Analysis**: Upload and analyze government PDFs
    - **RAG Q&A**: Ask questions and get document-backed answers
    - **Fact-Checker**: Verify claims against official documents
    - **Multi-language**: Support for Hindi, Tamil, Telugu, and more
    
    ### Microsoft Azure Services Used:
    - Azure AI Document Intelligence (PDF extraction)
    - Azure AI Search (Vector database)
    - Azure Translator (Multi-language support)
    
    Built for Microsoft Imagine Cup 2026
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        # Azure production domains
        "https://nitisatya-affwa8f5brapasf9.centralindia-01.azurewebsites.net",
        "https://nitisatya-affwa8f5brapasf9.scm.centralindia-01.azurewebsites.net",
        # Allow all for demo (can restrict later)
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(router, prefix="/api")


# Serve documents directory for PDF viewing
documents_path = os.path.join(os.path.dirname(__file__), settings.documents_dir)
os.makedirs(documents_path, exist_ok=True)
app.mount("/documents", StaticFiles(directory=documents_path), name="documents")


# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# Startup event
@app.on_event("startup")
async def startup():
    print("🚀 Government Truth Portal API starting...")
    
    # Check services
    services = settings.validate_required_keys()
    
    print("\n📋 Service Status:")
    for service, configured in services.items():
        status = "✅" if configured else "❌"
        print(f"   {status} {service}")
    
    llm = settings.get_available_llm()
    print(f"\n🤖 LLM Provider: {llm}")
    
    # Create search index if configured
    if services.get("azure_search"):
        try:
            from services.azure_search import get_search_service
            search = get_search_service()
            await search.create_index()
            print("✅ Search index ready")
        except Exception as e:
            print(f"⚠️ Search index creation failed: {e}")
    
    print("\n✨ API ready at http://localhost:8000/docs")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    print("👋 Government Truth Portal API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
