"""
Multi-Agent Investment Analysis System
Main Streamlit Application

This is the main entry point for the investment analysis system.
Provides a web interface for stock analysis, portfolio recommendations, and backtesting.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta
import os
from pathlib import Path
import yaml
import json
import time

# Setup page config
st.set_page_config(
    page_title="Investment Analysis Platform",
    page_icon="IA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Custom CSS - Modern Investment Platform Theme
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #635bff;
    --primary-light: #7a73ff;
    --primary-bg: #f0efff;
    --primary-dark: #4f46e5;
    --success: #10b981;
    --success-bg: #ecfdf5;
    --warning: #f59e0b;
    --warning-bg: #fffbeb;
    --danger: #ef4444;
    --danger-bg: #fef2f2;
    --text: #111827;
    --text-secondary: #6b7280;
    --text-muted: #9ca3af;
    --border: #e5e7eb;
    --border-light: #f3f4f6;
    --surface: #ffffff;
    --bg: #f8fafc;
    --raised: #f9fafb;
    --shadow-xs: 0 1px 2px rgba(0,0,0,0.03);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.03);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -4px rgba(0,0,0,0.03);
    --r: 8px;
    --r-lg: 12px;
    --r-xl: 16px;
    --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== Global ===== */
.stApp {
    background-color: var(--bg) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}
.stApp > header { background: transparent !important; }
* { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

h1, h2, h3, h4, h5, h6 {
    color: var(--text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
h1 { font-size: 1.75rem !important; font-weight: 700 !important; }
h2 { font-size: 1.25rem !important; }
h3 { font-size: 1rem !important; }
p, li, span, div { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }

.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] hr { border-color: var(--border-light) !important; margin: 0.75rem 0 !important; }

/* ===== Metric Cards ===== */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    padding: 1rem 1.25rem !important;
    box-shadow: var(--shadow-xs) !important;
    transition: var(--transition);
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--shadow-md) !important;
    border-color: var(--primary) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
[data-testid="stMetricDelta"] svg { width: 12px !important; height: 12px !important; }

/* ===== Tabs - Pill Navigation ===== */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: var(--r-xl) !important;
    border: 1px solid var(--border) !important;
    padding: 4px !important;
    gap: 2px !important;
    box-shadow: var(--shadow-sm) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--r-lg) !important;
    padding: 0.5rem 1.15rem !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
    transition: var(--transition);
    white-space: nowrap !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: var(--bg) !important;
    color: var(--text) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--primary) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 4px rgba(99,91,255,0.25) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ===== Buttons ===== */
.stButton > button {
    border-radius: var(--r) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.25rem !important;
    border: none !important;
    box-shadow: var(--shadow-sm) !important;
    transition: var(--transition);
    letter-spacing: -0.01em;
}
.stButton > button:hover {
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary), var(--primary-light)) !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, var(--primary-dark), var(--primary)) !important;
    box-shadow: 0 4px 12px rgba(99,91,255,0.3) !important;
}
.stDownloadButton > button {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    font-weight: 500 !important;
    transition: var(--transition);
}
.stDownloadButton > button:hover {
    background: var(--bg) !important;
    border-color: var(--primary) !important;
    color: var(--primary) !important;
}

/* ===== Expanders ===== */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    box-shadow: var(--shadow-xs) !important;
    margin-bottom: 0.5rem !important;
    transition: var(--transition);
}
[data-testid="stExpander"]:hover {
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    color: var(--text) !important;
    font-size: 0.9rem !important;
}

/* ===== Alerts ===== */
.stAlert {
    border-radius: var(--r-lg) !important;
    border-left-width: 3px !important;
    font-size: 0.85rem !important;
}

/* ===== Inputs ===== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    background: var(--surface) !important;
    padding: 0.6rem 0.875rem !important;
    font-size: 0.875rem !important;
    transition: var(--transition);
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-bg) !important;
}
.stSelectbox > div > div { border-radius: var(--r) !important; }

/* ===== Data Tables ===== */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ===== Dividers ===== */
.stMarkdown hr {
    border: none !important;
    border-top: 1px solid var(--border-light) !important;
    margin: 1.25rem 0 !important;
}

/* ===== Progress Bars ===== */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--primary), var(--primary-light)) !important;
    border-radius: 999px !important;
}

/* ===== Forms ===== */
[data-testid="stForm"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    padding: 1.25rem !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-xs) !important;
}

/* ===== Score Badge ===== */
.score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 72px; height: 72px;
    border-radius: 50%;
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    box-shadow: var(--shadow-md);
}
.score-badge.excellent { background: linear-gradient(135deg, #10b981, #059669); }
.score-badge.good { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.score-badge.moderate { background: linear-gradient(135deg, #f59e0b, #d97706); }
.score-badge.poor { background: linear-gradient(135deg, #ef4444, #dc2626); }

/* ===== Columns ===== */
[data-testid="column"] { padding: 0 0.375rem !important; }

/* ===== Selectbox / Multiselect ===== */
.stMultiSelect [data-baseweb="tag"] {
    background: var(--primary-bg) !important;
    color: var(--primary) !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}

/* ===== Smooth Scrolling ===== */
html { scroll-behavior: smooth; }

/* ===== Plotly Chart Containers ===== */
.js-plotly-plot { border-radius: var(--r-lg) !important; }
.js-plotly-plot .plotly .modebar { opacity: 0; transition: opacity 0.2s ease; }
.js-plotly-plot:hover .plotly .modebar { opacity: 1; }

/* ===== Toast / Notification ===== */
[data-testid="stToast"] { border-radius: var(--r-lg) !important; box-shadow: var(--shadow-lg) !important; }

/* ===== Hide Streamlit Branding ===== */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Plotly Light Theme
# ---------------------------------------------------------------------------
CHART_COLORS = ["#635bff", "#0ea371", "#3b82f6", "#d97706", "#ec4899",
                "#8b5cf6", "#06b6d4", "#f43f5e", "#10b981", "#6366f1"]

_chart_template = dict(
    layout=dict(
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  color="#111827", size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(size=15, color="#111827")),
        xaxis=dict(gridcolor="#f3f4f6", linecolor="#e5e7eb",
                   tickfont=dict(color="#6b7280", size=11),
                   title_font=dict(color="#6b7280", size=12), zeroline=False),
        yaxis=dict(gridcolor="#f3f4f6", linecolor="#e5e7eb",
                   tickfont=dict(color="#6b7280", size=11),
                   title_font=dict(color="#6b7280", size=12), zeroline=False),
        legend=dict(font=dict(color="#6b7280", size=12),
                    bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=20, t=40, b=40),
        hoverlabel=dict(bgcolor="white", bordercolor="#e5e7eb",
                        font=dict(color="#111827", size=13)),
        colorway=CHART_COLORS,
    )
)
pio.templates["invest_light"] = pio.templates["plotly_white"]
pio.templates["invest_light"].update(_chart_template)
pio.templates.default = "invest_light"



# Import system components
from dotenv import load_dotenv
from utils.config_loader import get_config_loader
from utils.logger import setup_logging, get_disclosure_logger
from utils.tier_manager import TierManager
from data.enhanced_data_provider import EnhancedDataProvider
from engine.portfolio_orchestrator import PortfolioOrchestrator
from engine.backtest import BacktestEngine

# Import OpenAI at module level to avoid circular dependency issues
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

# Suppress noisy WebSocket errors from Streamlit (these are harmless)
import logging
logging.getLogger('tornado.application').setLevel(logging.ERROR)
logging.getLogger('tornado.websocket').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

# Create logger instance
import logging
logger = logging.getLogger(__name__)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.data_provider = None
    st.session_state.orchestrator = None
    st.session_state.config_loader = None




def initialize_system():
    """Initialize the system components."""
    if st.session_state.initialized:
        return True

    # Initialize tier manager
    if 'tier_manager' not in st.session_state:
        st.session_state.tier_manager = TierManager()
    tier = st.session_state.tier_manager

    # Check API keys via tier manager
    if not tier.get_api_key('OPENAI_API_KEY'):
        st.error("OPENAI_API_KEY not found. Please set it in .env file or provide your own key in the sidebar.")
        return False

    if not tier.get_api_key('ALPHA_VANTAGE_API_KEY'):
        st.warning("ALPHA_VANTAGE_API_KEY not found. Some features may be limited.")

    try:
        # Initialize components
        st.session_state.config_loader = get_config_loader()

        # Use Enhanced Data Provider with tier-resolved keys
        st.session_state.data_provider = EnhancedDataProvider(
            alpha_vantage_key=tier.get_api_key('ALPHA_VANTAGE_API_KEY'),
            news_api_key=tier.get_api_key('NEWS_API_KEY'),
            polygon_key=tier.get_api_key('POLYGON_API_KEY'),
        )

        # Load configurations
        model_config = st.session_state.config_loader.load_model_config()
        ips_config = st.session_state.config_loader.load_ips()

        # Initialize AI clients for advanced features
        openai_client = None
        gemini_api_key = None

        try:
            if OpenAI is not None:
                openai_client = OpenAI(api_key=tier.get_api_key('OPENAI_API_KEY'))
                st.session_state.openai_client = openai_client
            else:
                st.warning("OpenAI library not available. Please install: pip install openai")
        except Exception as e:
            st.warning(f"OpenAI client initialization failed: {e}")

        gemini_api_key = tier.get_api_key('GEMINI_API_KEY')
        if gemini_api_key:
            st.session_state.gemini_api_key = gemini_api_key
        else:
            st.warning("GEMINI_API_KEY not found. Portfolio AI selection will be limited.")

        # Initialize orchestrator with enhanced data provider and AI clients
        st.session_state.orchestrator = PortfolioOrchestrator(
            model_config=model_config,
            ips_config=ips_config,
            enhanced_data_provider=st.session_state.data_provider,
            openai_client=openai_client,
            gemini_api_key=gemini_api_key
        )
        
        
        # Initialize analysis time tracking (simple historical average)
        if 'analysis_times' not in st.session_state:
            st.session_state.analysis_times = []  # List of historical analysis times in seconds
        
        st.session_state.initialized = True
        return True
        
    except Exception as e:
        st.error(f"System initialization failed: {e}")
        return False


def main():
    """Main application entry point."""

    # Initialize tier manager early (before system init) so sidebar shows
    if 'tier_manager' not in st.session_state:
        st.session_state.tier_manager = TierManager()
    st.session_state.tier_manager.render_sidebar_ui()

    # Branded header
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
        <div style="background:linear-gradient(135deg,#635bff,#7a73ff);color:white;font-weight:700;font-size:1rem;
                    width:38px;height:38px;border-radius:10px;display:flex;
                    align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(99,91,255,0.25);
                    letter-spacing:-0.02em;">Investment </div>
        <div>
            <div style="font-size:1.2rem;font-weight:700;color:#111827;letter-spacing:-0.03em;line-height:1.2;">
                Investment Analysis</div>
            <div style="font-size:0.75rem;color:#9ca3af;font-weight:400;letter-spacing:0.01em;">
                Multi-Agent Research Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    # Initialize system
    if not initialize_system():
        st.stop()
    
    
    # Top navigation tabs
    tab_stock, tab_portfolio, tab_config, tab_status = st.tabs([
        "Stock Analysis",
        "Portfolio Recs",
        "Configuration",
        "System Status",
    ])

    with tab_stock:
        stock_analysis_page()
    with tab_portfolio:
        portfolio_recommendations_page()
    with tab_config:
        configuration_page()
    with tab_status:
        system_status_and_ai_disclosure_page()


def stock_analysis_page():
    """Single or multiple stock analysis page."""
    import time as time_module  # Explicit import to avoid shadowing issues
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
    
    # Weight preset
    st.markdown("### ⚖️ Agent Weights")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        weight_preset = st.selectbox(
            "Choose Weight Configuration:",
            options=["equal_weights", "custom_weights"],
            format_func=lambda x: {
                "equal_weights": "1. Equal Weights",
                "custom_weights": "2. Custom Weights"
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
            if st.button("Configure Custom Weights"):
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
            
            @st.fragment
            def _weight_slider_fragment():
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

            st.write("**Configure Custom Agent Weights:**")
            _weight_slider_fragment()

            # Lock in weights button
            st.markdown("---")
            if st.button("Lock In Custom Weights", type="primary"):
                st.session_state.locked_custom_weights = st.session_state.custom_agent_weights.copy()
                st.success("Custom weights locked in! These will be used for analysis.")
                st.session_state.show_custom_weights = False
        
        # Use locked custom weights if available
        if 'locked_custom_weights' in st.session_state:
            agent_weights = st.session_state.locked_custom_weights
            
            # Show which weights are active
            with st.expander("Active Custom Weights", expanded=False):
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

    else:  # equal_weights
        with col2:
            if st.button("Apply Equal Weights"):
                agent_weights = {
                    'value': 1.0,
                    'growth_momentum': 1.0,
                    'macro_regime': 1.0,
                    'risk': 1.0,
                    'sentiment': 1.0
                }
                st.success("Equal weights applied!")
    
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
        status_text.text("Initializing analysis...")
        
        # Track analysis start time for adaptive estimates
        import time as time_module
        analysis_start_time = time_module.time()
        
        # Initialize progress tracking in session state
        st.session_state.analysis_progress = {
            'progress_bar': progress_bar,
            'status_text': status_text,
            'start_time': analysis_start_time
        }
        
        # Handle single or multiple stock analysis
        if analysis_mode == "Single Stock":
            # Single stock analysis (existing logic)
            try:
                # Initialize step tracking for this analysis
                st.session_state.current_analysis_start = time_module.time()
                st.session_state.current_step_start = time_module.time()
                st.session_state.last_step = 0
                
                # Calculate estimated time
                if st.session_state.analysis_times:
                    avg_time = sum(st.session_state.analysis_times) / len(st.session_state.analysis_times)
                    est_minutes = int(avg_time // 60)
                    est_seconds = int(avg_time % 60)
                    status_text.text(f"Starting analysis... (Est. {est_minutes}m {est_seconds}s)")
                else:
                    status_text.text("Starting analysis... (Est. ~30-40s)")
                
                progress_bar.progress(0)
                
                # Track start time
                start_time = time_module.time()
                
                # Convert analysis_date to string format
                # Handle both date object and potential tuple from date_input
                if isinstance(analysis_date, (datetime, type(datetime.now().date()))):
                    date_str = analysis_date.strftime('%Y-%m-%d') if hasattr(analysis_date, 'strftime') else str(analysis_date)
                elif isinstance(analysis_date, tuple) and len(analysis_date) > 0:
                    date_str = analysis_date[0].strftime('%Y-%m-%d') if hasattr(analysis_date[0], 'strftime') else str(analysis_date[0])
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                
                # Run analysis with optional agent weights
                result = st.session_state.orchestrator.analyze_stock(
                    ticker=ticker,
                    analysis_date=date_str,
                    agent_weights=agent_weights
                )
                
                # Track end time and store
                end_time = time_module.time()
                analysis_duration = end_time - start_time
                st.session_state.analysis_times.append(analysis_duration)
                
                # Keep only last 50 times for better estimates
                if len(st.session_state.analysis_times) > 50:
                    st.session_state.analysis_times = st.session_state.analysis_times[-50:]
                
                # Final completion with actual time
                actual_minutes = int(analysis_duration // 60)
                actual_seconds = int(analysis_duration % 60)
                status_text.text(f"Analysis complete! (Took {actual_minutes}m {actual_seconds}s)")
                progress_bar.progress(100)
                
                # Clear progress indicators after a brief moment
                time_module.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                if 'error' in result:
                    st.error(f"{result['error']}")
                    return
                
                # Display results
                display_stock_analysis(result)
                
            except Exception as e:
                # Clear progress indicators on error
                progress_bar.empty()
                status_text.empty()
                st.error(f"Analysis failed: {e}")
        
        else:
            # Multiple stocks analysis
            import time
            
            st.info(f"Analyzing {len(tickers)} stocks: {', '.join(tickers)}")
            
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
                stock_start_time = time_module.time()
                
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
                    
                    overall_status.text(f"Analyzing {stock_ticker} ({idx + 1} of {len(tickers)}) - Est. {est_minutes}m {est_seconds}s remaining (Rate: {stocks_per_minute:.1f} stocks/min)")
                else:
                    # Use historical average for first stock
                    remaining_stocks = len(tickers) - idx
                    est_remaining_seconds = int(avg_time * remaining_stocks)
                    est_minutes = est_remaining_seconds // 60
                    est_seconds = est_remaining_seconds % 60
                    overall_status.text(f"Analyzing {stock_ticker} ({idx + 1} of {len(tickers)}) - Est. {est_minutes}m {est_seconds}s remaining")
                
                # Create progress tracking for individual stock - VISIBLE FROM START
                stock_progress_bar = st.progress(0.0)  # Start at 0% but visible
                stock_status_text = st.empty()
                stock_status_text.text("Initializing analysis...")  # Show initial status
                
                # Create progress tracking for individual stock - VISIBLE FROM START
                stock_progress_bar = st.progress(0.0)  # Start at 0% but visible
                stock_status_text = st.empty()
                stock_status_text.text("Initializing analysis...")  # Show initial status
                
                # Track analysis start time for adaptive estimates
                analysis_start_time = time_module.time()
                
                # Simple progress tracking in session state
                st.session_state.analysis_progress = {
                    'progress_bar': stock_progress_bar,
                    'status_text': stock_status_text,
                    'start_time': analysis_start_time
                }
                
                try:
                    # Convert analysis_date to string format
                    # Handle both date object and potential tuple from date_input
                    if isinstance(analysis_date, (datetime, type(datetime.now().date()))):
                        date_str = analysis_date.strftime('%Y-%m-%d') if hasattr(analysis_date, 'strftime') else str(analysis_date)
                    elif isinstance(analysis_date, tuple) and len(analysis_date) > 0:
                        date_str = analysis_date[0].strftime('%Y-%m-%d') if hasattr(analysis_date[0], 'strftime') else str(analysis_date[0])
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # Run analysis for this stock
                    result = st.session_state.orchestrator.analyze_stock(
                        ticker=stock_ticker,
                        analysis_date=date_str,
                        agent_weights=agent_weights
                    )
                    
                    # Track time for this stock
                    stock_end_time = time_module.time()
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
            overall_status.text(f"Batch analysis complete! (Total time: {total_minutes}m {total_seconds}s)")
            time_estimate_display.success(f"Analyzed {len(results)} stocks successfully in {total_minutes}m {total_seconds}s")
            time.sleep(1.5)
            overall_progress.empty()
            overall_status.empty()
            time_estimate_display.empty()
            
            # Display results summary
            if results:
                display_multiple_stock_analysis(results, failed_tickers)
            else:
                st.error("All analyses failed!")
                for ticker_name, error_msg in failed_tickers:
                    st.error(f"**{ticker_name}**: {error_msg}")


def display_stock_analysis(result: dict):
    """Display detailed stock analysis results with enhanced rationales."""
    
    
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
        # Score badge
        final_score = result['final_score']
        if final_score >= 70:
            st.success(f"Score: {final_score:.1f}")
        elif final_score >= 50:
            st.info(f"Score: {final_score:.1f}")
        else:
            st.warning(f"Score: {final_score:.1f}")
    
    # Show which weights were used for this analysis
    weight_preset = st.session_state.get('weight_preset', 'equal_weights')
    if weight_preset == 'custom_weights' and 'locked_custom_weights' in st.session_state:
        with st.expander("Custom Weights Used in This Analysis", expanded=False):
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
                
                st.caption("Higher weights mean that agent's score had MORE influence on the final score.")
    

    
    # Enhanced key metrics section with modern card-style layout
    st.markdown("### 📊 Key Investment Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        final_score = result['final_score']
        delta_color = "normal" if final_score >= 70 else "inverse" if final_score < 50 else "off"
        st.metric("Final Score", f"{final_score:.1f}/100", help="Overall investment recommendation score")
    with col2:
        price_value = result['fundamentals'].get('price')
        st.metric("Current Price", f"${price_value:.2f}" if price_value and price_value != 0 else "N/A")
    with col3:
        pe_ratio = result['fundamentals'].get('pe_ratio')
        st.metric("P/E Ratio", f"{pe_ratio:.1f}" if pe_ratio and pe_ratio != 0 else "N/A", help="Price-to-Earnings ratio")
    with col4:
        beta = result['fundamentals'].get('beta')
        st.metric("Beta", f"{beta:.2f}" if beta and beta != 0 else "N/A", help="Market volatility coefficient")
    
    # Additional Enhanced Metrics Row
    col5, col6, col7, col8, col9 = st.columns(5)
    with col5:
        div_yield = result['fundamentals'].get('dividend_yield')
        # Dividend yield can be a decimal (0.02 = 2%) or already a percentage (2.0 = 2%)
        if div_yield and div_yield != 0:
            # If it's a small decimal, multiply by 100, otherwise use as-is
            display_yield = div_yield * 100 if div_yield < 1 else div_yield
            st.metric("Dividend Yield", f"{display_yield:.2f}%", help="Annual dividend yield percentage")
        else:
            st.metric("Dividend Yield", "N/A", help="Annual dividend yield percentage")
    with col6:
        eps = result['fundamentals'].get('eps')
        if eps and eps != 0:
            st.metric("EPS", f"${eps:.2f}", help="Earnings per share")
        else:
            st.metric("EPS", "N/A", help="Earnings per share")
    with col7:
        week_52_low = result['fundamentals'].get('week_52_low')
        week_52_high = result['fundamentals'].get('week_52_high')
        if week_52_low and week_52_high:
            st.metric("52W Low", f"${week_52_low:.2f}", help="52-week low price")
        else:
            st.metric("52W Low", "N/A", help="52-week low price")
    with col8:
        week_52_low = result['fundamentals'].get('week_52_low')
        week_52_high = result['fundamentals'].get('week_52_high')
        if week_52_low and week_52_high:
            st.metric("52W High", f"${week_52_high:.2f}", help="52-week high price")
        else:
            st.metric("52W High", "N/A", help="52-week high price")
    with col9:
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
        st.subheader("52-Week Price Range")

        # Calculate position of current price within the range
        price_position = (current_price - week_52_low) / (week_52_high - week_52_low)
        price_position = max(0, min(1, price_position))  # Clamp between 0 and 1

        # Determine color based on position
        if price_position >= 0.80:
            bar_color = "#0ea371"
            position_text = "Near 52W High"
        elif price_position >= 0.60:
            bar_color = "#3b82f6"
            position_text = "Upper Range"
        elif price_position >= 0.40:
            bar_color = "#d97706"
            position_text = "Mid Range"
        elif price_position >= 0.20:
            bar_color = "#ea580c"
            position_text = "Lower Range"
        else:
            bar_color = "#dc2626"
            position_text = "Near 52W Low"

        # Single HTML bar with prices embedded at each end and current price marker
        bar_html = f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-weight: 600; font-size: 14px; color: #dc2626;">${week_52_low:.2f}</span>
                <span style="font-weight: 600; font-size: 13px; color: #1a1a2e;">Current: ${current_price:.2f}</span>
                <span style="font-weight: 600; font-size: 14px; color: #0ea371;">${week_52_high:.2f}</span>
            </div>
            <div style="position: relative; width: 100%; height: 36px; background-color: #f0f0f5; border-radius: 8px; overflow: visible; border: 1px solid #e5e7eb;">
                <div style="position: absolute; left: 0; top: 0; width: {price_position*100}%; height: 100%; background: {bar_color}; border-radius: 8px 0 0 8px; opacity: 0.85;"></div>
                <div style="position: absolute; left: {price_position*100}%; top: 50%; transform: translate(-50%, -50%); width: 3px; height: 44px; background-color: #1a1a2e; z-index: 10; border-radius: 2px;"></div>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

        # Position info
        st.markdown(f"**{position_text}** - {price_position*100:.1f}% of 52-week range")
    
    # ========== COMPREHENSIVE SCORE ANALYSIS SECTION ==========
    st.markdown("---")
    st.markdown("### ⚖️ Score Analysis & Agent Breakdown")
    
    with st.expander("Detailed Breakdown", expanded=False):
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
            weights_source = "Default Weights"
        
        st.write(f"**Weights Source:** {weights_source}")
        st.write("---")
        
        # Calculate weight breakdown
        total_weighted_score = 0
        total_weight = 0
        breakdown_data = []
        
        agent_order = ['value_agent', 'growth_momentum_agent', 'macro_regime_agent', 'risk_agent', 'sentiment_agent']
        agent_labels = {
            'value_agent': 'Value',
            'growth_momentum_agent': 'Growth/Momentum',
            'macro_regime_agent': 'Macro Regime',
            'risk_agent': 'Risk',
            'sentiment_agent': 'Sentiment'
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
                st.success(f"Custom weights INCREASED the score by {weight_effect:.2f} points by emphasizing higher-scoring agents")
            else:
                st.warning(f"Custom weights DECREASED the score by {abs(weight_effect):.2f} points by emphasizing lower-scoring agents")
        else:
            st.info("Custom weights had minimal impact on the final score")
        
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
    st.markdown("### 🤖 Agent Analysis Details")
    
    # Display enhanced agent rationales with collaboration
    display_enhanced_agent_rationales(result)
    
    # Comprehensive rationale
    st.markdown("---")
    st.markdown("### 📋 Investment Rationale")
    
    with st.expander("View Full Report", expanded=False):
        # Get the comprehensive rationale from the result
        comprehensive_rationale = result.get('rationale', '')
        
        if comprehensive_rationale:
            # Display in a code block for better formatting
            st.text(comprehensive_rationale)
            
            # Add download button for the rationale
            st.download_button(
                label="Download Complete Rationale (TXT)",
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
        
        if final_score >= 80:
            st.success(f"**STRONG BUY** - Excellent score of {final_score:.1f} with compelling fundamentals and strong multi-factor support.")
        elif final_score >= 70:
            st.success(f"**BUY** - Strong score of {final_score:.1f} indicating good investment potential with favorable risk/reward profile.")
        elif final_score >= 60:
            st.info(f"**HOLD** - Moderate score of {final_score:.1f}. Suitable for holding if already owned, but not a priority for new positions.")
        elif final_score >= 40:
            st.warning(f"**WEAK HOLD** - Below-average score of {final_score:.1f}. Consider for portfolio review or reduction.")
        else:
            st.error(f"**SELL** - Low score of {final_score:.1f} with significant concerns. Consider alternatives.")

    # Export functionality
    with st.expander("Export Analysis", expanded=False):
        agent_scores = result['agent_scores']
        export_data = {
            'Ticker': [result['ticker']],
            'Name': [result['fundamentals'].get('name', 'N/A')],
            'Final Score': [result['final_score']],
            'Sector': [result['fundamentals'].get('sector', 'N/A')],
            'Price': [result['fundamentals'].get('price', 0)],
            **{f"{agent.replace('_', ' ').title()}_Score": [score] for agent, score in agent_scores.items()}
        }
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        current_timestamp = datetime.now().strftime('%Y%m%d')
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.download_button(
                label="� Download CSV Report",
                data=csv,
                file_name=f"{result['ticker']}_analysis_{current_timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            # Generate detailed markdown report
            ticker = result['ticker']
            report = f"""# Investment Analysis: {ticker}
