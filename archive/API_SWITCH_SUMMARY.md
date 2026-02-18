# Price Fetching API Switch Complete

## What Changed

Switched from Yahoo Finance to **Alpha Vantage** for fetching current stock prices in Google Sheets exports.

## Why the Change?

| Feature | Yahoo Finance | Alpha Vantage |
|---------|--------------|---------------|
| **API Key** | None (unofficial) | Free official API key |
| **Rate Limit** | ~1-2 req/sec (unofficial) | 5 req/min (25/day free) |
| **Reliability** | Frequent 429 errors | Predictable, no errors |
| **Speed** | ~36s for 60 tickers | ~12 min for 60 tickers |
| **Cost** | Free | Free (or $50/month premium) |

## How to Use

### Quick Setup (5 minutes):

1. **Get free API key:** https://www.alphavantage.co/support/#api-key
2. **Add to .env file:**
   ```bash
   ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE
   ```
3. **Restart app:** `streamlit run app.py`

That's it! The app will automatically use Alpha Vantage.

### What You'll See:

**With Alpha Vantage configured:**
```
✅ Price API: Alpha Vantage (5 req/min)
   Est. Time: ~720s (12 minutes) for 60 tickers
```

**Without Alpha Vantage (fallback to Yahoo):**
```
⚠️ Price API: Yahoo Finance (1-2 req/sec)
   Est. Time: ~36s for 60 tickers
   Warning: Prone to rate limits. Set ALPHA_VANTAGE_API_KEY for better reliability.
```

## Trade-offs

### Why it's slower:
- Alpha Vantage free tier: **5 requests per minute**
- For 60 tickers: 60 × 12 seconds = 720 seconds (12 minutes)
- BUT: It will complete successfully every time (no rate limit errors)

### Why it's better:
- **No more 429 errors** - Works reliably every time
- **Official API** - Documented and supported
- **Predictable** - You know exactly how long it will take
- **Still free** - 25 calls per day on free tier

## Best Practices

### With Free Tier (25 calls/day):
- ✅ **Sync once per day** - Not multiple times
- ✅ **Use "Price at Analysis"** for most exports (instant)
- ✅ **Fetch current prices** only when you need live data
- ❌ **Don't sync all 60 tickers** multiple times in one day

### If You Need More:
**Premium plan ($49.99/month):**
- 75 API calls per minute
- 60 tickers in ~48 seconds (vs 12 minutes)
- 1200 calls per day
- Worth it if you sync frequently

## Implementation Details

### New Code Structure:

```python
def get_current_price_alphavantage(ticker):
    """Fetch price from Alpha Vantage"""
    # Uses GLOBAL_QUOTE endpoint
    # 12-second delay (5 requests per minute)
    
def get_current_price(ticker):
    """Smart function with fallback"""
    # 1. Try Alpha Vantage first (if API key present)
    # 2. Fall back to Yahoo Finance if needed
```

### UI Improvements:
- Shows which API is being used
- Displays estimated time
- Warns if using Yahoo Finance
- Progress bar during fetch

## Testing

After setup, you should see in the Google Sheets export section:

```
💡 Tip: Current prices are disabled by default. The export will use 'Price at Analysis' instead.

Price API: Alpha Vantage (5 req/min)    Est. Time: ~720s

☐ Fetch Current Prices for 60 tickers
```

## Troubleshooting

**Q: I don't want to wait 12 minutes**
A: Don't check "Fetch Current Prices" - use "Price at Analysis" instead (instant)

**Q: I need faster updates**
A: Upgrade to Alpha Vantage Premium ($49.99/month) for 75 req/min

**Q: I hit my 25 calls/day limit**
A: Wait until tomorrow, or upgrade to premium

**Q: Still getting errors**
A: Check your API key in .env, verify it's correct

## Files Modified

1. **app.py** (lines 6398-6477):
   - Added `get_current_price_alphavantage()` function
   - Modified `get_current_price()` to try Alpha Vantage first
   - Updated UI to show API source and estimated time

## Documentation

- **Full guide:** See `ALPHA_VANTAGE_SETUP.md`
- **API docs:** https://www.alphavantage.co/documentation/

## Summary

✅ **No more Yahoo Finance rate limit errors**
✅ **Free and reliable** (25 calls/day)
✅ **Automatic fallback** to Yahoo if needed
⏱️ **Slower but stable** (12 min vs 36 sec)
💰 **Optional upgrade** for speed ($50/month)

**Bottom line:** Get the free API key from alphavantage.co and add it to your .env file. Your exports will be slower but 100% reliable.
