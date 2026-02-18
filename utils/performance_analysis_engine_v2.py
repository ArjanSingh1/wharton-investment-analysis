"""
Performance Analysis Engine V2 - Robust & Fast
Completely rebuilt for reliability, speed, and usefulness.

Key Improvements:
- Async-friendly with regular progress updates
- Fast data fetching with intelligent caching
- Resilient error handling
- Actionable insights
- Simple, maintainable code
- Dynamic time estimation based on actual performance
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StockMovement:
    """Simple, focused data structure for stock movements."""
    ticker: str
    price_change_pct: float
    start_price: float
    end_price: float
    start_date: str
    end_date: str
    magnitude: str  # "significant" (5-10%), "major" (10-20%), "extreme" (>20%)
    sector: Optional[str] = None
    
    @property
    def direction(self) -> str:
        return "up" if self.price_change_pct > 0 else "down"
    
    @property
    def change_abs(self) -> float:
        return abs(self.price_change_pct)


@dataclass
class MovementInsight:
    """Key insights about a stock movement."""
    ticker: str
    catalyst_type: str  # "earnings", "news", "sector", "technical", "unknown"
    confidence: int  # 1-5 stars
    summary: str  # 1-2 sentence explanation
    actionable: str  # What the model should do differently


class DynamicTimeEstimator:
    """
    Adaptive time estimation that learns from actual execution times.
    Provides increasingly accurate estimates as the task progresses.
    """
    
    def __init__(self):
        self.phase_times = {}  # Store actual times for each phase
        self.current_phase = None
        self.phase_start_time = None
        self.total_start_time = None
        
        # Historical averages (initial estimates, will be updated)
        self.historical_averages = {
            'identify_movements': 2.0,      # seconds
            'analyze_per_movement': 0.15,   # seconds per movement
            'generate_recommendations': 1.0, # seconds
            'create_report': 0.5            # seconds
        }
        
        # Load historical data if available
        self._load_history()
    
    def _load_history(self):
        """Load historical timing data to improve initial estimates."""
        try:
            history_file = Path("data/performance_analysis_v2/timing_history.json")
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    if 'averages' in data:
                        self.historical_averages.update(data['averages'])
                        logger.info(f"Loaded timing history: {self.historical_averages}")
        except Exception as e:
            logger.debug(f"Could not load timing history: {e}")
    
    def _save_history(self):
        """Save timing data for future runs."""
        try:
            history_file = Path("data/performance_analysis_v2/timing_history.json")
            history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Update averages with exponential moving average (70% old, 30% new)
            if self.phase_times:
                for phase, duration in self.phase_times.items():
                    if phase in self.historical_averages:
                        old = self.historical_averages[phase]
                        self.historical_averages[phase] = old * 0.7 + duration * 0.3
                    else:
                        self.historical_averages[phase] = duration
                
                with open(history_file, 'w') as f:
                    json.dump({
                        'averages': self.historical_averages,
                        'last_updated': datetime.now().isoformat()
                    }, f, indent=2)
                
                logger.info(f"Saved timing history: {self.historical_averages}")
        except Exception as e:
            logger.debug(f"Could not save timing history: {e}")
    
    def start_total(self):
        """Mark the start of the entire analysis."""
        self.total_start_time = time.time()
        self.phase_times = {}
    
    def start_phase(self, phase_name: str):
        """Mark the start of a phase."""
        # End previous phase if exists
        if self.current_phase and self.phase_start_time:
            duration = time.time() - self.phase_start_time
            self.phase_times[self.current_phase] = duration
            logger.debug(f"Phase '{self.current_phase}' took {duration:.2f}s")
        
        self.current_phase = phase_name
        self.phase_start_time = time.time()
    
    def end_phase(self):
        """Mark the end of current phase."""
        if self.current_phase and self.phase_start_time:
            duration = time.time() - self.phase_start_time
            self.phase_times[self.current_phase] = duration
            logger.debug(f"Phase '{self.current_phase}' took {duration:.2f}s")
            self.current_phase = None
            self.phase_start_time = None
    
    def estimate_remaining(self, current_phase: str, progress_pct: float, movement_count: int = 0) -> float:
        """
        Estimate remaining time based on:
        1. Actual time taken so far for completed phases
        2. Historical averages for remaining phases
        3. Current phase progress
        
        Returns: estimated seconds remaining
        """
        elapsed_total = time.time() - self.total_start_time if self.total_start_time else 0
        
        # Calculate time for remaining work in current phase
        if current_phase == 'analyze_movements' and movement_count > 0:
            # Use actual time per movement if we have data
            if self.phase_start_time:
                elapsed_in_phase = time.time() - self.phase_start_time
                movements_processed = int(movement_count * progress_pct)
                if movements_processed > 0:
                    time_per_movement = elapsed_in_phase / movements_processed
                    remaining_movements = movement_count - movements_processed
                    phase_remaining = remaining_movements * time_per_movement
                else:
                    # Fallback to historical average
                    phase_remaining = movement_count * self.historical_averages['analyze_per_movement']
            else:
                phase_remaining = movement_count * self.historical_averages['analyze_per_movement']
        else:
            # For other phases, estimate based on historical data
            phase_key_map = {
                'identify_movements': 'identify_movements',
                'analyze_movements': 'analyze_per_movement',
                'generate_recommendations': 'generate_recommendations',
                'create_report': 'create_report'
            }
            
            if current_phase in phase_key_map:
                phase_key = phase_key_map[current_phase]
                estimated_phase_time = self.historical_averages.get(phase_key, 1.0)
                if phase_key == 'analyze_per_movement':
                    estimated_phase_time *= max(movement_count, 1)
                phase_remaining = estimated_phase_time * (1.0 - progress_pct)
            else:
                phase_remaining = 1.0 * (1.0 - progress_pct)
        
        # Add time for remaining phases
        phase_order = ['identify_movements', 'analyze_movements', 'generate_recommendations', 'create_report']
        remaining_phases = []
        
        try:
            current_idx = phase_order.index(current_phase)
            remaining_phases = phase_order[current_idx + 1:]
        except ValueError:
            remaining_phases = []
        
        remaining_phase_time = 0
        for phase in remaining_phases:
            if phase == 'analyze_movements':
                remaining_phase_time += self.historical_averages['analyze_per_movement'] * max(movement_count, 1)
            else:
                phase_key_map_full = {
                    'identify_movements': 'identify_movements',
                    'generate_recommendations': 'generate_recommendations',
                    'create_report': 'create_report'
                }
                if phase in phase_key_map_full:
                    remaining_phase_time += self.historical_averages[phase_key_map_full[phase]]
        
        total_remaining = phase_remaining + remaining_phase_time
        
        # Apply adjustment factor based on actual vs estimated time so far
        if elapsed_total > 5:  # Only after we have some data
            # Compare actual time to what we would have estimated
            estimated_so_far = 0
            for completed_phase, duration in self.phase_times.items():
                if completed_phase == 'identify_movements':
                    estimated_so_far += self.historical_averages['identify_movements']
                elif 'analyze' in completed_phase:
                    estimated_so_far += self.historical_averages['analyze_per_movement'] * max(movement_count, 1)
            
            if estimated_so_far > 0:
                adjustment_factor = elapsed_total / estimated_so_far
                total_remaining *= adjustment_factor
        
        return max(0.5, total_remaining)  # Never show less than 0.5s
    
    def finalize(self):
        """Complete the timing session and save history."""
        self.end_phase()
        self._save_history()
        
        if self.total_start_time:
            total_time = time.time() - self.total_start_time
            logger.info(f"Total analysis time: {total_time:.2f}s")
            return total_time
        return 0


class PerformanceAnalysisEngineV2:
    """
    Rebuilt Performance Analysis Engine focused on:
    1. SPEED - Get results quickly without blocking UI
    2. RELIABILITY - Handle errors gracefully
    3. USEFULNESS - Actionable insights, not just data
    4. SIMPLICITY - Easy to understand and maintain
    """
    
    def __init__(self, data_provider, openai_client=None, perplexity_client=None):
        """Initialize the engine with required components."""
        self.data_provider = data_provider
        self.openai_client = openai_client
        self.perplexity_client = perplexity_client
        
        # Storage
        self.storage_dir = Path("data/performance_analysis_v2")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Time estimator
        self.time_estimator = DynamicTimeEstimator()
        
        logger.info("Performance Analysis Engine V2 initialized")
    
    def analyze_performance_period(
        self,
        start_date: str,
        end_date: str,
        tickers: Optional[List[str]] = None,
        qa_system=None,
        sheets_integration=None,
        min_threshold: float = 15.0,
        progress_callback: Optional[Callable[[str, int, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Main analysis method - FAST and RELIABLE with dynamic time estimates.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            tickers: Optional list of tickers (None = use all from sheets)
            qa_system: Optional QA system
            sheets_integration: Google Sheets integration (preferred data source)
            min_threshold: Minimum movement threshold (default 15%)
            progress_callback: Optional callback(message, progress_pct, time_remaining_sec)
        
        Returns:
            Complete analysis report with actionable insights
        """
        logger.info(f"Starting Performance Analysis V2: {start_date} to {end_date}")
        logger.info(f"   Threshold: {min_threshold}% | Tickers: {'ALL' if tickers is None else len(tickers)}")
        
        # Start timing
        self.time_estimator.start_total()
        
        try:
            # Step 1: Identify significant movements (FAST)
            self.time_estimator.start_phase('identify_movements')
            
            if progress_callback:
                time_remaining = self.time_estimator.estimate_remaining('identify_movements', 0.0)
                progress_callback("Scanning Google Sheets for stocks with significant price movements...", 10, time_remaining)
            
            movements = self._identify_movements_fast(
                start_date, end_date, tickers, sheets_integration, min_threshold
            )
            
            self.time_estimator.end_phase()
            
            if not movements:
                logger.info("No significant movements found")
                self.time_estimator.finalize()
                return self._create_empty_report(start_date, end_date, min_threshold)
            
            logger.info(f"Found {len(movements)} significant movements")
            
            # Step 2: Analyze movements (FAST - no heavy API calls)
            self.time_estimator.start_phase('analyze_movements')
            
            if progress_callback:
                time_remaining = self.time_estimator.estimate_remaining('analyze_movements', 0.0, len(movements))
                progress_callback(f"Identified {len(movements)} stocks to analyze - performing pattern-based analysis...", 40, time_remaining)
            
            insights = self._analyze_movements_fast(movements, progress_callback, len(movements))
            
            self.time_estimator.end_phase()
            
            logger.info(f"Generated {len(insights)} insights")
            
            # Step 3: Generate recommendations (FAST)
            self.time_estimator.start_phase('generate_recommendations')
            
            if progress_callback:
                time_remaining = self.time_estimator.estimate_remaining('generate_recommendations', 0.0)
                progress_callback(f"Synthesizing insights and generating {len(insights)} model improvement recommendations...", 70, time_remaining)
            
            recommendations = self._generate_recommendations_fast(movements, insights)
            
            self.time_estimator.end_phase()
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            
            # Step 4: Create report
            self.time_estimator.start_phase('create_report')
            
            if progress_callback:
                time_remaining = self.time_estimator.estimate_remaining('create_report', 0.0)
                progress_callback("Compiling comprehensive analysis report with patterns and actionable insights...", 90, time_remaining)
            
            report = self._create_report(
                movements, insights, recommendations, start_date, end_date
            )
            
            self.time_estimator.end_phase()
            
            # Step 5: Save results
            self._save_results(report)
            
            # Finalize timing and save history
            total_time = self.time_estimator.finalize()
            
            if progress_callback:
                progress_callback(f"Analysis complete! Processed {len(movements)} stocks in {total_time:.1f}s", 100, 0.0)
            
            logger.info(f"Performance Analysis V2 COMPLETE in {total_time:.2f}s")
            return report
            
        except Exception as e:
            logger.error(f"Performance Analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_error_report(str(e), start_date, end_date)
    
    def _identify_movements_fast(
        self,
        start_date: str,
        end_date: str,
        tickers: Optional[List[str]],
        sheets_integration,
        min_threshold: float
    ) -> List[StockMovement]:
        """
        FAST movement identification using Google Sheets data.
        No slow API calls, just read from sheets.
        """
        movements = []
        
        try:
            # Try to get data from Google Sheets (FAST)
            df = self._get_sheets_data_fast(sheets_integration)
            
            if df is None or df.empty:
                logger.warning("No data from Google Sheets")
                return movements
            
            # Filter by tickers if provided
            if tickers:
                df = df[df['Ticker'].isin(tickers)]
            
            logger.info(f"Processing {len(df)} stocks from Google Sheets")
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    ticker = row.get('Ticker', '').strip()
                    if not ticker:
                        continue
                    
                    # Get percent change
                    pct_change = self._extract_percent_change(row)
                    if pct_change is None:
                        continue
                    
                    # Check if meets threshold
                    if abs(pct_change) < min_threshold:
                        continue
                    
                    # Get prices
                    start_price, end_price = self._extract_prices(row, pct_change)
                    
                    # Determine magnitude
                    magnitude = self._classify_magnitude(abs(pct_change))
                    
                    # Get sector
                    sector = row.get('Sector', None)
                    
                    movement = StockMovement(
                        ticker=ticker,
                        price_change_pct=pct_change,
                        start_price=start_price,
                        end_price=end_price,
                        start_date=str(row.get('Analysis Date', start_date)),
                        end_date=end_date,
                        magnitude=magnitude,
                        sector=sector
                    )
                    
                    movements.append(movement)
                    
                except Exception as e:
                    logger.debug(f"Error processing row: {e}")
                    continue
            
            # Sort by absolute change (largest first)
            movements.sort(key=lambda x: x.change_abs, reverse=True)
            
            logger.info(f"Found {len(movements)} movements meeting {min_threshold}% threshold")
            
        except Exception as e:
            logger.error(f"Error identifying movements: {e}")
        
        return movements
    
    def _get_sheets_data_fast(self, sheets_integration) -> Optional[pd.DataFrame]:
        """
        FAST Google Sheets data fetch with minimal overhead.
        """
        try:
            if not sheets_integration or not hasattr(sheets_integration, 'sheet'):
                return None
            
            sheet = sheets_integration.sheet
            if not sheet:
                return None
            
            # Try common worksheet names
            worksheet = None
            for name in ['Historical Price Analysis', 'Portfolio Analysis', 'Price Analysis']:
                try:
                    worksheet = sheet.worksheet(name)
                    break
                except:
                    continue
            
            if not worksheet:
                return None
            
            # Get all data at once (FAST)
            data = worksheet.get_all_records()
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip()
            
            logger.info(f"Fetched {len(df)} rows from Google Sheets")
            return df
            
        except Exception as e:
            logger.debug(f"Sheets fetch error: {e}")
            return None
    
    def _extract_percent_change(self, row: pd.Series) -> Optional[float]:
        """
        Extract percent change from row, trying multiple column names.
        """
        # Try direct percent change column
        for col in ['Percent Change', 'Price Change %', '% Change', 'Percent_Change']:
            if col in row.index:
                val = row[col]
                if val is None or (isinstance(val, str) and val.strip() == ''):
                    continue
                
                try:
                    # Handle numeric or string
                    if isinstance(val, (int, float)):
                        return float(val)
                    
                    # Parse string
                    val_str = str(val).strip().replace('%', '').replace(',', '')
                    if val_str and val_str.lower() not in ['nan', 'n/a', '-', 'none']:
                        return float(val_str)
                except:
                    continue
        
        # Calculate from prices if available
        for price_col in ['Price at Analysis', 'Price_at_Analysis']:
            for current_col in ['Price', 'Current Price']:
                if price_col in row.index and current_col in row.index:
                    try:
                        price_at = float(str(row[price_col]).replace(',', '').replace('$', ''))
                        price_now = float(str(row[current_col]).replace(',', '').replace('$', ''))
                        
                        if price_at > 0:
                            return ((price_now - price_at) / price_at) * 100
                    except:
                        continue
        
        return None
    
    def _extract_prices(self, row: pd.Series, pct_change: float) -> Tuple[float, float]:
        """Extract start and end prices, or estimate from percent change."""
        start_price = 0.0
        end_price = 0.0
        
        # Try to get actual prices
        for col in ['Price at Analysis', 'Price_at_Analysis']:
            if col in row.index:
                try:
                    val = str(row[col]).replace(',', '').replace('$', '').strip()
                    if val and val.lower() not in ['nan', 'n/a', '-']:
                        start_price = float(val)
                        break
                except:
                    continue
        
        for col in ['Price', 'Current Price']:
            if col in row.index:
                try:
                    val = str(row[col]).replace(',', '').replace('$', '').strip()
                    if val and val.lower() not in ['nan', 'n/a', '-']:
                        end_price = float(val)
                        break
                except:
                    continue
        
        # Calculate missing price from the other
        if start_price > 0 and end_price == 0:
            end_price = start_price * (1 + pct_change / 100)
        elif end_price > 0 and start_price == 0:
            start_price = end_price / (1 + pct_change / 100)
        elif start_price == 0 and end_price == 0:
            # Use arbitrary baseline
            start_price = 100.0
            end_price = start_price * (1 + pct_change / 100)
        
        return start_price, end_price
    
    def _classify_magnitude(self, abs_change: float) -> str:
        """Classify movement magnitude."""
        if abs_change >= 20:
            return "extreme"
        elif abs_change >= 10:
            return "major"
        else:
            return "significant"
    
    def _analyze_movements_fast(
        self,
        movements: List[StockMovement],
        progress_callback=None,
        total_movements: int = 0
    ) -> List[MovementInsight]:
        """
        FAST analysis without heavy API calls.
        Focus on pattern recognition and heuristics.
        """
        insights = []
        total = len(movements)
        
        for i, movement in enumerate(movements):
            try:
                # Update progress with dynamic time estimate
                if progress_callback and i % 3 == 0:  # Update every 3 movements
                    progress_pct = i / total
                    progress_display = 40 + int(progress_pct * 30)
                    time_remaining = self.time_estimator.estimate_remaining(
                        'analyze_movements', 
                        progress_pct,
                        total
                    )
                    
                    # Build detailed status message
                    analyzed_count = i
                    remaining_count = total - i
                    pct_change = movement.price_change_pct
                    direction = "gained" if pct_change > 0 else "lost"
                    
                    status_msg = (f"Analyzing {movement.ticker} ({analyzed_count + 1}/{total}) - "
                                f"Stock {direction} {abs(pct_change):.1f}% | "
                                f"{remaining_count} stocks remaining...")
                    
                    progress_callback(status_msg, progress_display, time_remaining)
                
                # Quick analysis based on patterns
                insight = self._quick_insight(movement)
                insights.append(insight)
                
            except Exception as e:
                logger.debug(f"Error analyzing {movement.ticker}: {e}")
                continue
        
        return insights
    
    def _quick_insight(self, movement: StockMovement) -> MovementInsight:
        """
        Generate quick insight using heuristics (no slow API calls).
        """
        ticker = movement.ticker
        pct = movement.price_change_pct
        direction = "up" if pct > 0 else "down"
        
        # Determine likely catalyst type based on magnitude and patterns
        if movement.magnitude == "extreme":
            # Extreme moves are usually earnings or major news
            catalyst_type = "earnings_or_news"
            confidence = 4
            summary = f"{ticker} moved {direction} {abs(pct):.1f}% - likely earnings report or major company news."
            actionable = "Increase sentiment agent weight to catch major news events earlier."
            
        elif movement.magnitude == "major":
            # Major moves could be analyst actions, sector trends, or business developments
            catalyst_type = "analyst_or_sector"
            confidence = 3
            summary = f"{ticker} moved {direction} {abs(pct):.1f}% - possible analyst upgrade/downgrade or sector momentum."
            actionable = "Monitor analyst ratings and sector trends more closely."
            
        else:
            # Significant moves are often technical or gradual accumulation
            catalyst_type = "technical"
            confidence = 2
            summary = f"{ticker} moved {direction} {abs(pct):.1f}% - technical momentum or gradual trend."
            actionable = "Consider momentum indicators and technical analysis in scoring."
        
        return MovementInsight(
            ticker=ticker,
            catalyst_type=catalyst_type,
            confidence=confidence,
            summary=summary,
            actionable=actionable
        )
    
    def _generate_recommendations_fast(
        self,
        movements: List[StockMovement],
        insights: List[MovementInsight]
    ) -> List[Dict[str, Any]]:
        """
        Generate ACTIONABLE recommendations based on patterns.
        """
        recommendations = []
        
        # Analyze patterns
        total = len(movements)
        up_count = sum(1 for m in movements if m.direction == "up")
        down_count = total - up_count
        extreme_count = sum(1 for m in movements if m.magnitude == "extreme")
        
        # Pattern-based recommendations
        catalyst_types = {}
        for insight in insights:
            catalyst_types[insight.catalyst_type] = catalyst_types.get(insight.catalyst_type, 0) + 1
        
        # Recommendation 1: Agent weight adjustments
        if catalyst_types.get('earnings_or_news', 0) / total > 0.3:
            recommendations.append({
                'priority': 'high',
                'category': 'agent_weight',
                'title': 'Increase Sentiment Agent Weight',
                'description': f'{catalyst_types.get("earnings_or_news", 0)} of {total} movements ({catalyst_types.get("earnings_or_news", 0)/total*100:.0f}%) were driven by earnings/news events.',
                'action': 'Increase sentiment agent weight by 20% (1.0 → 1.2)',
                'expected_impact': 'Faster reaction to breaking news and earnings reports',
                'confidence': 85
            })
        
        # Recommendation 2: Sector momentum
        if catalyst_types.get('analyst_or_sector', 0) / total > 0.25:
            recommendations.append({
                'priority': 'medium',
                'category': 'feature_focus',
                'title': 'Enhance Sector Analysis',
                'description': f'{catalyst_types.get("analyst_or_sector", 0)} movements appeared sector-driven.',
                'action': 'Add sector rotation tracking and peer comparison',
                'expected_impact': 'Better capture of sector trends and relative strength',
                'confidence': 75
            })
        
        # Recommendation 3: Risk management for extreme moves
        if extreme_count / total > 0.2:
            recommendations.append({
                'priority': 'critical',
                'category': 'risk_management',
                'title': 'Tighten Risk Controls',
                'description': f'{extreme_count} stocks had extreme movements (>{20}%), indicating high volatility.',
                'action': 'Increase risk agent weight and add volatility screening',
                'expected_impact': 'Better downside protection in volatile markets',
                'confidence': 90
            })
        
        # Recommendation 4: Market direction bias
        if up_count / total > 0.7 or down_count / total > 0.7:
            market_bias = "bullish" if up_count > down_count else "bearish"
            recommendations.append({
                'priority': 'medium',
                'category': 'macro_adjustment',
                'title': f'Adjust for {market_bias.title()} Market',
                'description': f'{max(up_count, down_count)} of {total} movements were {market_bias}.',
                'action': f'Increase macro agent weight to better capture market regime',
                'expected_impact': 'Better alignment with overall market direction',
                'confidence': 70
            })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: (priority_order.get(x['priority'], 4), -x['confidence']))
        
        return recommendations
    
    def _create_report(
        self,
        movements: List[StockMovement],
        insights: List[MovementInsight],
        recommendations: List[Dict],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Create comprehensive but clean report."""
        # Top movers
        up_moves = [m for m in movements if m.direction == "up"]
        down_moves = [m for m in movements if m.direction == "down"]
        
        top_gainers = sorted(up_moves, key=lambda x: x.price_change_pct, reverse=True)[:10]
        top_losers = sorted(down_moves, key=lambda x: x.price_change_pct)[:10]
        
        # Executive summary
        exec_summary = self._create_executive_summary(movements, insights, recommendations)
        
        report = {
            'report_id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'generated_at': datetime.now().isoformat(),
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_movements': len(movements),
                'up_movements': len(up_moves),
                'down_movements': len(down_moves),
                'extreme_movements': sum(1 for m in movements if m.magnitude == "extreme"),
                'recommendations_count': len(recommendations)
            },
            'executive_summary': exec_summary,
            'top_gainers': [asdict(m) for m in top_gainers],
            'top_losers': [asdict(m) for m in top_losers],
            'insights': [asdict(i) for i in insights],
            'recommendations': recommendations,
            'metadata': {
                'engine_version': '2.0',
                'analysis_duration_ms': 0  # Will be updated if tracked
            }
        }
        
        return report
    
    def _create_executive_summary(
        self,
        movements: List[StockMovement],
        insights: List[MovementInsight],
        recommendations: List[Dict]
    ) -> str:
        """Generate concise executive summary."""
        total = len(movements)
        up = sum(1 for m in movements if m.direction == "up")
        down = total - up
        extreme = sum(1 for m in movements if m.magnitude == "extreme")
        
        parts = []
        parts.append(f"Analyzed {total} significant stock movements ({up} up, {down} down).")
        
        if extreme > 0:
            parts.append(f"{extreme} extreme movements (>20%) detected, indicating high volatility.")
        
        if recommendations:
            critical = sum(1 for r in recommendations if r['priority'] == 'critical')
            high = sum(1 for r in recommendations if r['priority'] == 'high')
            
            if critical > 0:
                parts.append(f"{critical} CRITICAL recommendations require immediate attention.")
            elif high > 0:
                parts.append(f"{high} high-priority recommendations identified.")
            
            # Highlight top recommendation
            top_rec = recommendations[0]
            parts.append(f"Top action: {top_rec['action']}")
        
        return " ".join(parts)
    
    def _create_empty_report(self, start_date: str, end_date: str, threshold: float) -> Dict:
        """Create report when no movements found."""
        return {
            'report_id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'status': 'no_movements',
            'message': f'No stocks moved ≥{threshold}% in this period. Try lowering the threshold or expanding the date range.',
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_movements': 0,
                'up_movements': 0,
                'down_movements': 0,
                'extreme_movements': 0,
                'recommendations_count': 0
            },
            'executive_summary': 'No significant movements detected in analysis period.',
            'top_gainers': [],
            'top_losers': [],
            'insights': [],
            'recommendations': []
        }
    
    def _create_error_report(self, error_msg: str, start_date: str, end_date: str) -> Dict:
        """Create report when analysis fails."""
        return {
            'report_id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'status': 'error',
            'error': error_msg,
            'message': f'Analysis failed: {error_msg}',
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_movements': 0,
                'up_movements': 0,
                'down_movements': 0,
                'extreme_movements': 0,
                'recommendations_count': 0
            },
            'executive_summary': f'Analysis failed: {error_msg}',
            'top_gainers': [],
            'top_losers': [],
            'insights': [],
            'recommendations': []
        }
    
    def _save_results(self, report: Dict):
        """Save analysis results to storage."""
        try:
            # Save latest report
            report_file = self.storage_dir / "latest_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Save to history
            history_file = self.storage_dir / "report_history.json"
            history = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            history.append(report)
            history = history[-50:]  # Keep last 50 reports
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
            
            logger.info(f"Saved report to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def get_latest_report(self) -> Optional[Dict]:
        """Get the most recent analysis report."""
        try:
            report_file = self.storage_dir / "latest_report.json"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading latest report: {e}")
        return None
    
    def get_latest_recommendations(self, limit: int = 10) -> List[Dict]:
        """Get the most recent recommendations from latest report."""
        report = self.get_latest_report()
        if report and 'recommendations' in report:
            return report['recommendations'][:limit]
        return []
    
    def mark_recommendation_implemented(self, recommendation_id: str, notes: str = ""):
        """Mark a recommendation as implemented and start tracking its impact."""
        try:
            tracking_file = self.storage_dir / "implementation_tracking.json"
            
            # Load existing tracking data
            tracking_data = {'implemented_recommendations': []}
            if tracking_file.exists():
                with open(tracking_file, 'r') as f:
                    tracking_data = json.load(f)
            
            # Create implementation record
            implementation_record = {
                'recommendation_id': recommendation_id,
                'implemented_at': datetime.now().isoformat(),
                'notes': notes,
                'performance_before': {},  # Will be populated with pre-implementation metrics
                'performance_after': {}   # Will be tracked post-implementation
            }
            
            # Add to tracking
            if 'implemented_recommendations' not in tracking_data:
                tracking_data['implemented_recommendations'] = []
            
            tracking_data['implemented_recommendations'].append(implementation_record)
            
            # Save tracking data
            with open(tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=2, default=str)
            
            logger.info(f"Marked recommendation {recommendation_id} as implemented")
            
        except Exception as e:
            logger.error(f"Failed to mark recommendation as implemented: {e}")
