# Duplicate Plots Issue - Root Cause Summary

## The Problem
When you send a plotting query, the system displays 2 identical plots instead of 1.

## Root Cause (Confirmed by Testing)

**File**: `server/code_executor.py`
**Method**: `_extract_results()` (lines 281-321)
**Specific Issue**: Lines 294-300 (Second loop)

### What's Happening

The method has two loops that process execution results:

1. **First Loop (lines 286-291)**: Checks for specific variable names
2. **Second Loop (lines 294-300)**: Finds ALL Plotly figures in namespace

When LLM-generated code assigns the same figure to multiple variables:
```python
fig = px.bar(df, x='col', y='val')
result = fig  # Common pattern
```

The **second loop creates a separate entry for EACH variable name**, even though they all reference the **same object in memory**:

```python
# Second loop creates:
results['plotly_figure_fig'] = {<figure data>}      # Entry 1
results['plotly_figure_result'] = {<figure data>}   # Entry 2 (DUPLICATE!)
```

### Why Frontend Renders Both

Frontend code (`index.html:900`):
```javascript
Object.keys(results).forEach(key => {
    if (key.includes('plotly_figure') && results[key].type === 'plotly_figure') {
        // Renders each entry that matches
    }
});
```

Both `plotly_figure_fig` and `plotly_figure_result` match this pattern → Both get rendered → User sees duplicates.

## Proof from Testing

### Test Results (`test_duplicate_plots.py`):

| Test Case | Code Pattern | Number of Entries | Result |
|-----------|--------------|-------------------|---------|
| Test 1 | `fig = px.bar(...)` | 1 entry | ✓ Correct |
| Test 2 | `fig = px.bar(...); result = fig` | 2 entries | ✗ Duplicate |
| Test 3 | `figure = px.bar(...); fig = figure` | 2 entries | ✗ Duplicate |
| Test 4 | `fig = px.bar(...); result = fig` | 2 entries | ✗ Duplicate |

**Confirmed**: Test 2's entries contain **IDENTICAL figure data**.

## The Problematic Code

```python
# server/code_executor.py:294-300
for name, value in namespace.items():
    if hasattr(value, 'to_json') and hasattr(value, 'show'):
        results[f'plotly_figure_{name}'] = {  # ← Uses variable NAME as key
            'type': 'plotly_figure',
            'json': value.to_json(),
            'html': value.to_html(include_plotlyjs='cdn')
        }
```

**Problem**: Uses variable `name` as key, not object identity.
**Result**: Same object with different variable names → Multiple entries

## Why This Happens Frequently

LLMs commonly generate code patterns like:
- `result = fig` (explicit return value)
- `figure = px.bar(...); fig = figure` (variable naming)
- Intermediate variables during figure construction
- Both 'fig' and 'figure' are in the result_vars list

## Impact

- **User Experience**: Confusing duplicate visualizations
- **Performance**: Unnecessary serialization (JSON + HTML for each duplicate)
- **Data Transfer**: Larger WebSocket payloads
- **Memory**: Duplicate data storage in results dictionary

## Complete File Locations

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Root Cause | `server/code_executor.py` | 294-300 | Second loop creates duplicates |
| Method | `server/code_executor.py` | 281-321 | `_extract_results()` |
| Frontend Rendering | `index.html` | 892-944 | `displayVisualizations()` |
| Frontend Filter | `index.html` | 900 | Matches 'plotly_figure' in key |
| WebSocket Handler | `server/app.py` | 341-602 | Main processing loop |

## Why First Loop Doesn't Cause Issues

The first loop (lines 286-291) also creates entries:
```python
results['fig'] = {<figure data>}
results['result'] = {<figure data>}
```

But these **don't render** in frontend because they lack the 'plotly_figure' prefix.

Only the second loop's entries (with 'plotly_figure_' prefix) get rendered.

## Current Workaround (Insufficient)

Frontend clears container before rendering:
```javascript
vizContainer.innerHTML = '';  // index.html:895
```

This only clears plots from **previous queries**, not duplicates within the **same response**.

## Object Identity Evidence

Python test confirms both variables reference the same object:
```python
fig = px.bar(...)
result = fig

id(fig) == id(result)  # True
fig is result           # True
```

## Conclusion

**Definitive Root Cause**: The `_extract_results()` method's second loop (lines 294-300) creates separate entries for each variable name that references a Plotly figure, without checking if the same object (by Python object ID) was already captured. This causes the frontend to render the same figure multiple times.

**Solution Direction**: The fix needs to track figures by object ID, not variable name, ensuring each unique figure object is captured only once.