## {result['fundamentals'].get('name', 'N/A')}

**Date:** {datetime.now().strftime('%B %d, %Y')}
**Sector:** {result['fundamentals'].get('sector', 'N/A')}
**Price:** ${result['fundamentals'].get('price', 0):.2f}

---

## Score: {result['final_score']:.1f}/100
**Recommendation:** {result.get('recommendation', 'N/A')}

---

## Agent Breakdown
"""
            for agent, score in agent_scores.items():
                agent_name = agent.replace('_', ' ').title()
                report += f"- **{agent_name}:** {score:.1f}/100\n"
            
            report += f"\n---\n\n## Key Metrics\n"
            report += f"- **Market Cap:** ${result['fundamentals'].get('market_cap', 0)/1e9:.2f}B\n"
            report += f"- **P/E Ratio:** {result['fundamentals'].get('pe_ratio', 'N/A')}\n"
            report += f"- **Beta:** {result['fundamentals'].get('beta', 'N/A')}\n"
            
            if result['fundamentals'].get('dividend_yield'):
                report += f"- **Dividend Yield:** {result['fundamentals']['dividend_yield']*100:.2f}%\n"
            
            report += f"\n---\n\n## Agent Analysis\n"
            for agent, rationale in result.get('agent_rationales', {}).items():
                if rationale:
                    agent_name = agent.replace('_', ' ').title()
                    report += f"### {agent_name}\n{rationale}\n\n"
            
            report += f"\n---\n*Investment Analysis Platform*\n"
            
            st.download_button(
                label="� Download Full Report",
                data=report,
                file_name=f"{ticker}_report_{current_timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
    

def display_multiple_stock_analysis(results: list, failed_tickers: list):
    """Display analysis results for multiple stocks in a comparison table."""
    
    st.success(f"Successfully analyzed {len(results)} stock{'s' if len(results) != 1 else ''}")
    
    if failed_tickers:
        st.warning(f"Failed to analyze {len(failed_tickers)} stock{'s' if len(failed_tickers) != 1 else ''}")
        with st.expander("View Failed Tickers", expanded=False):
            for ticker_name, error_msg in failed_tickers:
                st.error(f"**{ticker_name}**: {error_msg}")
    
    # Summary comparison
    st.markdown("---")
    st.markdown("### 📊 Comparison")
    
    # Prepare data for comparison table
    comparison_data = []
    for result in results:
        row = {
            'Ticker': result['ticker'],
            'Final Score': result['final_score'],
            'Recommendation': result.get('recommendation', 'N/A'),
            'Price': result['fundamentals'].get('price', 0),
            'Market Cap': result['fundamentals'].get('market_cap', 0),
            'Sector': result['fundamentals'].get('sector', 'N/A'),
            'Value Score': result.get('agent_scores', {}).get('value_agent', 0),
            'Growth Score': result.get('agent_scores', {}).get('growth_momentum_agent', 0),
            'Macro Score': result.get('agent_scores', {}).get('macro_regime_agent', 0),
            'Risk Score': result.get('agent_scores', {}).get('risk_agent', 0),
            'Sentiment Score': result.get('agent_scores', {}).get('sentiment_agent', 0),
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
    
    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Export to CSV button
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Comparison (CSV)",
        data=csv,
        file_name=f"stock_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Visual comparison
    st.markdown("---")
    st.markdown("### 📊 Charts")
    
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
    
    # Portfolio insights
    st.markdown("---")
    st.markdown("### 🎯 Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Sector Diversification**")
        
        # Calculate sector distribution
        sector_counts = {}
        sector_scores = {}
        for result in results:
            sector = result['fundamentals'].get('sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if sector not in sector_scores:
                sector_scores[sector] = []
            sector_scores[sector].append(result['final_score'])
        
        # Create pie chart
        fig_sector = go.Figure(data=[go.Pie(
            labels=list(sector_counts.keys()),
            values=list(sector_counts.values()),
            hole=.3,
            textinfo='label+percent',
            marker=dict(colors=CHART_COLORS)
        )])
        
        fig_sector.update_layout(height=350, showlegend=True)
        st.plotly_chart(fig_sector, use_container_width=True)
        
        # Sector concentration warning
        max_sector_pct = max(sector_counts.values()) / len(results) * 100
        if max_sector_pct > 40:
            st.warning(f"High concentration: {max_sector_pct:.0f}% in one sector")
        elif max_sector_pct > 30:
            st.info(f"Moderate concentration: {max_sector_pct:.0f}% in one sector")
        else:
            st.success(f"Well diversified: Max {max_sector_pct:.0f}% in any sector")
    
    with col2:
        st.write("**Risk Distribution Matrix**")
        
        # Create risk/score scatter plot
        risk_scores = [r['agent_scores'].get('risk_agent', 50) for r in results]
        final_scores = [r['final_score'] for r in results]
        tickers = [r['ticker'] for r in results]
        market_caps = [r['fundamentals'].get('market_cap', 0) for r in results]
        
        fig_risk = go.Figure()
        
        fig_risk.add_trace(go.Scatter(
            x=risk_scores,
            y=final_scores,
            mode='markers+text',
            text=tickers,
            textposition='top center',
            marker=dict(
                size=[max(10, min(30, mc/1e10)) for mc in market_caps],  # Size by market cap
                color=final_scores,
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Score")
            ),
            hovertemplate='<b>%{text}</b><br>Risk: %{x:.1f}<br>Score: %{y:.1f}<extra></extra>'
        ))
        
        # Add quadrant lines
        fig_risk.add_hline(y=70, line_dash="dash", line_color="gray", opacity=0.5)
        fig_risk.add_vline(x=70, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add quadrant labels
        fig_risk.add_annotation(x=85, y=85, text="High Score<br>Low Risk", showarrow=False, opacity=0.5)
        fig_risk.add_annotation(x=55, y=85, text="High Score<br>High Risk", showarrow=False, opacity=0.5)
        fig_risk.add_annotation(x=85, y=55, text="Low Score<br>Low Risk", showarrow=False, opacity=0.5)
        fig_risk.add_annotation(x=55, y=55, text="Low Score<br>High Risk", showarrow=False, opacity=0.5)
        
        fig_risk.update_layout(
            xaxis_title="Risk Score (Higher = Safer)",
            yaxis_title="Final Score",
            xaxis_range=[0, 100],
            yaxis_range=[0, 100],
            height=350
        )
        st.plotly_chart(fig_risk, use_container_width=True)
        
        # Risk summary
        high_risk_count = sum(1 for r in risk_scores if r < 50)
        if high_risk_count > len(results) * 0.5:
            st.warning(f"{high_risk_count}/{len(results)} stocks are high risk")
        else:
            st.success(f"Balanced risk: {high_risk_count}/{len(results)} high risk stocks")
    
    # Sector performance breakdown
    st.write("**Sector Performance Summary**")
    sector_summary = []
    for sector, scores in sector_scores.items():
        sector_summary.append({
            'Sector': sector,
            'Count': len(scores),
            'Avg Score': sum(scores) / len(scores),
            'Max Score': max(scores),
            'Min Score': min(scores)
        })
    
    sector_df = pd.DataFrame(sector_summary).sort_values('Avg Score', ascending=False)
    sector_df['Avg Score'] = sector_df['Avg Score'].round(1)
    sector_df['Max Score'] = sector_df['Max Score'].round(1)
    sector_df['Min Score'] = sector_df['Min Score'].round(1)
    
    st.dataframe(sector_df, use_container_width=True, hide_index=True)
    
    # Individual stock details
    st.markdown("---")
    st.markdown("### 📋 Stock Details")
    
    tabs = st.tabs([result['ticker'] for result in results])
    
    for idx, (tab, result) in enumerate(zip(tabs, results)):
        with tab:
            display_stock_analysis(result)


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
        # Get actual scraped article count from sentiment agent details
        agent_results = result.get('agent_results', {})
        sentiment_details = agent_results.get('sentiment_agent', {}).get('details', {})
        news_count = sentiment_details.get('num_articles', 0)
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

    # Create agent names from keys
    agent_names = [key.replace('_', ' ').title() for key in agent_scores.keys()]
    
    # Agent collaboration results
    collaboration_results = get_agent_collaboration(result)
    
    # Display agent scores chart
    st.write("**� Agent Score Overview**")
    
    # Create bar chart with gradient colors 
    fig = go.Figure()
    gradient_colors = [get_gradient_color(score) for score in agent_scores.values()]
    
    fig.add_trace(go.Bar(
        x=agent_names,
        y=list(agent_scores.values()),
        marker_color=gradient_colors,
        text=[f"{s:.1f}" for s in agent_scores.values()],
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
    
    # Create detailed rationale display for each agent 
    for i, (agent_key, agent_name) in enumerate(zip(agent_scores.keys(), agent_names)):
        score = agent_scores[agent_key]
        rationale = agent_rationales.get(agent_key, "Analysis not available")
        
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
                ">
                    <h2 style="margin: 0; color: white;">{score:.1f}</h2>
                    <p style="margin: 0; color: white;">out of 100</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Score interpretation
                if score >= 80:
                    st.success("**Excellent**\nStrong positive signals")
                elif score >= 65:
                    st.info("**Good**\nPositive with minor concerns")
                elif score >= 50:
                    st.warning("**Moderate**\nMixed signals")
                elif score >= 35:
                    st.error("**Concerning**\nSeveral negative factors")
                else:
                    st.error("**Poor**\nSignificant issues identified")
            
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

{'**Large-Cap Classification:** Recognized as inherently lower risk due to institutional size, market liquidity, and regulatory oversight.' if is_low_risk else '**Standard Risk Assessment:** Evaluated using traditional risk metrics without size-based adjustments.'}

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
    st.header("AI-Powered Portfolio Recommendations")
    st.write("Multi-stage AI selection using OpenAI o3 and Gemini 2.5 Pro to identify optimal stocks.")
    st.markdown("---")
    
    # Challenge context input
    st.subheader("Investment Challenge Context")
    challenge_context = st.text_area(
        "Describe the investment challenge, goals, and requirements:",
        value="""Generate an optimal diversified portfolio that maximizes risk-adjusted returns 
