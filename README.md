# Niti Satya AI (नीति सत्य) 🇮🇳

> **🏆 Microsoft Imagine Cup 2026 Submission**

AI-powered platform to combat misinformation about Indian government policies by fact-checking claims against official documents.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Azure](https://img.shields.io/badge/Microsoft-Azure-0078D4.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🎯 What It Does

1. **📚 Simplifies Documents** - Summarizes 500+ page bills into key points
2. **✅ Fact-Checks URLs** - Paste YouTube/Twitter/Instagram links to verify claims
3. **❓ Answers Questions** - Ask anything about government policies
4. **🌐 Multi-language** - Hindi, Tamil, Telugu, Bengali, and more

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Frontend** | HTML, CSS, JavaScript |
| **Backend** | Python FastAPI |
| **AI/LLM** | Google Gemini / Azure OpenAI |
| **Search** | Azure AI Search (Vector) |
| **PDF Processing** | Azure Document Intelligence |
| **Translation** | Azure Translator |

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/niti-satya-ai.git
cd niti-satya-ai
```

### 2. Setup Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your keys
```

### 4. Download Documents
```bash
python download_documents.py
```

### 5. Run
```bash
python -m uvicorn main:app --reload
# Open index.html in browser
```

---

## 📤 Deployment Guide

### Option 1: GitHub + Azure Static Web Apps (Frontend)

```bash
# Initialize git
git init
git add .
git commit -m "Initial commit"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/niti-satya-ai.git
git push -u origin main
```

Then in Azure Portal:
1. Create **Azure Static Web Apps**
2. Connect to your GitHub repo
3. Build preset: **Custom**
4. App location: `/`
5. API location: (leave blank for now)

### Option 2: Azure App Service (Full Stack)

```bash
# Login to Azure
az login

# Create resource group
az group create --name niti-satya-rg --location centralindia

# Create App Service plan
az appservice plan create --name niti-satya-plan --resource-group niti-satya-rg --sku B1 --is-linux

# Create Web App
az webapp create --name niti-satya-ai --resource-group niti-satya-rg --plan niti-satya-plan --runtime "PYTHON:3.10"

# Deploy from GitHub
az webapp deployment source config --name niti-satya-ai --resource-group niti-satya-rg --repo-url https://github.com/YOUR_USERNAME/niti-satya-ai --branch main --manual-integration
```

### Option 3: Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📁 Project Structure

```
niti-satya-ai/
├── index.html              # Homepage
├── article.html            # Document viewer
├── fact-checker.html       # Standalone fact-checker
├── style.css               # Styles
├── main.js                 # Frontend logic
├── document-viewer.js      # AI panel
└── backend/
    ├── main.py             # FastAPI app
    ├── config.py           # Configuration
    ├── download_documents.py  # PDF downloader
    ├── api/
    │   ├── routes.py       # API endpoints
    │   └── schemas.py      # Data models
    ├── services/
    │   ├── azure_doc_intel.py   # PDF extraction
    │   ├── azure_search.py      # Vector search
    │   ├── fact_checker.py      # Claim verification
    │   ├── url_extractor.py     # Extract from URLs
    │   └── rag_engine.py        # Q&A engine
    └── data/documents/          # Document storage
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/documents` | GET | List documents |
| `/api/documents/{id}/ask` | POST | Ask about document |
| `/api/fact-check` | POST | Verify text claim |
| `/api/fact-check-url` | POST | Verify claim from URL |
| `/api/translate` | POST | Translate text |

---

## 🔑 Environment Variables

```env
# Azure Document Intelligence
AZURE_DOC_INTEL_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_DOC_INTEL_KEY=your-key

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-key

# Azure Translator
AZURE_TRANSLATOR_KEY=your-key
AZURE_TRANSLATOR_REGION=centralindia

# Google Gemini (Free alternative to Azure OpenAI)
GEMINI_API_KEY=your-gemini-key
```

---

## 👥 Team

**Developed by**: Yuvraj Sharma & Tushar Jain

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.
