"""
URL Content Extractor Service
Extracts text/claims from URLs (articles, YouTube, social media)
Checks if content is related to Indian government policies/bills
"""

import re
import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import json


class URLContentExtractor:
    """
    Extracts content from various URL sources:
    - News articles (web scraping)
    - YouTube videos (via transcript API or title/description)
    - Social media posts (via oEmbed or API)
    """
    
    # Keywords that indicate government-related content
    GOVT_KEYWORDS = [
        # General
        'government', 'ministry', 'parliament', 'lok sabha', 'rajya sabha',
        'bill', 'act', 'policy', 'scheme', 'notification', 'gazette',
        'supreme court', 'high court', 'constitution', 'amendment',
        
        # Hindi
        'सरकार', 'मंत्रालय', 'विधेयक', 'योजना', 'नीति',
        
        # Specific
        'modi', 'pmo', 'cabinet', 'niti aayog', 'rbi', 'sebi',
        'income tax', 'gst', 'budget', 'finance ministry',
        'education', 'ugc', 'aicte', 'ncert',
        'aravali', 'environment', 'forest', 'mining',
        'election', 'voting', 'ec', 'evm',
        'health', 'ayushman', 'neet', 'jee',
        'agriculture', 'msp', 'farmer', 'kisan',
        
        # Ministries
        'mea', 'external affairs', 'home ministry', 'defence',
        'law ministry', 'justice', 'corporate affairs',
        
        # Legal
        'section', 'article', 'clause', 'provision', 'regulation',
        'rti', 'pil', 'judgment', 'verdict', 'order'
    ]
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a URL and determine if it's government-related
        
        Returns:
            {
                "success": bool,
                "url": str,
                "source_type": str,  # youtube, article, twitter, instagram, facebook, unknown
                "title": str,
                "content": str,  # Extracted text/transcript
                "is_govt_related": bool,
                "govt_keywords_found": List[str],
                "error": Optional[str]
            }
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Determine source type
            source_type = self._get_source_type(domain)
            
            # Extract content based on source
            if source_type == "youtube":
                result = await self._extract_youtube(url)
            elif source_type == "twitter":
                result = await self._extract_twitter(url)
            elif source_type == "instagram":
                result = await self._extract_instagram(url)
            elif source_type == "facebook":
                result = await self._extract_facebook(url)
            else:
                result = await self._extract_article(url)
            
            # Check if government-related
            content = f"{result.get('title', '')} {result.get('content', '')}"
            is_govt, keywords = self._check_govt_related(content)
            
            result["is_govt_related"] = is_govt
            result["govt_keywords_found"] = keywords
            result["source_type"] = source_type
            result["url"] = url
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "source_type": "unknown",
                "title": "",
                "content": "",
                "is_govt_related": False,
                "govt_keywords_found": [],
                "error": str(e)
            }
    
    def _get_source_type(self, domain: str) -> str:
        """Identify the source type from domain"""
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return 'twitter'
        elif 'instagram.com' in domain:
            return 'instagram'
        elif 'facebook.com' in domain or 'fb.com' in domain:
            return 'facebook'
        else:
            return 'article'
    
    async def _extract_youtube(self, url: str) -> Dict[str, Any]:
        """Extract title, description, and attempt transcript from YouTube"""
        try:
            # Try oEmbed for basic info
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            response = await self.client.get(oembed_url)
            
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', '')
                author = data.get('author_name', '')
                
                # For transcript, we'd need youtube-transcript-api
                # For now, use title + basic extraction
                return {
                    "success": True,
                    "title": title,
                    "content": f"Video by {author}: {title}",
                    "author": author
                }
            else:
                return await self._extract_article(url)
                
        except Exception as e:
            return {
                "success": False,
                "title": "",
                "content": "",
                "error": str(e)
            }
    
    async def _extract_twitter(self, url: str) -> Dict[str, Any]:
        """Extract content from Twitter/X"""
        try:
            # Try oEmbed
            oembed_url = f"https://publish.twitter.com/oembed?url={url}"
            response = await self.client.get(oembed_url)
            
            if response.status_code == 200:
                data = response.json()
                # Parse HTML to get text
                html = data.get('html', '')
                # Simple extraction - remove HTML tags
                text = re.sub(r'<[^>]+>', '', html)
                text = re.sub(r'— .*$', '', text)  # Remove attribution
                
                return {
                    "success": True,
                    "title": "Twitter Post",
                    "content": text.strip(),
                    "author": data.get('author_name', '')
                }
            else:
                return await self._extract_article(url)
                
        except Exception as e:
            return {
                "success": False,
                "title": "",
                "content": "",
                "error": str(e)
            }
    
    async def _extract_instagram(self, url: str) -> Dict[str, Any]:
        """Extract content from Instagram"""
        try:
            # Instagram oEmbed requires app ID - fallback to basic
            return {
                "success": True,
                "title": "Instagram Post",
                "content": f"Instagram content from: {url}. Please provide the text content from the post for fact-checking.",
                "note": "Instagram requires manual content input for accurate fact-checking"
            }
        except Exception as e:
            return {
                "success": False,
                "title": "",
                "content": "",
                "error": str(e)
            }
    
    async def _extract_facebook(self, url: str) -> Dict[str, Any]:
        """Extract content from Facebook"""
        try:
            return {
                "success": True,
                "title": "Facebook Post",
                "content": f"Facebook content from: {url}. Please provide the text content from the post for fact-checking.",
                "note": "Facebook requires manual content input for accurate fact-checking"
            }
        except Exception as e:
            return {
                "success": False,
                "title": "",
                "content": "",
                "error": str(e)
            }
    
    async def _extract_article(self, url: str) -> Dict[str, Any]:
        """Extract content from web articles"""
        try:
            response = await self.client.get(url)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "title": "",
                    "content": "",
                    "error": f"HTTP {response.status_code}"
                }
            
            html = response.text
            
            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            
            # Try to get meta description
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not desc_match:
                desc_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract main content (simplified)
            # Remove scripts, styles, and HTML tags
            content = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Limit content length
            if len(content) > 5000:
                content = content[:5000] + "..."
            
            return {
                "success": True,
                "title": title,
                "content": f"{description} {content}".strip()
            }
            
        except Exception as e:
            return {
                "success": False,
                "title": "",
                "content": "",
                "error": str(e)
            }
    
    def _check_govt_related(self, text: str) -> tuple[bool, List[str]]:
        """Check if content is related to Indian government"""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.GOVT_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        # Require at least 2 keywords or 1 strong keyword
        strong_keywords = ['ministry', 'parliament', 'bill', 'act', 'supreme court', 'government']
        has_strong = any(kw in found_keywords for kw in strong_keywords)
        
        is_related = len(found_keywords) >= 2 or has_strong
        
        return is_related, found_keywords[:10]  # Limit to 10 keywords
    
    async def extract_claims(self, content: str, llm_client) -> List[str]:
        """Use LLM to extract verifiable claims from content"""
        prompt = f"""Extract all verifiable factual claims about Indian government policies, bills, or official matters from this content.
Only include specific, checkable claims. Ignore opinions and predictions.

Content:
{content[:3000]}

Return as a JSON array of claim strings. Example:
["The new tax bill reduces sections from 819 to 536", "UGC will merge with AICTE"]
"""
        try:
            response = await llm_client._generate(prompt)
            claims = json.loads(response)
            if isinstance(claims, list):
                return claims[:5]  # Limit to 5 claims
        except:
            pass
        return []


# Singleton
_extractor: Optional[URLContentExtractor] = None


def get_url_extractor() -> URLContentExtractor:
    global _extractor
    if _extractor is None:
        _extractor = URLContentExtractor()
    return _extractor
