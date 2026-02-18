# ✅ Perplexity API Model Update

## Issue Fixed
**Error**: `Invalid model 'llama-3.1-sonar-large-128k-online'`

Perplexity AI updated their model naming convention. The old model names are no longer valid.

## Changes Made

### 1. `engine/ai_portfolio_selector.py`
**Lines 336 & 359**: Updated model name
```python
# Before:
model="llama-3.1-sonar-large-128k-online"

# After:
model="sonar-pro"
```

### 2. `.env` Configuration
**Line 107**: Updated default model
```bash
# Before:
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online

# After:
PERPLEXITY_MODEL=sonar-pro
```

## Current Perplexity Models (as of October 2025)

### Available Models:

1. **`sonar-pro`** (Recommended for complex tasks)
   - High quality responses
   - Real-time web search
   - Best for analysis and reasoning
   - **USE THIS**: Portfolio selection, analysis

2. **`sonar`** (Standard model)
   - Fast responses
   - Real-time web search
   - Good balance of speed/quality
   - **USE THIS**: Quick queries, metrics extraction

3. **`sonar-reasoning`** (Advanced reasoning)
   - Complex problem-solving
   - Deep analysis
   - Slower but more thorough

## Where Each Model is Used

### Current Usage in Codebase:

| File | Model | Purpose |
|------|-------|---------|
| `engine/ai_portfolio_selector.py` | `sonar-pro` | Portfolio ticker selection |
| `agents/sentiment_agent.py` | `sonar-pro` | Article URL extraction |
| `data/enhanced_data_provider.py` | `sonar` | Quick metrics extraction |
| `data/enhanced_data_provider.py` | `sonar-pro` | Comprehensive analysis |
| `utils/comprehensive_verification.py` | `sonar` | Verification queries |

## Model Selection Guide

### Use `sonar-pro` when:
✅ Portfolio analysis and selection  
✅ Complex reasoning required  
✅ High-quality responses needed  
✅ Multiple factors to consider  

### Use `sonar` when:
✅ Quick metric extraction  
✅ Simple queries  
✅ Fast responses needed  
✅ Cost optimization important  

### Use `sonar-reasoning` when:
✅ Very complex problems  
✅ Multi-step reasoning  
✅ Critical decisions  
✅ Time not a constraint  

## Verification

After update, portfolio generation should work correctly:
✅ AI ticker selection via Perplexity  
✅ Real-time market analysis  
✅ No 400 Bad Request errors  
✅ Proper model usage  

## Alternative Configuration

If you want to use faster/cheaper model, update `.env`:

```bash
# For faster responses (less thorough):
PERPLEXITY_MODEL=sonar

# For complex reasoning (slower):
PERPLEXITY_MODEL=sonar-reasoning

# For balanced performance (recommended):
PERPLEXITY_MODEL=sonar-pro
```

---

**Status**: Perplexity model names updated to current API standards! ✅