while adhering to the Investment Policy Statement constraints.
Focus on high-quality companies with strong fundamentals and growth potential.""",
        height=120,
        help="Provide detailed context about the investment challenge"
    )
    
    st.markdown("---")
    
    # Configuration options
    with st.expander("Portfolio Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_positions = st.number_input(
                "Target Portfolio Positions",
                min_value=3,
                max_value=20,
                value=5,
                help="Target number of holdings in portfolio (up to 20 for diversified growth)"
            )
    
    # Advanced options
    with st.expander("Investment Focus & Strategy"):
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
    
    # AI-powered ticker selection
    tickers = None
    st.info("""
    **AI Selection Process:**
    1. OpenAI o3 selects 20 best tickers
    2. Gemini 2.5 Pro selects 20 best tickers
    3. Aggregate to 40 unique candidates
    4. Generate 4-sentence rationale for each
    5. Run 3 rounds of top-5 selection
    6. Consolidate to final 5 tickers
    7. Full analysis on all final selections
    """)
    
    if st.button("Generate Portfolio", type="primary", use_container_width=True):
        with st.spinner("Running AI-powered portfolio generation..."):
            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Generate recommendations
                status_text.text("AI agents selecting optimal tickers across all market caps...")
                progress_bar.progress(10)

                result = st.session_state.orchestrator.recommend_portfolio(
                    challenge_context=challenge_context,
                    tickers=tickers,
                    num_positions=num_positions
                )

                status_text.text("Running multi-agent analysis on selected stocks...")
                progress_bar.progress(60)

                status_text.text("Constructing portfolio with position sizing...")
                progress_bar.progress(85)

                status_text.text("Portfolio generation complete!")
                progress_bar.progress(100)
                
                # Store result in session state
                st.session_state.portfolio_result = result
                
                
                # Display results
                display_portfolio_recommendations(result)
                
            except Exception as e:
                st.error(f"Portfolio generation failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def display_portfolio_recommendations(result: dict):
    """Display portfolio recommendations with AI selection details."""
    
    portfolio = result['portfolio']
    summary = result['summary']
    selection_log = result.get('selection_log', {})
    
    if not portfolio:
        st.warning("No stocks found in universe")
        return
    
    # AI Selection Summary (if available)
    if not selection_log.get('manual_selection', False):
        st.subheader("AI Selection Process")
        
        with st.expander("View AI Selection Details", expanded=False):
            stages = selection_log.get('stages', [])
            
            for stage_info in stages:
                stage = stage_info.get('stage', 'Unknown')
                
                if stage == 'openai_initial_selection':
                    st.markdown("#### 1️⃣ OpenAI Initial Selection")
                    tickers = stage_info.get('tickers', [])
                    st.write(f"Selected {len(tickers)} tickers: {', '.join(tickers)}")
                
                elif stage == 'gemini_initial_selection':
                    st.markdown("#### 2. Gemini 2.5 Pro Initial Selection")
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
                    st.success(f"Final tickers: {', '.join(final)}")
            
            # Download log
            import json
            log_json = json.dumps(selection_log, indent=2)
            st.download_button(
                label="Download Full Selection Log (JSON)",
                data=log_json,
                file_name=f"ai_selection_log_{result['analysis_date']}.json",
                mime="application/json"
            )
        
        # Download complete archives section
        st.markdown("---")
        st.subheader("Complete Archives")
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
                    st.info(f"Found **{len(log_files)}** archived portfolio selection(s)")
                
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
                        label="Download All Archives (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"portfolio_archives_{result['analysis_date']}.zip",
                        mime="application/zip",
                        use_container_width=True,
                        help="Download all portfolio selection logs as a ZIP file"
                    )
                
                # Show list of available archives
                with st.expander("View Available Archives", expanded=False):
                    for log_file in sorted(log_files, reverse=True):
                        file_path = os.path.join(logs_dir, log_file)
                        file_size = os.path.getsize(file_path)
                        file_size_kb = file_size / 1024
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(f"{log_file}")
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
                st.info("No archived selections found yet. Generate a portfolio to create archives.")
        else:
            st.warning("Portfolio selection logs directory not found.")
    
    st.markdown("---")
    
    # Summary metrics
    st.subheader("Portfolio Summary")
    
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
    st.subheader("Portfolio Holdings")
    
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
    st.subheader("Holdings Table")
    df = pd.DataFrame(portfolio)
    df = df[['ticker', 'name', 'sector', 'final_score', 'target_weight_pct']]
    df.columns = ['Ticker', 'Name', 'Sector', 'Score', 'Weight %']

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
        }
    )
    
    # Sector allocation
    st.subheader("Sector Allocation")
    
    sector_data = summary['sector_exposure']
    fig = go.Figure(data=[go.Pie(
        labels=list(sector_data.keys()),
        values=list(sector_data.values()),
        hole=.3,
        textinfo='label+percent',
        marker=dict(colors=CHART_COLORS)
    )])
    
    fig.update_layout(height=400, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    st.subheader("Export Portfolio")
    
    col1, col2 = st.columns(2)

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
    



def system_status_and_ai_disclosure_page():
    """Combined system status and AI disclosure page."""
    st.header("System Status & AI Disclosure")
    st.write("Monitor system health, data provider status, and AI usage information.")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["System Status", "AI Usage Disclosure"])
    
    with tab1:
        st.subheader("Data Provider Status")
        
        # Check if data provider is available
        if not st.session_state.data_provider:
            st.error("Data provider not initialized. Please restart the application.")
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
            has_gemini = bool(os.getenv('GEMINI_API_KEY'))
            premium_count = sum([has_polygon, has_gemini])
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
            "Gemini AI": bool(os.getenv('GEMINI_API_KEY')),
            "NewsAPI": bool(os.getenv('NEWSAPI_KEY')),
            "IEX Cloud": bool(os.getenv('IEX_TOKEN'))
        }
        
        cols = st.columns(3)
        for i, (service, available) in enumerate(api_keys_status.items()):
            with cols[i % 3]:
                icon = "" if available else ""
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
            "AI-Enhanced Analysis": bool(os.getenv('GEMINI_API_KEY')),
            "52-Week Range Verification": True,
            "Multi-Source Fallback": True
        }
        
        col1, col2 = st.columns(2)
        for i, (capability, available) in enumerate(capabilities.items()):
            with col1 if i % 2 == 0 else col2:
                icon = "" if available else ""
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
                        results['Price Data'] = f"{len(price_data)} days of data"
                        if 'SYNTHETIC_DATA' in price_data.columns:
                            results['Price Data'] += " (⚠️ Synthetic)"
                    else:
                        results['Price Data'] = "No data"
                        
                except Exception as e:
                    results['Price Data'] = f"Error: {str(e)}"
                
                # Test fundamentals
                try:
                    if hasattr(st.session_state.data_provider, 'get_fundamentals_enhanced'):
                        fund_data = st.session_state.data_provider.get_fundamentals_enhanced(test_ticker)
                    else:
                        fund_data = st.session_state.data_provider.get_fundamentals(test_ticker)
                    
                    if fund_data:
                        results['Fundamentals'] = f"{len(fund_data)} data points"
                        if fund_data.get('estimated'):
                            results['Fundamentals'] += " (⚠️ Estimated)"
                    else:
                        results['Fundamentals'] = "No data"
                        
                except Exception as e:
                    results['Fundamentals'] = f"Error: {str(e)}"
                
                # Display results
                for source, result in results.items():
                    st.write(f"**{source}:** {result}")
        
        # Clear Cache
        if st.button("Clear Cache", help="Clear cached data to force fresh API calls"):
            cache_dir = Path("data/cache")
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                st.success("Cache cleared!")
            else:
                st.info("No cache to clear")
    
    with tab2:
        st.subheader("AI Usage Disclosure")
        
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
                label="Download Disclosure Log",
                data=log_data,
                file_name="ai_disclosure_log.jsonl",
                mime="application/json"
            )
        
        st.info("""
        **For Works Cited:**
        
        This system uses the following APIs/tools:
        - OpenAI o3 for agent reasoning and portfolio selection, Gemini 2.5 Pro for AI-powered ticker discovery and real-time data synthesis. 
        - yfinance/PolygonIO for market data
        - Alpha Vantage for fundamental data and macroeconomic indicators
        - NewsAPI for news sentiment analysis 
        
        All API calls are logged with timestamps, purposes, and token usage for full disclosure.
        """)
        
        # Premium Setup Guide
        st.markdown("---")
        st.subheader("Premium Setup Guide")
        
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
    st.write("Manage analysis constraints and model parameters.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Analysis Configuration", "Agent Weights", "Timing Analytics"])

    with tab1:
        st.subheader("Analysis Configuration")
        st.write("Configure analysis constraints and parameters.")
        
        # Load current IPS
        ips = st.session_state.config_loader.load_ips()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Position & Sector Constraints:**")
            max_position = st.number_input(
                "Max Single Position (%)", 
                value=float(ips.get('position_limits', {}).get('max_position_pct', 10.0)), 
                min_value=1.0, 
                max_value=50.0
            )
            max_sector = st.number_input(
                "Max Sector Allocation (%)", 
                value=float(ips.get('position_limits', {}).get('max_sector_pct', 30.0)), 
                min_value=10.0, 
                max_value=100.0
            )
            
            st.write("**Price & Market Cap:**")
            min_price = st.number_input(
                "Min Stock Price ($)", 
                value=float(ips.get('universe', {}).get('min_price', 1.0)), 
                min_value=0.0
            )
            min_market_cap = st.number_input(
                "Min Market Cap ($B)", 
                value=float(ips.get('universe', {}).get('min_market_cap', 1000000000)) / 1000000000, 
                min_value=0.0
            )
        
        with col2:
            st.write("**Risk Parameters:**")
            min_beta = st.number_input(
                "Min Beta", 
                value=float(ips.get('portfolio_constraints', {}).get('beta_min', 0.7)), 
                min_value=0.0, 
                max_value=3.0
            )
            max_beta = st.number_input(
                "Max Beta", 
                value=float(ips.get('portfolio_constraints', {}).get('beta_max', 1.3)), 
                min_value=0.0, 
                max_value=3.0
            )
            max_volatility = st.number_input(
                "Max Portfolio Volatility (%)", 
                value=float(ips.get('portfolio_constraints', {}).get('max_portfolio_volatility', 18.0)), 
                min_value=0.0, 
                max_value=50.0
            )
        
        st.write("**Excluded Sectors:**")
        current_exclusions = ips.get('exclusions', {}).get('sectors', [])
        excluded_sectors = st.multiselect(
            "Select sectors to exclude",
            options=["Energy", "Financials", "Healthcare", "Technology", "Consumer Staples", "Consumer Discretionary", 
                    "Industrials", "Materials", "Real Estate", "Utilities", "Communication Services", "Tobacco", "Weapons"],
            default=current_exclusions
        )
        
        if st.button("Save Configuration"):
            # Update IPS with proper structure
            if 'position_limits' not in ips:
                ips['position_limits'] = {}
            ips['position_limits']['max_position_pct'] = max_position
            ips['position_limits']['max_sector_pct'] = max_sector
            
            if 'universe' not in ips:
                ips['universe'] = {}
            ips['universe']['min_price'] = min_price
            ips['universe']['min_market_cap'] = min_market_cap * 1000000000
            
            if 'portfolio_constraints' not in ips:
                ips['portfolio_constraints'] = {}
            ips['portfolio_constraints']['beta_min'] = min_beta
            ips['portfolio_constraints']['beta_max'] = max_beta
            ips['portfolio_constraints']['max_portfolio_volatility'] = max_volatility
            
            if 'exclusions' not in ips:
                ips['exclusions'] = {}
            ips['exclusions']['sectors'] = excluded_sectors

            st.session_state.config_loader.save_ips(ips)
            st.success("Configuration saved!")

    with tab2:
        st.subheader("Agent Weights")
        st.write("Adjust how much each agent influences the final score.")
        
        # Load current weights
        model_config = st.session_state.config_loader.load_model_config()
        weights = model_config['agent_weights']
        
        new_weights = {}
        for agent, weight in weights.items():
            new_weights[agent] = st.slider(
                f"{agent.replace('_', ' ').title()}",
                min_value=0.0,
                max_value=3.0,
                value=float(weight),
                step=0.1,
                help=f"Current weight: {weight}"
            )
        
        if st.button("Save Agent Weights"):
            st.session_state.config_loader.update_model_weights(new_weights)
            st.success("Agent weights updated!")
            st.info("System will be reinitialized on next analysis.")
            st.session_state.initialized = False
    
    with tab3:
        st.subheader("⏱️ Analysis Timing Analytics")
        st.write("Deep insights into step-level timing data collected from all analyses.")
        
        if hasattr(st.session_state, 'step_time_manager'):
            manager = st.session_state.step_time_manager
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            
            total_samples = sum(len(manager.step_times.get(i, [])) for i in range(1, 11))
            all_stats = manager.get_all_stats()
            
            with col1:
                st.metric("Total Data Points", f"{total_samples:,}")
            
            with col2:
                steps_tracked = len(all_stats)
                st.metric("Steps Tracked", f"{steps_tracked}/10")
            
            with col3:
                if all_stats:
                    avg_analysis_time = sum(s['avg'] for s in all_stats.values())
                    st.metric("Est. Analysis Time", f"{avg_analysis_time:.1f}s")
                else:
                    st.metric("Est. Analysis Time", "No data")
            
            st.markdown("---")
            
            # Detailed step breakdown
            st.subheader("Step-by-Step Breakdown")
            
            step_names = {
                1: "Data Gathering - Fundamentals",
                2: "Data Gathering - Market Data",
                3: "Value Agent Analysis",
                4: "Growth/Momentum Agent Analysis",
                5: "Macro Regime Agent Analysis",
                6: "Risk Agent Analysis",
                7: "Sentiment Agent Analysis",
                8: "Score Blending",
                9: "Finalizing",
                10: "Final Analysis"
            }
            
            if all_stats:
                for step in sorted(all_stats.keys()):
                    stats = all_stats[step]
                    name = step_names.get(step, f"Step {step}")
                    
                    with st.expander(f"**{name}**", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Samples", stats['count'])
                            st.metric("Average", f"{stats['avg']:.2f}s")
                        
                        with col2:
                            st.metric("Median", f"{stats['median']:.2f}s")
                            st.metric("Std Dev", f"{stats['std_dev']:.2f}s")
                        
                        with col3:
                            st.metric("Minimum", f"{stats['min']:.2f}s")
                            st.metric("Maximum", f"{stats['max']:.2f}s")
                        
                        with col4:
                            st.metric("25th %ile", f"{stats['p25']:.2f}s")
                            st.metric("75th %ile", f"{stats['p75']:.2f}s")
                
                st.markdown("---")
                
                # Export option
                if st.button("Export Timing Data"):
                    import pandas as pd
                    from datetime import datetime
                    
                    export_data = []
                    for step, stats in all_stats.items():
                        export_data.append({
                            'Step': step,
                            'Name': step_names.get(step, f"Step {step}"),
                            'Count': stats['count'],
                            'Average': stats['avg'],
                            'Median': stats['median'],
                            'Std_Dev': stats['std_dev'],
                            'Min': stats['min'],
                            'Max': stats['max'],
                            'P25': stats['p25'],
                            'P75': stats['p75']
                        })
                    
                    df = pd.DataFrame(export_data)
                    csv_data = df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download Timing Data CSV",
                        data=csv_data,
                        file_name=f"timing_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No timing data available yet. Run some analyses to collect timing statistics.")
        else:
            st.warning("Step time manager not initialized.")



if __name__ == "__main__":
    main()