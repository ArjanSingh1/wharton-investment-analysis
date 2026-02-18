# Quick Start: Alpha Vantage Setup

## 1️⃣ Get Your Free API Key (2 minutes)
👉 https://www.alphavantage.co/support/#api-key

Fill out:
- Email: your_email@example.com
- Organization: Personal
- Purpose: Stock price tracking

Click "GET FREE API KEY" → Check your email

## 2️⃣ Add to .env File (1 minute)
```bash
# Open your .env file
nano /Users/arjansingh/Wharton/.env

# Add this line:
ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE

# Save and exit (Ctrl+X, Y, Enter)
```

## 3️⃣ Restart App
```bash
streamlit run app.py
```

## ✅ Verify It's Working
Look for this in Google Sheets export:
```
✅ Price API: Alpha Vantage (5 req/min)
```

Instead of:
```
⚠️ Price API: Yahoo Finance (1-2 req/sec)
```

---

## That's It!
**No more 429 errors** 🎉

Trade-off: Slower (12 min for 60 tickers) but **100% reliable**
