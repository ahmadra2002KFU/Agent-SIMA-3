# Root Cause Analysis: Duplicate Plotting Issue

## Problem Statement
When sending a plotting query, the system responds with 2 identical plots instead of one.

## Root Cause Identified

**Location**: `server/code_executor.py`, lines 281-321, specifically the `_extract_results()` method

### The Issue

The `_extract_results()` method creates **duplicate entries** when the same Plotly figure object is assigned to multiple variables in the execution namespace.

### Code Analysis

```python
def _extract_results(self, namespace: Dict[str, Any]) -> Dict[str, Any]:
    """Extract important results from the execution namespace."""
    results = {}

    # FIRST LOOP (lines 286-291)
    # Look for common result variables
    result_vars = ['result', 'output', 'fig', 'figure', 'plot', 'chart', 'summary', 'analysis']

    for var_name in result_vars:
        if var_name in namespace:
            value = namespace[var_name]
            results[var_name] = self._serialize_value(value)

    # SECOND LOOP (lines 294-300) - THIS IS THE PROBLEM!
    # Look for any plotly figures
    for name, value in namespace.items():
        if hasattr(value, 'to_json') and hasattr(value, 'show'):  # Likely a plotly figure
            results[f'plotly_figure_{name}'] = {
                'type': 'plotly_figure',
                'json': value.to_json(),
                'html': value.to_html(include_plotlyjs='cdn')
            }
```

### The Problem Flow

1. **When LLM-generated code creates a figure and assigns it to multiple variables:**

```python
fig = px.bar(df, x='Category', y='Values')
result = fig  # Common pattern for returning the figure
```

2. **Both variables reference the SAME object in memory** (confirmed by testing)

3. **The second loop iterates through ALL namespace items** and finds BOTH variables:
   - Creates entry: `results['plotly_figure_fig']`
   - Creates entry: `results['plotly_figure_result']`

4. **Frontend renders ALL entries** that match the pattern (index.html:900):
```javascript
Object.keys(results).forEach(key => {
    if (key.includes('plotly_figure') && results[key].type === 'plotly_figure') {
        // Renders the plot
    }
});
```

5. **Result**: The same figure is rendered twice!

## Test Results Confirming the Issue

### Test 1: Single variable assignment
```python
fig = px.bar(df, x='Category', y='Values')
```
**Result**: 1 plotly figure entry ✓ CORRECT

### Test 2: Multiple variable assignment
```python
fig = px.bar(df, x='Category', y='Values')
result = fig
```
**Result**: 2 plotly figure entries ✗ DUPLICATE
- `plotly_figure_fig`
- `plotly_figure_result`

**Both contain IDENTICAL figure data!**

### Test 3: Common variable naming pattern
```python
figure = px.bar(df, x='Category', y='Values')
fig = figure
```
**Result**: 2 plotly figure entries ✗ DUPLICATE
- `plotly_figure_figure`
- `plotly_figure_fig`

### Test 4: Modified figure assignment
```python
fig = px.bar(df, x='Category', y='Values')
fig.update_layout(title='Test Chart')
result = fig
```
**Result**: 2 plotly figure entries ✗ DUPLICATE
- `plotly_figure_fig`
- `plotly_figure_result`

## Why This Happens in Practice

LLM-generated code often includes patterns like:
1. Assigning to `result` for explicit return value
2. Creating intermediate variables during figure construction
3. Using both `fig` and `figure` (both in the `result_vars` list)
4. Reassigning figures for modification chains

## Additional Findings

### First Loop (lines 286-291)
- Captures variables from predefined list: `['result', 'output', 'fig', 'figure', 'plot', 'chart', 'summary', 'analysis']`
- Serializes them using `_serialize_value()`
- These entries (e.g., `results['fig']`) are NOT rendered in frontend because they don't match `key.includes('plotly_figure')`

### Second Loop (lines 294-300)
- Iterates through **ALL namespace items**
- Finds every variable that has `to_json()` and `show()` methods (Plotly figures)
- Creates entries with `plotly_figure_` prefix
- These entries ARE rendered in frontend

### The Redundancy
The first loop is actually unnecessary for plotting purposes, since:
1. It captures the same figures that the second loop will capture
2. Its entries are not rendered in the frontend (no 'plotly_figure' in key name)
3. The second loop's entries are what actually get rendered

## Impact

- **User Experience**: Confusion when seeing duplicate identical plots
- **Performance**: Unnecessary data serialization and transmission
- **Memory**: Duplicate JSON/HTML storage for same figure

## Current Workarounds Being Used

Looking at the frontend code (index.html:895):
```javascript
vizContainer.innerHTML = '';  // Clear previous visualizations
```

This only clears plots from **previous queries**, not duplicates within the **same response**.

## Architecture Components Involved

1. **Backend**: `server/code_executor.py` - `_extract_results()` method
2. **Frontend**: `index.html` - `displayVisualizations()` function (lines 892-944)
3. **Communication**: Results passed via `/execute-code` endpoint and WebSocket

## Related Code Locations

- **Result extraction**: `server/code_executor.py:281-321`
- **Result serialization**: `server/code_executor.py:323-379`
- **Frontend rendering**: `index.html:892-944`
- **Frontend filter**: `index.html:900`

## Conclusion

The root cause is definitively identified: The `_extract_results()` method's second loop (lines 294-300) creates separate entries for each variable name that references the same Plotly figure object, causing duplicate plots to be rendered in the frontend.

The fix needs to ensure that each unique figure object (by Python object ID) is only captured once, regardless of how many variables reference it.