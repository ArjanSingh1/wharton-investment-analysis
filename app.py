"""
Wharton Investing Challenge - Multi-Agent Investment Analysis System
Main Streamlit Application

This is the main entry point for the investment analysis system.
Provides a web interface for stock analysis, portfolio recommendations, and backtesting.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from pathlib import Path
import yaml

# Setup page config
st.set_page_config(
    page_title="Wharton Investment Analysis System",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Import system components
from dotenv import load_dotenv
from utils.config_loader import get_config_loader
from utils.logger import setup_logging, get_disclosure_logger
from utils.qa_system import QASystem, RecommendationType
from utils.google_sheets_integration import get_sheets_integration
from data.enhanced_data_provider import EnhancedDataProvider
from engine.portfolio_orchestrator import PortfolioOrchestrator
from engine.backtest import BacktestEngine

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.data_provider = None
    st.session_state.orchestrator = None
    st.session_state.config_loader = None
    st.session_state.client_data = None
    st.session_state.qa_system = None
    st.session_state.sheets_integration = None
    st.session_state.sheets_enabled = False
    st.session_state.sheets_auto_update = False


def get_client_profile_weights(client_name: str) -> dict:
    """Derive agent weights from detailed client profile characteristics and specific metrics."""
    from utils.client_profile_manager import ClientProfileManager
    
    profile_manager = ClientProfileManager()
    profile_data = profile_manager.load_client_profile(client_name)
    
    if not profile_data:
        # Default equal weights if profile not found
        return {
            'value': 1.0,
            'growth_momentum': 1.0,
            'macro_regime': 1.0,
            'risk': 1.0,
            'sentiment': 1.0
        }
    
    profile_text = profile_data.get('profile_text', '').lower()
    ips_data = profile_data.get('ips_data', {})
    weights = {'value': 1.0, 'growth_momentum': 1.0, 'macro_regime': 1.0, 'risk': 1.0, 'sentiment': 1.0}
    
    # SPECIFIC METRIC-BASED ANALYSIS
    
    # 1. Risk Tolerance Analysis (from exact risk_tolerance field)
    risk_tolerance = ips_data.get('risk_tolerance', 'moderate')
    if risk_tolerance == 'conservative' or 'conservative' in profile_text:
        weights['value'] = 1.6      # Strong emphasis on value metrics
        weights['risk'] = 1.9       # Very high risk assessment priority
        weights['growth_momentum'] = 0.5  # De-emphasize momentum plays
        weights['sentiment'] = 0.4  # Ignore market sentiment noise
        weights['macro_regime'] = 1.3     # Monitor macro for safety
    elif risk_tolerance == 'aggressive' or any(word in profile_text for word in ['aggressive', 'high-risk', 'growth']):
        weights['growth_momentum'] = 1.9  # Prioritize growth opportunities
        weights['sentiment'] = 1.6        # Use market sentiment for timing
        weights['value'] = 0.6           # Lower focus on traditional value
        weights['risk'] = 0.7           # Accept higher risk for returns
        weights['macro_regime'] = 1.1   # Standard macro monitoring
    
    # 2. Time Horizon Analysis (from exact time_horizon_years)
    time_horizon = ips_data.get('time_horizon_years', 5)
    if time_horizon >= 10:  # Long-term (10+ years)
        weights['value'] *= 1.3          # Value compounds over time
        weights['growth_momentum'] *= 1.2 # Growth more important long-term
        weights['sentiment'] *= 0.6      # Less relevant for long horizons
        weights['macro_regime'] *= 0.9   # Macro cycles matter less long-term
    elif time_horizon <= 3:  # Short-term (3 years or less)
        weights['sentiment'] *= 1.4      # Market timing more critical
        weights['macro_regime'] *= 1.4   # Economic cycles highly relevant
        weights['risk'] *= 1.3          # Downside protection crucial
        weights['growth_momentum'] *= 0.8 # Less time for growth to materialize
    
    # 3. Return Requirements Analysis (from required_growth_rate)
    required_return = ips_data.get('required_growth_rate', 8.0)
    if required_return >= 12.0:  # High return requirement (12%+)
        weights['growth_momentum'] *= 1.5 # Need strong growth stocks
        weights['sentiment'] *= 1.3      # Use sentiment for alpha generation
        weights['value'] *= 0.8         # Value may not meet return needs
        weights['risk'] *= 0.9         # Must accept higher risk
    elif required_return <= 6.0:  # Conservative return target (6% or less)
        weights['value'] *= 1.4         # Focus on undervalued, stable stocks
        weights['risk'] *= 1.5         # Prioritize capital preservation
        weights['growth_momentum'] *= 0.7 # Don't need high growth
        weights['sentiment'] *= 0.7     # Less aggressive positioning
    
    # 4. Drawdown Requirements Analysis (from annual_drawdown)
    has_drawdowns = ips_data.get('annual_drawdown', 0) > 0
    if has_drawdowns:
        weights['risk'] *= 1.4          # Liquidity and stability critical
        weights['value'] *= 1.2        # Need reliable dividend/cash flow
        weights['macro_regime'] *= 1.2  # Economic conditions affect liquidity
        weights['growth_momentum'] *= 0.8 # Can't afford volatile growth stocks
        weights['sentiment'] *= 0.8     # Less speculation allowed
    
    # 5. Mission/ESG Focus Analysis (from foundation_mission and focus_areas)
    has_mission = bool(ips_data.get('foundation_mission') or ips_data.get('focus_areas'))
    if has_mission:
        weights['risk'] *= 1.2          # ESG screening may limit universe
        weights['value'] *= 1.1        # Need sustainable business models
        weights['macro_regime'] *= 1.1  # Policy/regulation impacts ESG stocks
        weights['sentiment'] *= 0.9     # Less focus on pure market dynamics
    
    # 6. Capital Size Analysis (from initial_capital)
    initial_capital = ips_data.get('initial_capital', 100000)
    if initial_capital >= 1000000:  # Large portfolios ($1M+)
        weights['macro_regime'] *= 1.2  # Macro factors more impactful
        weights['risk'] *= 1.1         # Institutional-level risk management
        weights['sentiment'] *= 0.9     # Less tactical, more strategic
    elif initial_capital <= 100000:  # Smaller portfolios (<$100K)
        weights['growth_momentum'] *= 1.2 # Need higher growth to build wealth
        weights['sentiment'] *= 1.1      # More tactical opportunities
        weights['value'] *= 0.9         # May not have luxury of patience
    
    # 7. Organization Type Analysis (from organization field)
    org_type = ips_data.get('organization', '').lower()
    if 'foundation' in org_type or 'nonprofit' in org_type:
        weights['risk'] *= 1.3          # Fiduciary responsibility
        weights['value'] *= 1.2        # Need sustainable returns
        weights['growth_momentum'] *= 0.9 # Less aggressive growth seeking
        weights['sentiment'] *= 0.7     # Avoid speculative positioning
    
    # 8. Professional Background Analysis (from background field)
    background = ips_data.get('background', '').lower()
    if any(word in background for word in ['finance', 'investment', 'business']):
        weights['macro_regime'] *= 1.2  # Sophisticated macro understanding
        weights['sentiment'] *= 1.1     # Can handle market timing
    elif any(word in background for word in ['teacher', 'government', 'nonprofit']):
        weights['risk'] *= 1.3          # Conservative, steady approach
        weights['value'] *= 1.2        # Prefer understandable investments
        weights['sentiment'] *= 0.8     # Less comfort with market speculation
    
    # Normalize weights and ensure they're reasonable
    for key in weights:
        weights[key] = max(0.3, min(2.5, weights[key]))  # Clamp between 0.3 and 2.5
    
    return weights


def initialize_system():
    """Initialize the system components."""
    if st.session_state.initialized:
        return True
    
    # Check API keys
    if not os.getenv('OPENAI_API_KEY'):
        st.error("⚠️ OPENAI_API_KEY not found. Please set it in .env file.")
        return False
    
    if not os.getenv('ALPHA_VANTAGE_API_KEY'):
        st.warning("⚠️ ALPHA_VANTAGE_API_KEY not found. Some features may be limited.")
    
    try:
        # Initialize components
        st.session_state.config_loader = get_config_loader()
        
        # Use Enhanced Data Provider with fallbacks
        st.session_state.data_provider = EnhancedDataProvider()
        
        # Load configurations
        model_config = st.session_state.config_loader.load_model_config()
        ips_config = st.session_state.config_loader.load_ips()
        
        # Initialize AI clients for advanced features
        openai_client = None
        perplexity_client = None
        
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            st.session_state.openai_client = openai_client
        except Exception as e:
            st.warning(f"⚠️ OpenAI client initialization failed: {e}")
        
        try:
            from openai import OpenAI
            perplexity_client = OpenAI(
                api_key=os.getenv('PERPLEXITY_API_KEY'),
                base_url="https://api.perplexity.ai"
            )
            st.session_state.perplexity_client = perplexity_client
        except Exception as e:
            st.warning(f"⚠️ Perplexity client initialization failed: {e}")
        
        # Initialize orchestrator with enhanced data provider and AI clients
        st.session_state.orchestrator = PortfolioOrchestrator(
            model_config=model_config,
            ips_config=ips_config,
            enhanced_data_provider=st.session_state.data_provider,
            openai_client=openai_client,
            perplexity_client=perplexity_client
        )
        
        # Initialize QA system
        st.session_state.qa_system = QASystem()
        
        # Initialize Step Time Manager for persistent step-level timing
        from utils.step_time_manager import StepTimeManager
        if 'step_time_manager' not in st.session_state:
            st.session_state.step_time_manager = StepTimeManager()
            print(st.session_state.step_time_manager.get_summary())
        
        # Initialize analysis time tracking
        if 'analysis_times' not in st.session_state:
            st.session_state.analysis_times = []  # List of historical analysis times in seconds
        
        # Initialize current analysis tracking
        if 'current_analysis_start' not in st.session_state:
            st.session_state.current_analysis_start = None
        if 'current_step_start' not in st.session_state:
            st.session_state.current_step_start = None
        if 'last_step' not in st.session_state:
            st.session_state.last_step = 0
        
        st.session_state.initialized = True
        return True
        
    except Exception as e:
        st.error(f"❌ System initialization failed: {e}")
        return False


def main():
    """Main application entry point."""
    
    # Header
    st.title("Wharton Investment Analysis System")
    st.markdown("**Multi-Agent Investment Research Platform**")
    st.markdown("---")
    
    # Initialize system
    if not initialize_system():
        st.stop()
    
    # Check for stocks due for weekly review and show notification
    if st.session_state.qa_system:
        stocks_due = st.session_state.qa_system.get_stocks_due_for_review()
        if stocks_due:
            st.sidebar.warning(f"⏰ {len(stocks_due)} stock(s) due for weekly review")
            st.sidebar.info("Visit QA & Learning Center to conduct reviews")
    
    # Google Sheets Settings
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Google Sheets Integration")
    
    # Ensure Google Sheets session state variables exist (must be first!)
    if 'sheets_integration' not in st.session_state:
        st.session_state.sheets_integration = get_sheets_integration()
    if 'sheets_enabled' not in st.session_state:
        st.session_state.sheets_enabled = False
    if 'sheets_auto_update' not in st.session_state:
        st.session_state.sheets_auto_update = False
    
    sheets_integration = st.session_state.sheets_integration
    
    # Safety check: ensure sheets_integration is not None
    if sheets_integration is None:
        sheets_integration = get_sheets_integration()
        st.session_state.sheets_integration = sheets_integration
    
    if sheets_integration and sheets_integration.enabled:
        st.sidebar.success("✅ Google Sheets API Ready")
        
        # Auto-connect if Sheet ID is in .env and not yet connected
        env_sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
        if env_sheet_id and not st.session_state.sheets_enabled and sheets_integration.sheet is None:
            with st.spinner("Auto-connecting to Google Sheet..."):
                if sheets_integration.connect_to_sheet(env_sheet_id):
                    st.session_state.sheets_enabled = True
                    st.sidebar.success(f"✅ Auto-connected from .env!")
                    
                    # Auto-sync existing QA analyses on first connection
                    with st.spinner("📤 Syncing QA analyses to Google Sheets..."):
                        if sync_all_archives_to_sheets():
                            st.sidebar.success("✅ QA analyses synced! New portfolios will sync automatically.")
                        else:
                            st.sidebar.info("ℹ️ No QA analyses to sync yet")
        
        # Sheet ID input (shows current value from .env or manual entry)
        sheet_id = st.sidebar.text_input(
            "Google Sheet ID",
            value=env_sheet_id,
            help="Enter the Sheet ID from the URL (or set GOOGLE_SHEET_ID in .env)",
            key="sheet_id_input"
        )
        
        # Manual connect button (only if not already connected)
        if sheet_id and sheets_integration.sheet is None:
            if st.sidebar.button("🔗 Connect to Sheet"):
                with st.spinner("Connecting..."):
                    if sheets_integration.connect_to_sheet(sheet_id):
                        st.sidebar.success(f"✅ Connected!")
                        st.session_state.sheets_enabled = True
                        # Save to env for persistence
                        os.environ['GOOGLE_SHEET_ID'] = sheet_id
                        
                        # Auto-sync existing QA analyses
                        with st.spinner("📤 Syncing QA analyses to Google Sheets..."):
                            if sync_all_archives_to_sheets():
                                st.sidebar.success("✅ QA analyses synced! New portfolios will sync automatically.")
                            else:
                                st.sidebar.info("ℹ️ No QA analyses to sync yet")
                    else:
                        st.sidebar.error("❌ Connection failed")
            
            # Auto-update toggle
            if st.session_state.sheets_enabled:
                st.session_state.sheets_auto_update = st.sidebar.checkbox(
                    "🔄 Auto-update on analysis",
                    value=st.session_state.sheets_auto_update,
                    help="Automatically push results to Google Sheets"
                )
                
                if sheets_integration.sheet:
                    sheet_url = sheets_integration.get_sheet_url()
                    if sheet_url:
                        st.sidebar.markdown(f"[📄 Open Sheet]({sheet_url})")
                    
                    # Manual sync QA analyses button
                    if st.sidebar.button("🔄 Sync QA Analyses Now"):
                        with st.spinner("📤 Syncing QA analyses..."):
                            if sync_all_archives_to_sheets():
                                st.sidebar.success("✅ QA analyses synced!")
                            else:
                                st.sidebar.info("ℹ️ No QA analyses to sync")
    else:
        st.sidebar.warning("⚙️ Not configured (optional)")
        with st.sidebar.expander("📖 Setup Instructions (Optional)"):
            st.markdown("""
            **Google Sheets integration is optional** - the app works fully without it.
            
            To enable automatic portfolio syncing to Google Sheets:
            
            1. Create a [Google Cloud project](https://console.cloud.google.com)
            2. Enable the Google Sheets API
            3. Create a service account
            4. Download the credentials JSON file
            5. Save it as `google_credentials.json` in the project root
            6. Create a Google Sheet and share it with the service account email
            7. Add the Sheet ID to `.env` as `GOOGLE_SHEET_ID=your_sheet_id`
            
            **Benefits:**
            - Auto-sync all analyses to Google Sheets
            - Track portfolio history over time
            - Share results with clients/team
            - Advanced filtering and charting
            
            **Without it:**
            - All analysis still works perfectly
            - Results shown in the app
            - QA system still tracks everything
            
            [Full Setup Guide](https://docs.gspread.org/en/latest/oauth2.html)
            """)
    
    # Sidebar navigation
    st.sidebar.markdown("---")
    st.sidebar.title("NAVIGATION")
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Select Analysis Mode:",
        ["Stock Analysis", "Portfolio Recommendations", "QA & Learning Center", "System Configuration", "System Status & AI Disclosure"]
    )
    
    # Route to appropriate page
    if page == "Stock Analysis":
        stock_analysis_page()
    elif page == "Portfolio Recommendations":
        portfolio_recommendations_page()
    elif page == "QA & Learning Center":
        qa_learning_center_page()
    elif page == "System Configuration":
        configuration_page()
    elif page == "System Status & AI Disclosure":
        system_status_and_ai_disclosure_page()


def stock_analysis_page():
    """Single or multiple stock analysis page."""
    st.header("Stock Analysis")
    st.write("Evaluate individual securities or analyze multiple stocks at once using multi-agent investment research methodology.")
    st.markdown("---")
    
    # Analysis mode selection
    analysis_mode = st.radio(
        "Analysis Mode",
        options=["Single Stock", "Multiple Stocks"],
        horizontal=True,
        help="Choose to analyze one stock or multiple stocks at once"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if analysis_mode == "Single Stock":
            ticker = st.text_input(
                "Stock Ticker Symbol",
                value="AAPL",
                help="Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
            ).upper()
        else:
            ticker_input = st.text_area(
                "Stock Ticker Symbols",
                value="AAPL MSFT GOOGL",
                height=100,
                help="Enter multiple ticker symbols separated by spaces, commas, or line breaks (e.g., AAPL MSFT GOOGL or AAPL, MSFT, GOOGL)"
            )
            # Parse tickers - handle spaces, commas, and newlines, remove duplicates
            import re
            ticker_list = [t.strip().upper() for t in re.split(r'[,\s\n]+', ticker_input) if t.strip()]
            # Remove duplicates while preserving order
            seen = set()
            tickers = []
            for t in ticker_list:
                if t not in seen:
                    seen.add(t)
                    tickers.append(t)
            ticker = None  # Not used in multi mode
    
    with col2:
        analysis_date = st.date_input(
            "Analysis Date",
            value=datetime.now(),
            help="Date for analysis (leave as today for latest data)"
        )
    
    # Weight Preset Selection
    st.subheader("⚖️ Agent Weight Preset Selection")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        weight_preset = st.selectbox(
            "Choose Weight Configuration:",
            options=["equal_weights", "custom_weights", "client_profile_weights"],
            format_func=lambda x: {
                "equal_weights": "1. Equal Weights",
                "custom_weights": "2. Custom Weights", 
                "client_profile_weights": "3. Client Profile Weights"
            }[x],
            help="Select how agent weights should be configured for this analysis"
        )
        
        # Store weight preset in session state for use in display functions
        st.session_state.weight_preset = weight_preset
    
    # Initialize session state for custom weights
    if 'custom_agent_weights' not in st.session_state:
        st.session_state.custom_agent_weights = {
            'value': 1.0,
            'growth_momentum': 1.0,
            'macro_regime': 1.0,
            'risk': 1.0,
            'sentiment': 1.0
        }
    
    # Handle weight preset selection
    agent_weights = None
    if weight_preset == "custom_weights":
        with col2:
            if st.button("🔧 Configure Custom Weights"):
                st.session_state.show_custom_weights = not st.session_state.get('show_custom_weights', False)
        
        if st.session_state.get('show_custom_weights', False):
            st.info("""
            **📊 Custom Weights Explanation:**
            
            These weights control **how much each agent's score influences the final score**.
            
            - **Higher weight (2.0)** = Agent's opinion has MORE influence on final score
            - **Lower weight (0.5)** = Agent's opinion has LESS influence on final score  
            - **Weight of 1.0** = Standard/equal influence
            
            **Example:** If Value Agent = 2.0 and Growth Agent = 0.5:
            - Final score will be heavily weighted toward value metrics
            - Growth metrics will have less impact on the final score
            
            **Important:** Agents still score independently (0-100). Weights only affect how 
            those scores are combined into the final score.
            """)
            
            st.write("**Configure Custom Agent Weights:**")
            weight_cols = st.columns(5)
            
            agents = ['value', 'growth_momentum', 'macro_regime', 'risk', 'sentiment']
            agent_labels = ['Value', 'Growth/Momentum', 'Macro Regime', 'Risk', 'Sentiment']
            
            for i, (agent, label) in enumerate(zip(agents, agent_labels)):
                with weight_cols[i]:
                    st.session_state.custom_agent_weights[agent] = st.slider(
                        label,
                        min_value=0.0,
                        max_value=2.0,
                        value=st.session_state.custom_agent_weights[agent],
                        step=0.1,
                        key=f"custom_weight_{agent}",
                        help=f"Weight for {label} agent's contribution to final score"
                    )
            
            # Show current weight distribution
            st.write("**Current Weight Distribution:**")
            total_weight = sum(st.session_state.custom_agent_weights.values())
            percentages = {k: (v/total_weight)*100 for k, v in st.session_state.custom_agent_weights.items()}
            
            dist_cols = st.columns(5)
            for i, (agent, pct) in enumerate(percentages.items()):
                with dist_cols[i]:
                    st.metric(agent_labels[i], f"{pct:.1f}%", help=f"This agent's influence: {pct:.1f}%")
            
            # 🆕 IMPROVEMENT #2: Save/Load Weight Presets
            st.markdown("---")
            col_save, col_load = st.columns(2)
            
            with col_save:
                st.write("**💾 Save Current Weights as Preset:**")
                preset_name = st.text_input("Preset Name", placeholder="e.g., Aggressive Growth", key="save_preset_name")
                if st.button("💾 Save Preset", key="save_preset_btn"):
                    if preset_name:
                        if 'saved_weight_presets' not in st.session_state:
                            st.session_state.saved_weight_presets = {}
                        st.session_state.saved_weight_presets[preset_name] = st.session_state.custom_agent_weights.copy()
                        # Persist to disk
                        import json
                        presets_file = Path("data/weight_presets.json")
                        presets_file.parent.mkdir(exist_ok=True)
                        with open(presets_file, 'w') as f:
                            json.dump(st.session_state.saved_weight_presets, f, indent=2)
                        st.success(f"✅ Saved preset: {preset_name}")
                    else:
                        st.warning("Please enter a preset name")
            
            with col_load:
                st.write("**📂 Load Saved Preset:**")
                # Load presets from disk if not in session state
                if 'saved_weight_presets' not in st.session_state:
                    import json
                    presets_file = Path("data/weight_presets.json")
                    if presets_file.exists():
                        with open(presets_file, 'r') as f:
                            st.session_state.saved_weight_presets = json.load(f)
                    else:
                        st.session_state.saved_weight_presets = {}
                
                if st.session_state.saved_weight_presets:
                    preset_to_load = st.selectbox("Select Preset", options=list(st.session_state.saved_weight_presets.keys()), key="load_preset_select")
                    if st.button("📂 Load Preset", key="load_preset_btn"):
                        st.session_state.custom_agent_weights = st.session_state.saved_weight_presets[preset_to_load].copy()
                        st.success(f"✅ Loaded preset: {preset_to_load}")
                        st.rerun()
                else:
                    st.info("No saved presets yet")
            
            # Lock in weights button
            st.markdown("---")
            if st.button("🔒 Lock In Custom Weights", type="primary"):
                st.session_state.locked_custom_weights = st.session_state.custom_agent_weights.copy()
                st.success("✅ Custom weights locked in! These will be used for analysis.")
                st.session_state.show_custom_weights = False
        
        # Use locked custom weights if available
        if 'locked_custom_weights' in st.session_state:
            agent_weights = st.session_state.locked_custom_weights
            
            # Show which weights are active
            with st.expander("⚖️ Active Custom Weights", expanded=False):
                st.write("**These custom weights will be applied to your analysis:**")
                total_weight = sum(agent_weights.values())
                cols = st.columns(5)
                agent_labels_dict = {
                    'value': 'Value',
                    'growth_momentum': 'Growth/Momentum',
                    'macro_regime': 'Macro Regime',
                    'risk': 'Risk',
                    'sentiment': 'Sentiment'
                }
                for i, (agent, weight) in enumerate(agent_weights.items()):
                    with cols[i]:
                        pct = (weight / total_weight) * 100
                        st.metric(agent_labels_dict.get(agent, agent), f"{weight:.1f}x", delta=f"{pct:.1f}%")
    
    elif weight_preset == "client_profile_weights":
        with col2:
            # Load available client profiles
            from utils.client_profile_manager import ClientProfileManager
            profile_manager = ClientProfileManager()
            available_profiles = profile_manager.list_client_profiles()
            
            if available_profiles:
                profile_names = [p['client_name'] for p in available_profiles]
                selected_profile = st.selectbox(
                    "Select Client Profile:",
                    options=profile_names,
                    help="Choose a client profile to derive agent weights"
                )
                
                if st.button("📋 Apply Profile Weights"):
                    agent_weights = get_client_profile_weights(selected_profile)
                    st.success(f"✅ Applied weights based on {selected_profile} profile!")
            else:
                st.warning("⚠️ No client profiles found. Please create a client profile in System Configuration first.")
    
    else:  # equal_weights
        with col2:
            if st.button("⚖️ Apply Equal Weights"):
                agent_weights = {
                    'value': 1.0,
                    'growth_momentum': 1.0,
                    'macro_regime': 1.0,
                    'risk': 1.0,
                    'sentiment': 1.0
                }
                st.success("✅ Equal weights applied!")
    
    st.markdown("---")
    
    if st.button("Run Analysis", type="primary"):
        # Validation
        if analysis_mode == "Single Stock":
            if not ticker:
                st.error("Please enter a ticker symbol")
                return
        else:
            if not tickers:
                st.error("Please enter at least one ticker symbol")
                return
        
        # Create detailed progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize progress tracking in session state
        if 'analysis_progress' not in st.session_state:
            st.session_state.analysis_progress = {
                'step': 0,
                'total_steps': 10,
                'current_status': 'Starting analysis...',
                'progress_bar': None,
                'status_text': None
            }
        
        # Store progress components in session state for orchestrator access
        st.session_state.analysis_progress['progress_bar'] = progress_bar
        st.session_state.analysis_progress['status_text'] = status_text
        
        # Handle single or multiple stock analysis
        if analysis_mode == "Single Stock":
            # Single stock analysis (existing logic)
            try:
                import time
                
                # Initialize step tracking for this analysis
                st.session_state.current_analysis_start = time.time()
                st.session_state.current_step_start = time.time()
                st.session_state.last_step = 0
                
                # Calculate estimated time
                if st.session_state.analysis_times:
                    avg_time = sum(st.session_state.analysis_times) / len(st.session_state.analysis_times)
                    est_minutes = int(avg_time // 60)
                    est_seconds = int(avg_time % 60)
                    status_text.text(f"🚀 Starting analysis... (Est. {est_minutes}m {est_seconds}s)")
                else:
                    status_text.text("🚀 Starting analysis... (Est. ~30-40s)")
                
                progress_bar.progress(0)
                
                # Track start time
                start_time = time.time()
                
                # Run analysis with optional agent weights
                # Normalize analysis_date to YYYY-MM-DD string (handle date_input returning date, datetime, tuple/range, or None)
                analysis_date_value = analysis_date
                if isinstance(analysis_date_value, (tuple, list)):
                    analysis_date_value = analysis_date_value[0] if analysis_date_value else datetime.now().date()
                if analysis_date_value is None:
                    analysis_date_str = datetime.now().strftime('%Y-%m-%d')
                elif isinstance(analysis_date_value, datetime):
                    analysis_date_str = analysis_date_value.strftime('%Y-%m-%d')
                elif hasattr(analysis_date_value, 'strftime'):
                    try:
                        analysis_date_str = analysis_date_value.strftime('%Y-%m-%d')
                    except Exception:
                        analysis_date_str = str(analysis_date_value)
                else:
                    analysis_date_str = str(analysis_date_value)
                
                result = st.session_state.orchestrator.analyze_stock(
                    ticker=ticker,
                    analysis_date=analysis_date_str,
                    agent_weights=agent_weights
                )
                
                # Track end time and store
                end_time = time.time()
                analysis_duration = end_time - start_time
                st.session_state.analysis_times.append(analysis_duration)
                
                # Keep only last 50 times for better estimates
                if len(st.session_state.analysis_times) > 50:
                    st.session_state.analysis_times = st.session_state.analysis_times[-50:]
                
                # Final completion with actual time
                actual_minutes = int(analysis_duration // 60)
                actual_seconds = int(analysis_duration % 60)
                status_text.text(f"✅ Analysis complete! (Took {actual_minutes}m {actual_seconds}s)")
                progress_bar.progress(100)
                
                # Clear progress indicators after a brief moment
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                if 'error' in result:
                    st.error(f"❌ {result['error']}")
                    return
                
                # Display results
                display_stock_analysis(result)
                
            except Exception as e:
                # Clear progress indicators on error
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Analysis failed: {e}")
        
        else:
            # Multiple stocks analysis
            import time
            
            st.info(f"🔍 Analyzing {len(tickers)} stocks: {', '.join(tickers)}")
            
            # Create overall progress tracking
            overall_progress = st.progress(0)
            overall_status = st.empty()
            time_estimate_display = st.empty()
            
            results = []
            failed_tickers = []
            batch_start_time = time.time()
            
            # Initial time estimate
            if st.session_state.analysis_times:
                avg_time = sum(st.session_state.analysis_times) / len(st.session_state.analysis_times)
            else:
                avg_time = 35  # Default estimate in seconds
            
            total_est_seconds = int(avg_time * len(tickers))
            est_minutes = total_est_seconds // 60
            est_seconds = total_est_seconds % 60
            time_estimate_display.info(f"⏱️ Initial estimate: ~{est_minutes}m {est_seconds}s for {len(tickers)} stocks")
            
            for idx, stock_ticker in enumerate(tickers):
                stock_start_time = time.time()
                
                # Calculate dynamic time remaining using actual batch performance
                completed_count = idx  # Number of stocks completed so far
                if completed_count > 0:
                    # Calculate elapsed time and stocks per minute
                    elapsed_time = time.time() - batch_start_time
                    stocks_per_minute = completed_count / (elapsed_time / 60)
                    
                    # Calculate remaining time based on actual rate
                    remaining_stocks = len(tickers) - idx
                    est_remaining_minutes = remaining_stocks / stocks_per_minute if stocks_per_minute > 0 else 0
                    est_minutes = int(est_remaining_minutes)
                    est_seconds = int((est_remaining_minutes - est_minutes) * 60)
                    
                    overall_status.text(f"📊 Analyzing {stock_ticker} ({idx + 1} of {len(tickers)}) - Est. {est_minutes}m {est_seconds}s remaining (Rate: {stocks_per_minute:.1f} stocks/min)")
                else:
                    # Use historical average for first stock
                    remaining_stocks = len(tickers) - idx
                    est_remaining_seconds = int(avg_time * remaining_stocks)
                    est_minutes = est_remaining_seconds // 60
                    est_seconds = est_remaining_seconds % 60
                    overall_status.text(f"📊 Analyzing {stock_ticker} ({idx + 1} of {len(tickers)}) - Est. {est_minutes}m {est_seconds}s remaining")
                
                # Create progress tracking for individual stock
                stock_progress_bar = st.progress(0)
                stock_status_text = st.empty()
                
                # Initialize step tracking for this stock
                st.session_state.current_analysis_start = time.time()
                st.session_state.current_step_start = time.time()
                st.session_state.last_step = 0
                
                # Re-initialize progress tracking in session state for this stock
                st.session_state.analysis_progress = {
                    'step': 0,
                    'total_steps': 10,
                    'current_status': 'Starting analysis...',
                    'progress_bar': stock_progress_bar,
                    'status_text': stock_status_text
                }
                
                try:
                    # Normalize analysis_date to YYYY-MM-DD string (handle date_input returning date, datetime, tuple/range, or None)
                    analysis_date_value = analysis_date
                    if isinstance(analysis_date_value, (tuple, list)):
                        analysis_date_value = analysis_date_value[0] if analysis_date_value else datetime.now().date()
                    if analysis_date_value is None:
                        analysis_date_str = datetime.now().strftime('%Y-%m-%d')
                    elif isinstance(analysis_date_value, datetime):
                        analysis_date_str = analysis_date_value.strftime('%Y-%m-%d')
                    elif hasattr(analysis_date_value, 'strftime'):
                        try:
                            analysis_date_str = analysis_date_value.strftime('%Y-%m-%d')
                        except Exception:
                            analysis_date_str = str(analysis_date_value)
                    else:
                        analysis_date_str = str(analysis_date_value)
                    
                    # Run analysis for this stock
                    result = st.session_state.orchestrator.analyze_stock(
                        ticker=stock_ticker,
                        analysis_date=analysis_date_str,
                        agent_weights=agent_weights
                    )
                    
                    # Track time for this stock
                    stock_end_time = time.time()
                    stock_duration = stock_end_time - stock_start_time
                    st.session_state.analysis_times.append(stock_duration)
                    
                    # Keep only last 50 times
                    if len(st.session_state.analysis_times) > 50:
                        st.session_state.analysis_times = st.session_state.analysis_times[-50:]
                    
                    # Clear individual progress indicators
                    stock_progress_bar.empty()
                    stock_status_text.empty()
                    
                    if 'error' in result:
                        failed_tickers.append((stock_ticker, result['error']))
                    else:
                        results.append(result)
                    
                    # Update time estimate with actual batch performance
                    completed = idx + 1
                    remaining = len(tickers) - completed
                    if completed > 0 and remaining > 0:
                        elapsed_total = time.time() - batch_start_time
                        stocks_per_minute = completed / (elapsed_total / 60)
                        est_remaining_minutes = remaining / stocks_per_minute if stocks_per_minute > 0 else 0
                        est_minutes = int(est_remaining_minutes)
                        est_seconds = int((est_remaining_minutes - est_minutes) * 60)
                        time_estimate_display.info(f"⏱️ Updated estimate: ~{est_minutes}m {est_seconds}s remaining ({completed}/{len(tickers)} complete, {stocks_per_minute:.1f} stocks/min)")
                    
                except Exception as e:
                    stock_progress_bar.empty()
                    stock_status_text.empty()
                    failed_tickers.append((stock_ticker, str(e)))
                
                # Update overall progress
                overall_progress.progress((idx + 1) / len(tickers))
            
            # Clear overall progress and show final time
            batch_end_time = time.time()
            total_duration = batch_end_time - batch_start_time
            total_minutes = int(total_duration // 60)
            total_seconds = int(total_duration % 60)
            overall_status.text(f"✅ Batch analysis complete! (Total time: {total_minutes}m {total_seconds}s)")
            time_estimate_display.success(f"🎉 Analyzed {len(results)} stocks successfully in {total_minutes}m {total_seconds}s")
            time.sleep(1.5)
            overall_progress.empty()
            overall_status.empty()
            time_estimate_display.empty()
            
            # Display results summary
            if results:
                display_multiple_stock_analysis(results, failed_tickers)
            else:
                st.error("❌ All analyses failed!")
                for ticker_name, error_msg in failed_tickers:
                    st.error(f"**{ticker_name}**: {error_msg}")


def display_stock_analysis(result: dict):
    """Display detailed stock analysis results with enhanced rationales."""
    
    # Automatically log complete analysis to archive
    if st.session_state.get('qa_system'):
        try:
            qa_system = st.session_state.qa_system
            recommendation_type = _determine_recommendation_type(result['final_score'])
            
            # Create comprehensive rationale
            agent_rationales = result.get('agent_rationales', {})
            current_date = datetime.now().strftime('%Y-%m-%d')
            final_rationale = f"Investment analysis for {result['ticker']} completed on {current_date}"
            if 'client_layer_agent' in agent_rationales:
                final_rationale = agent_rationales['client_layer_agent'][:500] + "..." if len(agent_rationales.get('client_layer_agent', '')) > 500 else agent_rationales.get('client_layer_agent', final_rationale)
            
            # Log complete analysis
            analysis_id = qa_system.log_complete_analysis(
                ticker=result['ticker'],
                price=result['fundamentals'].get('price', 0),
                recommendation=recommendation_type,
                confidence_score=result['final_score'],
                final_rationale=final_rationale,
                agent_scores=result.get('agent_scores', {}),
                agent_rationales=agent_rationales,
                key_factors=[],  # Will be populated later
                fundamentals=result.get('fundamentals', {}),
                market_data=result.get('market_data', {}),
                sector=result['fundamentals'].get('sector'),
                market_cap=result['fundamentals'].get('market_cap')
            )
            
            if analysis_id:
                # Add a small indicator that analysis was saved
                st.info(f"📚 Analysis automatically saved to archive (ID: {analysis_id})")
                
        except Exception as e:
            st.warning(f"⚠️ Could not auto-save analysis: {e}")
    
    # Header with company info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"{result['ticker']} - Investment Analysis")
        if 'name' in result['fundamentals']:
            st.caption(result['fundamentals']['name'])
        # Display analysis date in MM/DD/YYYY format
        if 'analysis_date' in result:
            try:
                date_obj = datetime.strptime(result['analysis_date'], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m/%d/%Y')
                st.caption(f"Analysis Date: {formatted_date}")
            except:
                st.caption(f"Analysis Date: {result['analysis_date']}")
    with col2:
        # Eligibility badge
        if result['eligible']:
            st.success("✅ ELIGIBLE")
            st.caption("This stock meets all client investment criteria")
        else:
            st.error("❌ NOT ELIGIBLE")
            st.caption("This stock violates one or more client criteria")
    
    # Show which weights were used for this analysis
    weight_preset = st.session_state.get('weight_preset', 'equal_weights')
    if weight_preset == 'custom_weights' and 'locked_custom_weights' in st.session_state:
        with st.expander("⚖️ Custom Weights Used in This Analysis", expanded=False):
            st.info("This analysis used custom agent weights to calculate the final score.")
            
            custom_weights = st.session_state.get('locked_custom_weights', {})
            agent_scores = result.get('agent_scores', {})
            
            if custom_weights and agent_scores:
                st.write("**Weight Distribution & Score Contributions:**")
                
                # Calculate total weight and weighted contributions
                total_weight = sum(custom_weights.values())
                
                # Create a detailed breakdown
                breakdown_data = []
                for agent_key in ['value', 'growth_momentum', 'macro_regime', 'risk', 'sentiment']:
                    # Map to agent score keys
                    score_key = f"{agent_key}_agent"
                    score = agent_scores.get(score_key, 50)
                    weight = custom_weights.get(agent_key, 1.0)
                    contribution = score * weight
                    percentage = (weight / total_weight) * 100
                    
                    breakdown_data.append({
                        'Agent': agent_key.replace('_', ' ').title(),
                        'Weight': f"{weight:.1f}x",
                        'Score': f"{score:.1f}",
                        'Contribution': f"{contribution:.1f}",
                        'Influence': f"{percentage:.1f}%"
                    })
                
                df = pd.DataFrame(breakdown_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Calculate and show final score calculation
                weighted_sum = sum(agent_scores.get(f"{k}_agent", 50) * v for k, v in custom_weights.items())
                calculated_final = weighted_sum / total_weight
                
                st.write(f"**Final Score Calculation:**")
                st.code(f"""
                Weighted Sum = {weighted_sum:.2f}
                Total Weight = {total_weight:.2f}
                Final Score = {weighted_sum:.2f} / {total_weight:.2f} = {calculated_final:.2f}
                """)
                
                st.caption("💡 Higher weights mean that agent's score had MORE influence on the final score.")
    
    elif weight_preset == 'client_profile_weights':
        st.info("ℹ️ This analysis used weights derived from the selected client profile.")
    
    # Enhanced key metrics section
    st.subheader("📊 Enhanced Investment Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        final_score = result['final_score']
        delta_color = "normal" if final_score >= 70 else "inverse" if final_score < 50 else "off"
        st.metric("Final Score", f"{final_score:.1f}/100", help="Overall investment recommendation score")
    with col2:
        price_value = result['fundamentals'].get('price')
        st.metric("Current Price", f"${price_value:.2f}" if price_value and price_value != 0 else "N/A")
    with col3:
        pe_ratio = result['fundamentals']['pe_ratio']
        st.metric("P/E Ratio", f"{pe_ratio:.1f}" if pe_ratio else "N/A", help="Price-to-Earnings ratio")
    with col4:
        beta = result['fundamentals']['beta']
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A", help="Market volatility coefficient")
    
    # Additional Enhanced Metrics Row
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        div_yield = result['fundamentals'].get('dividend_yield')
        if div_yield:
            st.metric("Dividend Yield", f"{div_yield*100:.2f}%", help="Annual dividend yield percentage")
        else:
            st.metric("Dividend Yield", "N/A", help="Annual dividend yield percentage")
    with col6:
        eps = result['fundamentals'].get('eps')
        if eps:
            st.metric("EPS", f"${eps:.2f}", help="Earnings per share")
        else:
            st.metric("EPS", "N/A", help="Earnings per share")
    with col7:
        week_52_low = result['fundamentals'].get('week_52_low')
        week_52_high = result['fundamentals'].get('week_52_high')
        if week_52_low and week_52_high:
            st.metric("52W Range", f"${week_52_low:.2f}-${week_52_high:.2f}", help="52-week price range")
        else:
            st.metric("52W Range", "N/A", help="52-week price range")
    with col8:
        market_cap = result['fundamentals'].get('market_cap')
        if market_cap:
            if market_cap >= 1e12:
                st.metric("Market Cap", f"${market_cap/1e12:.1f}T", help="Market capitalization")
            elif market_cap >= 1e9:
                st.metric("Market Cap", f"${market_cap/1e9:.1f}B", help="Market capitalization")
            else:
                st.metric("Market Cap", f"${market_cap/1e6:.0f}M", help="Market capitalization")
        else:
            st.metric("Market Cap", "N/A", help="Market capitalization")
    
    # 52-Week Range Visualization
    week_52_low = result['fundamentals'].get('week_52_low')
    week_52_high = result['fundamentals'].get('week_52_high')
    current_price = result['fundamentals'].get('price')
    
    if week_52_low and week_52_high and current_price:
        st.subheader("📈 52-Week Price Range")
        
        # Create a simple visualization using Streamlit's native components
        col1, col2, col3 = st.columns([1, 8, 1])
        
        with col1:
            st.metric("52W Low", f"${week_52_low:.2f}")
        
        with col2:
            # Calculate position of current price within the range
            price_position = (current_price - week_52_low) / (week_52_high - week_52_low)
            price_position = max(0, min(1, price_position))  # Clamp between 0 and 1
            
            # Create a visual representation using a progress bar
            st.markdown("**Current Price Position in 52-Week Range:**")
            st.progress(price_position)
            st.markdown(f"**Current: ${current_price:.2f}** ({price_position*100:.1f}% of range)")
            
        with col3:
            st.metric("52W High", f"${week_52_high:.2f}")
    
    # ========== COMPREHENSIVE SCORE ANALYSIS SECTION ==========
    st.markdown("---")
    st.subheader("⚖️ Comprehensive Score Analysis")
    
    with st.expander("📊 Detailed Score Breakdown & Weight Analysis", expanded=False):
        # Get agent scores and weights
        agent_scores = result.get('agent_scores', {})
        blended_score = result.get('blended_score', result.get('final_score', 0))
        
        # Determine which weights were used
        weight_preset = st.session_state.get('weight_preset', 'equal_weights')
        if weight_preset == 'custom_weights' and 'locked_custom_weights' in st.session_state:
            weights_used = st.session_state.locked_custom_weights
            weights_source = "Custom Weights"
        else:
            # Get default weights from orchestrator
            orchestrator = st.session_state.get('orchestrator')
            if orchestrator:
                weights_used = orchestrator.agent_weights
            else:
                weights_used = {
                    'value_agent': 0.25,
                    'growth_momentum_agent': 0.20,
                    'macro_regime_agent': 0.15,
                    'risk_agent': 0.25,
                    'sentiment_agent': 0.15
                }
            weights_source = "Default IPS Weights"
        
        st.write(f"**Weights Source:** {weights_source}")
        st.write("---")
        
        # Calculate weight breakdown
        total_weighted_score = 0
        total_weight = 0
        breakdown_data = []
        
        agent_order = ['value_agent', 'growth_momentum_agent', 'macro_regime_agent', 'risk_agent', 'sentiment_agent']
        agent_labels = {
            'value_agent': '💎 Value',
            'growth_momentum_agent': '📈 Growth/Momentum',
            'macro_regime_agent': '🌍 Macro Regime',
            'risk_agent': '⚠️ Risk',
            'sentiment_agent': '📰 Sentiment'
        }
        
        for agent_key in agent_order:
            score = agent_scores.get(agent_key, 50)
            
            # Map agent key to weight key
            if agent_key == 'value_agent':
                weight_key = 'value_agent'
            elif agent_key == 'growth_momentum_agent':
                weight_key = 'growth_momentum_agent'
            elif agent_key == 'macro_regime_agent':
                weight_key = 'macro_regime_agent'
            elif agent_key == 'risk_agent':
                weight_key = 'risk_agent'
            elif agent_key == 'sentiment_agent':
                weight_key = 'sentiment_agent'
            else:
                weight_key = agent_key
            
            # Get weight - try exact key first, then simplified key
            weight = weights_used.get(weight_key, 1.0)
            if weight == 1.0 and '_agent' in weight_key:
                simplified_key = weight_key.replace('_agent', '')
                weight = weights_used.get(simplified_key, 1.0)
            
            weighted_contribution = score * weight
            total_weighted_score += weighted_contribution
            total_weight += weight
            
            breakdown_data.append({
                'Agent': agent_labels.get(agent_key, agent_key),
                'Score': f"{score:.1f}",
                'Weight': f"{weight:.2f}x",
                'Weighted Score': f"{weighted_contribution:.2f}",
                'Influence': f"{(weight/sum(w for w in [weights_used.get(k, 1.0) for k in agent_order]))*100:.1f}%"
            })
        
        # Display breakdown table
        st.write("**Individual Agent Contributions:**")
        df_breakdown = pd.DataFrame(breakdown_data)
        st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
        
        # Show calculation
        st.write("---")
        st.write("**Final Score Calculation:**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Weighted Sum", f"{total_weighted_score:.2f}", help="Sum of all weighted scores")
        with col2:
            st.metric("Total Weight", f"{total_weight:.2f}", help="Sum of all weights")
        with col3:
            calculated_score = total_weighted_score / total_weight if total_weight > 0 else 50
            st.metric("Blended Score", f"{calculated_score:.2f}", help="Weighted average of all agent scores")
        
        # Show formula
        st.code(f"""
Formula: Blended Score = Weighted Sum / Total Weight
         Blended Score = {total_weighted_score:.2f} / {total_weight:.2f} = {calculated_score:.2f}
        """)
        
        # Weight impact analysis
        st.write("---")
        st.write("**Weight Impact Analysis:**")
        
        # Calculate equal weight score for comparison
        equal_weight_score = sum(float(agent_scores.get(k, 50)) for k in agent_order) / len(agent_order)
        weight_effect = calculated_score - equal_weight_score
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Equal Weight Score", f"{equal_weight_score:.2f}", 
                     help="What the score would be if all weights were 1.0")
        with col2:
            st.metric("Weight Effect", f"{weight_effect:+.2f}", 
                     help="How much the custom weights changed the score",
                     delta=f"{weight_effect:+.2f}")
        
        if abs(weight_effect) > 0.5:
            if weight_effect > 0:
                st.success(f"✅ Custom weights INCREASED the score by {weight_effect:.2f} points by emphasizing higher-scoring agents")
            else:
                st.warning(f"⚠️ Custom weights DECREASED the score by {abs(weight_effect):.2f} points by emphasizing lower-scoring agents")
        else:
            st.info("ℹ️ Custom weights had minimal impact on the final score")
        
        # Visual representation
        st.write("---")
        st.write("**Visual Weight Distribution:**")
        
        # Create bar chart of weights
        chart_data = pd.DataFrame({
            'Agent': [agent_labels.get(k, k) for k in agent_order],
            'Weight': [weights_used.get(k, weights_used.get(k.replace('_agent', ''), 1.0)) for k in agent_order],
            'Score': [agent_scores.get(k, 50) for k in agent_order]
        })
        
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(chart_data.set_index('Agent')['Weight'], use_container_width=True)
            st.caption("Agent Weights (Higher = More Influence)")
        with col2:
            st.bar_chart(chart_data.set_index('Agent')['Score'], use_container_width=True)
            st.caption("Agent Scores (0-100)")
    
    # Enhanced Agent Analysis Section
    st.markdown("---")
    st.subheader("🤖 Multi-Agent Analysis")
    
    # Display enhanced agent rationales with collaboration
    display_enhanced_agent_rationales(result)
    
    # ========== COMPREHENSIVE OVERALL RATIONALE SECTION ==========
    st.markdown("---")
    st.subheader("📋 Comprehensive Investment Rationale")
    
    with st.expander("📄 View Complete Analysis Report", expanded=False):
        # Get the comprehensive rationale from the result
        comprehensive_rationale = result.get('rationale', '')
        
        if comprehensive_rationale:
            # Display in a code block for better formatting
            st.text(comprehensive_rationale)
            
            # Add download button for the rationale
            st.download_button(
                label="📥 Download Complete Rationale (TXT)",
                data=comprehensive_rationale,
                file_name=f"{result['ticker']}_comprehensive_analysis_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                help="Download the complete investment analysis report"
            )
        else:
            st.warning("Comprehensive rationale not available")
        
        # Add a summary section
        st.write("---")
        st.write("**Key Takeaways:**")
        
        # Extract some key points
        agent_scores = result.get('agent_scores', {})
        final_score = result.get('final_score', 0)
        eligible = result.get('eligible', False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Strengths:**")
            strengths = [f"• {k.replace('_agent', '').replace('_', ' ').title()}: {v:.1f}/100" 
                        for k, v in agent_scores.items() if v >= 70]
            if strengths:
                for strength in strengths:
                    st.success(strength)
            else:
                st.info("No exceptional strengths identified")
        
        with col2:
            st.write("**Concerns:**")
            concerns = [f"• {k.replace('_agent', '').replace('_', ' ').title()}: {v:.1f}/100" 
                       for k, v in agent_scores.items() if v < 50]
            if concerns:
                for concern in concerns:
                    st.error(concern)
            else:
                st.success("No major concerns identified")
        
        # Overall assessment
        st.write("---")
        st.write("**Overall Assessment:**")
        
        if not eligible:
            st.error(f"❌ **NOT RECOMMENDED** - While the analysis score is {final_score:.1f}, this investment does not meet client suitability criteria.")
        elif final_score >= 80:
            st.success(f"✅ **STRONG BUY** - Excellent score of {final_score:.1f} with compelling fundamentals and strong multi-factor support.")
        elif final_score >= 70:
            st.success(f"✅ **BUY** - Strong score of {final_score:.1f} indicating good investment potential with favorable risk/reward profile.")
        elif final_score >= 60:
            st.info(f"⚖️ **HOLD** - Moderate score of {final_score:.1f}. Suitable for holding if already owned, but not a priority for new positions.")
        elif final_score >= 40:
            st.warning(f"⚠️ **WEAK HOLD** - Below-average score of {final_score:.1f}. Consider for portfolio review or reduction.")
        else:
            st.error(f"❌ **SELL** - Low score of {final_score:.1f} with significant concerns. Not recommended for client portfolio.")
    
    # Client validation summary
    st.markdown("---")
    st.subheader("✅ Investment Eligibility")
    if result['eligible']:
        st.success("**✅ Approved** - This investment passes all client suitability requirements")
    else:
        st.error("**❌ Rejected** - This investment does not meet client suitability requirements")
        if result['client_layer'].get('violations'):
            st.write("**Specific Violations:**")
            for violation in result['client_layer']['violations']:
                st.write(f"• {violation}")
    
    # Export functionality
    with st.expander("📥 Export Analysis"):
        agent_scores = result['agent_scores']
        export_data = {
            'Ticker': [result['ticker']],
            'Name': [result['fundamentals'].get('name', 'N/A')],
            'Eligible': [result['eligible']],
            'Final Score': [result['final_score']],
            'Sector': [result['fundamentals'].get('sector', 'N/A')],
            'Price': [result['fundamentals'].get('price', 0)],
            **{f"{agent.replace('_', ' ').title()}_Score": [score] for agent, score in agent_scores.items()}
        }
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        
        st.markdown("---")
        
        current_timestamp = datetime.now().strftime('%Y%m%d')
        st.download_button(
            label="📄 Download Analysis Report (CSV)",
            data=csv,
            file_name=f"{result['ticker']}_investment_analysis_{current_timestamp}.csv",
            mime="text/csv"
        )
    
    # QA System Integration - Log for Learning (MOVED OUTSIDE EXPANDER)
    st.markdown("---")
    st.subheader("🎯 Quality Assurance & Learning")
    print(f"🔧 DEBUG: *** REACHED QA SECTION FOR {result['ticker']} ***")
    
    # Check if QA system is available
    qa_system = st.session_state.get('qa_system')
    print(f"🔧 DEBUG: QA system check - Available: {qa_system is not None}")
    if not qa_system:
        st.error("❌ QA System not initialized. Please restart the application to enable learning features.")
        st.info("💡 The QA system tracks recommendation performance and helps improve analysis over time.")
    else:
        try:
            # Show current recommendation details
            recommendation_type = _determine_recommendation_type(result['final_score'])
            confidence_score = result['final_score']
            
            st.write("**Log this analysis for performance tracking and model improvement?**")
            st.write(f"**Recommendation:** {recommendation_type.value.upper()} | **Confidence:** {confidence_score:.1f}/100")
            
            # Check if already logged
            already_logged = result['ticker'] in qa_system.recommendations if qa_system else False
            print(f"🔧 DEBUG: Already logged check for {result['ticker']}: {already_logged}")
            if already_logged:
                st.info(f"ℹ️ {result['ticker']} is already being tracked.")
                st.write("**Ticker is already tracked, but you can click the button to update the tracking.**")
            
            # Always show the button, regardless of tracking status
            st.write("**Available for tracking:**")
            print(f"🔧 DEBUG: About to render button for {result['ticker']}")
            if st.button("🎯 Track Ticker for QA Monitoring", type="primary", use_container_width=True, key=f"track_btn_{result['ticker']}"):
                print(f"🔧 DEBUG: *** BUTTON CLICKED *** Track Ticker button clicked for {result['ticker']}")
                print(f"🔧 DEBUG: *** BUTTON PROCESSING STARTED ***")
                st.success(f"🎯 Button clicked for {result['ticker']}! Processing...")
                try:
                    ticker = result['ticker']
                    print(f"🔧 DEBUG: Processing ticker: {ticker}")
                    
                    # Check if this ticker already exists in the analysis archive
                    analysis_archive = qa_system.get_analysis_archive()
                    print(f"🔧 DEBUG: Analysis archive keys: {list(analysis_archive.keys())}")
                    
                    if ticker in analysis_archive and analysis_archive[ticker]:
                        print(f"🔧 DEBUG: Found {ticker} in analysis archive with {len(analysis_archive[ticker])} analyses")
                        # Use the most recent analysis data (same as Recent Analysis Activity)
                        most_recent_analysis = analysis_archive[ticker][0]  # Already sorted by timestamp desc
                        print(f"🔧 DEBUG: Using analysis from {most_recent_analysis.timestamp}")
                        
                        # Extract data from the existing analysis
                        price = most_recent_analysis.price_at_analysis
                        recommendation_type = most_recent_analysis.recommendation
                        confidence_score = most_recent_analysis.confidence_score
                        rationale = most_recent_analysis.final_rationale
                        agent_scores = most_recent_analysis.agent_scores
                        key_factors = most_recent_analysis.key_factors
                        sector = most_recent_analysis.sector
                        market_cap = most_recent_analysis.market_cap
                        
                        st.info(f"📊 Using existing analysis data from {most_recent_analysis.timestamp.strftime('%m/%d/%Y %H:%M')}")
                    else:
                        # Fallback to current result data if no archive entry exists
                        price = result['fundamentals'].get('price', 100.0)
                        agent_scores = result.get('agent_scores', {})
                        
                        # Create simple rationale
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        rationale = f"Investment analysis for {ticker} completed on {current_date}"
                        
                        # Get basic factors
                        key_factors = ["Financial metrics", "Market analysis", "Risk assessment"]
                        
                        # Get stock info
                        sector = result['fundamentals'].get('sector', 'Unknown')
                        market_cap = result['fundamentals'].get('market_cap')
                    
                    # Log the recommendation (this moves it from analysis archive to tracked tickers)
                    print(f"🔧 DEBUG: About to log recommendation for {ticker} with price {price}")
                    success = qa_system.log_recommendation(
                        ticker=ticker,
                        price=price,
                        recommendation=recommendation_type,
                        confidence_score=confidence_score,
                        rationale=rationale,
                        agent_scores=agent_scores,
                        key_factors=key_factors,
                        sector=sector,
                        market_cap=market_cap
                    )
                    print(f"🔧 DEBUG: log_recommendation returned: {success}")
                    
                    if success:
                        # Force reload QA data from storage to ensure consistency
                        qa_system.recommendations = qa_system._load_recommendations()
                        qa_system.all_analyses = qa_system._load_all_analyses()
                        
                        # Update session state to refresh data
                        st.session_state.qa_system = qa_system
                        
                        # Debug: Show current recommendations count
                        current_count = len(qa_system.get_tracked_tickers())
                        st.success(f"✅ Successfully added {ticker} to tracked tickers!")
                        st.info(f"📊 Total tracked tickers: {current_count}")
                        
                        # Show the actual tickers for verification
                        if current_count > 0:
                            tickers_list = qa_system.get_tracked_tickers()
                            st.info(f"📋 Currently tracking: {', '.join(tickers_list)}")
                            
                        # Provide clear debugging information
                        st.success("🎯 Ticker is now being monitored in the QA system!")
                        st.info("💡 Go to the QA & Learning Center → 🎯 Tracked Tickers tab to see your analysis.")
                        # Since we can't programmatically change radio selection, show clear instruction
                        st.markdown("**👈 Click 'QA & Learning Center' in the sidebar, then go to the '🎯 Tracked Tickers' tab!**")
                        # Removed st.rerun() to prevent page refresh that loses analysis results
                    else:
                        st.error("❌ Failed to log recommendation. Please try again.")
                        
                except Exception as e:
                    st.error(f"❌ Error logging recommendation: {str(e)}")
                    
        except Exception as e:
            st.warning(f"⚠️ Error in QA section: {str(e)}")


def display_multiple_stock_analysis(results: list, failed_tickers: list):
    """Display analysis results for multiple stocks in a comparison table."""
    
    st.success(f"✅ Successfully analyzed {len(results)} stock{'s' if len(results) != 1 else ''}")
    
    if failed_tickers:
        st.warning(f"⚠️ Failed to analyze {len(failed_tickers)} stock{'s' if len(failed_tickers) != 1 else ''}")
        with st.expander("View Failed Tickers", expanded=False):
            for ticker_name, error_msg in failed_tickers:
                st.error(f"**{ticker_name}**: {error_msg}")
    
    # Create summary comparison table
    st.markdown("---")
    st.subheader("📊 Comparison Summary")
    
    # Prepare data for comparison table
    comparison_data = []
    for result in results:
        row = {
            'Ticker': result['ticker'],
            'Final Score': result['final_score'],
            'Eligible': '✅' if result['eligible'] else '❌',
            'Price': result['fundamentals'].get('price', 0),
            'Market Cap': result['fundamentals'].get('market_cap', 0),
            'Sector': result['fundamentals'].get('sector', 'N/A'),
            'Value Score': result.get('agent_scores', {}).get('value_agent', 0),
            'Growth Score': result.get('agent_scores', {}).get('growth_momentum_agent', 0),
            'Macro Score': result.get('agent_scores', {}).get('macro_regime_agent', 0),
            'Risk Score': result.get('agent_scores', {}).get('risk_agent', 0),
            'Sentiment Score': result.get('agent_scores', {}).get('sentiment_agent', 0),
            'Client Score': result.get('agent_scores', {}).get('client_layer_agent', 0),
        }
        comparison_data.append(row)
    
    # Sort by final score (descending)
    comparison_data = sorted(comparison_data, key=lambda x: x['Final Score'], reverse=True)
    
    # Create DataFrame
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    
    # Format numeric columns
    df['Final Score'] = df['Final Score'].round(1)
    df['Price'] = df['Price'].apply(lambda x: f"${x:,.2f}")
    df['Market Cap'] = df['Market Cap'].apply(lambda x: f"${x/1e9:.2f}B" if x >= 1e9 else f"${x/1e6:.2f}M")
    df['Value Score'] = df['Value Score'].round(1)
    df['Growth Score'] = df['Growth Score'].round(1)
    df['Macro Score'] = df['Macro Score'].round(1)
    df['Risk Score'] = df['Risk Score'].round(1)
    df['Sentiment Score'] = df['Sentiment Score'].round(1)
    df['Client Score'] = df['Client Score'].round(1)
    
    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Export to CSV button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Comparison (CSV)",
        data=csv,
        file_name=f"stock_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # 🆕 IMPROVEMENT #1: Visual Comparison Charts
    st.markdown("---")
    st.subheader("📊 Visual Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Agent Scores Comparison Bar Chart
        st.write("**Agent Scores Comparison**")
        agent_categories = ['Value', 'Growth', 'Macro', 'Risk', 'Sentiment']
        
        fig_bar = go.Figure()
        for result in results:
            scores = [
                result['agent_scores'].get('value_agent', 0),
                result['agent_scores'].get('growth_momentum_agent', 0),
                result['agent_scores'].get('macro_regime_agent', 0),
                result['agent_scores'].get('risk_agent', 0),
                result['agent_scores'].get('sentiment_agent', 0)
            ]
            fig_bar.add_trace(go.Bar(
                name=result['ticker'],
                x=agent_categories,
                y=scores,
                text=[f"{s:.1f}" for s in scores],
                textposition='auto'
            ))
        
        fig_bar.update_layout(
            barmode='group',
            yaxis_range=[0, 100],
            yaxis_title="Score",
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # Radar Chart for Multi-Stock Comparison
        st.write("**Multi-Dimensional Comparison**")
        
        fig_radar = go.Figure()
        
        for result in results:
            scores = [
                result['agent_scores'].get('value_agent', 0),
                result['agent_scores'].get('growth_momentum_agent', 0),
                result['agent_scores'].get('macro_regime_agent', 0),
                result['agent_scores'].get('risk_agent', 0),
                result['agent_scores'].get('sentiment_agent', 0),
                result['agent_scores'].get('value_agent', 0)  # Close the polygon
            ]
            
            fig_radar.add_trace(go.Scatterpolar(
                r=scores,
                theta=['Value', 'Growth', 'Macro', 'Risk', 'Sentiment', 'Value'],
                fill='toself',
                name=result['ticker']
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    # Final Score Ranking
    st.write("**Final Score Ranking**")
    fig_final = go.Figure()
    
    tickers = [r['ticker'] for r in results]
    final_scores = [r['final_score'] for r in results]
    colors = [get_gradient_color(score) for score in final_scores]
    
    fig_final.add_trace(go.Bar(
        x=tickers,
        y=final_scores,
        marker_color=colors,
        text=[f"{s:.1f}" for s in final_scores],
        textposition='auto',
        name='Final Score'
    ))
    
    fig_final.update_layout(
        yaxis_range=[0, 100],
        yaxis_title="Final Score",
        xaxis_title="Stock",
        height=350,
        showlegend=False
    )
    st.plotly_chart(fig_final, use_container_width=True)
    
    # Individual stock details in tabs
    st.markdown("---")
    st.subheader("📋 Detailed Analysis by Stock")
    
    tabs = st.tabs([result['ticker'] for result in results])
    
    for idx, (tab, result) in enumerate(zip(tabs, results)):
        with tab:
            display_stock_analysis(result)


def _determine_recommendation_type(final_score: float) -> RecommendationType:
    """Determine recommendation type based on final score."""
    if final_score >= 80:
        return RecommendationType.STRONG_BUY
    elif final_score >= 65:
        return RecommendationType.BUY
    elif final_score >= 45:
        return RecommendationType.HOLD
    elif final_score >= 30:
        return RecommendationType.SELL
    else:
        return RecommendationType.STRONG_SELL


def get_gradient_color(score: float) -> str:
    """Generate gradient color based on score value (0-100).
    Red (low) -> Yellow (medium) -> Green (high)"""
    
    # Normalize score to 0-1 range
    normalized = max(0, min(100, score)) / 100
    
    if normalized <= 0.5:
        # Red to Yellow gradient (0-50)
        ratio = normalized * 2  # 0 to 1
        red = 255
        green = int(255 * ratio)
        blue = 0
    else:
        # Yellow to Green gradient (50-100)
        ratio = (normalized - 0.5) * 2  # 0 to 1
        red = int(255 * (1 - ratio))
        green = 255
        blue = 0
    
    return f"rgb({red},{green},{blue})"


def get_agent_specific_context(agent_key: str, result: dict) -> dict:
    """Get agent-specific context and key metrics for display."""
    
    fundamentals = result.get('fundamentals', {})
    data = result.get('data', {})
    context = {}
    
    if agent_key == 'value_agent':
        context.update({
            'P/E Ratio': f"{fundamentals.get('pe_ratio', 'N/A')}" if fundamentals.get('pe_ratio') else 'N/A',
            'Market Cap': f"${fundamentals.get('market_cap', 0)/1e9:.1f}B" if fundamentals.get('market_cap') else 'N/A',
            'Dividend Yield': f"{fundamentals.get('dividend_yield', 0)*100:.2f}%" if fundamentals.get('dividend_yield') else 'N/A',
            'Price': f"${fundamentals.get('price', 'N/A')}" if fundamentals.get('price') else 'N/A'
        })
    
    elif agent_key == 'growth_momentum_agent':
        context.update({
            'Current Price': f"${fundamentals.get('price', 'N/A')}" if fundamentals.get('price') else 'N/A',
            '52-Week High': f"${fundamentals.get('week_52_high', 'N/A')}" if fundamentals.get('week_52_high') else 'N/A',
            '52-Week Low': f"${fundamentals.get('week_52_low', 'N/A')}" if fundamentals.get('week_52_low') else 'N/A',
            'Volume': f"{fundamentals.get('volume', 'N/A'):,.0f}" if fundamentals.get('volume') else 'N/A'
        })
    
    elif agent_key == 'risk_agent':
        context.update({
            'Beta': f"{fundamentals.get('beta', 'N/A'):.2f}" if fundamentals.get('beta') else 'N/A',
            'Market Cap': f"${fundamentals.get('market_cap', 0)/1e9:.1f}B" if fundamentals.get('market_cap') else 'N/A',
            'Sector': f"{fundamentals.get('sector', 'Unknown')}",
            'Volatility': f"{data.get('volatility', 0)*100:.1f}%" if data.get('volatility') else 'N/A'
        })
    
    elif agent_key == 'sentiment_agent':
        news_count = len(result.get('news', []))
        context.update({
            'News Articles Analyzed': f"{news_count}",
            'Sector': f"{fundamentals.get('sector', 'Unknown')}",
            'Recent Price': f"${fundamentals.get('price', 'N/A')}" if fundamentals.get('price') else 'N/A'
        })
    
    elif agent_key == 'macro_regime_agent':
        context.update({
            'Sector': f"{fundamentals.get('sector', 'Unknown')}",
            'Market Cap Category': get_market_cap_category(fundamentals.get('market_cap', 0)),
            'Beta': f"{fundamentals.get('beta', 'N/A'):.2f}" if fundamentals.get('beta') else 'N/A'
        })
    
    # Remove None values and empty strings
    return {k: v for k, v in context.items() if v is not None and v != 'N/A' and str(v).strip()}


def get_market_cap_category(market_cap: float) -> str:
    """Categorize market cap size."""
    if not market_cap or market_cap == 0:
        return 'Unknown'
    elif market_cap > 200_000_000_000:  # > $200B
        return 'Large Cap'
    elif market_cap > 10_000_000_000:   # $10B - $200B
        return 'Mid Cap'
    else:                               # < $10B
        return 'Small Cap'


def display_enhanced_agent_rationales(result: dict):
    """Display enhanced agent rationales with detailed analysis and collaboration."""
    
    agent_scores = result['agent_scores']
    agent_rationales = result['agent_rationales']
    
    # Exclude client layer agent from individual rationales - it has its own section at bottom
    filtered_scores = {k: v for k, v in agent_scores.items() if k != 'client_layer_agent'}
    filtered_rationales = {k: v for k, v in agent_rationales.items() if k != 'client_layer_agent'}
    
    # Create agent names from filtered keys
    agent_names = [key.replace('_', ' ').title() for key in filtered_scores.keys()]
    
    # Agent collaboration results
    collaboration_results = get_agent_collaboration(result)
    
    # Display agent scores chart
    st.write("**� Agent Score Overview**")
    
    # Create bar chart with gradient colors (excluding client layer agent)
    fig = go.Figure()
    gradient_colors = [get_gradient_color(score) for score in filtered_scores.values()]
    
    fig.add_trace(go.Bar(
        x=agent_names,
        y=list(filtered_scores.values()),
        marker_color=gradient_colors,
        text=[f"{s:.1f}" for s in filtered_scores.values()],
        textposition='auto',
        name='Scores'
    ))
    
    fig.update_layout(
        title="Agent Analysis Scores",
        xaxis_title="",
        yaxis_title="Score",
        yaxis_range=[0, 100],
        height=350,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Individual Agent Rationales Section
    st.write("---")
    st.write("**🧠 Individual Agent Analysis**")
    
    # Create detailed rationale display for each agent (excluding client layer agent)
    for i, (agent_key, agent_name) in enumerate(zip(filtered_scores.keys(), agent_names)):
        score = filtered_scores[agent_key]
        rationale = filtered_rationales.get(agent_key, "Analysis not available")
        
        # Create expandable section for each agent
        with st.expander(f"**{agent_name}** - Score: {score:.1f}/100", expanded=False):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Score display with gradient color
                score_color = get_gradient_color(score)
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {score_color}, {score_color}aa);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
                ">
                    <h2 style="margin: 0; color: white;">{score:.1f}</h2>
                    <p style="margin: 0; color: white;">out of 100</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Score interpretation
                if score >= 80:
                    st.success("🟢 **Excellent**\nStrong positive signals")
                elif score >= 65:
                    st.info("🔵 **Good**\nPositive with minor concerns")
                elif score >= 50:
                    st.warning("🟡 **Moderate**\nMixed signals")
                elif score >= 35:
                    st.error("🟠 **Concerning**\nSeveral negative factors")
                else:
                    st.error("🔴 **Poor**\nSignificant issues identified")
            
            with col2:
                st.write("**Detailed Analysis:**")
                
                # Display the rationale with proper formatting
                if isinstance(rationale, str) and rationale.strip():
                    # Clean up and format the rationale text
                    formatted_rationale = rationale.replace("\\n", "\n").strip()
                    
                    # Split into paragraphs for better readability
                    paragraphs = [p.strip() for p in formatted_rationale.split('\n') if p.strip()]
                    
                    for paragraph in paragraphs:
                        if paragraph.startswith('**') or paragraph.startswith('##'):
                            st.markdown(paragraph)
                        else:
                            st.write(paragraph)
                else:
                    st.info("Detailed rationale not available for this agent.")
                
                # Add agent-specific context based on agent type
                agent_context = get_agent_specific_context(agent_key, result)
                if agent_context:
                    st.write("**Key Metrics:**")
                    for key, value in agent_context.items():
                        if value is not None:
                            st.write(f"• **{key}**: {value}")


def analyze_client_fit(ticker: str, result: dict, client_data: dict = None) -> dict:  # type: ignore
    """
    Analyze how well a stock fits the client's investment restrictions and preferences using
    advanced LLM analysis with complete client profile and all agent scores and rationales.
    """
    
    if not client_data:
        # Try to get client data from session state or default profile
        if 'selected_profile' in st.session_state:
            try:
                from utils.client_profile_manager import ClientProfileManager
                profile_manager = ClientProfileManager()
                client_data = profile_manager.load_client_profile(st.session_state['selected_profile'])
            except:
                client_data = {}
        else:
            client_data = {}
    
    # If still no client data, create default
    if not client_data:
        client_data = {
            'risk_tolerance': 'moderate',
            'investment_style': 'balanced',
            'time_horizon': 'medium',
            'restricted_sectors': [],
            'max_position_pct': 5,
            'return_expectation': 'moderate'
        }
    
    # Extract comprehensive analysis data
    agent_scores = result.get('agent_scores', {})
    agent_rationales = result.get('agent_rationales', {})
    fundamentals = result.get('fundamentals', {})
    final_score = result.get('final_score', 50)
    
    # Generate comprehensive client fit analysis using OpenAI
    try:
        openai_client = st.session_state.get('openai_client')
        if openai_client:
            return _generate_llm_client_fit_analysis(
                ticker, client_data, agent_scores, agent_rationales, 
                fundamentals, final_score, openai_client
            )
    except Exception as e:
        print(f"Warning: LLM client fit analysis failed: {e}")
    
    # Fallback to rule-based analysis if LLM fails
    return _generate_fallback_client_fit_analysis(
        ticker, client_data, agent_scores, fundamentals, final_score
    )


def _generate_llm_client_fit_analysis(
    ticker: str, 
    client_data: dict, 
    agent_scores: dict, 
    agent_rationales: dict,
    fundamentals: dict,
    final_score: float,
    openai_client
) -> dict:
    """Generate comprehensive client fit analysis using OpenAI with complete context."""
    
    # Prepare comprehensive prompt with all available data
    client_profile_text = _format_client_profile_for_llm(client_data)
    agent_analysis_text = _format_agent_analysis_for_llm(agent_scores, agent_rationales)
    stock_fundamentals_text = _format_stock_fundamentals_for_llm(ticker, fundamentals, final_score)
    
    prompt = f"""You are an expert investment advisor conducting a comprehensive client suitability analysis.

TASK: Analyze how well the stock {ticker} fits this specific client's investment profile, constraints, and objectives.

CLIENT PROFILE:
{client_profile_text}

COMPREHENSIVE STOCK ANALYSIS:
{stock_fundamentals_text}

DETAILED AGENT ANALYSIS:
{agent_analysis_text}

ANALYSIS REQUIREMENTS:
1. Provide a numerical fit score (0-100) based on comprehensive suitability analysis
2. Identify specific positive factors that align with client requirements
3. Identify specific negative factors that conflict with client constraints
4. Provide neutral factors that are neither strongly positive nor negative
5. Give an overall fit assessment (excellent/good/moderate/poor/incompatible)
6. Include specific IPS compliance considerations
7. Address risk tolerance alignment, investment style match, sector restrictions, position sizing
8. Consider time horizon compatibility and return expectations

OUTPUT FORMAT (JSON):
{{
    "fit_score": <0-100 numerical score>,
    "overall_fit": "<excellent|good|moderate|poor|incompatible>",
    "positive_factors": [
        "Specific positive alignment factor 1",
        "Specific positive alignment factor 2"
    ],
    "negative_factors": [
        "Specific concern or constraint violation 1", 
        "Specific concern or constraint violation 2"
    ],
    "neutral_factors": [
        "Neutral factor 1",
        "Neutral factor 2"
    ],
    "ips_compliance": {{
        "fully_compliant": ["Compliant area 1", "Compliant area 2"],
        "requires_attention": ["Area needing attention 1"],
        "violations": ["Violation 1 if any"]
    }},
    "recommendation": "Detailed investment recommendation with specific position sizing and monitoring requirements",
    "key_risks": ["Primary risk 1", "Primary risk 2"],
    "monitoring_requirements": ["Monitor factor 1", "Monitor factor 2"]
}}

Ensure your analysis is thorough, specific, and directly addresses the client's unique profile and constraints."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )
        
        import json
        analysis_text = response.choices[0].message.content
        
        # Extract JSON from response
        if '```json' in analysis_text:
            json_start = analysis_text.find('```json') + 7
            json_end = analysis_text.find('```', json_start)
            analysis_text = analysis_text[json_start:json_end]
        elif '{' in analysis_text:
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            analysis_text = analysis_text[json_start:json_end]
        
        analysis = json.loads(analysis_text)
        
        # Validate and normalize the response
        return _validate_and_normalize_llm_response(analysis, ticker)
        
    except Exception as e:
        print(f"Error: LLM client fit analysis failed: {e}")
        raise


def _format_client_profile_for_llm(client_data: dict) -> str:
    """Format client profile data for LLM analysis."""
    profile_text = []
    
    if client_data.get('name'):
        profile_text.append(f"Client: {client_data['name']}")
    
    profile_text.append(f"Risk Tolerance: {client_data.get('risk_tolerance', 'moderate').title()}")
    profile_text.append(f"Investment Style: {client_data.get('investment_style', 'balanced').title()}")
    profile_text.append(f"Time Horizon: {client_data.get('time_horizon', 'medium').title()}")
    profile_text.append(f"Return Expectation: {client_data.get('return_expectation', 'moderate').title()}")
    
    if client_data.get('restricted_sectors'):
        sectors = client_data['restricted_sectors']
        if isinstance(sectors, str):
            sectors = [s.strip() for s in sectors.split(',')]
        profile_text.append(f"Restricted Sectors: {', '.join(sectors)}")
    
    profile_text.append(f"Maximum Position Size: {client_data.get('max_position_pct', 5)}%")
    
    if client_data.get('market_cap_preference'):
        profile_text.append(f"Market Cap Preference: {client_data['market_cap_preference']}")
    
    if client_data.get('esg_preference'):
        profile_text.append(f"ESG Preference: {client_data['esg_preference']}")
    
    if client_data.get('income_requirement'):
        profile_text.append(f"Income Requirement: {client_data['income_requirement']}")
    
    if client_data.get('liquidity_needs'):
        profile_text.append(f"Liquidity Needs: {client_data['liquidity_needs']}")
    
    return '\n'.join(profile_text)


def _format_agent_analysis_for_llm(agent_scores: dict, agent_rationales: dict) -> str:
    """Format agent analysis data for LLM."""
    analysis_text = []
    
    agent_names = {
        'value_agent': 'Value Analysis',
        'growth_momentum_agent': 'Growth & Momentum Analysis', 
        'macro_regime_agent': 'Macro Economic Analysis',
        'risk_agent': 'Risk Analysis',
        'sentiment_agent': 'Market Sentiment Analysis'
    }
    
    for agent_key, display_name in agent_names.items():
        score = agent_scores.get(agent_key, 50)
        rationale = agent_rationales.get(agent_key, "Analysis not available")
        
        analysis_text.append(f"\n{display_name}: {score:.1f}/100")
        analysis_text.append(f"Rationale: {rationale}")
    
    return '\n'.join(analysis_text)


def _format_stock_fundamentals_for_llm(ticker: str, fundamentals: dict, final_score: float) -> str:
    """Format stock fundamentals for LLM analysis."""
    fund_text = [f"Stock: {ticker}"]
    fund_text.append(f"Overall Analysis Score: {final_score:.1f}/100")
    
    if fundamentals.get('name'):
        fund_text.append(f"Company: {fundamentals['name']}")
    
    if fundamentals.get('sector'):
        fund_text.append(f"Sector: {fundamentals['sector']}")
    
    if fundamentals.get('price'):
        fund_text.append(f"Current Price: ${fundamentals['price']:.2f}")
    
    if fundamentals.get('market_cap'):
        mc = fundamentals['market_cap']
        if mc > 1_000_000_000:
            fund_text.append(f"Market Cap: ${mc/1_000_000_000:.1f}B")
        else:
            fund_text.append(f"Market Cap: ${mc/1_000_000:.0f}M")
    
    if fundamentals.get('pe_ratio'):
        fund_text.append(f"P/E Ratio: {fundamentals['pe_ratio']:.1f}")
    
    if fundamentals.get('beta'):
        fund_text.append(f"Beta: {fundamentals['beta']:.2f}")
    
    if fundamentals.get('dividend_yield'):
        fund_text.append(f"Dividend Yield: {fundamentals['dividend_yield']*100:.2f}%")
    
    if fundamentals.get('week_52_low') and fundamentals.get('week_52_high'):
        fund_text.append(f"52-Week Range: ${fundamentals['week_52_low']:.2f} - ${fundamentals['week_52_high']:.2f}")
    
    return '\n'.join(fund_text)


def _validate_and_normalize_llm_response(analysis: dict, ticker: str) -> dict:
    """Validate and normalize LLM response to ensure consistency."""
    
    # Ensure required keys exist
    normalized = {
        'fit_score': max(0, min(100, analysis.get('fit_score', 50))),
        'overall_fit': analysis.get('overall_fit', 'moderate'),
        'positive_factors': analysis.get('positive_factors', []),
        'negative_factors': analysis.get('negative_factors', []),
        'neutral_factors': analysis.get('neutral_factors', []),
        'ips_compliance': analysis.get('ips_compliance', {}),
        'recommendation': analysis.get('recommendation', f"Analysis completed for {ticker}"),
        'key_risks': analysis.get('key_risks', []),
        'monitoring_requirements': analysis.get('monitoring_requirements', [])
    }
    
    # Validate overall_fit values
    valid_fits = ['excellent', 'good', 'moderate', 'poor', 'incompatible']
    if normalized['overall_fit'] not in valid_fits:
        normalized['overall_fit'] = 'moderate'
    
    # Ensure IPS compliance structure
    normalized['ips_compliance'] = {
        'fully_compliant': normalized['ips_compliance'].get('fully_compliant', []),
        'requires_attention': normalized['ips_compliance'].get('requires_attention', []),
        'violations': normalized['ips_compliance'].get('violations', [])
    }
    
    return normalized


def _generate_fallback_client_fit_analysis(
    ticker: str, 
    client_data: dict, 
    agent_scores: dict, 
    fundamentals: dict,
    final_score: float
) -> dict:
    """Fallback rule-based analysis if LLM fails."""
    
    # Basic rule-based analysis
    risk_score = agent_scores.get('risk_agent', 50) or 50
    value_score = agent_scores.get('value_agent', 50) or 50
    growth_score = agent_scores.get('growth_momentum_agent', 50) or 50
    
    # Get stock data for sector/industry analysis
    sector = fundamentals.get('sector', 'Unknown')
    market_cap = fundamentals.get('market_cap') or 0
    
    fit_score = 50  # Start at neutral
    positive_factors = []
    negative_factors = []
    neutral_factors = []
    
    # Risk tolerance analysis
    risk_tolerance = client_data.get('risk_tolerance', 'moderate').lower()
    if risk_tolerance == 'low' and risk_score > 70:
        negative_factors.append(f"High risk score ({risk_score:.1f}) conflicts with conservative risk tolerance")
        fit_score -= 15
    elif risk_tolerance == 'high' and risk_score < 40:
        negative_factors.append(f"Low risk score ({risk_score:.1f}) may not meet aggressive growth expectations")
        fit_score -= 10
    elif risk_tolerance == 'moderate' and 40 <= risk_score <= 70:
        positive_factors.append(f"Risk profile ({risk_score:.1f}) aligns with moderate risk tolerance")
        fit_score += 10
    
    # Investment style analysis
    investment_style = client_data.get('investment_style', 'balanced').lower()
    if investment_style == 'value' and value_score > 65:
        positive_factors.append(f"Strong value characteristics ({value_score:.1f}) match value investment style")
        fit_score += 15
    elif investment_style == 'growth' and growth_score > 65:
        positive_factors.append(f"Strong growth potential ({growth_score:.1f}) aligns with growth investment style")
        fit_score += 15
    elif investment_style == 'balanced':
        avg_score = (value_score + growth_score) / 2
        if avg_score > 55:
            positive_factors.append(f"Balanced value/growth profile ({avg_score:.1f}) suits balanced approach")
            fit_score += 10
    
    # Sector restrictions
    restricted_sectors = client_data.get('restricted_sectors', [])
    if restricted_sectors and isinstance(restricted_sectors, str):
        restricted_sectors = [s.strip().lower() for s in restricted_sectors.split(',')]
    elif isinstance(restricted_sectors, list):
        restricted_sectors = [s.lower() for s in restricted_sectors]
    
    if restricted_sectors and sector.lower() in restricted_sectors:
        negative_factors.append(f"Stock is in restricted sector: {sector}")
        fit_score -= 30
    
    # Overall score considerations
    if final_score > 70:
        positive_factors.append(f"Strong overall analysis score ({final_score:.1f})")
        fit_score += 10
    elif final_score < 40:
        negative_factors.append(f"Weak overall analysis score ({final_score:.1f})")
        fit_score -= 15
    
    # Determine overall fit
    fit_score = max(0, min(100, fit_score))
    
    if fit_score >= 75:
        overall_fit = 'high'
    elif fit_score >= 60:
        overall_fit = 'good'  
    elif fit_score >= 40:
        overall_fit = 'moderate'
    elif fit_score >= 25:
        overall_fit = 'poor'
    else:
        overall_fit = 'incompatible'
    
    # Add some neutral factors if we don't have many
    if len(positive_factors) + len(negative_factors) < 3:
        neutral_factors.append(f"Market cap: ${market_cap/1_000_000:.0f}M")
        neutral_factors.append(f"Sector: {sector}")
    
    fit_analysis = {
        'fit_score': fit_score,
        'overall_fit': overall_fit,
        'positive_factors': positive_factors,
        'negative_factors': negative_factors,
        'neutral_factors': neutral_factors,
        'ips_compliance': {
            'fully_compliant': ["Basic suitability assessment completed"],
            'requires_attention': [],
            'violations': []
        },
        'recommendation': f"Fallback analysis completed for {ticker}. Consider detailed manual review.",
        'key_risks': ["Limited analysis depth", "Rule-based assessment only"],
        'monitoring_requirements': ["Regular portfolio review", "Performance monitoring"]
    }
    
    return fit_analysis


def generate_comprehensive_ips_compliance_analysis(ticker: str, result: dict, client_fit: dict, client_data: dict = None) -> dict:  # type: ignore
    """Generate comprehensive IPS compliance analysis with detailed score breakdown and specific rationale."""
    
    if not client_data:
        if 'selected_profile' in st.session_state:
            try:
                from utils.client_profile_manager import ClientProfileManager
                profile_manager = ClientProfileManager()
                client_data = profile_manager.load_client_profile(st.session_state['selected_profile'])
            except:
                client_data = {}
        else:
            client_data = {}
    
    # Extract comprehensive metrics for detailed analysis
    agent_scores = result.get('agent_scores', {})
    risk_score = agent_scores.get('risk_agent', 50) or 50
    value_score = agent_scores.get('value_agent', 50) or 50
    growth_score = agent_scores.get('growth_momentum_agent', 50) or 50
    sentiment_score = agent_scores.get('sentiment_agent', 50) or 50
    macro_score = agent_scores.get('macro_regime_agent', 50) or 50
    
    stock_data = result.get('data', {})
    fundamentals = result.get('fundamentals', {})
    final_score = result.get('final_score', 50)
    
    # Extract detailed financial metrics
    sector = (stock_data.get('sector') or fundamentals.get('sector') or 'Unknown')
    market_cap = fundamentals.get('market_cap') or 0
    pe_ratio = fundamentals.get('pe_ratio')
    beta = fundamentals.get('beta')
    # Treat 0 as None for dividend_yield (0 means no dividend data, not 0% yield)
    dividend_yield = fundamentals.get('dividend_yield')
    if dividend_yield == 0:
        dividend_yield = None
    price = fundamentals.get('price', 0)
    
    # Initialize comprehensive analysis structure
    analysis = {
        'fit_score_breakdown': {
            'base_score': 50,
            'adjustments': [],
            'final_calculated_score': client_fit.get('fit_score', 50)
        },
        'ips_compliance_detailed': {
            'fully_compliant': [],
            'partially_compliant': [],
            'non_compliant': [],
            'requires_attention': []
        },
        'score_explanation': {
            'why_this_score': '',
            'why_not_higher': [],
            'why_not_lower': [],
            'key_factors': []
        },
        'investment_constraints_analysis': {},
        'recommendation_rationale': ''
    }
    
    # COMPREHENSIVE IPS COMPLIANCE ANALYSIS
    
    # 1. RISK TOLERANCE COMPLIANCE ANALYSIS
    risk_tolerance = client_data.get('risk_tolerance', 'moderate').lower()
    
    if risk_tolerance == 'conservative':
        if risk_score > 80:
            analysis['ips_compliance_detailed']['non_compliant'].append({
                'constraint': 'Conservative Risk Tolerance',
                'violation': f'Risk score {risk_score:.1f}/100 significantly exceeds conservative limits',
                'impact': 'Major compliance violation - unsuitable for conservative investor',
                'score_impact': -20
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Risk Tolerance Violation', -20))
        elif risk_score > 65:
            analysis['ips_compliance_detailed']['requires_attention'].append({
                'constraint': 'Conservative Risk Tolerance',
                'concern': f'Risk score {risk_score:.1f}/100 at upper boundary of conservative tolerance',
                'mitigation': 'Reduced position size (max 3-4% allocation) and enhanced monitoring required',
                'score_impact': -10
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Risk Tolerance Concern', -10))
        elif risk_score > 50:
            analysis['ips_compliance_detailed']['partially_compliant'].append({
                'constraint': 'Conservative Risk Tolerance',
                'status': f'Risk score {risk_score:.1f}/100 within acceptable range with conditions',
                'conditions': 'Standard position sizing (max 5% allocation) with quarterly reviews',
                'score_impact': -5
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Risk Tolerance Conditional', -5))
        else:
            analysis['ips_compliance_detailed']['fully_compliant'].append({
                'constraint': 'Conservative Risk Tolerance',
                'compliance': f'Risk score {risk_score:.1f}/100 fully compliant with conservative parameters',
                'benefit': 'Suitable for core conservative portfolio allocation up to 7%',
                'score_impact': +5
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Risk Tolerance Match', +5))
    
    elif risk_tolerance == 'aggressive':
        if risk_score < 40:
            analysis['ips_compliance_detailed']['partially_compliant'].append({
                'constraint': 'Aggressive Risk Tolerance',
                'status': f'Risk score {risk_score:.1f}/100 below aggressive targets but acceptable',
                'note': 'May not maximize return potential given risk tolerance',
                'score_impact': -5
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Below Risk Target', -5))
        else:
            analysis['ips_compliance_detailed']['fully_compliant'].append({
                'constraint': 'Aggressive Risk Tolerance',
                'compliance': f'Risk score {risk_score:.1f}/100 aligns with aggressive risk parameters',
                'benefit': 'Suitable for growth-oriented allocations up to 10%',
                'score_impact': +8
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Risk Tolerance Match', +8))
    
    # 2. INVESTMENT STYLE COMPLIANCE
    investment_style = client_data.get('investment_style', 'balanced').lower()
    
    if 'value' in investment_style:
        if value_score > 75:
            # Build metrics string with available data
            metrics_parts = []
            if pe_ratio:
                metrics_parts.append(f'P/E ratio {pe_ratio:.1f}x')
            if dividend_yield:
                metrics_parts.append(f'dividend yield {dividend_yield*100:.1f}%')
            metrics_str = ', '.join(metrics_parts) if metrics_parts else 'Strong value characteristics confirmed'
            
            analysis['ips_compliance_detailed']['fully_compliant'].append({
                'constraint': 'Value Investment Style',
                'compliance': f'Value score {value_score:.1f}/100 strongly matches value mandate',
                'metrics': metrics_str,
                'score_impact': +12
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Value Style Strong Match', +12))
        elif value_score > 55:
            analysis['ips_compliance_detailed']['partially_compliant'].append({
                'constraint': 'Value Investment Style',
                'status': f'Value score {value_score:.1f}/100 provides moderate value characteristics',
                'conditions': 'Acceptable for blended value approach with reduced allocation',
                'score_impact': +5
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Value Style Moderate', +5))
        else:
            analysis['ips_compliance_detailed']['requires_attention'].append({
                'constraint': 'Value Investment Style',
                'concern': f'Value score {value_score:.1f}/100 insufficient for value mandate',
                'recommendation': 'Consider alternative value opportunities or style drift analysis',
                'score_impact': -8
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Value Style Mismatch', -8))
    
    # 3. SECTOR RESTRICTIONS COMPLIANCE
    restricted_sectors = client_data.get('restricted_sectors', [])
    if isinstance(restricted_sectors, str):
        restricted_sectors = [s.strip() for s in restricted_sectors.split(',')]
    
    if restricted_sectors:
        sector_violation = any(sector.lower() in rs.lower() or rs.lower() in sector.lower() 
                              for rs in restricted_sectors if rs.strip())
        if sector_violation:
            analysis['ips_compliance_detailed']['non_compliant'].append({
                'constraint': 'Sector Restrictions',
                'violation': f'{sector} sector explicitly prohibited in IPS',
                'restricted_list': ', '.join(restricted_sectors),
                'impact': 'Absolute exclusion - cannot be held regardless of other merits',
                'score_impact': -50  # Major penalty
            })
            analysis['fit_score_breakdown']['adjustments'].append(('Sector Restriction Violation', -50))
        else:
            analysis['ips_compliance_detailed']['fully_compliant'].append({
                'constraint': 'Sector Restrictions',
                'compliance': f'{sector} sector approved - not in restricted list',
                'cleared_restrictions': ', '.join(restricted_sectors),
                'score_impact': 0
            })
    
    # 4. POSITION SIZE CONSTRAINTS
    max_position = client_data.get('max_position_pct', 5)
    if risk_score > 70:
        recommended_position = min(max_position, 3)
        analysis['investment_constraints_analysis']['position_sizing'] = {
            'max_allowed': f'{max_position}%',
            'recommended': f'{recommended_position}%',
            'rationale': f'Reduced from {max_position}% due to elevated risk score ({risk_score:.1f})',
            'compliance_status': 'Requires reduced sizing'
        }
        analysis['fit_score_breakdown']['adjustments'].append(('Position Size Constraint', -3))
    else:
        analysis['investment_constraints_analysis']['position_sizing'] = {
            'max_allowed': f'{max_position}%',
            'recommended': f'{max_position}%',
            'rationale': f'Standard sizing appropriate given risk score ({risk_score:.1f})',
            'compliance_status': 'Fully compliant'
        }
    
    # 5. LIQUIDITY REQUIREMENTS
    if market_cap < 1_000_000_000:  # Less than $1B
        analysis['ips_compliance_detailed']['requires_attention'].append({
            'constraint': 'Liquidity Requirements',
            'concern': f'${market_cap/1e6:.0f}M market cap may present liquidity constraints',
            'mitigation': 'Reduced position size and extended trading timeframes required',
            'score_impact': -8
        })
        analysis['fit_score_breakdown']['adjustments'].append(('Liquidity Concern', -8))
    elif market_cap > 10_000_000_000:  # Greater than $10B
        analysis['ips_compliance_detailed']['fully_compliant'].append({
            'constraint': 'Liquidity Requirements',
            'compliance': f'${market_cap/1e9:.1f}B market cap provides excellent liquidity',
            'benefit': 'Enables flexible position sizing and efficient execution',
            'score_impact': +3
        })
        analysis['fit_score_breakdown']['adjustments'].append(('Liquidity Advantage', +3))
    
    # CALCULATE FINAL SCORE AND EXPLANATIONS
    base_score = analysis['fit_score_breakdown']['base_score']
    total_adjustments = sum(adj[1] for adj in analysis['fit_score_breakdown']['adjustments'])
    calculated_score = max(0, min(100, base_score + total_adjustments))
    
    analysis['fit_score_breakdown']['final_calculated_score'] = calculated_score
    
    # DETAILED SCORE EXPLANATION
    actual_fit_score = client_fit.get('fit_score', calculated_score)
    
    analysis['score_explanation']['why_this_score'] = f"""
    The {actual_fit_score:.0f}/100 client fit score reflects a comprehensive IPS compliance analysis:
    
    BASE SCORE: {base_score}/100 (neutral starting point)
    ADJUSTMENTS: {total_adjustments:+.0f} points from IPS factors
    CALCULATED: {calculated_score:.0f}/100
    """
    
    # Why not higher?
    if actual_fit_score < 80:
        negative_adjustments = [adj for adj in analysis['fit_score_breakdown']['adjustments'] if adj[1] < 0]
        analysis['score_explanation']['why_not_higher'] = [
            f"{factor}: {impact:+.0f} points" for factor, impact in negative_adjustments
        ]
    
    # Why not lower?  
    if actual_fit_score > 40:
        positive_adjustments = [adj for adj in analysis['fit_score_breakdown']['adjustments'] if adj[1] > 0]
        analysis['score_explanation']['why_not_lower'] = [
            f"{factor}: {impact:+.0f} points" for factor, impact in positive_adjustments  
        ]
    
    # Key factors
    significant_factors = [adj for adj in analysis['fit_score_breakdown']['adjustments'] if abs(adj[1]) >= 5]
    analysis['score_explanation']['key_factors'] = [
        f"{factor} ({impact:+.0f})" for factor, impact in significant_factors
    ]
    
    # FINAL RECOMMENDATION
    compliance_violations = len(analysis['ips_compliance_detailed']['non_compliant'])
    attention_items = len(analysis['ips_compliance_detailed']['requires_attention'])
    
    if compliance_violations > 0:
        analysis['recommendation_rationale'] = f"NOT SUITABLE: {compliance_violations} IPS violation(s) present. Major constraints prevent investment regardless of financial merits."
    elif attention_items > 2:
        analysis['recommendation_rationale'] = f"PROCEED WITH CAUTION: {attention_items} items require attention. Enhanced due diligence and modified parameters necessary."
    elif actual_fit_score >= 70:
        analysis['recommendation_rationale'] = f"SUITABLE: Strong IPS alignment with score of {actual_fit_score}/100. Standard investment process and sizing appropriate."
    elif actual_fit_score >= 50:
        analysis['recommendation_rationale'] = f"CONDITIONALLY SUITABLE: Moderate fit ({actual_fit_score}/100) with specific conditions. Reduced sizing and enhanced monitoring recommended."
    else:
        analysis['recommendation_rationale'] = f"POOR FIT: Low compatibility ({actual_fit_score}/100) with client IPS. Consider alternatives better aligned with constraints."
    
    return analysis


def get_agent_collaboration(result: dict) -> dict:
    """Generate collaboration insights between agents."""
    collaboration = {}
    
    agent_scores = result['agent_scores']
    
    # Value vs Growth/Momentum collaboration
    if 'value_agent' in agent_scores and 'growth_momentum_agent' in agent_scores:
        value_score = agent_scores['value_agent']
        growth_score = agent_scores['growth_momentum_agent']
        
        if abs(value_score - growth_score) < 10:
            collaboration['value_agent'] = f"Growth agent agrees (score: {growth_score:.1f}) - balanced value/growth profile"
            collaboration['growth_momentum_agent'] = f"Value agent concurs (score: {value_score:.1f}) - well-balanced investment"
        elif value_score > growth_score + 15:
            collaboration['value_agent'] = f"Growth agent disagrees (score: {growth_score:.1f}) - potential value trap concern"
            collaboration['growth_momentum_agent'] = f"Value agent sees opportunity (score: {value_score:.1f}) - momentum may be lacking"
        else:
            collaboration['value_agent'] = f"Growth agent is more optimistic (score: {growth_score:.1f}) - growth may justify premium"
            collaboration['growth_momentum_agent'] = f"Value agent is cautious (score: {value_score:.1f}) - high growth expectations"
    
    # Risk vs Sentiment collaboration
    if 'risk_agent' in agent_scores and 'sentiment_agent' in agent_scores:
        risk_score = agent_scores['risk_agent']
        sentiment_score = agent_scores['sentiment_agent']
        
        if risk_score > 70 and sentiment_score > 70:
            collaboration['risk_agent'] = f"Sentiment agent confirms (score: {sentiment_score:.1f}) - low risk supported by positive sentiment"
            collaboration['sentiment_agent'] = f"Risk agent validates (score: {risk_score:.1f}) - positive sentiment backed by solid risk profile"
        elif risk_score < 50 and sentiment_score < 50:
            collaboration['risk_agent'] = f"Sentiment agent agrees (score: {sentiment_score:.1f}) - high risk confirmed by negative sentiment"
            collaboration['sentiment_agent'] = f"Risk agent concurs (score: {risk_score:.1f}) - negative sentiment reflects real risks"
    
    return collaboration


def get_detailed_agent_analysis(agent_key: str, result: dict) -> str:
    """Generate detailed analysis for each agent based on available data."""
    
    fundamentals = result['fundamentals']
    ticker = result['ticker']
    score = result['agent_scores'].get(agent_key, 0)
    
    # Map display agent keys to orchestrator agent keys
    agent_key_mapping = {
        'value_agent': 'value',
        'growth_momentum_agent': 'growth_momentum', 
        'risk_agent': 'risk',
        'sentiment_agent': 'sentiment',
        'macro_regime_agent': 'macro_regime'
    }
    
    # Use the mapped key for agent details lookup
    mapped_key = agent_key_mapping.get(agent_key, agent_key)
    
    if agent_key == 'value_agent':
        value_details = result.get('agent_details', {}).get(mapped_key, {})
        component_scores = value_details.get('component_scores', {})
        
        # Use the ACTUAL agent score, not the passed score parameter
        actual_value_score = result['agent_scores'].get(agent_key, score)
        
        pe_ratio = value_details.get('pe_ratio', fundamentals.get('pe_ratio', 0))
        price = fundamentals.get('price', 0)
        sector = fundamentals.get('sector', 'Unknown')
        pe_discount = value_details.get('pe_discount_pct', 0)
        # Get dividend yield, treating 0 as None
        div_yield = value_details.get('dividend_yield_pct', fundamentals.get('dividend_yield'))
        if div_yield == 0:
            div_yield = None
        ev_ebitda = value_details.get('ev_ebitda', 'N/A')
        fcf_yield = value_details.get('fcf_yield_pct', 0)
        
        pe_score = component_scores.get('pe_score', 50)
        ev_score = component_scores.get('ev_ebitda_score', 50)
        fcf_score = component_scores.get('fcf_yield_score', 50)
        yield_score = component_scores.get('shareholder_yield_score', 50)
        
        analysis = f"""
**Comprehensive Value Analysis for {ticker}:**

**Current Valuation Overview:**
Trading at ${price:.2f} with a {actual_value_score:.1f}/100 value score, representing {'exceptional value' if actual_value_score >= 80 else 'good value' if actual_value_score >= 70 else 'fair value' if actual_value_score >= 50 else 'poor value'} opportunity.

**Detailed Valuation Metrics:**

**1. P/E Ratio Analysis** (Score: {pe_score:.1f}/100)
- Current P/E: {pe_ratio:.1f}x
- Sector Premium/Discount: {pe_discount:+.1f}%
- Assessment: {'Excellent discount' if pe_discount > 15 else 'Good discount' if pe_discount > 5 else 'Fair pricing' if pe_discount > -5 else 'Premium pricing' if pe_discount > -15 else 'Significant premium'}
- Implication: {'Strong value signal' if pe_score >= 70 else 'Moderate value signal' if pe_score >= 50 else 'Overvaluation concern'}

**2. EV/EBITDA Multiple** (Score: {ev_score:.1f}/100)
- Current EV/EBITDA: {ev_ebitda if ev_ebitda != 'N/A' else 'Data unavailable'}
- {'Attractive enterprise valuation' if ev_score >= 70 else 'Reasonable valuation' if ev_score >= 50 else 'Expensive enterprise valuation' if ev_ebitda != 'N/A' else 'Unable to assess enterprise value'}

**3. Free Cash Flow Yield** (Score: {fcf_score:.1f}/100)
- FCF Yield: {fcf_yield:.1f}%
- {'Excellent cash generation' if fcf_yield > 8 else 'Good cash flow' if fcf_yield > 5 else 'Moderate cash generation' if fcf_yield > 2 else 'Weak cash flow' if fcf_yield > 0 else 'Negative cash flow'}
- Cash return to investors: {'Very attractive' if fcf_score >= 70 else 'Decent' if fcf_score >= 50 else 'Concerning'}

**4. Dividend Yield & Shareholder Returns** (Score: {yield_score:.1f}/100)
- Dividend Yield: {f'{div_yield*100:.1f}%' if div_yield else 'N/A (likely growth-focused company)'}
- Income Potential: {'High income' if div_yield and div_yield > 0.04 else 'Moderate income' if div_yield and div_yield > 0.02 else 'Low/No dividend income (growth reinvestment strategy)' if div_yield and div_yield > 0 else 'No dividend (growth-focused)'}

**Value Investment Thesis:**
{'Strong value opportunity with multiple attractive metrics supporting potential outperformance' if actual_value_score >= 75 else
 'Reasonable value play with selective attractive characteristics' if actual_value_score >= 60 else
 'Mixed value signals requiring careful analysis' if actual_value_score >= 45 else
 'Limited value appeal with overvaluation concerns'}

**Sector Context ({sector}):**
{sector} sector valuation comparison shows this stock is {'significantly undervalued' if pe_discount > 20 else 'moderately undervalued' if pe_discount > 10 else 'fairly valued' if pe_discount > -10 else 'overvalued'} relative to peers.

**Investment Strategy Implications:**
- **Value Style:** {'Core value holding' if actual_value_score >= 70 else 'Opportunistic value play' if actual_value_score >= 50 else 'Value trap risk'}
- **Time Horizon:** {'Long-term value realization expected' if actual_value_score >= 60 else 'Extended holding period may be required'}
- **Risk/Reward:** {'Favorable risk-adjusted returns potential' if actual_value_score >= 65 else 'Balanced risk/reward profile' if actual_value_score >= 50 else 'Higher risk relative to value potential'}
"""
    
    elif agent_key == 'growth_momentum_agent':
        # Use the ACTUAL agent score, not the passed score parameter
        actual_growth_score = result['agent_scores'].get(agent_key, score)
        
        beta = fundamentals.get('beta', 1.0)
        sector = fundamentals.get('sector', 'Unknown')
        
        analysis = f"""
**Growth & Momentum Analysis for {ticker}:**

Beta coefficient of {beta:.2f} indicates {'higher' if beta > 1.2 else 'moderate' if beta > 0.8 else 'lower'} 
volatility relative to market. {sector} sector positioning provides context for growth expectations.

**Growth Indicators:**
- Revenue Growth: Analyzing recent quarters for acceleration/deceleration
- Earnings Growth: Tracking EPS progression and guidance
- Market Share: Competitive position and expansion opportunities

**Momentum Factors:**
- Technical indicators suggest {'strong positive' if actual_growth_score >= 70 else 'mixed' if actual_growth_score >= 50 else 'weak'} momentum
- Volume and price action analysis
- Relative strength vs sector and market

**Growth Score Reasoning:**
{'Excellent growth trajectory with strong momentum indicators' if actual_growth_score >= 70 else
 'Moderate growth potential with some momentum factors' if actual_growth_score >= 50 else
 'Limited growth visibility and weak momentum signals'}

**Forward Outlook:**
Growth sustainability depends on continued market expansion, competitive advantages, 
and management execution of strategic initiatives.
"""
    
    elif agent_key == 'risk_agent':
        risk_details = result.get('agent_details', {}).get(mapped_key, {})
        component_scores = risk_details.get('component_scores', {})
        
        # Use the ACTUAL agent score, not the passed score parameter
        actual_risk_score = result['agent_scores'].get(agent_key, score)
        
        beta = risk_details.get('beta', fundamentals.get('beta', 1.0))
        sector = fundamentals.get('sector', 'Unknown')
        is_low_risk = risk_details.get('is_low_risk_asset', False)
        risk_boost = risk_details.get('risk_boost_applied', 0)
        volatility = risk_details.get('volatility_pct')
        max_drawdown = risk_details.get('max_drawdown_pct')
        
        vol_score = component_scores.get('volatility_score', 50)
        beta_score = component_scores.get('beta_score', 50)
        dd_score = component_scores.get('drawdown_score', 50)
        div_score = component_scores.get('diversification_score', 50)
        
        analysis = f"""
**Comprehensive Risk Assessment for {ticker}:**

{'🏛️ **Large-Cap Classification:** Recognized as inherently lower risk due to institutional size, market liquidity, and regulatory oversight.' if is_low_risk else '**Standard Risk Assessment:** Evaluated using traditional risk metrics without size-based adjustments.'}

**Detailed Risk Metrics:**
- **Market Beta:** {beta:.2f} (Score: {beta_score:.1f}/100)
  - {'Market-neutral positioning' if abs(beta - 1.0) < 0.2 else f'{"Higher" if beta > 1.2 else "Lower"} volatility than market'}
  - Systematic risk exposure {'well-controlled' if beta_score >= 70 else 'moderate' if beta_score >= 50 else 'concerning'}

- **Price Volatility:** {f'{volatility:.1f}%' if volatility else 'N/A'} annualized (Score: {vol_score:.1f}/100)
  - {'Low volatility suggests stable price action' if volatility and volatility < 20 else 'Moderate volatility within normal range' if volatility and volatility < 35 else 'High volatility indicates price instability' if volatility else 'Volatility data unavailable'}

- **Maximum Drawdown:** {f'{max_drawdown:.1f}%' if max_drawdown else 'N/A'} (Score: {dd_score:.1f}/100)
  - {'Excellent downside protection' if max_drawdown and max_drawdown > -10 else 'Good risk management' if max_drawdown and max_drawdown > -20 else 'Concerning downside risk' if max_drawdown else 'Historical drawdown data unavailable'}

- **Portfolio Diversification:** Score {div_score:.1f}/100
  - {'Strong diversification benefit for portfolio construction' if div_score >= 70 else 'Moderate diversification value' if div_score >= 50 else 'Limited diversification benefit'}

{'**Institutional Risk Adjustment:** +' + str(risk_boost) + ' points applied recognizing large-cap stability, liquidity advantages, and reduced default risk' if risk_boost > 0 else ''}

**Risk Assessment Summary:**
Based on the {actual_risk_score:.1f}/100 risk score, this asset is classified as {'extremely low risk' if actual_risk_score >= 90 else 'low risk' if actual_risk_score >= 70 else 'moderate risk' if actual_risk_score >= 50 else 'high risk'}. 

**Investment Implications:**
- **Position Sizing:** {'Suitable for large allocations in conservative portfolios' if actual_risk_score >= 80 else 'Appropriate for moderate allocations' if actual_risk_score >= 60 else 'Requires careful position sizing'}
- **Portfolio Role:** {'Core holding providing stability' if is_low_risk else 'Strategic allocation based on risk tolerance'}
- **Monitoring:** {'Standard quarterly review sufficient' if actual_risk_score >= 70 else 'Monthly monitoring recommended' if actual_risk_score >= 50 else 'Active monitoring required'}

**Sector Context ({sector}):**
Technology sector typically exhibits moderate to high volatility but offers growth potential. {'This large-cap position provides sector exposure with reduced volatility' if is_low_risk else 'Standard sector risk characteristics apply'}.
"""
    
    elif agent_key == 'sentiment_agent':
        # Use the ACTUAL agent score, not the passed score parameter
        actual_sentiment_score = result['agent_scores'].get(agent_key, score)
        
        # Get detailed sentiment analysis including articles
        sentiment_details = result.get('agent_details', {}).get(mapped_key, {})
        article_details = sentiment_details.get('article_details', [])
        key_events = sentiment_details.get('key_events', [])
        num_articles = sentiment_details.get('num_articles', 0)
        
        analysis = f"""
**Market Sentiment Analysis for {ticker}:**

Analyzed {num_articles} recent articles to assess market sentiment and narrative trends.

**Key Events Detected:**
{', '.join(key_events) if key_events else 'No significant events detected in recent news coverage'}

**Sentiment Score Interpretation:**
{'Very positive sentiment with broad bullish consensus across news sources' if actual_sentiment_score >= 70 else
 'Mixed sentiment with balanced perspectives in media coverage' if actual_sentiment_score >= 50 else
 'Negative sentiment with bearish undertones in recent reporting'}

**Recent News Articles:**"""
        
        if article_details:
            for i, article in enumerate(article_details, 1):
                analysis += f"""

**Article {i}: {article['source']}**
- **Title:** {article['title']}
- **Published:** {article['published_at']}
- **Description:** {article['description']}
- **Link:** {article['url'] if article['url'] else 'No link available'}
"""
        else:
            analysis += "\n\nNo detailed article information available. Analysis based on headline sentiment only."
        
        analysis += f"""

**Market Implications:**
- News sentiment {'supports' if actual_sentiment_score >= 60 else 'challenges' if actual_sentiment_score <= 40 else 'provides mixed signals for'} current stock valuation
- Media narrative {'reinforces positive' if actual_sentiment_score >= 70 else 'creates neutral' if actual_sentiment_score >= 50 else 'contributes to negative'} investor expectations
- Contrarian opportunities may exist if sentiment reaches extreme levels

**Risk Considerations:**
Sentiment can shift rapidly based on new developments. Monitor for narrative changes that could impact investor perception.
"""
    
    elif agent_key == 'macro_regime_agent':
        # Use the ACTUAL agent score, not the passed score parameter
        actual_macro_score = result['agent_scores'].get(agent_key, score)
        
        analysis = f"""
**Macroeconomic Environment Analysis:**

Current macroeconomic regime assessment and impact on {ticker}:

**Economic Cycle Position:**
- GDP growth trends and economic expansion/contraction signals
- Interest rate environment and Federal Reserve policy stance
- Inflation trends and purchasing power considerations

**Market Regime Analysis:**
- Bull/bear market characteristics and typical sector rotation patterns
- Volatility environment and risk appetite indicators
- Currency trends and international trade considerations

**Sector-Specific Macro Factors:**
- How current macro environment affects {fundamentals.get('sector', 'this')} sector
- Regulatory environment and policy changes
- Global supply chain and commodity price impacts

**Macro Score Rationale:**
{'Favorable macro environment supporting stock performance' if actual_macro_score >= 70 else
 'Mixed macro signals requiring careful monitoring' if actual_macro_score >= 50 else
 'Challenging macro headwinds affecting outlook'}

**Forward-Looking Indicators:**
Monitor leading indicators for regime changes that could impact positioning.
"""
    
    else:
        analysis = f"""
**Comprehensive Analysis for {agent_key.replace('_', ' ').title()}:**

Detailed assessment pending enhanced agent implementation. 
Current score of {score:.1f} reflects preliminary analysis.

Please refer to the basic rationale above for current insights.
"""
    
    return analysis.strip()


def extract_key_factors(agent_key: str, result: dict) -> list:
    """Extract key factors that influenced each agent's decision."""
    
    fundamentals = result['fundamentals']
    score = result['agent_scores'].get(agent_key, 0)
    
    factors = []
    
    if agent_key == 'value_agent':
        pe_ratio = fundamentals.get('pe_ratio', 0)
        if pe_ratio and pe_ratio < 15:
            factors.append(f"Low P/E ratio ({pe_ratio:.1f}) suggests undervaluation")
        elif pe_ratio and pe_ratio > 25:
            factors.append(f"High P/E ratio ({pe_ratio:.1f}) indicates premium valuation")
        
        dividend_yield = fundamentals.get('dividend_yield')
        # Treat 0 as None for dividend yield (0 means no data, not 0% yield)
        if dividend_yield and dividend_yield > 0.03:  # 3% as decimal (0.03)
            factors.append(f"Attractive dividend yield ({dividend_yield*100:.1f}%)")
    
    elif agent_key == 'growth_momentum_agent':
        beta = fundamentals.get('beta', 1.0)
        if beta > 1.5:
            factors.append(f"High beta ({beta:.2f}) indicates strong market sensitivity")
        elif beta < 0.5:
            factors.append(f"Low beta ({beta:.2f}) suggests defensive characteristics")
    
    elif agent_key == 'risk_agent':
        beta = fundamentals.get('beta', 1.0)
        if beta < 0.8:
            factors.append("Low beta suggests reduced portfolio risk")
        elif beta > 1.5:
            factors.append("High beta increases portfolio volatility")
    
    # Add score-based factors
    if score >= 80:
        factors.append("Exceptionally strong fundamentals in this category")
    elif score >= 70:
        factors.append("Strong positive indicators across key metrics")
    elif score < 40:
        factors.append("Significant concerns in multiple areas")
    
    return factors


def portfolio_recommendations_page():
    """Portfolio recommendation page with AI-powered selection."""
    st.header("🎯 AI-Powered Portfolio Recommendations")
    st.write("Multi-stage AI selection using OpenAI and Perplexity to identify optimal stocks.")
    st.markdown("---")
    
    # Challenge context input
    st.subheader("📋 Investment Challenge Context")
    challenge_context = st.text_area(
        "Describe the investment challenge, goals, and requirements:",
        value="""Generate an optimal diversified portfolio that maximizes risk-adjusted returns 
while adhering to the client's Investment Policy Statement constraints.
Focus on high-quality companies with strong fundamentals and growth potential.""",
        height=120,
        help="Provide detailed context about the investment challenge"
    )
    
    st.markdown("---")
    
    # Configuration options
    with st.expander("⚙️ Portfolio Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            selection_mode = st.selectbox(
                "Selection Mode",
                ["AI-Powered Selection (Recommended)", "Manual Ticker Input"],
                help="AI-Powered uses OpenAI + Perplexity to select best tickers across ALL market caps"
            )
        
        with col2:
            num_positions = st.number_input(
                "Target Portfolio Positions",
                min_value=3,
                max_value=20,
                value=5,
                help="Target number of holdings in portfolio (up to 20 for diversified growth)"
            )
    
    # Advanced options
    with st.expander("🎛️ Investment Focus & Strategy"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Investment Focus**")
            focus_value = st.checkbox("Emphasize Value (Undervalued stocks)", value=False)
            focus_growth = st.checkbox("Emphasize Growth & Momentum", value=False)
            focus_upside = st.checkbox("Emphasize Potential Upside (High-growth niche stocks)", value=False, 
                                      help="Discover small-cap and emerging companies with massive growth potential")
            focus_dividend = st.checkbox("Emphasize Dividend Income", value=False)
            focus_lowrisk = st.checkbox("Emphasize Low Volatility", value=False)
        
        with col2:
            st.markdown("**Portfolio Strategy**")
            sector_constraint = st.selectbox(
                "Sector Diversification",
                ["No Preference", "Tech-Heavy", "Tech-Light", "Diversified Only"],
                help="Control sector concentration"
            )
            
            market_cap_pref = st.selectbox(
                "Market Cap Preference",
                ["All Market Caps (Best opportunities anywhere)", 
                 "Small & Mid Cap Focus (Higher growth potential)", 
                 "Large Cap Focus (Established companies)",
                 "Mix of All Sizes"],
                index=0,
                help="Define which company sizes to prioritize"
            )
    
    # Build custom instructions from advanced options
    custom_instructions = []
    if focus_value:
        custom_instructions.append("Prioritize value stocks with low P/E ratios, strong fundamentals, and attractive valuations.")
    if focus_growth:
        custom_instructions.append("Seek high-growth companies with strong revenue acceleration and momentum indicators.")
    if focus_upside:
        custom_instructions.append("CRITICAL: Discover hidden gems - small-cap, mid-cap, and emerging companies with MASSIVE growth potential. Look beyond well-known names. Seek niche players, disruptors, and companies in high-growth sectors (AI, biotech, clean energy, fintech, SaaS, semiconductors). Market cap is NOT a constraint - find the best opportunities regardless of size.")
    if focus_dividend:
        custom_instructions.append("Include dividend-paying stocks with sustainable yields above 2%.")
    if focus_lowrisk:
        custom_instructions.append("Favor low-beta stocks with reduced volatility and defensive characteristics.")
    
    if sector_constraint == "Tech-Heavy":
        custom_instructions.append("Allocate 40-60% to technology sector stocks.")
    elif sector_constraint == "Tech-Light":
        custom_instructions.append("Limit technology sector exposure to 20% maximum.")
    elif sector_constraint == "Diversified Only":
        custom_instructions.append("Ensure no single sector exceeds 25% of portfolio weight.")
    
    if market_cap_pref == "Small & Mid Cap Focus (Higher growth potential)":
        custom_instructions.append("Focus primarily on small-cap ($300M-$2B) and mid-cap ($2B-$10B) companies with high growth potential.")
    elif market_cap_pref == "Large Cap Focus (Established companies)":
        custom_instructions.append("Focus on large-cap companies ($10B+) with established market positions.")
    elif market_cap_pref == "Mix of All Sizes":
        custom_instructions.append("Include a balanced mix of small-cap, mid-cap, and large-cap companies.")
    else:  # All Market Caps
        custom_instructions.append("Consider companies of ALL sizes - from small-cap emerging players to mega-cap leaders. Find the best opportunities regardless of market capitalization.")
    
    # Append custom instructions to challenge context
    if custom_instructions:
        challenge_context += "\n\nAdditional Requirements:\n" + "\n".join(f"- {inst}" for inst in custom_instructions)
    
    # Manual ticker input (optional)
    if selection_mode == "Manual Ticker Input":
        custom_tickers = st.text_area(
            "Enter Tickers (comma-separated):",
            value="AAPL, MSFT, GOOGL, AMZN, NVDA",
            help="Enter stock tickers separated by commas"
        )
        tickers = [t.strip().upper() for t in custom_tickers.split(',') if t.strip()]
    else:
        tickers = None  # Will use AI selection
        st.info("""
        🤖 **AI Selection Process:**
        1. OpenAI selects 20 best tickers
        2. Perplexity selects 20 best tickers  
        3. Aggregate to 40 unique candidates
        4. Generate 4-sentence rationale for each
        5. Run 3 rounds of top-5 selection
        6. Consolidate to final 5 tickers
        7. Full analysis on all final selections
        """)
    
    if st.button("🚀 Generate Portfolio", type="primary", use_container_width=True):
        with st.spinner("🤖 Running AI-powered portfolio generation..."):
            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Generate recommendations
                status_text.text("Stage 1/4: AI Ticker Selection (Searching ALL market caps for best opportunities)...")
                progress_bar.progress(25)
                
                result = st.session_state.orchestrator.recommend_portfolio(
                    challenge_context=challenge_context,
                    tickers=tickers,
                    num_positions=num_positions
                )
                
                status_text.text("Stage 2/4: Analyzing Stocks...")
                progress_bar.progress(50)
                
                status_text.text("Stage 3/4: Constructing Portfolio...")
                progress_bar.progress(75)
                
                status_text.text("Stage 4/4: Finalizing Recommendations...")
                progress_bar.progress(100)
                
                status_text.text("✅ Portfolio generation complete!")
                
                # Store result in session state
                st.session_state.portfolio_result = result
                
                # Log ALL analyzed stocks to QA archive (every stock gets same treatment as individual analysis)
                status_text.text("📝 Logging all analyzed stocks to QA archive...")
                all_analyses = result.get('all_analyses', [])
                for analysis in all_analyses:
                    try:
                        # Convert analysis dict to StockAnalysis object if needed
                        if not hasattr(analysis, 'ticker'):
                            # It's already a dict, convert to StockAnalysis-like object
                            from types import SimpleNamespace
                            analysis_obj = SimpleNamespace(**analysis)
                            # Convert nested dicts
                            if 'fundamentals' in analysis and isinstance(analysis['fundamentals'], dict):
                                analysis_obj.fundamentals = SimpleNamespace(**analysis['fundamentals'])
                            if 'agent_scores' in analysis and isinstance(analysis['agent_scores'], dict):
                                analysis_obj.agent_scores = analysis['agent_scores']
                            if 'agent_rationales' in analysis and isinstance(analysis['agent_rationales'], dict):
                                analysis_obj.agent_rationales = analysis['agent_rationales']
                            if 'recommendation' in analysis:
                                # Convert string recommendation to RecommendationType enum
                                from utils.qa_system import RecommendationType
                                rec_str = analysis['recommendation'].upper()
                                # Map orchestrator recommendations to QA system types
                                if 'STRONG BUY' in rec_str or 'STRONG_BUY' in rec_str:
                                    analysis_obj.recommendation = RecommendationType.STRONG_BUY
                                elif 'BUY' in rec_str:
                                    analysis_obj.recommendation = RecommendationType.BUY
                                elif 'STRONG SELL' in rec_str or 'STRONG_SELL' in rec_str:
                                    analysis_obj.recommendation = RecommendationType.STRONG_SELL
                                elif 'SELL' in rec_str or 'AVOID' in rec_str:
                                    analysis_obj.recommendation = RecommendationType.SELL
                                elif 'HOLD' in rec_str:
                                    analysis_obj.recommendation = RecommendationType.HOLD
                                else:
                                    # Default to HOLD if unclear
                                    analysis_obj.recommendation = RecommendationType.HOLD
                            analysis = analysis_obj
                        
                        # Log to QA system using correct method
                        if hasattr(st.session_state, 'qa_system') and st.session_state.qa_system:
                            # Extract values from either dict or SimpleNamespace
                            ticker = getattr(analysis, 'ticker', None) or analysis.get('ticker') if isinstance(analysis, dict) else getattr(analysis, 'ticker', 'UNKNOWN')
                            
                            # Get fundamentals first to extract price
                            fundamentals = getattr(analysis, 'fundamentals', {}) if hasattr(analysis, 'fundamentals') else analysis.get('fundamentals', {}) if isinstance(analysis, dict) else {}
                            
                            # Extract price from fundamentals (portfolio analysis stores it there)
                            if isinstance(fundamentals, dict):
                                fund_dict = fundamentals
                            elif hasattr(fundamentals, '__dict__'):
                                fund_dict = fundamentals.__dict__
                            elif hasattr(fundamentals, 'get'):
                                fund_dict = fundamentals
                            else:
                                fund_dict = {}
                            
                            price = fund_dict.get('price', 0) if fund_dict else 0
                            
                            # Get confidence score from final_score (portfolio analysis uses this)
                            confidence = getattr(analysis, 'final_score', 0) if hasattr(analysis, 'final_score') else analysis.get('final_score', 0) if isinstance(analysis, dict) else 0
                            
                            recommendation = getattr(analysis, 'recommendation', RecommendationType.HOLD)
                            final_rationale = getattr(analysis, 'rationale', 'Portfolio generation analysis') if hasattr(analysis, 'rationale') else analysis.get('rationale', 'Portfolio generation analysis') if isinstance(analysis, dict) else 'Portfolio generation analysis'
                            agent_scores = getattr(analysis, 'agent_scores', {}) if hasattr(analysis, 'agent_scores') else analysis.get('agent_scores', {}) if isinstance(analysis, dict) else {}
                            agent_rationales = getattr(analysis, 'agent_rationales', {}) if hasattr(analysis, 'agent_rationales') else analysis.get('agent_rationales', {}) if isinstance(analysis, dict) else {}
                            
                            st.session_state.qa_system.log_complete_analysis(
                                ticker=ticker,
                                price=price,
                                recommendation=recommendation,
                                confidence_score=confidence,
                                final_rationale=final_rationale,
                                agent_scores=agent_scores,
                                agent_rationales=agent_rationales,
                                key_factors=[],
                                fundamentals=fund_dict,
                                sector=fund_dict.get('sector'),
                                market_cap=fund_dict.get('market_cap')
                            )
                    except Exception as e:
                        # Get ticker safely for error message
                        ticker = 'unknown'
                        if isinstance(analysis, dict):
                            ticker = analysis.get('ticker', 'unknown')
                        elif hasattr(analysis, 'ticker'):
                            ticker = analysis.ticker  # type: ignore
                        st.warning(f"Failed to log {ticker} to QA archive: {e}")
                
                status_text.text(f"✅ Logged {len(all_analyses)} analyses to QA archive")
                
                # Auto-update Google Sheets if enabled
                if st.session_state.sheets_auto_update and st.session_state.sheets_integration.sheet:
                    status_text.text("📊 Updating Google Sheets...")
                    
                    # Update both QA Analyses sheet (all stocks) and Portfolio Recommendations sheet (selected only)
                    sheets_success = update_google_sheets_portfolio(result)
                    
                    # Also update QA analyses with all analyzed stocks
                    if hasattr(st.session_state, 'qa_system') and st.session_state.qa_system:
                        qa_archive = st.session_state.qa_system.get_analysis_archive()
                        update_google_sheets_qa_analyses(qa_archive)
                    
                    if sheets_success:
                        st.success("✅ Google Sheets updated successfully!")
                    else:
                        st.warning("⚠️ Google Sheets update failed (see logs)")
                
                # Display results
                display_portfolio_recommendations(result)
                
            except Exception as e:
                st.error(f"❌ Portfolio generation failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def display_portfolio_recommendations(result: dict):
    """Display portfolio recommendations with AI selection details."""
    
    portfolio = result['portfolio']
    summary = result['summary']
    selection_log = result.get('selection_log', {})
    
    if not portfolio:
        st.warning("No eligible stocks found in universe")
        return
    
    # AI Selection Summary (if available)
    if not selection_log.get('manual_selection', False):
        st.subheader("🤖 AI Selection Process")
        
        with st.expander("View AI Selection Details", expanded=False):
            stages = selection_log.get('stages', [])
            
            for stage_info in stages:
                stage = stage_info.get('stage', 'Unknown')
                
                if stage == 'openai_initial_selection':
                    st.markdown("#### 1️⃣ OpenAI Initial Selection")
                    tickers = stage_info.get('tickers', [])
                    st.write(f"Selected {len(tickers)} tickers: {', '.join(tickers)}")
                
                elif stage == 'perplexity_initial_selection':
                    st.markdown("#### 2️⃣ Perplexity Initial Selection")
                    tickers = stage_info.get('tickers', [])
                    st.write(f"Selected {len(tickers)} tickers: {', '.join(tickers)}")
                
                elif stage == 'aggregation':
                    st.markdown("#### 3️⃣ Aggregation")
                    count = stage_info.get('count', 0)
                    st.write(f"Total unique candidates: **{count}** tickers")
                
                elif stage == 'rationale_generation':
                    st.markdown("#### 4️⃣ Rationale Generation")
                    rationales = stage_info.get('ticker_rationales', {})
                    st.write(f"Generated 4-sentence rationales for {len(rationales)} tickers")
                
                elif stage == 'final_selection_rounds':
                    st.markdown("#### 5️⃣ Final Selection Rounds")
                    round_1 = stage_info.get('round_1', [])
                    round_2 = stage_info.get('round_2', [])
                    round_3 = stage_info.get('round_3', [])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("**Round 1:**")
                        st.write(", ".join(round_1))
                    with col2:
                        st.write("**Round 2:**")
                        st.write(", ".join(round_2))
                    with col3:
                        st.write("**Round 3:**")
                        st.write(", ".join(round_3))
                
                elif stage == 'final_consolidation':
                    st.markdown("#### 6️⃣ Final Consolidation")
                    unique = stage_info.get('unique_finalists', [])
                    final = stage_info.get('final_5', [])
                    st.write(f"Unique finalists: {len(unique)} → Final selection: **{len(final)}**")
                    st.success(f"✅ Final tickers: {', '.join(final)}")
            
            # Download log
            import json
            log_json = json.dumps(selection_log, indent=2)
            st.download_button(
                label="📥 Download Full Selection Log (JSON)",
                data=log_json,
                file_name=f"ai_selection_log_{result['analysis_date']}.json",
                mime="application/json"
            )
        
        # Download complete archives section
        st.markdown("---")
        st.subheader("📦 Complete Archives")
        st.write("Download all portfolio selection logs and archives from the system.")
        
        import os
        import zipfile
        from io import BytesIO
        
        # Check if portfolio_selection_logs directory exists
        logs_dir = "portfolio_selection_logs"
        if os.path.exists(logs_dir) and os.path.isdir(logs_dir):
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
            
            if log_files:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info(f"📊 Found **{len(log_files)}** archived portfolio selection(s)")
                
                with col2:
                    # Create ZIP file in memory
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Add all JSON files
                        for log_file in log_files:
                            file_path = os.path.join(logs_dir, log_file)
                            with open(file_path, 'r') as f:
                                zip_file.writestr(log_file, f.read())
                        
                        # Add README if exists
                        readme_path = os.path.join(logs_dir, 'README.md')
                        if os.path.exists(readme_path):
                            with open(readme_path, 'r') as f:
                                zip_file.writestr('README.md', f.read())
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="📦 Download All Archives (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"portfolio_archives_{result['analysis_date']}.zip",
                        mime="application/zip",
                        use_container_width=True,
                        help="Download all portfolio selection logs as a ZIP file"
                    )
                
                # Show list of available archives
                with st.expander("📋 View Available Archives", expanded=False):
                    for log_file in sorted(log_files, reverse=True):
                        file_path = os.path.join(logs_dir, log_file)
                        file_size = os.path.getsize(file_path)
                        file_size_kb = file_size / 1024
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(f"📄 {log_file}")
                        with col2:
                            st.text(f"{file_size_kb:.1f} KB")
                        with col3:
                            # Individual download
                            with open(file_path, 'r') as f:
                                st.download_button(
                                    label="⬇️",
                                    data=f.read(),
                                    file_name=log_file,
                                    mime="application/json",
                                    key=f"download_{log_file}"
                                )
            else:
                st.info("📭 No archived selections found yet. Generate a portfolio to create archives.")
        else:
            st.warning("📂 Portfolio selection logs directory not found.")
    
    st.markdown("---")
    
    # Summary metrics
    st.subheader("📊 Portfolio Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Positions", summary['num_positions'])
    with col2:
        st.metric("Invested Capital", f"{summary['total_weight_pct']:.1f}%")
    with col3:
        st.metric("Average Score", f"{summary['avg_score']:.1f}")
    with col4:
        st.metric("Selection Method", summary.get('selection_method', 'N/A'))
    with col5:
        st.metric("Analyzed", f"{result.get('total_analyzed', 0)}")
    
    # Holdings table with AI rationales
    st.subheader("📈 Portfolio Holdings")
    
    for i, holding in enumerate(portfolio, 1):
        with st.expander(f"{i}. {holding['ticker']} - {holding['name']} ({holding['sector']})", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.metric("Final Score", f"{holding['final_score']:.1f}/100")
                st.metric("Weight", f"{holding['target_weight_pct']:.1f}%")
                st.metric("Recommendation", holding['recommendation'])
            
            with col2:
                st.markdown("**AI Rationale:**")
                st.write(holding['rationale'])
    
    # Detailed table
    st.subheader("📋 Holdings Table")
    df = pd.DataFrame(portfolio)
    df = df[['ticker', 'name', 'sector', 'final_score', 'target_weight_pct', 'eligible']]
    df.columns = ['Ticker', 'Name', 'Sector', 'Score', 'Weight %', 'Eligible']
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                help="Final composite score",
                min_value=0,
                max_value=100,
            ),
            "Eligible": st.column_config.CheckboxColumn(
                "Eligible",
                help="Meets IPS requirements"
            ),
        }
    )
    
    # Sector allocation
    st.subheader("🥧 Sector Allocation")
    
    sector_data = summary['sector_exposure']
    fig = go.Figure(data=[go.Pie(
        labels=list(sector_data.keys()),
        values=list(sector_data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(height=400, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    st.subheader("📥 Export Portfolio")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export basic CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Portfolio CSV",
            data=csv,
            file_name=f"portfolio_recommendations_{result['analysis_date']}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export full analysis JSON
        import json
        full_data = {
            'portfolio': portfolio,
            'summary': summary,
            'analysis_date': result['analysis_date'],
            'selection_log': selection_log
        }
        json_data = json.dumps(full_data, indent=2, default=str)
        st.download_button(
            label="Download Full Analysis (JSON)",
            data=json_data,
            file_name=f"portfolio_full_analysis_{result['analysis_date']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # Manual Google Sheets export
        if st.session_state.sheets_integration.sheet:
            if st.button("📊 Push to Google Sheets", use_container_width=True):
                with st.spinner("Updating Google Sheets..."):
                    success = update_google_sheets_portfolio(result)
                    if success:
                        st.success("✅ Updated!")
                        sheet_url = st.session_state.sheets_integration.get_sheet_url()
                        if sheet_url:
                            st.markdown(f"[📄 Open Sheet]({sheet_url})")
                    else:
                        st.error("❌ Update failed")
        else:
            st.info("Connect to Google Sheet in sidebar")


# Backtesting functionality removed as requested


def parse_client_profile_with_ai(client_profile_text: str) -> dict:
    """Use OpenAI to parse client profile text into structured IPS.""" 
    from openai import OpenAI
    import os
    
    # Check if OpenAI key is available
    if not os.getenv('OPENAI_API_KEY'):
        st.error("OpenAI API key not found. Cannot parse client profile with AI.")
        return parse_client_profile_fallback(client_profile_text)
    
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    system_prompt = """You are an expert investment advisor. Parse the client profile text and extract key information to create an Investment Policy Statement (IPS).

Return a JSON object with this exact structure:
{
  "client": {
    "name": "extracted or 'Client'",
    "risk_tolerance": "low, moderate, or high",
    "time_horizon_years": number (1-30),
    "cash_buffer_pct": number (3-20)
  },
  "position_limits": {
    "max_position_pct": number (3-15),
    "max_sector_pct": number (15-50), 
    "max_industry_pct": number (10-30)
  },
  "exclusions": {
    "sectors": ["list of excluded sectors"],
    "tickers": ["list of excluded tickers"],
    "esg_screens": ["list of ESG exclusions"]
  },
  "portfolio_constraints": {
    "beta_min": number (0.5-1.0),
    "beta_max": number (1.0-2.0)
  },
  "universe": {
    "min_price": number (1-10),
    "min_avg_daily_volume": number (500000-5000000)
  }
}

Use reasonable defaults if information is missing. Be conservative with risk settings unless explicitly stated otherwise."""

    user_prompt = f"Parse this client profile:\n\n{client_profile_text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        import json
        response_content = response.choices[0].message.content
        if not response_content:
            st.error("AI parsing error: Empty response from OpenAI")
            return {}
        
        response_content = response_content.strip()
        
        # Check if response is empty
        if not response_content:
            st.error("AI parsing error: Empty response from OpenAI")
            return {}
        
        # Try to extract JSON from response (in case there's extra text)
        json_start = response_content.find('{')
        json_end = response_content.rfind('}') + 1
        
        if json_start == -1 or json_end <= json_start:
            st.error(f"AI parsing error: No valid JSON found in response")
            st.code(f"Response received: {response_content[:200]}...")
            return {}
        
        json_content = response_content[json_start:json_end]
        
        try:
            parsed_data = json.loads(json_content)
        except json.JSONDecodeError as json_error:
            st.error(f"AI parsing error: Invalid JSON format - {json_error}")
            st.code(f"JSON content: {json_content[:200]}...")
            return {}
        
        # Validate that we got the expected structure
        if not isinstance(parsed_data, dict):
            st.error("AI parsing error: Response is not a JSON object")
            return {}
        
        # Merge with default IPS structure
        default_ips = st.session_state.config_loader.load_ips()
        
        # Update with parsed values
        for section, values in parsed_data.items():
            if section in default_ips:
                if isinstance(values, dict):
                    default_ips[section].update(values)
                else:
                    default_ips[section] = values
            else:
                st.warning(f"Unknown section '{section}' in parsed data - skipping")
        
        st.success("✅ Client profile parsed successfully!")
        return default_ips
        
    except Exception as e:
        st.error(f"AI parsing error: {e}")
        st.warning("💡 Tip: Make sure your OpenAI API key is valid and you have sufficient credits")
        # Try fallback parsing
        st.info("🔄 Attempting fallback parsing method...")
        return parse_client_profile_fallback(client_profile_text)


def parse_client_profile_fallback(client_profile_text: str) -> dict:
    """Fallback method to parse client profile using keyword matching."""
    import re
    
    # Load default IPS
    default_ips = st.session_state.config_loader.load_ips()
    
    text_lower = client_profile_text.lower()
    
    # Parse risk tolerance
    if any(word in text_lower for word in ['conservative', 'low risk', 'safety', 'capital preservation']):
        default_ips['client']['risk_tolerance'] = 'low'
        default_ips['client']['cash_buffer_pct'] = 15
        default_ips['position_limits']['max_position_pct'] = 5
    elif any(word in text_lower for word in ['aggressive', 'high risk', 'growth', 'speculative']):
        default_ips['client']['risk_tolerance'] = 'high' 
        default_ips['client']['cash_buffer_pct'] = 5
        default_ips['position_limits']['max_position_pct'] = 10
    else:
        default_ips['client']['risk_tolerance'] = 'moderate'
        default_ips['client']['cash_buffer_pct'] = 10
        default_ips['position_limits']['max_position_pct'] = 7
    
    # Parse time horizon
    years_match = re.search(r'(\d+)\s*year', text_lower)
    if years_match:
        years = int(years_match.group(1))
        default_ips['client']['time_horizon_years'] = min(max(years, 1), 30)
    
    # Parse exclusions
    if 'esg' in text_lower or 'sustainable' in text_lower or 'ethical' in text_lower:
        default_ips['exclusions']['esg_screens'] = ['tobacco', 'weapons', 'fossil_fuels']
    
    if 'no tobacco' in text_lower or 'tobacco free' in text_lower:
        default_ips['exclusions']['sectors'].append('tobacco')
    
    if 'no crypto' in text_lower or 'cryptocurrency' in text_lower:
        default_ips['exclusions']['tickers'].extend(['COIN', 'MSTR', 'RIOT'])
    
    # Extract client name if mentioned
    name_match = re.search(r'(?:client|name|i am|my name is)\s+(?:is\s+)?([a-zA-Z\s]+)', text_lower)
    if name_match:
        name = name_match.group(1).strip().title()
        if len(name) < 50:  # Reasonable name length
            default_ips['client']['name'] = name
    
    st.info("✅ Used fallback parsing - review settings carefully")
    return default_ips


def display_backtest_results(results: dict):
    """Display backtest results."""
    
    metrics = results['metrics']
    benchmark = results['benchmark']
    
    st.success("✅ Backtest Complete!")
    st.write(results['performance_summary'])
    
    # Metrics comparison
    st.subheader("Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Strategy**")
        st.metric("Total Return", f"{metrics['total_return_pct']:.2f}%")
        st.metric("Annualized Return", f"{metrics['annualized_return_pct']:.2f}%")
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
        st.metric("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}")
        st.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.2f}%")
    
    with col2:
        st.write("**Benchmark (S&P 500)**")
        if benchmark:
            st.metric("Total Return", f"{benchmark['total_return_pct']:.2f}%")
            st.metric("Annualized Return", f"{benchmark['annualized_return_pct']:.2f}%")
            st.metric("Volatility", f"{benchmark['volatility_pct']:.2f}%")
            st.metric("Max Drawdown", f"{benchmark['max_drawdown_pct']:.2f}%")
            
            # Calculate alpha/IR
            if metrics and benchmark:
                alpha = metrics['annualized_return_pct'] - benchmark['annualized_return_pct']
                st.metric("Alpha vs Benchmark", f"{alpha:+.2f}%")
    
    # Equity curve
    st.subheader("💹 Equity Curve")
    
    portfolio_history = results['portfolio_history']
    dates = [p['date'] for p in portfolio_history]
    values = [p['total_value'] for p in portfolio_history]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        name='Strategy',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.update_layout(
        title="Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    st.subheader("📥 Export Results")
    
    df = pd.DataFrame(portfolio_history)
    csv = df.to_csv(index=False)
    
    st.download_button(
        label="Download Backtest Results CSV",
        data=csv,
        file_name=f"backtest_{results['config']['start_date']}_to_{results['config']['end_date']}.csv",
        mime="text/csv"
    )


def qa_learning_center_page():
    """QA & Learning Center page - tracks recommendation performance and enables model improvement."""
    st.header("🎯 QA & Learning Center")
    st.write("Track recommendation performance, conduct weekly reviews, and improve analysis through learning.")
    st.markdown("---")
    
    if not st.session_state.qa_system:
        st.error("QA System not initialized. Please restart the application.")
        return
    
    qa_system = st.session_state.qa_system
    
    # Add refresh button
    if st.button("🔄 Refresh QA Data", help="Reload data from storage"):
        qa_system.recommendations = qa_system._load_recommendations()
        qa_system.all_analyses = qa_system._load_all_analyses()
        qa_system.reviews = qa_system._load_reviews()
        st.success("QA data refreshed!")
        st.rerun()
    
    # Get data for display
    qa_summary = qa_system.get_qa_summary()
    tracked_tickers = qa_system.get_tracked_tickers()
    analysis_archive = qa_system.get_analysis_archive()
    analysis_stats = qa_system.get_analysis_stats()
    
    # Debug info
    st.sidebar.write(f"**Debug Info:**")
    st.sidebar.write(f"Tracked tickers: {len(tracked_tickers)}")
    st.sidebar.write(f"Analyses: {len(analysis_archive)}")
    if tracked_tickers:
        st.sidebar.write(f"Tickers: {', '.join(tracked_tickers)}")
    
    # Create tabs for different QA views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🎯 Tracked Tickers",
        "📚 Complete Archives", 
        "📈 Weekly Reviews", 
        "🧠 Learning Insights"
    ])
    
    with tab1:
        st.subheader("📊 System Dashboard")
        
        # Key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Analyses", analysis_stats['total_analyses'])
        
        with col2:
            st.metric("Unique Tickers", analysis_stats['unique_tickers'])
        
        with col3:
            st.metric("QA Recommendations", qa_summary['total_recommendations'])
        
        with col4:
            st.metric("Recent Activity", f"{analysis_stats['recent_activity_count']} (30d)")
        
        with col5:
            avg_confidence = analysis_stats['avg_confidence_score']
            st.metric("Avg Confidence", f"{avg_confidence:.1f}/100")
        
        # Charts
        if analysis_stats['total_analyses'] > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Recommendation Breakdown")
                rec_data = analysis_stats['recommendation_breakdown']
                if rec_data:
                    fig = px.bar(
                        x=list(rec_data.keys()),
                        y=list(rec_data.values()),
                        title="Analysis Recommendations"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Sector Distribution")
                sector_data = analysis_stats['sector_breakdown']
                if sector_data:
                    fig = px.pie(
                        values=list(sector_data.values()),
                        names=list(sector_data.keys()),
                        title="Sectors Analyzed"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Recent Analysis Activity with Ticker Names
        st.markdown("---")
        st.subheader("📈 Recent Analysis Activity")
        
        if analysis_archive:
            # Get recent analyses (last 5)
            all_recent_analyses = []
            for ticker, analyses in analysis_archive.items():
                for analysis in analyses:
                    all_recent_analyses.append((ticker, analysis))
            
            # Sort by timestamp (most recent first)
            all_recent_analyses.sort(key=lambda x: x[1].timestamp, reverse=True)
            recent_analyses = all_recent_analyses[:5]
            
            if recent_analyses:
                for ticker, analysis in recent_analyses:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    with col1:
                        st.write(f"**📊 {ticker}**")
                    with col2:
                        rec_color = "🟢" if analysis.recommendation.value in ['strong_buy', 'buy'] else "🔴" if analysis.recommendation.value in ['strong_sell', 'sell'] else "🟡"
                        st.write(f"{rec_color} {analysis.recommendation.value.upper()}")
                    with col3:
                        st.write(f"**{analysis.confidence_score:.1f}**/100")
                    with col4:
                        st.write(f"*{analysis.timestamp.strftime('%m/%d %H:%M')}*")
                
                st.caption(f"Showing {len(recent_analyses)} most recent analyses")
            else:
                st.info("No recent analyses to display")
        else:
            st.info("No analyses performed yet. Start analyzing stocks to see activity here.")
        
        # Tracked Tickers Summary with Names
        if tracked_tickers:
            st.markdown("---")
            st.subheader("🎯 Currently Tracked Tickers")
            st.write(f"**{len(tracked_tickers)} tickers** being monitored for QA tracking:")
            
            # Display as a formatted list with additional info
            for ticker in tracked_tickers:
                if ticker in st.session_state.qa_system.recommendations:
                    rec = st.session_state.qa_system.recommendations[ticker]
                    rec_color = "🟢" if rec.recommendation.value in ['strong_buy', 'buy'] else "🔴" if rec.recommendation.value in ['strong_sell', 'sell'] else "🟡"
                    st.write(f"• **{ticker}** - {rec_color} {rec.recommendation.value.upper()} ({rec.confidence_score:.1f}/100) - *{rec.timestamp.strftime('%m/%d/%Y')}*")
                else:
                    st.write(f"• **{ticker}**")
        
        # Performance tracking (if reviews exist)
        if qa_summary['total_reviews'] > 0:
            st.markdown("---")
            st.subheader("🎯 QA Performance Tracking")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                better_count = qa_summary['performance_stats']['better']
                total_reviews = qa_summary['total_reviews']
                success_rate = (better_count / total_reviews * 100) if total_reviews > 0 else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col2:
                st.metric("Total Reviews", qa_summary['total_reviews'])
            
            with col3:
                stocks_due = len(qa_summary['stocks_due_for_review'])
                st.metric("Due for Review", stocks_due)
    
    with tab2:
        st.subheader("🎯 Tracked Tickers in QA System")
        st.write("These tickers are currently being tracked for performance against recommendations.")
        
        if tracked_tickers:
            # Display tracked tickers in a nice grid
            cols_per_row = 4
            for i in range(0, len(tracked_tickers), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, ticker in enumerate(tracked_tickers[i:i+cols_per_row]):
                    with cols[j]:
                        st.info(f"📈 **{ticker}**")
            
            st.markdown("---")
            st.write(f"**Total: {len(tracked_tickers)} tickers being tracked**")
            
            # Show recommendation breakdown for tracked tickers
            if st.session_state.qa_system.recommendations:
                rec_types = {}
                for rec in st.session_state.qa_system.recommendations.values():
                    rec_type = rec.recommendation.value
                    rec_types[rec_type] = rec_types.get(rec_type, 0) + 1
                
                st.subheader("Recommendation Types")
                for rec_type, count in rec_types.items():
                    st.write(f"• **{rec_type.upper()}**: {count} ticker(s)")
        else:
            st.info("No tickers currently being tracked in QA system. Analyze stocks and log them to QA to start tracking.")
    
    with tab3:
        st.subheader("📚 Complete Analysis Archives")
        st.write("All analyses performed, organized by ticker with expandable details.")
        
        # Export all analyses to CSV button
        if analysis_archive:
            import pandas as pd
            from io import StringIO
            
            # Prepare comprehensive CSV data
            csv_rows = []
            for ticker, analyses in analysis_archive.items():
                for analysis in analyses:
                    row = {
                        'Ticker': ticker,
                        'Analysis Date': analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'Recommendation': analysis.recommendation.value.upper(),
                        'Confidence Score': f"{analysis.confidence_score:.1f}",
                        'Price at Analysis': f"${analysis.price_at_analysis:.2f}",
                        'Current Price': f"${analysis.current_price:.2f}" if hasattr(analysis, 'current_price') and analysis.current_price else 'N/A',
                        'Price Change %': f"{((analysis.current_price - analysis.price_at_analysis) / analysis.price_at_analysis * 100):.2f}%" if hasattr(analysis, 'current_price') and analysis.current_price else 'N/A',
                    }
                    
                    # Add fundamentals data
                    if analysis.fundamentals:
                        for key, value in analysis.fundamentals.items():
                            if value is not None:
                                formatted_key = key.replace('_', ' ').title()
                                if isinstance(value, float):
                                    row[formatted_key] = f"{value:.2f}"
                                else:
                                    row[formatted_key] = str(value)
                    
                    # Add agent scores if available
                    if hasattr(analysis, 'agent_scores') and analysis.agent_scores:
                        for agent, score in analysis.agent_scores.items():
                            agent_name = agent.replace('_', ' ').title()
                            row[f"{agent_name} Score"] = f"{score:.1f}"
                    
                    # Add key factors as single field
                    if analysis.key_factors:
                        row['Key Factors'] = ' | '.join(analysis.key_factors)
                    
                    # Add rationales
                    if analysis.agent_rationales:
                        for agent, rationale in analysis.agent_rationales.items():
                            if rationale and rationale.strip():
                                agent_name = agent.replace('_', ' ').title()
                                # Clean rationale for CSV (remove newlines, limit length)
                                clean_rationale = ' '.join(rationale.split())
                                if len(clean_rationale) > 500:
                                    clean_rationale = clean_rationale[:497] + '...'
                                row[f"{agent_name} Rationale"] = clean_rationale
                    
                    csv_rows.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(csv_rows)
            
            # Reorder columns for better readability
            priority_cols = ['Ticker', 'Analysis Date', 'Recommendation', 'Confidence Score', 
                           'Price at Analysis', 'Current Price', 'Price Change %']
            other_cols = [col for col in df.columns if col not in priority_cols]
            df = df[priority_cols + other_cols]
            
            # Convert to CSV
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Download button
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.info(f"📊 **{len(csv_rows)}** total analyses across **{len(analysis_archive)}** tickers ready for export")
            with col2:
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"complete_qa_analyses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Download all analyses as a comprehensive CSV file"
                )
            with col3:
                # Google Sheets export
                if st.session_state.sheets_integration.sheet:
                    if st.button("📊 Push to Sheets", use_container_width=True):
                        with st.spinner("Updating..."):
                            success = update_google_sheets_qa_analyses(analysis_archive)
                            if success:
                                st.success("✅ Updated!")
                                sheet_url = st.session_state.sheets_integration.get_sheet_url()
                                if sheet_url:
                                    st.markdown(f"[📄 Open Sheet]({sheet_url})")
                            else:
                                st.error("❌ Update failed")
                else:
                    st.info("Connect in sidebar")
            
            st.markdown("---")
        
        if analysis_archive:
            # Search and filter options
            col1, col2 = st.columns([2, 1])
            with col1:
                search_ticker = st.text_input("🔍 Search ticker:", placeholder="Enter ticker symbol...")
            with col2:
                sort_option = st.selectbox("Sort by:", ["Most Recent", "Ticker A-Z", "Confidence Score"])
            
            # Filter and sort archive
            filtered_archive = analysis_archive
            if search_ticker:
                filtered_archive = {k: v for k, v in analysis_archive.items() 
                                  if search_ticker.upper() in k.upper()}
            
            # Sort the archive
            if sort_option == "Ticker A-Z":
                sorted_tickers = sorted(filtered_archive.keys())
            elif sort_option == "Confidence Score":
                sorted_tickers = sorted(filtered_archive.keys(), 
                                      key=lambda t: max(a.confidence_score for a in filtered_archive[t]), 
                                      reverse=True)
            else:  # Most Recent
                sorted_tickers = sorted(filtered_archive.keys(), 
                                      key=lambda t: max(a.timestamp for a in filtered_archive[t]), 
                                      reverse=True)
            
            # Display archives
            for ticker in sorted_tickers:
                analyses = filtered_archive[ticker]
                
                with st.expander(f"📊 **{ticker}** ({len(analyses)} analysis{'es' if len(analyses) != 1 else ''})"):
                    # Add a "Delete All" button at the top of each ticker's expander
                    col_del1, col_del2 = st.columns([4, 1])
                    with col_del2:
                        if st.button(f"🗑️ Delete All", key=f"delete_all_{ticker}", help=f"Delete all analyses for {ticker}"):
                            if ticker in qa_system.all_analyses:
                                del qa_system.all_analyses[ticker]
                                qa_system._save_all_analyses()
                                st.success(f"✅ Deleted all analyses for {ticker}")
                                st.rerun()
                    
                    st.markdown("---")
                    
                    for i, analysis in enumerate(analyses):
                        st.markdown(f"### Analysis #{i+1}")
                        
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                        with col1:
                            st.write(f"**Date:** {analysis.timestamp.strftime('%Y-%m-%d %H:%M')}")
                        with col2:
                            st.write(f"**Recommendation:** {analysis.recommendation.value.upper()}")
                        with col3:
                            st.write(f"**Confidence:** {analysis.confidence_score:.1f}/100")
                        with col4:
                            st.write(f"**Price:** ${analysis.price_at_analysis:.2f}")
                        with col5:
                            # Delete button for this specific analysis
                            unique_key = f"delete_{ticker}_{analysis.timestamp.timestamp()}"
                            if st.button("🗑️", key=unique_key, help="Delete this analysis"):
                                # Delete this specific analysis by finding it by timestamp
                                if ticker in qa_system.all_analyses:
                                    # Find and remove the analysis with matching timestamp
                                    qa_system.all_analyses[ticker] = [
                                        a for a in qa_system.all_analyses[ticker] 
                                        if a.timestamp != analysis.timestamp
                                    ]
                                    # If no more analyses for this ticker, remove the ticker entirely
                                    if not qa_system.all_analyses[ticker]:
                                        del qa_system.all_analyses[ticker]
                                    # Save updated data
                                    qa_system._save_all_analyses()
                                    st.success(f"✅ Deleted analysis from {analysis.timestamp.strftime('%Y-%m-%d %H:%M')} for {ticker}")
                                    st.rerun()
                        
                        # Show rationales with collapsible sections
                        if analysis.agent_rationales:
                            st.markdown("**Agent Rationales:**")
                            for agent, rationale in analysis.agent_rationales.items():
                                if rationale and rationale.strip():
                                    st.markdown(f"**🤖 {agent.replace('_', ' ').title()}:**")
                                    st.write(rationale)
                                    st.markdown("---")
                        
                        # Show key factors
                        if analysis.key_factors:
                            st.markdown("**Key Factors:**")
                            for factor in analysis.key_factors:
                                st.write(f"• {factor}")
                        
                        # Show fundamentals summary
                        if analysis.fundamentals:
                            st.markdown("**📊 Fundamentals Data:**")
                            cols = st.columns(2)
                            fund_items = [(k, v) for k, v in analysis.fundamentals.items() if v is not None]
                            for idx, (key, value) in enumerate(fund_items):
                                with cols[idx % 2]:
                                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                        
                        if i < len(analyses) - 1:
                            st.markdown("---")
        else:
            st.info("No analyses in archive yet. Perform stock analyses to build your archive.")
    
    with tab4:
        st.subheader("📈 Weekly Reviews")
        
        # Check for stocks due for review
        stocks_due = qa_summary['stocks_due_for_review']
        
        if stocks_due:
            st.warning(f"⏰ {len(stocks_due)} stock(s) are due for weekly review")
            
            for ticker in stocks_due:
                with st.expander(f"Review {ticker} - Due for Weekly Check"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Stock:** {ticker}")
                        if ticker in qa_system.recommendations:
                            rec = qa_system.recommendations[ticker]
                            st.write(f"**Original Recommendation:** {rec.recommendation.value.upper()}")
                            st.write(f"**Original Price:** ${rec.price_at_recommendation:.2f}")
                            st.write(f"**Date:** {rec.timestamp.strftime('%Y-%m-%d')}")
                            current_time = datetime.now()
                            st.write(f"**Days Since:** {(current_time - rec.timestamp).days}")
                    
                    with col2:
                        if st.button(f"Conduct Review", key=f"review_{ticker}"):
                            with st.spinner(f"Conducting performance review for {ticker}..."):
                                try:
                                    # Get current price
                                    data_provider = st.session_state.data_provider
                                    current_data = data_provider.get_stock_data(ticker)
                                    
                                    if current_data and 'price' in current_data:
                                        current_price = current_data['price']
                                        
                                        # Conduct review
                                        openai_client = st.session_state.get('openai_client')
                                        review = qa_system.conduct_performance_review(
                                            ticker, current_price, openai_client
                                        )
                                        
                                        if review:
                                            st.success(f"✅ Review completed for {ticker}")
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to complete review for {ticker}")
                                    else:
                                        st.error(f"Could not fetch current price for {ticker}")
                                        
                                except Exception as e:
                                    st.error(f"Error conducting review: {e}")
        else:
            st.success("✅ All tracked stocks are up to date with their weekly reviews")
        
        # Display recent reviews with details
        if qa_summary['latest_reviews']:
            st.subheader("Recent Detailed Reviews")
            
            for review_data in qa_summary['latest_reviews'][:3]:  # Show top 3
                ticker = review_data['ticker']
                if ticker in qa_system.reviews:
                    latest_review = qa_system.reviews[ticker][-1]  # Most recent review
                    
                    with st.expander(f"{ticker} - Review from {latest_review.review_date.strftime('%Y-%m-%d')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Performance Metrics:**")
                            st.write(f"Price Change: {latest_review.price_change_pct:.2f}%")
                            st.write(f"Performance vs Prediction: {latest_review.performance_vs_prediction}")
                            st.write(f"Analysis Accuracy: {latest_review.analysis_accuracy}")
                        
                        with col2:
                            st.write("**Price Details:**")
                            st.write(f"Original: ${latest_review.original_recommendation.price_at_recommendation:.2f}")
                            st.write(f"Current: ${latest_review.current_price:.2f}")
                            st.write(f"Change: ${latest_review.price_change_absolute:.2f}")
                        
                        if latest_review.lessons_learned:
                            st.write("**Lessons Learned:**")
                            for lesson in latest_review.lessons_learned:
                                st.write(f"• {lesson}")
                        
                        if latest_review.unforeseen_factors:
                            st.write("**Unforeseen Factors:**")
                            for factor in latest_review.unforeseen_factors:
                                st.write(f"• {factor}")
    
    with tab5:
        st.subheader("🧠 Learning Insights")
        
        insights = qa_summary['insights']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if insights['common_mistakes']:
                st.write("**🚨 Common Mistakes to Avoid:**")
                for mistake in insights['common_mistakes'][-5:]:  # Show last 5
                    st.write(f"• {mistake}")
            
            if insights['improvement_patterns']:
                st.write("**📈 Key Improvements Identified:**")
                for improvement in insights['improvement_patterns'][-5:]:
                    st.write(f"• {improvement}")
        
        with col2:
            if insights['successful_strategies']:
                st.write("**✅ Successful Strategies:**")
                for strategy in insights['successful_strategies'][-5:]:
                    st.write(f"• {strategy}")
            
            if insights['market_lessons']:
                st.write("**📚 Market Lessons:**")
                for lesson in insights['market_lessons'][-5:]:
                    st.write(f"• {lesson}")
        
        # Learning insights for future analysis
        st.subheader("Insights for Future Analysis")
        learning_text = qa_system.get_learning_insights_for_analysis()
        st.text_area(
            "Copy this text to include in future analysis prompts:",
            learning_text,
            height=200
        )
        
        # Manual review interface
        st.markdown("---")
        st.subheader("Manual Review Tools")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Conduct Manual Review:**")
            
            # Select stock for manual review
            available_stocks = list(qa_system.recommendations.keys())
            if available_stocks:
                selected_stock = st.selectbox("Select stock for review:", available_stocks)
                
                if selected_stock:
                    rec = qa_system.recommendations[selected_stock]
                    st.write(f"**Original Recommendation:** {rec.recommendation.value.upper()}")
                    st.write(f"**Original Price:** ${rec.price_at_recommendation:.2f}")
                    st.write(f"**Date:** {rec.timestamp.strftime('%Y-%m-%d')}")
                    
                    current_price = st.number_input(
                        "Enter current price:",
                        min_value=0.01,
                        value=rec.price_at_recommendation,
                        step=0.01
                    )
                    
                    if st.button("Conduct Manual Review"):
                        with st.spinner("Conducting review..."):
                            openai_client = st.session_state.get('openai_client')
                            review = qa_system.conduct_performance_review(
                                selected_stock, current_price, openai_client
                            )
                            
                            if review:
                                st.success("✅ Manual review completed")
                                st.rerun()
            else:
                st.info("No recommendations logged yet. Analyze some stocks first!")
        
        with col2:
            st.write("**QA System Statistics:**")
            st.json({
                "Total Recommendations": qa_summary['total_recommendations'],
                "Total Reviews": qa_summary['total_reviews'],
                "Stocks Due for Review": len(qa_summary['stocks_due_for_review']),
                "Success Rate": f"{(qa_summary['performance_stats']['better'] / max(qa_summary['total_reviews'], 1) * 100):.1f}%"
            })


def system_status_and_ai_disclosure_page():
    """Combined system status and AI disclosure page."""
    st.header("🔧 System Status & AI Disclosure")
    st.write("Monitor system health, data provider status, and AI usage information.")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📊 System Status", "🤖 AI Usage Disclosure"])
    
    with tab1:
        st.subheader("📊 Data Provider Status")
        
        # Check if data provider is available
        if not st.session_state.data_provider:
            st.error("❌ Data provider not initialized. Please restart the application.")
            return
        
        data_provider = st.session_state.data_provider
        
        # Display Data Provider Information
        st.write("**Provider Information**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Provider Type", "Enhanced Data Provider")
        
        with col2:
            # Check if provider has premium services
            has_polygon = hasattr(data_provider, 'polygon_client') and data_provider.polygon_client is not None
            has_perplexity = hasattr(data_provider, 'perplexity_client') and data_provider.perplexity_client is not None
            premium_count = sum([has_polygon, has_perplexity])
            st.metric("Premium Services", f"{premium_count}/2 Available")
        
        with col3:
            # Check cache directory
            cache_dir = Path("data/cache")
            cache_exists = cache_dir.exists()
            st.metric("Cache Status", "Available" if cache_exists else "Not Found")
        
        # API Keys Status
        st.markdown("---")
        st.write("**🔑 API Keys Status**")
        
        api_keys_status = {
            "Alpha Vantage": bool(os.getenv('ALPHA_VANTAGE_API_KEY')),
            "OpenAI": bool(os.getenv('OPENAI_API_KEY')),
            "Polygon.io": bool(os.getenv('POLYGON_API_KEY')),
            "Perplexity AI": bool(os.getenv('PERPLEXITY_API_KEY')),
            "NewsAPI": bool(os.getenv('NEWSAPI_KEY')),
            "IEX Cloud": bool(os.getenv('IEX_TOKEN'))
        }
        
        cols = st.columns(3)
        for i, (service, available) in enumerate(api_keys_status.items()):
            with cols[i % 3]:
                icon = "✅" if available else "❌"
                status_text = "Available" if available else "Missing"
                st.write(f"{icon} **{service}**: {status_text}")
        
        # Provider Capabilities
        st.markdown("---")
        st.write("**⚡ Provider Capabilities**")
        
        capabilities = {
            "Stock Price Data": True,
            "Fundamentals Data": True,
            "News & Sentiment": bool(os.getenv('NEWSAPI_KEY')),
            "Premium Price Data": bool(os.getenv('POLYGON_API_KEY')),
            "AI-Enhanced Analysis": bool(os.getenv('PERPLEXITY_API_KEY')),
            "52-Week Range Verification": True,
            "Multi-Source Fallback": True
        }
        
        col1, col2 = st.columns(2)
        for i, (capability, available) in enumerate(capabilities.items()):
            with col1 if i % 2 == 0 else col2:
                icon = "✅" if available else "⚠️"
                st.write(f"{icon} {capability}")
        
        # Cache Information
        if cache_exists:
            st.markdown("---")
            st.write("**💾 Cache Information**")
            try:
                cache_files = list(cache_dir.glob("*"))
                total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
                total_size_mb = total_size / (1024 * 1024)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Cache Files", len(cache_files))
                with col2:
                    st.metric("Total Size", f"{total_size_mb:.1f} MB")
                with col3:
                    # Show newest cache file age
                    if cache_files:
                        newest_file = max(cache_files, key=lambda f: f.stat().st_mtime)
                        current_time = datetime.now().timestamp()
                        age_hours = (current_time - newest_file.stat().st_mtime) / 3600
                        st.metric("Newest Cache", f"{age_hours:.1f} hours ago")
            except Exception as e:
                st.warning(f"Could not read cache information: {e}")
        
        # Data Source Test
        st.markdown("---")
        st.write("**🧪 Test Data Sources**")
        
        test_ticker = st.text_input("Test ticker:", value="AAPL")
        
        if st.button("Test All Data Sources"):
            with st.spinner("Testing data sources..."):
                results = {}
                
                # Test price data
                try:
                    if hasattr(st.session_state.data_provider, 'get_price_history_enhanced'):
                        price_data = st.session_state.data_provider.get_price_history_enhanced(
                            test_ticker, "2024-01-01", "2024-12-31"
                        )
                    else:
                        price_data = st.session_state.data_provider.get_price_history(
                            test_ticker, "2024-01-01", "2024-12-31"
                        )
                    
                    if not price_data.empty:
                        results['Price Data'] = f"✅ {len(price_data)} days of data"
                        if 'SYNTHETIC_DATA' in price_data.columns:
                            results['Price Data'] += " (⚠️ Synthetic)"
                    else:
                        results['Price Data'] = "❌ No data"
                        
                except Exception as e:
                    results['Price Data'] = f"❌ Error: {str(e)}"
                
                # Test fundamentals
                try:
                    if hasattr(st.session_state.data_provider, 'get_fundamentals_enhanced'):
                        fund_data = st.session_state.data_provider.get_fundamentals_enhanced(test_ticker)
                    else:
                        fund_data = st.session_state.data_provider.get_fundamentals(test_ticker)
                    
                    if fund_data:
                        results['Fundamentals'] = f"✅ {len(fund_data)} data points"
                        if fund_data.get('estimated'):
                            results['Fundamentals'] += " (⚠️ Estimated)"
                    else:
                        results['Fundamentals'] = "❌ No data"
                        
                except Exception as e:
                    results['Fundamentals'] = f"❌ Error: {str(e)}"
                
                # Display results
                for source, result in results.items():
                    st.write(f"**{source}:** {result}")
        
        # Clear Cache
        if st.button("🗑️ Clear Cache", help="Clear cached data to force fresh API calls"):
            cache_dir = Path("data/cache")
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                st.success("Cache cleared!")
            else:
                st.info("No cache to clear")
    
    with tab2:
        st.subheader("🤖 AI Usage Disclosure")
        
        disclosure_logger = get_disclosure_logger()
        summary = disclosure_logger.get_disclosure_summary()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total API Calls", summary['total_calls'])
        with col2:
            st.metric("Total Tokens", f"{summary['total_tokens']:,}")
        with col3:
            st.metric("Estimated Cost", f"${summary['total_cost_usd']:.2f}")
        
        st.write(f"**Tools Used:** {', '.join(summary.get('tools_used', []))}")
        st.write(f"**Log File:** `{summary.get('log_file', 'N/A')}`")
        
        # Download log
        log_file = summary.get('log_file', '')
        if log_file and Path(log_file).exists():
            with open(log_file, 'r') as f:
                log_data = f.read()
            
            st.download_button(
                label="📥 Download Disclosure Log",
                data=log_data,
                file_name="ai_disclosure_log.jsonl",
                mime="application/json"
            )
        
        st.info("""
        **For Works Cited:**
        
        This system uses the following APIs/tools:
        - OpenAI GPT-4o-mini for agent reasoning and rationale generation, as well as perplexityAI for enforcing real time data retrieval. 
        - yfinance/PolygonIO for market data
        - Alpha Vantage for fundamental data and macroeconomic indicators
        - NewsAPI for news sentiment analysis 
        
        All API calls are logged with timestamps, purposes, and token usage for full disclosure.
        """)
        
        # Premium Setup Guide
        st.markdown("---")
        st.subheader("🔧 Premium Setup Guide")
        
        with st.expander("View Premium API Setup Instructions"):
            st.markdown("""
            ### Recommended Premium APIs for Production
            
            **For reliable data access without rate limits:**
            
            1. **IEX Cloud** ($9/month) - Excellent US stock data
               - Add to .env: `IEX_TOKEN=your_token_here`
               - Get token: https://iexcloud.io/
            
            2. **Alpha Vantage Premium** ($49.99/month) - Comprehensive fundamentals  
               - Upgrade your existing key at: https://www.alphavantage.co/premium/
               - 1200 calls/minute vs 5 calls/minute free
            
            3. **Polygon.io** ($99/month) - Professional grade data
               - Add to .env: `POLYGON_API_KEY=your_key_here` 
               - Get key: https://polygon.io/
            
            **Total recommended cost: ~$60/month for rock-solid data access**
            
            ### Current Free Tier Limitations:
            - yfinance: ~2000 requests/day (rate limited)
            - Alpha Vantage: 5 calls/minute, 500/day
            - NewsAPI: 100 requests/day
            
            ### Testing vs Production:
            - Free tier works fine for testing and development
            - Premium recommended for live trading or intensive analysis
            """)


def configuration_page():
    """Configuration management page."""
    st.header("System Configuration")
    st.write("Manage Investment Policy Statement constraints and model parameters.")
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Client Profile Upload", "IPS Configuration", "Agent Weights", "⏱️ Timing Analytics"])
    
    with tab1:
        st.subheader("Client Profile Upload")
        st.write("Configure client requirements and investment objectives (detailed text input)")
        
        # Text input for client profile
        client_profile = st.text_area(
            "Client Profile & Requirements:",
            height=300,
            placeholder="""Paste your client profile here. For example:

The client is a 35-year-old technology executive with a high risk tolerance and 10-year investment horizon. They are seeking aggressive growth and are comfortable with high volatility. The client wants to exclude tobacco and weapons companies from their portfolio.

Key constraints:
- No single position over 10% of portfolio
- Maximum 40% allocation to any single sector
- Prefer growth-oriented companies with strong fundamentals
- ESG considerations: exclude tobacco, weapons, fossil fuels
- Minimum $5 stock price
- Beta range: 0.8 to 1.3 acceptable

The client has expressed interest in technology, healthcare, and renewable energy sectors...""",
            help="Paste the detailed client profile text here. The system will parse this and update the IPS automatically."
        )


# Duplicate function removed - configuration_page defined above


# Old disclosure_page and data_status_page functions removed - consolidated into system_status_and_ai_disclosure_page


def sync_all_archives_to_sheets() -> bool:
    """
    Sync all existing portfolio and QA archives to Google Sheets on first connection.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        sheets_integration = st.session_state.sheets_integration
        
        if not sheets_integration or not sheets_integration.sheet:
            return False
        
        synced_count = 0
        
        # Note: Portfolio selection logs only contain the selection process, not full portfolio data
        # Full portfolio data with scores/rationales is only available during active analysis
        
        # Sync QA analyses
        qa_system = st.session_state.qa_system
        analysis_archive = qa_system.get_analysis_archive()
        
        if analysis_archive:
            success = update_google_sheets_qa_analyses(analysis_archive)
            if success:
                synced_count += len(analysis_archive)
        
        return synced_count > 0
        
    except Exception as e:
        print(f"Error syncing archives: {e}")
        return False


def update_google_sheets_portfolio(result: dict) -> bool:
    """
    Update Google Sheets with comprehensive portfolio analysis results.
    Creates a detailed "Portfolio Recommendations" sheet with full analysis data.
    
    Args:
        result: Portfolio analysis result dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sheets_integration = st.session_state.sheets_integration
        
        if not sheets_integration or not sheets_integration.sheet:
            return False
        
        # Get or create "Portfolio Recommendations" worksheet
        try:
            worksheet = sheets_integration.sheet.worksheet("Portfolio Recommendations")
            # Clear existing data
            worksheet.clear()
        except:
            worksheet = sheets_integration.sheet.add_worksheet(title="Portfolio Recommendations", rows=1000, cols=40)
        
        # Header row
        headers = [
            'Ticker', 'Company Name', 'Recommendation', 'Confidence Score', 'Eligible',
            'Price', 'Market Cap', 'Sector', 'Industry',
            'Value Score', 'Growth Score', 'Macro Score', 'Risk Score', 'Sentiment Score', 'Client Layer Score',
            'Value Rationale', 'Growth Rationale', 'Macro Rationale', 'Risk Rationale', 'Sentiment Rationale', 
            'Client Layer Rationale', 'Final Rationale',
            'P/E Ratio', 'P/B Ratio', 'ROE', 'Debt/Equity', 'Beta',
            'Data Sources', 'Key Metrics', 'Risk Assessment',
            'Export Date'
        ]
        
        # Format header
        worksheet.update('A1', [headers])
        worksheet.format('A1:AE1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.8},
            'textFormat': {'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
        })
        
        # Prepare data rows
        rows = []
        
        if 'final_portfolio' in result and result['final_portfolio']:
            for stock in result['final_portfolio']:
                recommendation_type = _determine_recommendation_type(stock['final_score'])
                
                row = [
                    stock['ticker'],
                    stock['fundamentals'].get('name', 'N/A'),
                    recommendation_type.value.upper(),
                    round(stock['final_score'], 1),
                    'Yes' if stock['eligible'] else 'No',
                    stock['fundamentals'].get('price', 0),
                    stock['fundamentals'].get('market_cap', 0),
                    stock['fundamentals'].get('sector', 'N/A'),
                    stock['fundamentals'].get('industry', 'N/A'),
                    round(stock.get('agent_scores', {}).get('value_agent', 0), 1),
                    round(stock.get('agent_scores', {}).get('growth_momentum_agent', 0), 1),
                    round(stock.get('agent_scores', {}).get('macro_regime_agent', 0), 1),
                    round(stock.get('agent_scores', {}).get('risk_agent', 0), 1),
                    round(stock.get('agent_scores', {}).get('sentiment_agent', 0), 1),
                    round(stock.get('agent_scores', {}).get('client_layer_agent', 0), 1),
                    stock.get('agent_rationales', {}).get('value_agent', '')[:200],
                    stock.get('agent_rationales', {}).get('growth_momentum_agent', '')[:200],
                    stock.get('agent_rationales', {}).get('macro_regime_agent', '')[:200],
                    stock.get('agent_rationales', {}).get('risk_agent', '')[:200],
                    stock.get('agent_rationales', {}).get('sentiment_agent', '')[:200],
                    stock.get('agent_rationales', {}).get('client_layer_agent', '')[:200],
                    stock.get('rationale', '')[:300],
                    stock['fundamentals'].get('pe_ratio', 0),
                    stock['fundamentals'].get('pb_ratio', 0),
                    stock['fundamentals'].get('roe', 0),
                    stock['fundamentals'].get('debt_to_equity', 0),
                    stock['fundamentals'].get('beta', 0),
                    ', '.join(stock.get('data_sources', [])),
                    ', '.join(stock.get('key_metrics', [])),
                    stock.get('risk_assessment', ''),
                    datetime.now().strftime('%Y-%m-%d')
                ]
                rows.append(row)
        
        # Write data
        if rows:
            worksheet.update('A2', rows)
            
            # Auto-resize columns
            for i in range(len(headers)):
                worksheet.format(f'{chr(65+i)}:{chr(65+i)}', {'wrapStrategy': 'WRAP'})
        
        return True
        
    except Exception as e:
        print(f"Error updating Google Sheets portfolio: {e}")
        return False


def update_google_sheets_qa_analyses(analysis_archive: dict) -> bool:
    """
    Update Google Sheets with QA analyses.
    
    Args:
        analysis_archive: Dictionary of analyses by ticker
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sheets_integration = st.session_state.sheets_integration
        
        if not sheets_integration or not sheets_integration.sheet:
            return False
        
        # Convert analysis_archive to list format
        qa_data = []
        for ticker, analyses_list in analysis_archive.items():
            if not analyses_list:
                continue
            
            # Get most recent analysis for this ticker
            analysis = analyses_list[-1] if isinstance(analyses_list, list) else analyses_list
            
            # Build comprehensive row
            fundamentals = analysis.fundamentals if hasattr(analysis, 'fundamentals') else {}
            agent_scores = analysis.agent_scores if hasattr(analysis, 'agent_scores') else {}
            agent_rationales = analysis.agent_rationales if hasattr(analysis, 'agent_rationales') else {}
            
            row = {
                'Ticker': ticker,
                'Recommendation': analysis.recommendation.value if hasattr(analysis, 'recommendation') else 'N/A',
                'Confidence Score': round(analysis.confidence_score, 1) if hasattr(analysis, 'confidence_score') else 0,
                'Price at Analysis': fundamentals.get('price', 0) if isinstance(fundamentals, dict) else 0,
                'Timestamp': analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(analysis, 'timestamp') else '',
            }
            qa_data.append(row)
        
        if not qa_data:
            return True
        
        # Update worksheet
        column_order = ['Ticker', 'Recommendation', 'Confidence Score', 'Price at Analysis', 'Timestamp']
        success = sheets_integration.update_qa_analyses(
            qa_data,
            worksheet_name="QA Analyses",
            column_order=column_order
        )
        
        return success
        
    except Exception as e:
        print(f"Error updating Google Sheets QA analyses: {e}")
        return False


if __name__ == "__main__":
    main()
