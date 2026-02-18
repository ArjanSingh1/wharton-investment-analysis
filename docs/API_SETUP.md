# API Setup Guide

This guide walks you through getting API keys for the Investment Analysis Platform.

## Required: OpenAI API Key

The system uses OpenAI for all AI-powered agent analysis.

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key and add to your `.env` file:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

**Cost**: ~$0.01-0.05 per stock analysis using `gpt-4o-mini` (default model).

## Recommended: Alpha Vantage (Free)

Provides fundamental data and economic indicators.

1. Go to [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
2. Fill in the form (no credit card needed)
3. Copy the key:
   ```
   ALPHA_VANTAGE_API_KEY=your-key-here
   ```

**Free tier**: 5 API calls per minute, 500 per day.

## Recommended: Polygon.io (Free)

Provides real-time stock prices and historical data.

1. Go to [polygon.io/dashboard/signup](https://polygon.io/dashboard/signup)
2. Sign up (no credit card required)
3. Copy your API key from the dashboard:
   ```
   POLYGON_API_KEY=your-key-here
   ```

**Free tier**: 5 API calls per minute, unlimited daily.

## Optional: Perplexity API

Provides real-time web search for current market conditions.

1. Go to [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
2. Sign up and add credits
3. Copy your API key:
   ```
   PERPLEXITY_API_KEY=pplx-your-key-here
   ```

**Cost**: Pay-per-use based on tokens.

## Optional: NewsAPI (Free)

Additional news sentiment analysis.

1. Go to [newsapi.org/register](https://newsapi.org/register)
2. Sign up for a free account
3. Copy your API key:
   ```
   NEWS_API_KEY=your-key-here
   ```

**Free tier**: 100 requests per day.

## Data Provider Fallback Hierarchy

The system intelligently falls back through data providers:

1. **Polygon.io** (primary) - Fast, reliable market data
2. **Perplexity AI** - Real-time web intelligence
3. **Alpha Vantage** - Fundamental data and economic indicators
4. **Yahoo Finance** - Backup price data (no API key needed)
5. **Synthetic Data** - Generated only when all providers are exhausted

The system works with just an OpenAI key, but adding more providers improves data quality. Yahoo Finance is always available as a backup without any API key.
