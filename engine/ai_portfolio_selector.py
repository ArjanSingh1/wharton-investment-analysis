"""
AI-Powered Portfolio Selector
Multi-stage AI selection process using OpenAI o3 and Gemini 2.5 Pro for optimal stock selection.
"""

import logging
import json
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class AIPortfolioSelector:
    """
    Multi-stage AI-powered portfolio selection system.

    Process:
    1. OpenAI o3 selects 20 best tickers with context
    2. Gemini 2.5 Pro selects 20 best tickers with context
    3. Aggregate to 40 unique tickers
    4. Generate 4-sentence rationale for each (why strong/beneficial/relevant)
    5. OpenAI o3 selects top 5 from 40 (run 3 times)
    6. If more than 5 unique, narrow down to final 5
    7. Log everything to portfolio_selection_logs/
    """

    def __init__(self, openai_client, gemini_api_key: str, ips_config: Dict[str, Any], model_config: Dict[str, Any]):
        """Initialize the AI Portfolio Selector."""
        self.openai_client = openai_client
        self.gemini_model = None
        self.ips_config = ips_config
        self.model_config = model_config

        # Initialize Gemini
        if gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel("gemini-2.5-pro")
                logger.info("Gemini 2.5 Pro initialized successfully")
            except Exception as e:
                logger.warning(f"Gemini initialization failed: {e}")

        # Create logs directory
        self.logs_dir = Path("portfolio_selection_logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Rate limiting configuration - balance speed with API limits
        self.min_delay_between_calls = 0.5  # 0.5 second delay to avoid 429 errors
        self.last_api_call_time = 0

        logger.info("AI Portfolio Selector initialized with rate limiting")

    def _rate_limited_api_call(self, api_func, *args, **kwargs):
        """
        Execute an API call with rate limiting to avoid 429 errors.
        Ensures minimum delay between calls and handles retries.
        """
        # Calculate time since last call
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call_time

        # If not enough time has passed, wait
        if time_since_last_call < self.min_delay_between_calls:
            sleep_time = self.min_delay_between_calls - time_since_last_call
            logger.info(f"   Rate limiting: waiting {sleep_time:.1f}s before next API call...")
            time.sleep(sleep_time)

        # Make the API call with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = api_func(*args, **kwargs)
                self.last_api_call_time = time.time()
                return result
            except Exception as e:
                error_msg = str(e)
                if '429' in error_msg or 'rate_limit' in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                        logger.warning(f"   Rate limit hit, waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"   Rate limit exceeded after {max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    raise

        return None

    def select_portfolio_tickers(
        self,
        challenge_context: str,
        client_profile: Dict[str, Any],
        universe_size: int = 500
    ) -> Dict[str, Any]:
        """
        Complete portfolio selection process.

        Args:
            challenge_context: Description of the investment challenge/goal
            client_profile: Complete client profile with IPS data
            universe_size: Size of universe to consider (default: S&P 500)

        Returns:
            Dict containing:
                - final_tickers: List of 5 selected tickers
                - ticker_rationales: Dict mapping ticker -> rationale
                - all_candidates: List of all 40 candidates with rationales
                - selection_log: Complete log of selection process
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_log = {
            'timestamp': timestamp,
            'challenge_context': challenge_context,
            'client_profile': client_profile,
            'universe_size': universe_size,
            'stages': []
        }

        logger.info(f"Starting AI Portfolio Selection - Session {timestamp}")

        # Stage 1: OpenAI o3 selects 20 tickers
        logger.info("Stage 1: OpenAI o3 Ticker Selection")
        openai_tickers, openai_log = self._openai_select_tickers(
            challenge_context, client_profile, universe_size, num_tickers=20
        )
        session_log['stages'].append({
            'stage': 'openai_initial_selection',
            'tickers': openai_tickers,
            'log': openai_log
        })

        # Stage 2: Gemini 2.5 Pro selects 20 tickers
        logger.info("Stage 2: Gemini 2.5 Pro Ticker Selection")
        gemini_tickers, gemini_log = self._gemini_select_tickers(
            challenge_context, client_profile, universe_size, num_tickers=20
        )
        session_log['stages'].append({
            'stage': 'gemini_initial_selection',
            'tickers': gemini_tickers,
            'log': gemini_log
        })

        # Stage 3: Aggregate to 40 unique tickers
        logger.info("Stage 3: Aggregating Tickers")
        all_candidates = list(set(openai_tickers + gemini_tickers))
        logger.info(f"   OpenAI: {len(openai_tickers)} tickers")
        logger.info(f"   Gemini: {len(gemini_tickers)} tickers")
        logger.info(f"   Unique Total: {len(all_candidates)} tickers")
        session_log['stages'].append({
            'stage': 'aggregation',
            'unique_tickers': all_candidates,
            'count': len(all_candidates)
        })

        # Stage 4: Generate 4-sentence rationales for each
        logger.info("Stage 4: Generating Rationales for All Candidates")
        ticker_rationales = {}
        for i, ticker in enumerate(all_candidates, 1):
            logger.info(f"   Generating rationale {i}/{len(all_candidates)}: {ticker}")
            rationale = self._generate_ticker_rationale(
                ticker, challenge_context, client_profile
            )
            ticker_rationales[ticker] = rationale

        session_log['stages'].append({
            'stage': 'rationale_generation',
            'ticker_rationales': ticker_rationales
        })

        # Stage 5: OpenAI o3 selects top 5 (run 3 times)
        logger.info("Stage 5: OpenAI o3 Final Selection (3 rounds)")
        final_selection_rounds = []

        for round_num in range(1, 4):
            logger.info(f"   Round {round_num}/3")
            top_5 = self._openai_select_top_5(
                all_candidates, ticker_rationales, challenge_context, client_profile
            )
            final_selection_rounds.append(top_5)
            logger.info(f"   Round {round_num} selected: {', '.join(top_5)}")

        session_log['stages'].append({
            'stage': 'final_selection_rounds',
            'round_1': final_selection_rounds[0],
            'round_2': final_selection_rounds[1],
            'round_3': final_selection_rounds[2]
        })

        # Stage 6: Determine final 5 (consolidate if needed)
        logger.info("Stage 6: Consolidating Final Selection")
        unique_finalists = list(set(
            final_selection_rounds[0] +
            final_selection_rounds[1] +
            final_selection_rounds[2]
        ))

        logger.info(f"   Unique finalists: {len(unique_finalists)} tickers")

        if len(unique_finalists) > 5:
            logger.info("   More than 5 unique, narrowing down...")
            final_tickers = self._openai_narrow_to_5(
                unique_finalists, ticker_rationales, challenge_context, client_profile
            )
        else:
            final_tickers = unique_finalists

        logger.info(f"   Final 5 tickers: {', '.join(final_tickers)}")

        session_log['stages'].append({
            'stage': 'final_consolidation',
            'unique_finalists': unique_finalists,
            'final_5': final_tickers
        })

        # Save complete session log
        log_file = self.logs_dir / f"portfolio_selection_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump(session_log, f, indent=2)

        logger.info(f"Session log saved: {log_file}")

        return {
            'final_tickers': final_tickers,
            'ticker_rationales': {t: ticker_rationales[t] for t in final_tickers},
            'all_candidates': all_candidates,
            'all_rationales': ticker_rationales,
            'selection_rounds': final_selection_rounds,
            'session_log': session_log,
            'log_file': str(log_file)
        }

    def _openai_select_tickers(
        self,
        challenge_context: str,
        client_profile: Dict[str, Any],
        universe_size: int,
        num_tickers: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Use OpenAI o3 to select initial tickers."""

        # Build comprehensive context
        context = self._build_selection_context(challenge_context, client_profile)

        prompt = f"""You are an expert portfolio manager specializing in discovering high-potential investment opportunities across ALL market capitalizations.

{context}

TASK: Select exactly {num_tickers} stock tickers with the HIGHEST growth potential that match this challenge and client profile.

CRITICAL REQUIREMENTS:
- Search BEYOND the S&P 500 - discover hidden gems in small-cap, mid-cap, and emerging companies
- Market cap is NOT a constraint - the best opportunity might be a $500M company or a $500B company
- Actively seek niche players, disruptors, and category leaders in high-growth sectors:
  * Artificial Intelligence & Machine Learning
  * Biotechnology & Gene Therapy
  * Clean Energy & Sustainability
  * Fintech & Digital Payments
  * SaaS & Cloud Infrastructure
  * Semiconductors & Advanced Hardware
  * Cybersecurity
  * Robotics & Automation
- Don't default to FAANG or well-known mega-caps unless they truly are the best opportunities
- Prioritize companies with:
  * Strong revenue growth (30%+ annually)
  * Expanding market share in growing industries
  * Innovative products/services with competitive moats
  * Solid fundamentals despite smaller size
- Match client risk tolerance and investment objectives
- Ensure some diversification across sectors

OUTPUT FORMAT:
Return a JSON array of exactly {num_tickers} ticker symbols:
["AAPL", "MSFT", "GOOGL", ...]

Only return the JSON array, nothing else.
"""

        try:
            # Use rate-limited API call with o3 model
            def make_call():
                return self.openai_client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    reasoning_effort="high",
                    max_completion_tokens=500
                )

            response = self._rate_limited_api_call(make_call)

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()

            tickers = json.loads(content)

            log = {
                'prompt': prompt,
                'response': content,
                'tickers': tickers,
                'model': 'o3'
            }

            logger.info(f"OpenAI o3 selected {len(tickers)} tickers")
            return tickers, log

        except Exception as e:
            logger.error(f"OpenAI o3 selection failed: {e}")
            # Fallback to default tickers
            fallback = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
                       "JPM", "V", "JNJ", "WMT", "PG", "MA", "HD", "DIS", "BAC", "CSCO", "ADBE", "CRM"]
            return fallback[:num_tickers], {'error': str(e), 'fallback': True}

    def _gemini_select_tickers(
        self,
        challenge_context: str,
        client_profile: Dict[str, Any],
        universe_size: int,
        num_tickers: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Use Gemini 2.5 Pro to select initial tickers."""

        context = self._build_selection_context(challenge_context, client_profile)

        prompt = f"""You are an expert portfolio manager with real-time market intelligence, specializing in discovering high-potential stocks that most investors overlook.

{context}

TASK: Select exactly {num_tickers} stock tickers with EXCEPTIONAL growth potential that match this challenge and client profile.

CRITICAL MISSION - DISCOVER HIDDEN OPPORTUNITIES:
- Your goal is to find stocks with 10x-100x potential, not just safe blue chips
- Market cap is IRRELEVANT - a $300M company can outperform a $300B company
- Actively hunt for:
  * Small-cap disruptors ($300M - $2B) dominating niche markets
  * Mid-cap innovators ($2B - $10B) scaling rapidly
  * Emerging category leaders with explosive revenue growth
  * Recent IPOs showing strong product-market fit
  * Undervalued companies in high-growth sectors
- Priority sectors for discovery:
  * AI/ML Infrastructure & Applications (beyond the obvious mega-caps)
  * Biotech: Gene therapy, CRISPR, precision medicine
  * Clean Energy: Solar, battery tech, hydrogen, carbon capture
  * Fintech: Digital payments, crypto infrastructure, embedded finance
  * SaaS: Vertical-specific software, automation platforms
  * Semiconductors: Specialty chips, quantum computing components
  * Cybersecurity: Zero-trust, cloud security
  * Robotics & Industrial Automation
  * Space Technology & Aerospace Innovation
- Use your knowledge to identify:
  * Companies with 50%+ YoY revenue growth
  * Recent breakouts in strong industry trends
  * Stocks that analysts are just starting to discover
  * Companies with insider buying and institutional accumulation
- AVOID defaulting to AAPL, MSFT, GOOGL unless they're truly the best opportunities
- Match client risk tolerance while maximizing upside potential
- Diversify across sectors and growth stages

OUTPUT FORMAT:
Return a JSON array of exactly {num_tickers} ticker symbols:
["AAPL", "MSFT", "GOOGL", ...]

Only return the JSON array, nothing else.
"""

        try:
            if not self.gemini_model:
                raise ValueError("Gemini model not initialized. Check GEMINI_API_KEY.")

            import google.generativeai as genai

            # Use Gemini with thinking enabled
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )

            content = response.text.strip()

            # Parse JSON response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            if content.startswith('```'):
                content = content.replace('```', '').strip()

            tickers = json.loads(content)

            log = {
                'prompt': prompt,
                'response': content,
                'tickers': tickers,
                'model': 'gemini-2.5-pro'
            }

            logger.info(f"Gemini 2.5 Pro selected {len(tickers)} tickers")
            return tickers, log

        except Exception as e:
            logger.error(f"Gemini selection failed: {e}")
            # Fallback to different default tickers
            fallback = ["COST", "NFLX", "AMD", "ORCL", "INTC", "QCOM", "AMAT", "TXN",
                       "HON", "UNP", "UPS", "RTX", "LMT", "CAT", "DE", "MMM", "GE", "BA", "DHR", "ABT"]
            return fallback[:num_tickers], {'error': str(e), 'fallback': True}

    def _generate_ticker_rationale(
        self,
        ticker: str,
        challenge_context: str,
        client_profile: Dict[str, Any]
    ) -> str:
        """Generate a 4-sentence rationale for why a ticker is strong/beneficial/relevant."""

        context = self._build_selection_context(challenge_context, client_profile)

        prompt = f"""You are analyzing why {ticker} is a strong investment candidate for this specific challenge.

{context}

TASK: Write exactly 4 sentences explaining why {ticker} is:
1. Strong (fundamentals, competitive position)
2. Beneficial (fits portfolio objectives)
3. Relevant (aligns with challenge/client requirements)
4. Strategic (adds value to the portfolio)

Each sentence should be clear, specific, and actionable. Focus on facts and strategic fit.

OUTPUT: Exactly 4 sentences, no introduction, no numbering.
"""

        try:
            # Use rate-limited API call with o3 model
            def make_call():
                return self.openai_client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    reasoning_effort="medium",
                    max_completion_tokens=200
                )

            response = self._rate_limited_api_call(make_call)

            rationale = response.choices[0].message.content.strip()
            logger.info(f"   Generated rationale for {ticker}")
            return rationale

        except Exception as e:
            logger.error(f"   Rationale generation failed for {ticker}: {e}")
            return f"{ticker} is a well-established company with strong market position. It aligns with the investment objectives and risk profile. The stock offers growth potential while maintaining reasonable valuation metrics. Adding this position contributes to portfolio diversification and strategic objectives."

    def _openai_select_top_5(
        self,
        candidates: List[str],
        rationales: Dict[str, str],
        challenge_context: str,
        client_profile: Dict[str, Any]
    ) -> List[str]:
        """Use OpenAI o3 to select top 5 from candidates."""

        context = self._build_selection_context(challenge_context, client_profile)

        # Build candidates list with rationales
        candidates_text = "\n\n".join([
            f"**{ticker}**\n{rationales[ticker]}"
            for ticker in candidates
        ])

        prompt = f"""You are an expert portfolio manager making final stock selections.

{context}

AVAILABLE CANDIDATES ({len(candidates)} stocks):
{candidates_text}

TASK: Select exactly 5 tickers that form the optimal portfolio for this challenge.

SELECTION CRITERIA:
- Best overall fit for challenge objectives
- Strongest alignment with client profile
- Optimal diversification
- Best risk-adjusted return potential
- Strategic portfolio composition

OUTPUT FORMAT:
Return a JSON array of exactly 5 ticker symbols:
["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

Only return the JSON array, nothing else.
"""

        try:
            # Use rate-limited API call with o3 model
            def make_call():
                return self.openai_client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    reasoning_effort="high",
                    max_completion_tokens=200
                )

            response = self._rate_limited_api_call(make_call)

            content = response.choices[0].message.content.strip()

            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()

            top_5 = json.loads(content)
            return top_5[:5]  # Ensure exactly 5

        except Exception as e:
            logger.error(f"Top 5 selection failed: {e}")
            return candidates[:5]  # Fallback to first 5

    def _openai_narrow_to_5(
        self,
        finalists: List[str],
        rationales: Dict[str, str],
        challenge_context: str,
        client_profile: Dict[str, Any]
    ) -> List[str]:
        """Narrow down more than 5 finalists to exactly 5."""

        context = self._build_selection_context(challenge_context, client_profile)

        finalists_text = "\n\n".join([
            f"**{ticker}**\n{rationales[ticker]}"
            for ticker in finalists
        ])

        prompt = f"""You are an expert portfolio manager making the final selection.

{context}

FINALISTS ({len(finalists)} stocks):
{finalists_text}

These {len(finalists)} stocks emerged from multiple selection rounds. You must now select exactly 5 for the final portfolio.

TASK: Select exactly 5 tickers that form the absolute best portfolio.

SELECTION CRITERIA:
- Maximum strategic fit
- Optimal diversification
- Best risk-adjusted returns
- Strongest rationales
- Most complementary positions

OUTPUT FORMAT:
Return a JSON array of exactly 5 ticker symbols:
["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

Only return the JSON array, nothing else.
"""

        try:
            # Use rate-limited API call with o3 model
            def make_call():
                return self.openai_client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    reasoning_effort="high",
                    max_completion_tokens=200
                )

            response = self._rate_limited_api_call(make_call)

            content = response.choices[0].message.content.strip()

            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()

            final_5 = json.loads(content)
            return final_5[:5]

        except Exception as e:
            logger.error(f"Final narrowing failed: {e}")
            return finalists[:5]

    def _build_selection_context(self, challenge_context: str, client_profile: Dict[str, Any]) -> str:
        """Build comprehensive context for AI selection."""

        ips_data = client_profile.get('ips_data', {})

        context = f"""
INVESTMENT CHALLENGE:
{challenge_context}

CLIENT PROFILE:
- Name: {client_profile.get('name', 'N/A')}
- Risk Tolerance: {ips_data.get('risk_tolerance', 'moderate')}
- Time Horizon: {ips_data.get('time_horizon_years', 5)} years
- Investment Objectives: {', '.join(ips_data.get('investment_objectives', []))}
- Target Return: {ips_data.get('target_return_pct', 'N/A')}%
- Max Portfolio Volatility: {ips_data.get('max_portfolio_volatility_pct', 'N/A')}%

CONSTRAINTS:
- Allowed Sectors: {', '.join(ips_data.get('allowed_sectors', ['All']))}
- Prohibited Sectors: {', '.join(ips_data.get('prohibited_sectors', ['None']))}
- Min Position Size: {ips_data.get('min_position_pct', 2)}%
- Max Position Size: {ips_data.get('max_position_pct', 20)}%
- Max Sector Concentration: {ips_data.get('max_sector_pct', 30)}%
"""

        return context
