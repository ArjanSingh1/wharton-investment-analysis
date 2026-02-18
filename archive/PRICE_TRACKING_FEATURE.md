# Price Tracking & Biggest Changes Feature

## Overview
Added comprehensive price tracking and a "Biggest Changes" section to monitor stock performance and score variations over time.

---

## 🆕 New Features

### 1. **Biggest Score Changes Section** (QA Learning Center)

**Location:** QA & Learning Center page, above "Recent Analysis Activity"

**Features:**
- Shows top 5 stocks with largest score changes between analyses
- Displays both previous and current scores
- Shows recommendation changes if any
- **Real-time price tracking** with percentage change since analysis
- Sorted by absolute score change (largest first)

**Display Format:**
```
🔥 Biggest Score Changes
Stocks with the largest score differences between their latest and previous analyses

AAPL    📈 +12.5 pts (65.0 → 77.5)    🟢 BUY (was HOLD) | Price: $180.50 (🟢 +5.2% since analysis)
TSLA    📉 -8.3 pts (82.1 → 73.8)     🟡 HOLD (was BUY) | Price: $245.00 (🔴 -2.1% since analysis)
AMZN    📈 +6.7 pts (70.0 → 76.7)     🟢 BUY | Price: $135.20 (🟢 +1.8% since analysis)
```

**Visual Indicators:**
- 📈 Score increased
- 📉 Score decreased
- ➡️ Score unchanged
- 🟢 Green price = up since analysis
- 🔴 Red price = down since analysis
- 🟢 Buy/Strong Buy recommendation
- 🟡 Hold recommendation
- 🔴 Sell/Strong Sell recommendation

**Requirements:**
- Only shows stocks with **2+ analyses**
- Compares latest analysis to previous one
- Updates automatically on page refresh

---

### 2. **Real-Time Price Tracking** (Google Sheets)

**New Columns Added:**
1. **Current Price** - Latest market price (fetched in real-time)
2. **Price Change $** - Dollar change from analysis price
3. **Price Change %** - Percentage change from analysis price

**Example:**
```
Ticker | Price at Analysis | Current Price | Price Change $ | Price Change %
AAPL   | $172.50          | $180.50       | $8.00         | +4.64%
TSLA   | $250.00          | $245.00       | -$5.00        | -2.00%
GOOGL  | $135.00          | $140.25       | $5.25         | +3.89%
```

**Update Behavior:**
- Current prices fetched **every time** Google Sheets syncs
- Uses yfinance API for real-time data
- Falls back to 0 if price unavailable
- Calculations automatic based on price at analysis

**Data Sources:**
- `currentPrice` from yfinance (primary)
- `regularMarketPrice` from yfinance (fallback)
- Returns 0 if both unavailable

---

## 🎯 Use Cases

### For Portfolio Monitoring
1. **Track Performance:** See which analyses predicted winning stocks
2. **Validate Scores:** High scores should correlate with price increases
3. **Review Timing:** Identify when recommendations worked best
4. **Re-analyze Trigger:** Large score drops signal need for new analysis

### For QA & Learning
1. **Model Accuracy:** Compare score changes to actual price movement
2. **Calibration:** Check if confidence scores match outcomes
3. **Agent Performance:** See which agent scores correlate with success
4. **Timing Analysis:** Understand optimal re-analysis frequency

### For Client Reporting
1. **Performance Dashboard:** Show real results vs predictions
2. **Transparency:** Full price history from analysis to present
3. **Track Record:** Historical performance of recommendations
4. **ROI Calculation:** Easy to calculate returns from entry prices

---

## 📊 Technical Implementation

### Price Fetching Function
```python
def get_current_price(ticker):
    """Fetch current price for a ticker."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        current_price = stock.info.get('currentPrice') or 
                       stock.info.get('regularMarketPrice', 0)
        return current_price if current_price else 0
    except:
        return 0
```

### Change Calculation Logic
```python
# For each stock with multiple analyses:
score_change = latest.confidence_score - previous.confidence_score
rec_changed = latest.recommendation.value != previous.recommendation.value

if price_at_analysis > 0 and current_price > 0:
    price_change_pct = ((current_price - price_at_analysis) / 
                        price_at_analysis) * 100
```

### Google Sheets Integration
- Fetches current price once per ticker (efficient)
- Updates all analyses for that ticker
- Calculates price changes automatically
- Maintains historical analysis prices

---

## 🔄 Update Frequency

### QA Learning Center Display
- **Manual refresh:** Click "🔄 Refresh QA Data" button
- **Automatic:** On page navigation
- **Price data:** Fetched from yfinance on each refresh

### Google Sheets Sync
- **Manual:** Click "Sync to Google Sheets" button
- **Automatic:** After new analysis (if enabled)
- **Price data:** Fetched fresh on every sync
- **Historical:** Previous prices preserved

---

## 📈 Example Insights

