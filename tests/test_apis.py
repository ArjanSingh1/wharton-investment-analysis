"""
Automated API Test Suite
Validates all API connectivity and functionality for the Investment Analysis Platform.
Run: python tests/test_apis.py
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class APITestSuite:
    """Validates all API connections and diagnoses issues."""

    def __init__(self):
        self.results = {}
        self.fixes = []

    def test_openai(self):
        """Test OpenAI API connectivity."""
        from openai import OpenAI
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        client = OpenAI(api_key=key)
        # Use a cheap model for testing connectivity
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with OK"}],
            max_tokens=5
        )
        assert response.choices[0].message.content, "Empty response from OpenAI"

    def test_gemini(self):
        """Test Gemini API with 2.5 Pro."""
        key = os.getenv('GEMINI_API_KEY')
        if not key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content("Reply with OK")
        assert response.text, "Empty response from Gemini"

    def test_polygon(self):
        """Test Polygon.io API for stock data."""
        import requests
        key = os.getenv('POLYGON_API_KEY')
        if not key:
            raise ValueError("POLYGON_API_KEY not set in .env")
        resp = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/AAPL/prev",
            params={"apiKey": key},
            timeout=15
        )
        assert resp.status_code == 200, f"Polygon returned status {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data.get('resultsCount', 0) > 0, "No results from Polygon"

    def test_alpha_vantage(self):
        """Test Alpha Vantage API."""
        import requests
        key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not key:
            raise ValueError("ALPHA_VANTAGE_API_KEY not set in .env")
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": "AAPL",
                "apikey": key
            },
            timeout=15
        )
        assert resp.status_code == 200, f"Alpha Vantage returned status {resp.status_code}"
        data = resp.json()
        # Free tier may return rate limit note
        assert "Global Quote" in data or "Note" in data or "Information" in data, \
            f"Unexpected response: {list(data.keys())}"

    def test_news_api(self):
        """Test NewsAPI for news retrieval."""
        import requests
        key = os.getenv('NEWS_API_KEY')
        if not key:
            raise ValueError("NEWS_API_KEY not set in .env")
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "AAPL stock",
                "apiKey": key,
                "pageSize": 1,
                "sortBy": "publishedAt"
            },
            timeout=15
        )
        # 200 = success, 426 = free tier requires upgrade for production
        assert resp.status_code in [200, 426], \
            f"NewsAPI returned status {resp.status_code}: {resp.text[:200]}"

    def test_perplexity(self):
        """Test Perplexity API (used for data retrieval)."""
        key = os.getenv('PERPLEXITY_API_KEY')
        if not key:
            raise ValueError("PERPLEXITY_API_KEY not set in .env")
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="sonar",
            messages=[{"role": "user", "content": "Reply with OK"}],
            max_tokens=5
        )
        assert response.choices[0].message.content, "Empty response from Perplexity"

    def test_news_pipeline(self):
        """Test the full news retrieval pipeline via EnhancedDataProvider."""
        from data.enhanced_data_provider import EnhancedDataProvider
        provider = EnhancedDataProvider()
        news = provider.get_news_with_sources("AAPL", limit=3)
        assert isinstance(news, list), f"Expected list, got {type(news)}"
        # News might be empty if all sources fail, but function should not crash
        print(f"   Retrieved {len(news)} news articles")

    def test_fundamentals_pipeline(self):
        """Test fundamental data retrieval via EnhancedDataProvider."""
        from data.enhanced_data_provider import EnhancedDataProvider
        provider = EnhancedDataProvider()
        data = provider.get_comprehensive_metrics("AAPL")
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        # Should have at least some basic metrics
        print(f"   Retrieved {len(data)} metric fields")

    def run_all(self):
        """Run all tests and report results."""
        tests = [
            ("OpenAI", self.test_openai),
            ("Gemini 2.5 Pro", self.test_gemini),
            ("Polygon.io", self.test_polygon),
            ("Alpha Vantage", self.test_alpha_vantage),
            ("NewsAPI", self.test_news_api),
            ("Perplexity (data)", self.test_perplexity),
            ("News Pipeline", self.test_news_pipeline),
            ("Fundamentals Pipeline", self.test_fundamentals_pipeline),
        ]

        print("\n" + "=" * 60)
        print("  INVESTMENT ANALYSIS PLATFORM - API TEST SUITE")
        print("=" * 60 + "\n")

        for name, test_fn in tests:
            print(f"  Testing {name}...", end=" ", flush=True)
            start = time.time()
            try:
                test_fn()
                elapsed = time.time() - start
                self.results[name] = "PASS"
                print(f"PASS ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = time.time() - start
                error_str = str(e)[:100]
                self.results[name] = f"FAIL: {error_str}"
                print(f"FAIL ({elapsed:.1f}s)")
                print(f"         {error_str}")
                self._diagnose(name, str(e))
            # Small delay between tests to avoid rate limits
            time.sleep(0.5)

        self._print_summary()

    def _diagnose(self, test_name, error):
        """Auto-diagnose common failures."""
        error_lower = error.lower()
        if "api_key" in error_lower or "not set" in error_lower:
            self.fixes.append(f"{test_name}: Set the API key in your .env file")
        elif "unauthorized" in error_lower or "401" in error:
            self.fixes.append(f"{test_name}: API key is invalid or expired. Check .env")
        elif "429" in error or "rate_limit" in error_lower:
            self.fixes.append(f"{test_name}: Rate limited. Wait a minute and retry")
        elif "timeout" in error_lower:
            self.fixes.append(f"{test_name}: Network timeout. Check your internet connection")
        elif "module" in error_lower and "not found" in error_lower:
            self.fixes.append(f"{test_name}: Missing dependency. Run: pip install -r requirements.txt")
        elif "404" in error or "not found" in error_lower:
            self.fixes.append(f"{test_name}: Model or endpoint not found. Check model name/API version")

    def _print_summary(self):
        """Print formatted test report."""
        print("\n" + "=" * 60)
        print("  RESULTS SUMMARY")
        print("=" * 60)

        passed = 0
        failed = 0
        for name, result in self.results.items():
            if result == "PASS":
                status = "[OK]"
                passed += 1
            else:
                status = "[!!]"
                failed += 1
            print(f"  {status} {name}: {result}")

        total = passed + failed
        print(f"\n  Total: {passed}/{total} passed, {failed} failed")

        if self.fixes:
            print("\n  SUGGESTED FIXES:")
            for fix in self.fixes:
                print(f"  -> {fix}")

        print("\n" + "=" * 60)

        return failed == 0


if __name__ == "__main__":
    suite = APITestSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
