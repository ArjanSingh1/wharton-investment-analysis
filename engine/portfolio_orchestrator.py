"""
Portfolio Orchestrator
Coordinates all agents and blends scores to generate final recommendations.
Handles position sizing and portfolio construction.
"""

from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.value_agent import ValueAgent
from agents.growth_momentum_agent import GrowthMomentumAgent
from agents.macro_regime_agent import MacroRegimeAgent
from agents.risk_agent import RiskAgent
from agents.sentiment_agent import SentimentAgent
from data.enhanced_data_provider import EnhancedDataProvider
from engine.ai_portfolio_selector import AIPortfolioSelector

logger = logging.getLogger(__name__)


class PortfolioOrchestrator:
    """
    Main orchestration engine for the multi-agent investment system.
    Coordinates data gathering, agent analysis, score blending, and portfolio construction.
    """
    
    def __init__(
        self,
        model_config: Dict[str, Any],
        ips_config: Dict[str, Any],
        enhanced_data_provider: EnhancedDataProvider,
        openai_client=None,
        gemini_api_key=None
    ):
        self.model_config = model_config
        self.ips_config = ips_config
        self.data_provider = enhanced_data_provider
        self.openai_client = openai_client
        self.gemini_api_key = gemini_api_key
        logger.info("Using Enhanced Data Provider with premium fallbacks")
        
        # Initialize agents with their dependencies
        self.agents = {}
        
        # Core analysis agents
        self.agents['value_agent'] = ValueAgent(model_config, openai_client)
        self.agents['growth_momentum_agent'] = GrowthMomentumAgent(model_config, openai_client)
        self.agents['macro_regime_agent'] = MacroRegimeAgent(model_config, openai_client)
        self.agents['risk_agent'] = RiskAgent(model_config, openai_client)
        self.agents['sentiment_agent'] = SentimentAgent(model_config, openai_client)

        # Initialize AI Portfolio Selector
        if openai_client and gemini_api_key:
            self.ai_selector = AIPortfolioSelector(
                openai_client, gemini_api_key, ips_config, model_config
            )
            logger.info("AI Portfolio Selector initialized")
        else:
            self.ai_selector = None
            logger.warning("AI Portfolio Selector not available (missing API clients)")
        
        # Agent weights for score blending - HEAVILY FAVOR UPSIDE POTENTIAL
        # Growth/Momentum is the most important for capturing upside
        agent_weights_config = ips_config.get('agent_weights', {})
        self.agent_weights = {
            'value_agent': agent_weights_config.get('value', 0.20),  # Value for reasonable entry
            'growth_momentum_agent': agent_weights_config.get('growth_momentum', 0.40),  # DOUBLED - Upside potential is KEY
            'macro_regime_agent': agent_weights_config.get('macro_regime', 0.10),  # Reduced - less important than growth
            'risk_agent': agent_weights_config.get('risk', 0.15),  # Reduced - upside > downside protection
            'sentiment_agent': agent_weights_config.get('sentiment', 0.15)  # Market momentum matters
        }
        
        logger.info(f"Portfolio Orchestrator initialized with UPSIDE-FOCUSED weights: {self.agent_weights}")
    
    def analyze_single_stock(
        self,
        ticker: str,
        analysis_date: str,
        existing_portfolio: List[Dict] = None,
        agent_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single stock using all agents.
        
        Returns complete analysis with scores, rationale, and recommendations.
        """
        logger.info(f"Starting comprehensive analysis for {ticker} as of {analysis_date}")

        # Phase durations based on measured runs (used for smooth progress interpolation)
        # Phase 1: Data gathering 0-42% (~35s, 42% of total time)
        # Phase 2: Agent analysis 42-98% (~48s, 56% of total time, 5 agents with article fetching)
        # Phase 3: Blending/finalization 98-100% (~1s, 2% of total time)
        PHASE_DATA_GATHER = (0, 42)    # 0% to 42%
        PHASE_AGENTS = (42, 98)         # 42% to 98%
        PHASE_FINALIZE = (98, 100)      # 98% to 100%

        # Default phase durations (seconds) - calibrated from real test runs
        DEFAULT_DATA_GATHER_DURATION = 35
        DEFAULT_AGENTS_DURATION = 48
        DEFAULT_FINALIZE_DURATION = 1

        analysis_start_time = time.time()

        # Smooth progress tracking with background interpolation
        _progress_lock = threading.Lock()
        _current_progress = {'pct': 0, 'message': f'Starting analysis for {ticker}...', 'stop': False}

        def update_progress(message, progress_pct):
            """Update progress bar and status text."""
            import streamlit as st

            try:
                if not hasattr(st, 'session_state') or not hasattr(st.session_state, 'analysis_progress'):
                    return

                progress = st.session_state.analysis_progress

                with _progress_lock:
                    _current_progress['pct'] = progress_pct
                    _current_progress['message'] = message

                # Update progress bar
                if progress.get('progress_bar'):
                    progress['progress_bar'].progress(progress_pct / 100.0)

                # Update status text with time remaining
                if progress.get('status_text'):
                    time_display = ""
                    if progress.get('start_time') and progress_pct >= 3:
                        elapsed = time.time() - progress['start_time']
                        time_display = PortfolioOrchestrator._estimate_time_remaining(
                            elapsed, progress_pct, st.session_state
                        )

                    progress['status_text'].text(f"{message}{time_display}")

                time.sleep(0.03)

            except Exception as e:
                logger.error(f"Progress update failed: {e}")

        def _smooth_progress_interpolator(start_pct, end_pct, duration_estimate, message_prefix):
            """
            Background thread that smoothly advances progress bar from start_pct to end_pct
            over duration_estimate seconds. Stops when _current_progress['stop'] is True
            or when actual progress exceeds the interpolated value.
            """
            import streamlit as st

            step_interval = 0.5  # Update every 500ms
            steps = max(1, int(duration_estimate / step_interval))
            pct_per_step = (end_pct - start_pct) / steps

            current_pct = start_pct
            for i in range(steps):
                with _progress_lock:
                    if _current_progress['stop'] or _current_progress['pct'] >= end_pct:
                        return
                    # Only advance if actual progress hasn't jumped ahead
                    if _current_progress['pct'] < current_pct:
                        _current_progress['pct'] = current_pct

                try:
                    if not hasattr(st, 'session_state') or not hasattr(st.session_state, 'analysis_progress'):
                        return
                    progress = st.session_state.analysis_progress
                    if progress.get('progress_bar'):
                        progress['progress_bar'].progress(current_pct / 100.0)
                    if progress.get('status_text'):
                        elapsed = time.time() - analysis_start_time
                        time_display = PortfolioOrchestrator._estimate_time_remaining(
                            elapsed, current_pct, getattr(st, 'session_state', None)
                        )
                        progress['status_text'].text(f"{message_prefix}{time_display}")
                except Exception:
                    pass

                current_pct += pct_per_step
                time.sleep(step_interval)
        
        # Set agent weights for this analysis if provided
        if agent_weights:
            # Map the simplified names to agent names used in the system
            weight_mapping = {
                'value': 'value_agent',
                'growth_momentum': 'growth_momentum_agent',
                'macro_regime': 'macro_regime_agent',
                'risk': 'risk_agent',
                'sentiment': 'sentiment_agent'
            }
            
            # Apply weights
            original_weights = self.agent_weights.copy()
            for simplified_name, weight in agent_weights.items():
                agent_name = weight_mapping.get(simplified_name, simplified_name)
                if agent_name in self.agent_weights:
                    self.agent_weights[agent_name] = weight
        
        # 1. Gather all data (Phase 1: 0-30%)
        update_progress(f"Fetching data for {ticker} from multiple sources...", 3)

        # Start smooth interpolator for data gathering phase
        data_gather_duration = DEFAULT_DATA_GATHER_DURATION
        import streamlit as st
        if hasattr(st, 'session_state'):
            hist = getattr(st.session_state, 'analysis_phase_times', {})
            if 'data_gather' in hist and len(hist['data_gather']) > 0:
                data_gather_duration = sum(hist['data_gather']) / len(hist['data_gather'])

        interpolator_thread = threading.Thread(
            target=_smooth_progress_interpolator,
            args=(3, 40, data_gather_duration, f"Gathering data for {ticker}..."),
            daemon=True
        )
        interpolator_thread.start()

        data_gather_start = time.time()
        try:
            data = self._gather_data(ticker, analysis_date, existing_portfolio)
        except Exception as e:
            logger.error(f"Error gathering data for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            with _progress_lock:
                _current_progress['stop'] = True
            return {
                'ticker': ticker,
                'error': f'Data gathering failed: {str(e)}',
                'fundamentals': {},
                'price_history': {},
                'agent_results': {},
                'agent_scores': {},
                'agent_rationales': {},
                'blended_score': 0,
                'final_score': 0,
                'eligible': False
            }

        # Stop interpolator and snap to 30%
        with _progress_lock:
            _current_progress['stop'] = True
        data_gather_elapsed = time.time() - data_gather_start

        # Record phase timing for future estimates
        try:
            if hasattr(st, 'session_state'):
                if not hasattr(st.session_state, 'analysis_phase_times'):
                    st.session_state.analysis_phase_times = {'data_gather': [], 'agents': []}
                phase_times = st.session_state.analysis_phase_times
                phase_times.setdefault('data_gather', []).append(data_gather_elapsed)
                # Keep last 5 runs
                if len(phase_times['data_gather']) > 5:
                    phase_times['data_gather'] = phase_times['data_gather'][-5:]
        except Exception:
            pass

        update_progress(f"Data gathered for {ticker} in {data_gather_elapsed:.0f}s", 42)
        
        if not data or not data.get('fundamentals'):
            logger.warning(f"No fundamental data for {ticker}")
            update_progress(f"No fundamental data found for {ticker}", 10)
            return {
                'ticker': ticker, 
                'error': 'No data available',
                'fundamentals': {},
                'price_history': {},
                'agent_results': {},
                'agent_scores': {},
                'agent_rationales': {},
                'blended_score': 0,
                'final_score': 0,
                'eligible': False
            }
        
        # Show specific extracted values
        fundamentals = data.get('fundamentals', {})
        price = fundamentals.get('price', 'N/A')
        eps = fundamentals.get('eps', 'N/A')
        pe_ratio = fundamentals.get('pe_ratio', 'N/A')
        market_cap = fundamentals.get('market_cap', 'N/A')
        
        # Format market cap for readability
        if isinstance(market_cap, (int, float)) and market_cap > 0:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.1f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.1f}B"
            elif market_cap >= 1e6:
                market_cap_str = f"${market_cap/1e6:.1f}M"
            else:
                market_cap_str = f"${market_cap:,.0f}"
        else:
            market_cap_str = "N/A"
        
        update_progress(f"Data ready: ${price} price, {pe_ratio} P/E, {market_cap_str} mkt cap", 42)

        # 2. Phase 2: Run all agents (42-98%)
        agent_results = {}
        agent_count = 0
        total_agents = len(self.agents)
        agent_phase_start = time.time()

        # Estimate per-agent duration for smooth interpolation
        avg_agent_duration = DEFAULT_AGENTS_DURATION / total_agents  # ~9.6s per agent
        try:
            if hasattr(st, 'session_state'):
                hist = getattr(st.session_state, 'analysis_phase_times', {})
                if 'agents' in hist and len(hist['agents']) > 0:
                    avg_agent_duration = (sum(hist['agents']) / len(hist['agents'])) / total_agents
        except Exception:
            pass

        agent_labels_map = {
            'value_agent': 'Value',
            'growth_momentum_agent': 'Growth/Momentum',
            'macro_regime_agent': 'Macro Regime',
            'risk_agent': 'Risk',
            'sentiment_agent': 'Sentiment'
        }

        for agent_name, agent in self.agents.items():
            agent_count += 1
            # Calculate progress range for this agent (42-98%, evenly divided)
            agent_pct_range = PHASE_AGENTS[1] - PHASE_AGENTS[0]  # 56
            agent_start_pct = PHASE_AGENTS[0] + ((agent_count - 1) / total_agents) * agent_pct_range
            agent_end_pct = PHASE_AGENTS[0] + (agent_count / total_agents) * agent_pct_range
            agent_label = agent_labels_map.get(agent_name, agent_name.replace('_agent', '').title())

            # Descriptive message for this agent
            if 'value' in agent_name.lower():
                pe_display = f"{pe_ratio:.1f}" if isinstance(pe_ratio, (int, float)) else str(pe_ratio)
                agent_msg = f"{agent_label} Agent: Evaluating P/E ({pe_display}), dividend yield, intrinsic value..."
            elif 'growth' in agent_name.lower():
                agent_msg = f"{agent_label} Agent: Analyzing earnings growth, revenue momentum, price trends..."
            elif 'macro' in agent_name.lower():
                sector = data['fundamentals'].get('sector', 'Unknown')
                agent_msg = f"{agent_label} Agent: Assessing {sector} sector in current macro regime..."
            elif 'risk' in agent_name.lower():
                beta_val = data['fundamentals'].get('beta', 'N/A')
                beta_display = f"{beta_val:.2f}" if isinstance(beta_val, (int, float)) else str(beta_val)
                agent_msg = f"{agent_label} Agent: Computing volatility, beta ({beta_display}), drawdown..."
            elif 'sentiment' in agent_name.lower():
                agent_msg = f"{agent_label} Agent: Fetching news articles and analyzing sentiment..."
            else:
                agent_msg = f"{agent_label} Agent: Running analysis..."

            update_progress(agent_msg, int(agent_start_pct))

            # Start smooth interpolator for this agent
            with _progress_lock:
                _current_progress['stop'] = False
            agent_interpolator = threading.Thread(
                target=_smooth_progress_interpolator,
                args=(agent_start_pct + 1, agent_end_pct - 1, avg_agent_duration, agent_msg),
                daemon=True
            )
            agent_interpolator.start()

            try:
                result = agent.analyze(ticker, data)
                agent_results[agent_name] = result

                # Stop interpolator
                with _progress_lock:
                    _current_progress['stop'] = True

                # Log results and show completion with score
                score = result.get('score')
                if score is None:
                    score = 50
                    result['score'] = 50
                logger.info(f"{agent_name}: {score:.1f} - {result['rationale']}")

                # Show agent completion
                if 'sentiment' in agent_name.lower():
                    num_articles = result.get('details', {}).get('num_articles', 0)
                    completion_msg = f"{agent_label} Agent: {num_articles} articles analyzed, score {score:.0f}/100"
                else:
                    completion_msg = f"{agent_label} Agent complete: {score:.0f}/100"
                update_progress(completion_msg, int(agent_end_pct))
            except Exception as e:
                logger.error(f"Error in {agent_name} for {ticker}: {e}")
                agent_results[agent_name] = {
                    'score': 50,
                    'rationale': f'Analysis failed: {str(e)}',
                    'details': {}
                }
        
        # 3. Phase 3: Blend scores and finalize (98-100%)
        agent_phase_elapsed = time.time() - agent_phase_start

        # Record agent phase timing
        try:
            if hasattr(st, 'session_state'):
                if not hasattr(st.session_state, 'analysis_phase_times'):
                    st.session_state.analysis_phase_times = {'data_gather': [], 'agents': []}
                phase_times = st.session_state.analysis_phase_times
                phase_times.setdefault('agents', []).append(agent_phase_elapsed)
                if len(phase_times['agents']) > 5:
                    phase_times['agents'] = phase_times['agents'][-5:]

                # Also record total time for overall ETA
                total_elapsed = time.time() - analysis_start_time
                if not hasattr(st.session_state, 'analysis_times'):
                    st.session_state.analysis_times = []
                st.session_state.analysis_times.append(total_elapsed)
                if len(st.session_state.analysis_times) > 5:
                    st.session_state.analysis_times = st.session_state.analysis_times[-5:]
        except Exception:
            pass

        update_progress(f"Blending agent scores with configured weights...", 98)
        blended_score = self._blend_scores(agent_results)

        recommendation = self._generate_recommendation(blended_score)
        update_progress(f"Analysis complete: {blended_score:.1f}/100 - {recommendation}", 99)
        final_score = blended_score

        total_time = time.time() - analysis_start_time
        update_progress(f"Analysis complete: {final_score:.1f}/100 ({total_time:.0f}s total)", 100)

        # Restore original weights if they were changed
        if agent_weights:
            self.agent_weights = original_weights

        # Extract agent scores and rationales for backward compatibility
        agent_scores = {agent_name: (result.get('score') or 50) for agent_name, result in agent_results.items()}
        agent_rationales = {agent_name: result.get('rationale', 'Analysis not available') for agent_name, result in agent_results.items()}

        return {
            'ticker': ticker,
            'analysis_date': analysis_date,
            'agent_results': agent_results,
            'agent_scores': agent_scores,
            'agent_rationales': agent_rationales,
            'blended_score': blended_score,
            'final_score': final_score,
            'eligible': True,
            'recommendation': self._generate_recommendation(final_score),
            'rationale': self._generate_comprehensive_rationale_simple(ticker, agent_results, final_score, data),
            'fundamentals': data.get('fundamentals', {}),
            'price_history': data.get('price_history', {})
        }
    
    def analyze_stock(
        self,
        ticker: str,
        analysis_date: str = None,
        existing_portfolio: List[Dict] = None,
        agent_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Alias for analyze_single_stock method for backward compatibility.
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Date for analysis (defaults to today)
            existing_portfolio: Existing portfolio for context
            agent_weights: Custom agent weights for this analysis
            
        Returns:
            Complete analysis results
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        return self.analyze_single_stock(
            ticker=ticker,
            analysis_date=analysis_date,
            existing_portfolio=existing_portfolio,
            agent_weights=agent_weights
        )
    
    @staticmethod
    def _estimate_time_remaining(elapsed: float, progress_pct: float, session_state=None) -> str:
        """
        Phase-aware time remaining estimation.

        Uses known phase boundaries and durations to calculate remaining time
        based on which phase we're currently in, rather than linear extrapolation.

        Phase allocations (calibrated from real test runs):
          0-42%:  Data gathering (~35s)
          42-98%: Agent analysis (~48s)
          98-100%: Finalization (~1s)
        """
        if progress_pct < 3 or elapsed < 1.0:
            return ""

        # Phase definitions: (start_pct, end_pct, default_duration_seconds)
        phases = [
            (0, 42, 35),    # Data gathering
            (42, 98, 48),   # Agent analysis
            (98, 100, 1),   # Finalization
        ]

        # Override defaults with historical data if available
        if session_state is not None:
            hist = getattr(session_state, 'analysis_phase_times', {})
            if hist.get('data_gather') and len(hist['data_gather']) > 0:
                phases[0] = (0, 42, sum(hist['data_gather']) / len(hist['data_gather']))
            if hist.get('agents') and len(hist['agents']) > 0:
                phases[1] = (42, 98, sum(hist['agents']) / len(hist['agents']))

        # Find current phase and calculate remaining time
        remaining = 0.0
        found_current = False

        for start_pct, end_pct, duration in phases:
            if not found_current:
                if progress_pct < end_pct:
                    # We're in this phase
                    found_current = True
                    phase_progress = (progress_pct - start_pct) / (end_pct - start_pct) if end_pct > start_pct else 1.0
                    phase_progress = max(0.0, min(1.0, phase_progress))
                    remaining += duration * (1.0 - phase_progress)
                # else: we've passed this phase, skip it
            else:
                # Future phase - add full duration
                remaining += duration

        if not found_current:
            return ""

        # EMA smoothing to prevent display jumps
        if session_state is not None:
            prev = getattr(session_state, '_eta_previous', None)
            if prev is not None and prev > 0:
                alpha = 0.4
                # Cap increases to 15% of previous to avoid upward jumps
                if remaining > prev * 1.15:
                    remaining = prev * 1.15
                remaining = alpha * remaining + (1 - alpha) * prev
            try:
                session_state._eta_previous = remaining
            except Exception:
                pass

        # Ensure non-negative
        if remaining <= 0:
            return ""

        # Format
        secs = max(1, int(remaining))
        if secs < 60:
            return f" ~{secs}s"
        else:
            mins = secs // 60
            s = secs % 60
            return f" ~{mins}m {s}s"

    def _blend_scores(self, agent_results: Dict[str, Dict]) -> float:
        """
        Blend agent scores using configured weights with UPSIDE POTENTIAL MULTIPLIER.
        
        Upside potential is THE MOST IMPORTANT factor. We boost scores based on:
        - Growth momentum (earnings growth, revenue growth, price momentum)
        - Distance from 52-week high (more room to run)
        - Positive sentiment (market recognition of upside)
        """
        # Calculate base weighted score
        total_score = 0
        total_weight = 0
        
        for agent_name, weight in self.agent_weights.items():
            if agent_name in agent_results:
                score = agent_results[agent_name].get('score') or 50
                total_score += score * weight
                total_weight += weight
        
        base_score = total_score / total_weight if total_weight > 0 else 50
        
        # ========== UPSIDE POTENTIAL MULTIPLIER ==========
        # This is THE KEY: boost stocks with high upside potential
        
        upside_multiplier = 1.0  # Start at neutral
        upside_factors = []
        
        # Factor 1: Growth/Momentum score (40% weight - most important!)
        if 'growth_momentum_agent' in agent_results:
            growth_score = agent_results['growth_momentum_agent'].get('score', 50)
            if growth_score >= 80:
                upside_multiplier += 0.15  # +15% boost for exceptional growth
                upside_factors.append(f"Exceptional growth ({growth_score:.0f}/100) → +15% boost")
            elif growth_score >= 70:
                upside_multiplier += 0.10  # +10% boost for strong growth
                upside_factors.append(f"Strong growth ({growth_score:.0f}/100) → +10% boost")
            elif growth_score >= 60:
                upside_multiplier += 0.05  # +5% boost for good growth
                upside_factors.append(f"Good growth ({growth_score:.0f}/100) → +5% boost")
            elif growth_score < 40:
                upside_multiplier -= 0.05  # -5% penalty for weak growth
                upside_factors.append(f"Weak growth ({growth_score:.0f}/100) → -5% penalty")
        
        # Factor 2: Sentiment (market recognizing upside)
        if 'sentiment_agent' in agent_results:
            sentiment_score = agent_results['sentiment_agent'].get('score') or 50
            if sentiment_score >= 75:
                upside_multiplier += 0.08  # +8% boost for very positive sentiment
                upside_factors.append(f"Very positive sentiment ({sentiment_score:.0f}/100) → +8% boost")
            elif sentiment_score >= 65:
                upside_multiplier += 0.05  # +5% boost for positive sentiment
                upside_factors.append(f"Positive sentiment ({sentiment_score:.0f}/100) → +5% boost")
        
        # Factor 3: Value (reasonable entry point amplifies upside)
        if 'value_agent' in agent_results:
            value_score = agent_results['value_agent'].get('score', 50)
            if value_score >= 75:
                upside_multiplier += 0.05  # +5% boost - good value = more upside runway
                upside_factors.append(f"Attractive valuation ({value_score:.0f}/100) → +5% boost")
        
        # Factor 4: Penalize very high risk (extreme risk reduces realizable upside)
        if 'risk_agent' in agent_results:
            risk_score = agent_results['risk_agent'].get('score', 50)
            if risk_score < 30:  # Very high risk
                upside_multiplier -= 0.10  # -10% penalty for extreme risk
                upside_factors.append(f"Extreme risk ({risk_score:.0f}/100) → -10% penalty")
        
        # Apply the multiplier (cap at 1.35 to prevent over-inflation)
        upside_multiplier = min(upside_multiplier, 1.35)
        upside_multiplier = max(upside_multiplier, 0.85)  # Floor at 0.85
        
        final_score = base_score * upside_multiplier
        
        # Log the upside calculation for transparency
        if upside_factors:
            logger.info(f"UPSIDE MULTIPLIER APPLIED: {upside_multiplier:.2f}x")
            logger.info(f"   Base Score: {base_score:.1f}")
            logger.info(f"   Upside Factors:")
            for factor in upside_factors:
                logger.info(f"     - {factor}")
            logger.info(f"   Final Score: {final_score:.1f} (boosted by {((upside_multiplier - 1) * 100):.0f}%)")
        
        return final_score
    
    def _generate_recommendation(self, score: float) -> str:
        """Generate investment recommendation based on score."""
        if score >= 80:
            return "STRONG BUY"
        elif score >= 70:
            return "BUY"
        elif score >= 60:
            return "HOLD"
        elif score >= 40:
            return "WEAK HOLD"
        else:
            return "SELL"
    
    def _generate_comprehensive_rationale_simple(self, ticker: str, agent_results: Dict, final_score: float, data: Dict) -> str:
        """Generate comprehensive investment rationale."""
        fundamentals = data.get('fundamentals', {})
        rationale_parts = []

        rationale_parts.append("=" * 80)
        rationale_parts.append(f"COMPREHENSIVE INVESTMENT ANALYSIS: {ticker}")
        rationale_parts.append("=" * 80)

        company_name = fundamentals.get('name', ticker)
        sector = fundamentals.get('sector', 'Unknown')
        rationale_parts.append(f"\nCOMPANY OVERVIEW:")
        rationale_parts.append(f"Company: {company_name}")
        rationale_parts.append(f"Sector: {sector}")

        rationale_parts.append(f"\nKEY FINANCIAL METRICS:")
        price = fundamentals.get('price')
        if price:
            rationale_parts.append(f"Current Price: ${price:.2f}")
        market_cap = fundamentals.get('market_cap')
        if market_cap:
            if market_cap >= 1e12:
                rationale_parts.append(f"Market Cap: ${market_cap/1e12:.2f}T")
            elif market_cap >= 1e9:
                rationale_parts.append(f"Market Cap: ${market_cap/1e9:.2f}B")
            else:
                rationale_parts.append(f"Market Cap: ${market_cap/1e6:.2f}M")
        pe_ratio = fundamentals.get('pe_ratio')
        if pe_ratio:
            rationale_parts.append(f"P/E Ratio: {pe_ratio:.2f}")
        beta = fundamentals.get('beta')
        if beta:
            rationale_parts.append(f"Beta: {beta:.2f}")
        dividend_yield = fundamentals.get('dividend_yield')
        if dividend_yield:
            rationale_parts.append(f"Dividend Yield: {dividend_yield*100:.2f}%")

        rationale_parts.append(f"\nMULTI-AGENT ANALYSIS:")
        rationale_parts.append("=" * 80)
        agent_order = ['value_agent', 'growth_momentum_agent', 'macro_regime_agent', 'risk_agent', 'sentiment_agent']
        agent_labels = {
            'value_agent': 'VALUE ANALYSIS',
            'growth_momentum_agent': 'GROWTH & MOMENTUM ANALYSIS',
            'macro_regime_agent': 'MACROECONOMIC ANALYSIS',
            'risk_agent': 'RISK ASSESSMENT',
            'sentiment_agent': 'MARKET SENTIMENT ANALYSIS'
        }
        for agent_name in agent_order:
            if agent_name in agent_results:
                result = agent_results[agent_name]
                score = result.get('score') or 50
                rationale = result.get('rationale', 'Analysis not available')
                rationale_parts.append(f"\n{agent_labels.get(agent_name, agent_name.upper())}:")
                rationale_parts.append(f"Score: {score:.2f}/100")
                rationale_parts.append(f"{rationale}")
                rationale_parts.append("-" * 80)

        rationale_parts.append(f"\nFINAL RECOMMENDATION:")
        rationale_parts.append(f"Final Score: {final_score:.2f}/100")
        rationale_parts.append("=" * 80)

        return '\n'.join(rationale_parts)

    def _check_ips_eligibility(self, ticker: str, fundamentals: dict, blended_score: float) -> bool:
        """Check if a stock meets basic IPS eligibility constraints."""
        ips = self.ips_config

        # Check minimum price
        price = fundamentals.get('price', 0)
        min_price = ips.get('universe', {}).get('min_price', 1.0)
        if price and price < min_price:
            return False

        # Check minimum market cap
        market_cap = fundamentals.get('market_cap', 0)
        min_market_cap = ips.get('universe', {}).get('min_market_cap', 0)
        if market_cap and market_cap < min_market_cap:
            return False

        # Check excluded sectors
        sector = fundamentals.get('sector', '')
        excluded_sectors = ips.get('exclusions', {}).get('sectors', [])
        if sector and excluded_sectors:
            if sector.lower() in [s.lower() for s in excluded_sectors]:
                return False

        # Check beta range
        beta = fundamentals.get('beta')
        if beta:
            beta_min = ips.get('portfolio_constraints', {}).get('beta_min', 0)
            beta_max = ips.get('portfolio_constraints', {}).get('beta_max', 999)
            if beta < beta_min or beta > beta_max:
                return False

        return True
    
    def _gather_data(
        self,
        ticker: str,
        analysis_date: str,
        existing_portfolio: Dict = None
    ) -> Dict[str, Any]:
        """Gather all necessary data for analysis using parallel API calls for speed."""
        # Calculate date range (1 year lookback) - ensure no future dates
        end_date = analysis_date
        start_date = pd.to_datetime(analysis_date) - pd.DateOffset(years=1)
        start_date = start_date.strftime('%Y-%m-%d')

        # Ensure we don't use future dates that break Yahoo Finance
        today = datetime.now().date()
        if pd.to_datetime(end_date).date() > today:
            end_date = today.strftime('%Y-%m-%d')
            start_date = (pd.to_datetime(today) - pd.DateOffset(years=1)).strftime('%Y-%m-%d')

        data = {
            'ticker': ticker,
            'analysis_date': analysis_date,
        }

        benchmark = self.ips_config.get('universe', {}).get('benchmark', '^GSPC')

        # PARALLEL DATA GATHERING - Run all 3 API calls simultaneously
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            # Task 1: Get fundamentals (API calls - slowest, ~30-40s)
            if hasattr(self.data_provider, 'get_fundamentals_enhanced'):
                futures['fundamentals'] = executor.submit(
                    self.data_provider.get_fundamentals_enhanced, ticker
                )
            else:
                futures['fundamentals'] = executor.submit(
                    self.data_provider.get_fundamentals, ticker
                )

            # Task 2: Get price history (Yahoo/Polygon API - medium, ~3-5s)
            if hasattr(self.data_provider, 'get_price_history_enhanced'):
                futures['price_history'] = executor.submit(
                    self.data_provider.get_price_history_enhanced,
                    ticker, start_date, end_date
                )
            else:
                futures['price_history'] = executor.submit(
                    self.data_provider.get_price_history,
                    ticker, start_date, end_date
                )

            # Task 3: Generate benchmark data (synthetic - fast, <1s)
            futures['benchmark'] = executor.submit(
                self._create_benchmark_data, benchmark, start_date, end_date
            )

            # Collect results using as_completed for real parallel processing
            future_to_name = {v: k for k, v in futures.items()}
            for future in as_completed(futures.values()):
                name = future_to_name[future]
                try:
                    result = future.result()
                    if name == 'fundamentals':
                        data['fundamentals'] = result
                        if result:
                            logger.info(f"ORCHESTRATOR RECEIVED FUNDAMENTALS FOR {ticker}:")
                            logger.info(f"   price: {result.get('price')} pe_ratio: {result.get('pe_ratio')} beta: {result.get('beta')}")
                            logger.info(f"   data_sources: {result.get('data_sources')}")
                    elif name == 'price_history':
                        data['_price_history_raw'] = result
                    elif name == 'benchmark':
                        data['benchmark_history'] = result
                    logger.info(f"Data task '{name}' completed for {ticker}")
                except Exception as e:
                    logger.error(f"Failed to get {name} for {ticker}: {e}")
                    if name == 'fundamentals':
                        data['fundamentals'] = {}
                    elif name == 'price_history':
                        data['_price_history_raw'] = None
                    elif name == 'benchmark':
                        data['benchmark_history'] = pd.DataFrame()

        # Process price history (may depend on fundamentals result)
        if data.get('fundamentals', {}).get('source') == 'comprehensive_enhanced':
            data['price_history'] = self._extract_price_history_from_fundamentals(data['fundamentals'])
        elif data.get('_price_history_raw') is not None:
            data['price_history'] = data['_price_history_raw']
        elif data.get('fundamentals'):
            data['price_history'] = self._extract_price_history_from_fundamentals(data['fundamentals'])
        else:
            data['price_history'] = pd.DataFrame()
        data.pop('_price_history_raw', None)

        if 'benchmark_history' not in data:
            data['benchmark_history'] = pd.DataFrame()

        # Add existing portfolio for risk analysis
        data['existing_portfolio'] = existing_portfolio or []

        return data
    
    def _extract_price_history_from_fundamentals(self, fundamentals: Dict) -> pd.DataFrame:
        """Extract/create price history from fundamentals data for synthetic analysis."""
        # This is a simplified synthetic price history for analysis
        # In a real implementation, you'd extract this from the comprehensive data
        current_price = fundamentals.get('price', 100)
        week_52_high = fundamentals.get('week_52_high', current_price * 1.2)
        week_52_low = fundamentals.get('week_52_low', current_price * 0.8)
        
        # Create synthetic daily data for the past year
        dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq='D')
        
        # Generate synthetic price movement between 52-week range
        np.random.seed(42)  # For reproducible results
        price_range = np.linspace(week_52_low, week_52_high, 252)
        noise = np.random.normal(0, current_price * 0.02, 252)  # 2% daily volatility
        synthetic_prices = price_range + noise
        
        # Ensure current price is the last price
        synthetic_prices[-1] = current_price
        
        # Create the DataFrame
        df = pd.DataFrame({
            'Date': dates,
            'Close': synthetic_prices,
            'High': synthetic_prices * 1.01,
            'Low': synthetic_prices * 0.99,
            'Volume': np.random.randint(1000000, 5000000, 252)
        }).set_index('Date')
        
        # Add Returns column that the risk agent expects
        df['Returns'] = df['Close'].pct_change()
        
        return df
    
    def _create_benchmark_data(self, benchmark_ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Create synthetic benchmark data to avoid API issues."""
        # Create simple synthetic S&P 500 data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate synthetic benchmark returns with realistic characteristics
        np.random.seed(42)  # Reproducible
        daily_returns = np.random.normal(0.0005, 0.01, len(dates))  # ~0.05% daily return, 1% volatility
        
        # Start at a reasonable level (e.g., 4000 for S&P 500)
        start_price = 4000
        prices = [start_price]
        
        for return_rate in daily_returns[1:]:
            prices.append(prices[-1] * (1 + return_rate))
        
        # Create the DataFrame
        df = pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'High': [p * 1.005 for p in prices],
            'Low': [p * 0.995 for p in prices],
            'Volume': np.random.randint(3000000000, 5000000000, len(dates))
        }).set_index('Date')
        
        # Add Returns column that the risk agent expects
        df['Returns'] = df['Close'].pct_change()
        
        return df
    
    def recommend_portfolio(
        self,
        challenge_context: str = None,
        tickers: List[str] = None,
        num_positions: int = 5,
        analysis_date: str = None,
        universe_size: int = 5000
    ) -> Dict[str, Any]:
        """
        Generate portfolio recommendations using AI-powered ticker selection.
        
        Args:
            challenge_context: Description of investment challenge/goal
            tickers: Optional manual list of tickers (bypasses AI selection)
            num_positions: Target number of positions
            analysis_date: Date for analysis
            universe_size: Size of stock universe to consider (default: 5000 for broad coverage)
        
        Returns:
            Complete portfolio recommendation with analysis
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Starting Portfolio Recommendation - {num_positions} positions")
        
        # If no challenge context provided, use default
        if challenge_context is None:
            challenge_context = """
            Generate an optimal diversified portfolio that maximizes risk-adjusted returns 
            while adhering to the Investment Policy Statement constraints.
            Focus on high-quality companies with strong fundamentals and growth potential.
            """
        
        # Build client profile for AI selection
        client_profile = {
            'name': 'Portfolio User',
            'ips_data': self.ips_config,
            'profile_text': challenge_context
        }
        
        # Stage 1: Get tickers (either AI-selected or manual)
        if tickers is None:
            if self.ai_selector is None:
                logger.error("AI Portfolio Selector not available")
                raise ValueError("AI Portfolio Selector not initialized. Check OpenAI and Gemini API keys.")
            
            logger.info(f"Running AI-powered ticker selection (universe: {universe_size})...")
            selection_result = self.ai_selector.select_portfolio_tickers(
                challenge_context=challenge_context,
                client_profile=client_profile,
                universe_size=universe_size
            )
            
            selected_tickers = selection_result['final_tickers']
            ticker_rationales = selection_result['ticker_rationales']
            all_candidates = selection_result['all_candidates']
            selection_log = selection_result['session_log']
            
            logger.info(f"AI selected {len(selected_tickers)} tickers: {', '.join(selected_tickers)}")
        else:
            # Manual ticker list provided
            selected_tickers = tickers[:num_positions]
            ticker_rationales = {t: "Manually selected ticker" for t in selected_tickers}
            all_candidates = selected_tickers
            selection_log = {'manual_selection': True, 'tickers': selected_tickers}
            logger.info(f"Using manual ticker list: {', '.join(selected_tickers)}")
        
        # Stage 2: Run full analysis on each ticker
        logger.info(f"Running comprehensive analysis on {len(selected_tickers)} tickers...")
        
        portfolio_analyses = []
        for i, ticker in enumerate(selected_tickers, 1):
            logger.info(f"   → Analyzing {i}/{len(selected_tickers)}: {ticker}")
            
            try:
                analysis = self.analyze_single_stock(
                    ticker=ticker,
                    analysis_date=analysis_date,
                    existing_portfolio=portfolio_analyses
                )
                
                # Add AI rationale if available
                if ticker in ticker_rationales:
                    analysis['ai_rationale'] = ticker_rationales[ticker]
                
                portfolio_analyses.append(analysis)
                logger.info(f"   {ticker}: Score {analysis['final_score']:.1f}")
                
            except Exception as e:
                logger.error(f"   Analysis failed for {ticker}: {e}")
                continue
        
        # Stage 3: Filter and construct portfolio
        logger.info("Constructing portfolio from analyzed stocks...")
        
        # Sort by final score
        portfolio_analyses.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        # Take top N positions
        portfolio_stocks = portfolio_analyses[:num_positions]
        
        # Stage 4: Calculate position sizes (equal weight for now)
        equal_weight = 100.0 / len(portfolio_stocks) if portfolio_stocks else 0
        
        portfolio = []
        for stock in portfolio_stocks:
            portfolio.append({
                'ticker': stock['ticker'],
                'name': stock['fundamentals'].get('name', stock['ticker']),
                'sector': stock['fundamentals'].get('sector', 'Unknown'),
                'final_score': stock['final_score'],
                'blended_score': stock['blended_score'],
                'eligible': True,
                'target_weight_pct': equal_weight,
                'rationale': stock.get('ai_rationale', 'See comprehensive analysis'),
                'recommendation': stock['recommendation'],
                'analysis': stock
            })
        
        # Stage 5: Calculate portfolio summary
        total_weight = sum(p['target_weight_pct'] for p in portfolio)
        avg_score = sum(p['final_score'] for p in portfolio) / len(portfolio) if portfolio else 0
        
        # Sector allocation
        sector_exposure = {}
        for p in portfolio:
            sector = p['sector']
            weight = p['target_weight_pct']
            sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
        
        summary = {
            'num_positions': len(portfolio),
            'total_weight_pct': total_weight,
            'avg_score': avg_score,
            'sector_exposure': sector_exposure,
            'challenge_context': challenge_context,
            'selection_method': 'AI-powered' if tickers is None else 'Manual'
        }
        
        logger.info(f"Portfolio constructed: {len(portfolio)} positions, Avg Score: {avg_score:.1f}")
        
        return {
            'portfolio': portfolio,
            'summary': summary,
            'analysis_date': analysis_date,
            'all_candidates': all_candidates if tickers is None else selected_tickers,
            'selection_log': selection_log,
            'eligible_count': len(portfolio_analyses),
            'total_analyzed': len(portfolio_analyses),
            'all_analyses': portfolio_analyses  # Include ALL analyzed stocks for QA archive
        }