# Wharton Investment Analysis System

A multi-agent AI-powered investment research platform built with Streamlit. Analyzes stocks across multiple dimensions, generates portfolio recommendations, and provides backtesting capabilities.

## Live Demo

**[Try the app on Streamlit Cloud](https://wharton-investment.streamlit.app)** (free, no setup required)

## Features

- **Multi-Agent Stock Analysis** - 5 specialized AI agents analyze stocks from different perspectives (value, growth/momentum, macro, risk, sentiment)
- **Portfolio Recommendations** - AI-powered portfolio construction with configurable weights and constraints
- **Backtesting Engine** - Walk-forward backtesting with biweekly rebalancing
- **Portfolio Management** - Track and manage portfolio positions with real-time prices
- **QA & Learning Center** - Track recommendation accuracy and learn from past performance
- **Google Sheets Export** - Auto-sync portfolio data to Google Sheets

## How It Works

The system uses a multi-agent architecture where each agent scores stocks independently (0-100):

| Agent | Focus | Key Inputs |
|-------|-------|-----------|
| Value Agent | Valuation metrics | P/E, EV/EBIT, FCF yield |
| Growth & Momentum Agent | Growth trajectory | Earnings growth, revenue CAGR, price momentum |
| Macro Regime Agent | Economic environment | Yield curve, inflation, PMI, unemployment |
| Risk Agent | Risk assessment | Beta, volatility, correlation, max drawdown |
| Sentiment Agent | Market sentiment | News headlines, analyst revisions, earnings surprises |

Scores are blended with configurable weights and adjusted for investor profile constraints.

## Quick Start

### Option 1: Use the Live Demo
Visit the [Streamlit Cloud deployment](https://wharton-investment.streamlit.app) - free tier available with no setup.

### Option 2: Run Locally

```bash
# Clone the repository
git clone https://github.com/yaboibean2/Wharton.git
cd Wharton

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys (see docs/API_SETUP.md for free key instructions)

# Run the app
streamlit run app.py
```

## API Keys Required

| API | Required? | Free Tier? | Purpose |
|-----|-----------|-----------|---------|
| OpenAI | Yes | Paid only | AI reasoning for all agents |
| Alpha Vantage | Recommended | Yes (5 req/min) | Fundamental data, economic indicators |
| Polygon.io | Recommended | Yes (5 req/min) | Real-time stock prices |
| Perplexity | Optional | Paid only | Real-time market intelligence |
| NewsAPI | Optional | Yes (100 req/day) | News sentiment analysis |

See [docs/API_SETUP.md](docs/API_SETUP.md) for step-by-step instructions on getting each key.

## Free vs. Pro Tier

| Feature | Free | Pro (BYOK) |
|---------|------|-----------|
| Stock Analysis | Full AI-powered | Full AI-powered |
| Analyses per day | 10 | Unlimited |
| Portfolio Building | Yes | Yes |
| Backtesting | Yes | Yes |
| Google Sheets Export | Yes | Yes |
| API Keys | Provided | Your own |

**Pro Tier**: Paste your own API keys in the sidebar to remove rate limits.

## Project Structure

```
wharton-investment-analysis/
├── app.py                    # Main Streamlit application
├── agents/                   # Multi-agent analysis system
│   ├── base_agent.py         # Abstract base class for all agents
│   ├── value_agent.py        # Valuation analysis
│   ├── growth_momentum_agent.py  # Growth & momentum
│   ├── macro_regime_agent.py # Macro economic analysis
│   ├── risk_agent.py         # Risk assessment
│   ├── sentiment_agent.py    # Sentiment analysis
│   ├── client_layer_agent.py # Client profile adjustments
│   └── learning_agent.py     # Performance learning
├── engine/                   # Core orchestration
│   ├── portfolio_orchestrator.py  # Agent coordination
│   ├── ai_portfolio_selector.py   # Portfolio selection
│   └── backtest.py           # Backtesting engine
├── data/                     # Data management
│   └── enhanced_data_provider.py  # Multi-API data sourcing
├── utils/                    # Utilities
│   ├── tier_manager.py       # Free/Pro tier management
│   ├── config_loader.py      # Configuration management
│   ├── qa_system.py          # QA & learning tracking
│   └── google_sheets_integration.py
├── config/                   # Configuration
│   ├── model.yaml            # Agent weights & parameters
│   ├── ips.yaml              # Investment Policy Statement
│   └── universe.yaml         # Stock universe definition
└── docs/                     # Documentation
```

## Configuration

### Agent Weights
Edit `config/model.yaml` to adjust how much each agent's analysis contributes:

```yaml
agent_weights:
  value: 1.2           # Valuation analysis weight
  growth_momentum: 1.25 # Growth & momentum weight
  macro_regime: 1.15    # Macro environment weight
  risk: 1.1            # Risk assessment weight
  sentiment: 1.25      # Market sentiment weight
```

### Investor Profile
Edit `config/ips.yaml` to set your investment constraints (risk tolerance, time horizon, position limits, etc.).

## Documentation

- [API Setup Guide](docs/API_SETUP.md) - How to get API keys
- [Deployment Guide](docs/DEPLOYMENT.md) - Deploy to Streamlit Cloud
- [System Architecture](docs/SYSTEM_FLOW_DIAGRAMS.md) - How the system works
- [Google Sheets Setup](docs/GOOGLE_SHEETS_SETUP.md) - Export integration
- [Changelog](docs/CHANGELOG.md) - Release history

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.