### Biggest Changes Section Example
```
🔥 Biggest Score Changes

NVDA    📈 +15.2 pts (72.5 → 87.7)    🟢 STRONG BUY (was BUY)
        Price: $495.00 (🟢 +12.5% since analysis 14 days ago)

META    📉 -11.8 pts (78.3 → 66.5)    🟡 HOLD (was BUY)  
        Price: $320.50 (🔴 -3.2% since analysis 7 days ago)

AAPL    📈 +9.3 pts (68.2 → 77.5)     🟢 BUY
        Price: $180.50 (🟢 +5.2% since analysis 21 days ago)
```

**Interpretation:**
- NVDA: Score up 15pts, price up 12.5% ✅ Good prediction
- META: Score down 12pts, price down 3.2% ✅ Caught the downturn
- AAPL: Score up 9pts, price up 5.2% ✅ Solid upward trend

### Google Sheets Example
```
Ticker | Recommendation | Score | Price @ Analysis | Current Price | Change $ | Change %
NVDA   | STRONG BUY     | 87.7  | $440.00         | $495.00      | +$55.00  | +12.50%
META   | HOLD           | 66.5  | $331.00         | $320.50      | -$10.50  | -3.17%
AAPL   | BUY            | 77.5  | $172.00         | $180.50      | +$8.50   | +4.94%
```

---

## 🎯 Benefits

### For Users
✅ **See Real Results** - Track actual performance vs predictions
✅ **Quick Review** - Top changes highlighted automatically
✅ **Price Context** - Know if stocks moved as expected
✅ **Re-analysis Trigger** - Large changes signal review needed
✅ **Portfolio Validation** - Verify model accuracy over time

### For Analysis
✅ **Model Calibration** - Validate scoring system
✅ **Timing Optimization** - Learn when to re-analyze
✅ **Agent Performance** - Which agents predict best
✅ **Risk Management** - Catch downturns early
✅ **Confidence Validation** - High scores = good returns?

### For Reporting
✅ **Client Transparency** - Show full price journey
✅ **Performance Metrics** - Easy ROI calculations
✅ **Historical Record** - Complete audit trail
✅ **Visual Proof** - Charts and comparisons
✅ **Export Ready** - All data in Google Sheets

---

## 📝 Data Points Tracked

### Per Analysis Record
1. **Ticker** - Stock symbol
2. **Analysis Date** - When analysis was performed
3. **Score at Analysis** - Confidence score assigned
4. **Recommendation at Analysis** - Buy/Sell/Hold decision
5. **Price at Analysis** - Stock price when analyzed
6. **Current Price** - Latest market price (updated each sync)
7. **Price Change ($)** - Dollar difference
8. **Price Change (%)** - Percentage return
9. **Days Since Analysis** - Time elapsed

### Calculated Metrics
1. **Score Change** - Difference between latest and previous scores
2. **Recommendation Change** - Did rec change? (Boolean)
3. **Absolute Score Change** - Used for ranking biggest changes
4. **Price Performance** - Correlation with score changes
5. **Time Decay** - Days since previous analysis

---

## 🔧 Configuration

### No Setup Required
- Features work automatically with existing data
- Uses yfinance (already installed)
- Google Sheets columns added automatically
- No additional API keys needed

### Optional Customization
- **Top N Changes:** Currently shows top 5, can be adjusted
- **Min Score Change:** Could filter by minimum change threshold
- **Time Window:** Could limit to changes in last X days
- **Price Source:** Could use other APIs instead of yfinance

---

## ⚠️ Limitations & Notes

### Price Data
- Requires active internet connection
- Market hours: Real-time during trading
- After hours: Last closing price
- Holidays: Previous trading day price
- Delisted stocks: Returns 0

### Score Changes
- Requires minimum 2 analyses per stock
- Compares latest to immediate previous (not oldest)
- New analyses automatically update rankings
- Historical analyses preserved

### Google Sheets
- Current price fetched fresh on each sync
- May take 10-30 seconds for large datasets
- Rate limited by yfinance API
- Price at analysis never changes (historical)

---

## 🚀 Future Enhancements

Potential additions:
1. **Historical Price Charts** - Visual price movement since analysis
2. **Performance Attribution** - Which agent predicted best
3. **Win Rate Statistics** - % of analyses that "won"
4. **Time-Based Analysis** - Optimal holding period identification
5. **Alerts** - Notify on large score/price divergence
6. **Correlation Metrics** - Score change vs price change correlation
7. **Benchmark Comparison** - vs S&P 500 performance
8. **Export Reports** - Automated performance PDF reports

---

## Files Modified

1. **`app.py`** - Lines ~4520-4580 (Biggest Changes section)
2. **`app.py`** - Lines ~6430-6470 (Price tracking in Google Sheets)

## Testing

To test the features:
1. Analyze a stock multiple times (different dates)
2. Check QA Learning Center for "Biggest Changes" section
3. Sync to Google Sheets
4. Verify "Current Price", "Price Change $", "Price Change %" columns
5. Refresh page to see updated prices

---

**Result:** Complete visibility into stock performance tracking with real-time price updates and automatic change detection! 🎯
