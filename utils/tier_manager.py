"""
Tier Manager for the Investment Analysis Platform.

Manages free vs pro tier detection and API key resolution.
- Free tier: Uses the system owner's API keys (from .env or Streamlit Secrets)
- Pro tier: Users provide their own API keys via the sidebar
"""

import os
import streamlit as st
from datetime import date
from typing import Optional


class TierManager:
    """Manages user tiers and API key resolution."""

    FREE_DAILY_LIMIT = 10  # Max analyses per day for free tier

    def __init__(self):
        self._init_session_state()

    def _init_session_state(self):
        """Initialize tier-related session state."""
        if 'user_tier' not in st.session_state:
            st.session_state.user_tier = 'free'
        if 'user_api_keys' not in st.session_state:
            st.session_state.user_api_keys = {}
        if 'daily_usage' not in st.session_state:
            st.session_state.daily_usage = {'date': str(date.today()), 'count': 0}

    @property
    def tier(self) -> str:
        return st.session_state.user_tier

    @property
    def is_pro(self) -> bool:
        return st.session_state.user_tier == 'pro'

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key with precedence: user-provided > streamlit secrets > env."""
        # Pro tier: use user-provided keys
        user_keys = st.session_state.get('user_api_keys', {})
        if user_keys.get(key_name):
            return user_keys[key_name]

        # Free tier: use system keys from Streamlit Secrets or .env
        try:
            return st.secrets[key_name]
        except (FileNotFoundError, KeyError, AttributeError):
            pass

        return os.getenv(key_name)

    def set_user_keys(self, keys: dict):
        """Set user-provided API keys and switch to pro tier."""
        st.session_state.user_api_keys = {k: v for k, v in keys.items() if v}
        if keys.get('OPENAI_API_KEY'):
            st.session_state.user_tier = 'pro'

    def clear_user_keys(self):
        """Clear user-provided keys and revert to free tier."""
        st.session_state.user_api_keys = {}
        st.session_state.user_tier = 'free'

    def check_rate_limit(self) -> bool:
        """Check if free tier user is within daily rate limit."""
        if self.is_pro:
            return True

        usage = st.session_state.daily_usage
        today = str(date.today())

        # Reset counter on new day
        if usage['date'] != today:
            st.session_state.daily_usage = {'date': today, 'count': 0}
            return True

        return usage['count'] < self.FREE_DAILY_LIMIT

    def increment_usage(self):
        """Increment daily usage counter."""
        today = str(date.today())
        usage = st.session_state.daily_usage
        if usage['date'] != today:
            st.session_state.daily_usage = {'date': today, 'count': 1}
        else:
            usage['count'] += 1

    def remaining_analyses(self) -> int:
        """Get remaining free tier analyses for today."""
        if self.is_pro:
            return -1  # Unlimited

        usage = st.session_state.daily_usage
        today = str(date.today())
        if usage['date'] != today:
            return self.FREE_DAILY_LIMIT
        return max(0, self.FREE_DAILY_LIMIT - usage['count'])

    def render_sidebar_ui(self):
        """Render the tier management UI in the Streamlit sidebar."""
        st.sidebar.markdown("---")
        st.sidebar.subheader("API Configuration")

        if self.is_pro:
            st.sidebar.success(f"Pro Tier (Your API Keys)")
            remaining = "Unlimited"
        else:
            remaining = self.remaining_analyses()
            st.sidebar.info(f"Free Tier ({remaining} analyses remaining today)")

        with st.sidebar.expander("Use Your Own API Keys (Pro)", expanded=False):
            st.markdown(
                "Provide your own API keys for unlimited access. "
                "Keys are stored in your session only and never saved."
            )

            openai_key = st.text_input(
                "OpenAI API Key",
                value=st.session_state.get('user_api_keys', {}).get('OPENAI_API_KEY', ''),
                type="password",
                help="Required for Pro tier. Get from: https://platform.openai.com/api-keys"
            )
            av_key = st.text_input(
                "Alpha Vantage API Key (optional)",
                value=st.session_state.get('user_api_keys', {}).get('ALPHA_VANTAGE_API_KEY', ''),
                type="password",
                help="Get free key from: https://www.alphavantage.co/support/#api-key"
            )
            polygon_key = st.text_input(
                "Polygon.io API Key (optional)",
                value=st.session_state.get('user_api_keys', {}).get('POLYGON_API_KEY', ''),
                type="password",
                help="Get free key from: https://polygon.io/dashboard/signup"
            )
            perplexity_key = st.text_input(
                "Perplexity API Key (optional)",
                value=st.session_state.get('user_api_keys', {}).get('PERPLEXITY_API_KEY', ''),
                type="password",
                help="Get from: https://www.perplexity.ai/settings/api"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Activate Pro", use_container_width=True):
                    if openai_key:
                        self.set_user_keys({
                            'OPENAI_API_KEY': openai_key,
                            'ALPHA_VANTAGE_API_KEY': av_key,
                            'POLYGON_API_KEY': polygon_key,
                            'PERPLEXITY_API_KEY': perplexity_key,
                        })
                        st.session_state.initialized = False
                        st.rerun()
                    else:
                        st.error("OpenAI API Key is required for Pro tier.")

            with col2:
                if self.is_pro and st.button("Revert to Free", use_container_width=True):
                    self.clear_user_keys()
                    st.session_state.initialized = False
                    st.rerun()
