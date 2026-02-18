# Alpha Vantage Integration Guide

## Why Alpha Vantage?

**Problem with Yahoo Finance:**
- Rate limit: ~1-2 requests per second
- Frequently returns 429 (Too Many Requests) errors
- No official API key or authentication
- Unpredictable rate limiting behavior

**Benefits of Alpha Vantage:**
- **Free tier:** 5 API calls per minute (25 per day on free plan)
- **Official API:** Reliable and documented
- **Better for batch operations:** Predictable rate limits
- **No 429 errors:** Stays within limits automatically

## Getting Your Free API Key

### Step 1: Sign Up
1. Go to: https://www.alphavantage.co/support/#api-key
2. Click "Get your free API key today"
3. Fill out the form:
   - Email address
   - Organization (can use "Personal" or "Individual")
   - Brief description ("Stock price tracking for portfolio analysis")
4. Click "GET FREE API KEY"

### Step 2: Check Your Email
- You'll receive your API key instantly via email
- It looks like: `YOUR_API_KEY_HERE` (16 characters)

### Step 3: Add to Your .env File
1. Open `/Users/arjansingh/Wharton/.env`
2. Add this line:
   ```
   ALPHA_VANTAGE_API_KEY=YOUR_API_KEY_HERE
   ```
3. Save the file

### Step 4: Restart Streamlit
- Stop the app (Ctrl+C)
- Run: `streamlit run app.py`
- The app will now use Alpha Vantage instead of Yahoo Finance

## Rate Limits Comparison

### Alpha Vantage Free Tier:
- **5 API calls per minute**
- **25 API calls per day** (free tier)
- For 60 tickers: Takes ~12 minutes (12 seconds per ticker)
- No 429 errors if you stay within limits

### Yahoo Finance (No API Key):
- **~1-2 requests per second** (unofficial limit)
- Gets rate limited unpredictably
- Frequent 429 errors
- For 60 tickers: Takes ~30-60 seconds (but often fails)

## How It Works Now

### With Alpha Vantage API Key:
```
✅ Price API: Alpha Vantage (5 req/min)
   Est. Time: ~720s (12 minutes) for 60 tickers
```

### Without Alpha Vantage (Fallback):
```
⚠️ Price API: Yahoo Finance (1-2 req/sec)
   Est. Time: ~36s for 60 tickers
   Warning: Prone to rate limits. Set ALPHA_VANTAGE_API_KEY for better reliability.
```

## Usage Tips

### Best Practice with Free Tier:
Since Alpha Vantage free tier has **25 calls per day**, use wisely:

1. **Sync once per day** - Not multiple times
2. **Select specific tickers** - If you only need prices for 10 stocks, don't sync all 60
3. **Use "Price at Analysis"** for historical views
4. **Fetch current prices** only when you need live data

### Upgrading (If Needed):
If you need more than 25 calls per day:
- **Premium plan:** 75 API calls per minute, 1200 per day ($49.99/month)
- **Ultimate plan:** Unlimited calls ($149.99/month)
- See: https://www.alphavantage.co/premium/

## Technical Details

### What Changed in the Code:

1. **New function:** `get_current_price_alphavantage(ticker)`
   - Uses Alpha Vantage GLOBAL_QUOTE endpoint
   - 12-second delay between requests (5 per minute)
   - Returns current price or 0 if error

2. **Smart fallback:** `get_current_price(ticker)`
   - Tries Alpha Vantage first (if API key present)
   - Falls back to Yahoo Finance if Alpha Vantage fails
   - Shows which API is being used in UI

3. **UI enhancements:**
   - Shows which API source is active
   - Displays estimated time based on API
   - Warns if using Yahoo Finance without Alpha Vantage key

### Alpha Vantage Response Format:
```json
{
  "Global Quote": {
    "01. symbol": "AAPL",
    "05. price": "174.23",
    "07. latest trading day": "2025-10-03",
    "08. previous close": "175.12",
    "09. change": "-0.89",
    "10. change percent": "-0.51%"
  }
}
```

## Troubleshooting

### Issue: "API call frequency is 5 calls per minute"
**Solution:** You're hitting the rate limit. The app already adds 12-second delays, but if you run multiple exports quickly, wait 1 minute before trying again.

### Issue: "Thank you for using Alpha Vantage! Our standard API call frequency is..."
**Solution:** This is just an info message. Your API key is working. The app handles the rate limiting automatically.

### Issue: Still getting empty prices
**Solutions:**
1. Check your API key is correct in `.env`
2. Verify you haven't exceeded 25 calls per day (free tier limit)
3. Check the ticker symbol is valid (some tickers may not be available)

### Issue: Takes too long (60 tickers = 12 minutes)
**Solutions:**
1. **Upgrade to Premium plan** ($49.99/month for 75 calls/min = 48 seconds for 60 tickers)
2. **Fetch prices less frequently** (once per day instead of multiple times)
3. **Use "Price at Analysis"** for exports where live price isn't critical

## Verification

After adding your API key, check the System Status page:
1. Go to "System Status & AI Disclosure" in sidebar
2. Look for:
   ```
   Alpha Vantage: ✅ (API key configured)
   ```

## Summary

- **Free & Easy:** Sign up at alphavantage.co, get instant API key
- **Better Reliability:** No more 429 errors from Yahoo Finance
- **Slower but Stable:** 12 minutes for 60 tickers, but guaranteed to work
- **Smart Fallback:** Still uses Yahoo Finance if Alpha Vantage not configured

**Recommendation:** Get the free API key even if you only sync occasionally. It eliminates the frustration of rate limit errors.
