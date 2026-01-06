"""
Document Download Script for Niti Satya AI
Downloads official government documents from verified sources
"""

import os
import requests
from pathlib import Path

# Create documents directory
DOCS_DIR = Path(__file__).parent / "data" / "documents" / "pdfs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Official document sources
DOCUMENTS = [
    {
        "name": "Income Tax Bill 2025",
        "filename": "income-tax-bill-2025.pdf",
        "sources": [
            "https://prsindia.org/files/bills_acts/bills_parliament/2025/Income-tax%20Bill,%202025.pdf",
            "https://loksabhadocs.nic.in/bill/6/Income-tax%20Bill,%202025.pdf"
        ]
    },
    {
        "name": "Viksit Bharat Shiksha Adhishthan Bill 2025",
        "filename": "shiksha-bill-2025.pdf",
        "sources": [
            "https://prsindia.org/files/bills_acts/bills_parliament/2025/Viksit_Bharat_Shiksha_Adhishthan_Bill,_2025.pdf"
        ]
    },
    {
        "name": "Securities Markets Code 2025",
        "filename": "securities-code-2025.pdf",
        "sources": [
            "https://prsindia.org/files/bills_acts/bills_parliament/2025/Securities_Markets_Code,_2025.pdf"
        ]
    }
]

def download_document(doc):
    """Try to download from multiple sources"""
    filepath = DOCS_DIR / doc["filename"]
    
    for url in doc["sources"]:
        try:
            print(f"⏳ Downloading {doc['name']} from {url[:50]}...")
            response = requests.get(url, timeout=60, allow_redirects=True)
            
            if response.status_code == 200 and len(response.content) > 1000:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"✅ Downloaded: {doc['filename']} ({len(response.content) // 1024} KB)")
                return True
        except Exception as e:
            print(f"❌ Failed from {url[:30]}...: {e}")
    
    return False

def main():
    print("=" * 60)
    print("Niti Satya AI - Document Downloader")
    print("=" * 60)
    print()
    
    success_count = 0
    for doc in DOCUMENTS:
        if download_document(doc):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"Downloaded {success_count}/{len(DOCUMENTS)} documents")
    print(f"Location: {DOCS_DIR}")
    print()
    print("MANUAL DOWNLOAD INSTRUCTIONS:")
    print("If automatic download fails, please manually download:")
    print()
    print("1. Income Tax Bill 2025:")
    print("   https://prsindia.org/billtrack/the-income-tax-bill-2025")
    print("   → Click 'Bill Text' → Save as 'income-tax-bill-2025.pdf'")
    print()
    print("2. Shiksha Adhishthan Bill 2025:")
    print("   https://prsindia.org/billtrack/viksit-bharat-shiksha-adhishthan-bill-2025")
    print("   → Click 'Bill Text' → Save as 'shiksha-bill-2025.pdf'")
    print()
    print("3. Securities Markets Code 2025:")
    print("   https://prsindia.org/billtrack/securities-markets-code-2025")
    print("   → Click 'Bill Text' → Save as 'securities-code-2025.pdf'")
    print()
    print(f"Save all files to: {DOCS_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
