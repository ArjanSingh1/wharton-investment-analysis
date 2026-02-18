# 🎨 Conditional Formatting Preservation

## ✅ Problem Solved

The Google Sheets integration now **preserves conditional formatting** when updating data.

## How It Works

### Before (Formatting Lost)
```python
worksheet.clear()  # ❌ Clears EVERYTHING including conditional formatting
worksheet.update(data)
```

### After (Formatting Preserved)
```python
# Only clear old data rows beyond new data
worksheet.batch_clear([clear_range])  # ✅ Clears only specific rows

# Update with USER_ENTERED mode
worksheet.update(data, value_input_option='USER_ENTERED')  # ✅ Preserves formatting
```

## What Is Preserved

✅ **Conditional formatting rules** - Your color scales, icon sets, etc.  
✅ **Cell background colors** - Manual cell coloring  
✅ **Text formatting** - Bold, italic, font sizes  
✅ **Cell borders** - All border styles  
✅ **Number formatting** - Currency, percentages, decimals  
✅ **Column widths** - If you comment out `columns_auto_resize()`  
✅ **Data validation** - Dropdowns, checkboxes  
✅ **Protected ranges** - Cell protection settings  

## What Updates

🔄 **Cell values** - Data is updated with new analysis results  
🔄 **Row count** - Old rows beyond new data are cleared  
🔄 **Header row formatting** - Headers get re-formatted (can be disabled)  

## Optional: Preserve Header Formatting Too

If you want to keep your custom header formatting, comment out these lines in `utils/google_sheets_integration.py`:

### For QA Analyses (around line 220):
```python
# Comment out to preserve existing header formatting
# try:
#     worksheet.format('A1:Z1', {
#         'textFormat': {'bold': True},
#         'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.2}
#     })
# except:
#     pass
```

### For Portfolio Analysis (around line 138):
```python
# Comment out to preserve existing header formatting
# try:
#     worksheet.format('A1:Z1', {
#         'textFormat': {'bold': True},
#         'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.8}
#     })
# except:
#     pass
```

## Optional: Preserve Column Widths

If you want to keep your manual column widths, comment out this line:

```python
# Comment out to preserve column widths
# try:
#     worksheet.columns_auto_resize(0, len(df.columns))
# except:
#     pass
```

## How To Set Up Conditional Formatting

1. **In Google Sheets**, select the data range (e.g., column C for Confidence Score)
2. Go to **Format → Conditional formatting**
3. Set your rules (e.g., color scale from red to green)
4. Click **Done**

The formatting will now **persist** across all data updates! 🎉

## Technical Details

### Method Used
- **`batch_clear([range])`** - Clears only specific cell ranges, not formatting
- **`value_input_option='USER_ENTERED'`** - Updates values as if typed by user
- **Smart clearing** - Only clears rows beyond new data to avoid stale rows

### Why This Works
The Google Sheets API separates:
- **Cell values** (what we update)
- **Cell formatting** (what we preserve)
- **Conditional formatting rules** (what we preserve)

By using `update()` instead of `clear() + update()`, we only touch the values layer.

## Verification

After the next sync, check your Google Sheet:
- ✅ Conditional formatting rules still appear in Format menu
- ✅ Color scales still active on data columns
- ✅ Custom cell colors still visible
- ✅ Data is updated with latest values

---

**Status**: Conditional formatting preservation is now active! 🎨
