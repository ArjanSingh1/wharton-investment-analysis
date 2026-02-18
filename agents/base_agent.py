"""
Base Agent Class
Abstract base class for all investment analysis agents.
Defines common interface and OpenAI integration.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from openai import OpenAI
import logging
from utils.logger import get_disclosure_logger

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Each agent analyzes stocks from a specific perspective.
    """
    
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        openai_client: Optional[OpenAI] = None
    ):
        self.name = name
        self.config = config
        self.disclosure_logger = get_disclosure_logger()
        
        # Initialize OpenAI client
        if openai_client:
            self.openai = openai_client
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.openai = OpenAI(api_key=api_key)
        
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        logger.info(f"Initialized {self.name}")
    
    @abstractmethod
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a stock and return a score + rationale.
        
        Args:
            ticker: Stock ticker symbol
            data: Dictionary containing all relevant data for analysis
        
        Returns:
            {
                'score': float (0-100),
                'rationale': str (one-line explanation),
                'details': dict (supporting metrics)
            }
        """
        pass
    
    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 500
    ) -> str:
        """
        Call OpenAI API with disclosure logging.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        
        Returns:
            Response text
        """
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
            # Estimate cost (gpt-4o-mini: $0.15/$0.60 per 1M tokens)
            cost = (response.usage.prompt_tokens * 0.15 + response.usage.completion_tokens * 0.60) / 1_000_000
            
            # Log for disclosure
            self.disclosure_logger.log_ai_usage(
                tool=f"OpenAI-{self.model}",
                purpose=f"{self.name} analysis",
                prompt_summary=user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt,
                output_summary=result[:100] + "..." if len(result) > 100 else result,
                tokens_used=tokens,
                cost_usd=cost
            )
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error in {self.name}: {e}")
            raise
    
    def _normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to 0-100 scale."""
        if max_val == min_val:
            return 50.0
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return max(0.0, min(100.0, normalized))
    
    def _safe_get(self, data: Dict, key: str, default: Any = None) -> Any:
        """Safely get value from dict with default."""
        return data.get(key, default)

    def _fetch_supporting_articles(self, ticker: str, domain_query: str, num_articles: int = 2) -> List[Dict]:
        """
        Fetch domain-specific supporting articles using Perplexity.

        Args:
            ticker: Stock ticker symbol
            domain_query: Domain-specific search query (e.g., "valuation P/E analysis")
            num_articles: Number of articles to fetch (default: 2)

        Returns:
            List of article dicts with 'title', 'url', 'source' keys
        """
        import requests
        import re

        perplexity_key = os.getenv('PERPLEXITY_API_KEY')
        if not perplexity_key:
            logger.debug(f"No Perplexity API key - skipping article fetch for {self.name}")
            return []

        prompt = (
            f"Find {num_articles} recent credible articles specifically about "
            f"{domain_query} for stock ticker {ticker}.\n\n"
            f"Requirements:\n"
            f"- From reputable financial sources (Reuters, Bloomberg, CNBC, WSJ, "
            f"Barron's, MarketWatch, SeekingAlpha, Yahoo Finance, Motley Fool)\n"
            f"- Directly relevant to {domain_query} for {ticker}\n"
            f"- Published within the last 30 days\n"
            f"- Return ONLY in this exact format, one per line:\n"
            f"TITLE: [article title] | URL: [full URL]"
        )

        headers = {
            "Authorization": f"Bearer {perplexity_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 400
        }

        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                articles = self._parse_article_citations(content, num_articles)
                logger.info(f"{self.name}: Found {len(articles)} supporting articles for {ticker}")
                return articles
            else:
                logger.warning(f"{self.name}: Perplexity article fetch failed with status {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"{self.name}: Failed to fetch supporting articles for {ticker}: {e}")
            return []

    def _parse_article_citations(self, content: str, max_articles: int = 2) -> List[Dict]:
        """Parse article citations from Perplexity response."""
        import re

        articles = []

        # Try TITLE: ... | URL: ... pattern first
        pattern = r'TITLE:\s*(.+?)\s*\|\s*URL:\s*(https?://[^\s\]]+)'
        matches = re.findall(pattern, content, re.IGNORECASE)

        for title, url in matches:
            url_clean = url.strip().rstrip('.,;)')
            source = url_clean.split('//')[1].split('/')[0].replace('www.', '') if '//' in url_clean else 'Unknown'
            articles.append({
                'title': title.strip(),
                'url': url_clean,
                'source': source
            })

        # Fallback: extract URLs and nearby text
        if not articles:
            url_pattern = r'(https?://[^\s\[\]<>()"]+)'
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                url_match = re.search(url_pattern, line)
                if url_match:
                    url = url_match.group(1).rstrip('.,;)')
                    title_part = line[:url_match.start()].strip()
                    title_part = re.sub(r'^[\d\.\)\-\*]+\s*', '', title_part).strip()
                    title_part = title_part.rstrip('|:- ').strip()
                    if not title_part or len(title_part) < 5:
                        title_part = "Financial Analysis Article"
                    source = url.split('//')[1].split('/')[0].replace('www.', '') if '//' in url else 'Unknown'
                    articles.append({
                        'title': title_part[:100],
                        'url': url,
                        'source': source
                    })

        return articles[:max_articles]

    def _format_article_references(self, articles: List[Dict]) -> str:
        """Format article references for inclusion in rationale."""
        if not articles:
            return ""

        refs = "\n\nSources:\n"
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Article')
            url = article.get('url', '')
            source = article.get('source', 'Unknown')
            if url:
                refs += f"{i}. {title} | {source} | {url}\n"
            else:
                refs += f"{i}. {title} | {source}\n"
        return refs
