# Execution Flow: From Query to Duplicate Plots

## Complete Flow Diagram

```
USER QUERY: "Create a bar chart"
           |
           v
    ┌──────────────────┐
    │  WebSocket       │
    │  app.py:341-602  │
    └──────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  LLM generates code (Layer 1)        │
    │  lm_studio_client.py                 │
    └──────────────────────────────────────┘
           |
           v
    Generated Code Example:
    ┌─────────────────────────────────────┐
    │ fig = px.bar(df, x='col', y='val')  │
    │ result = fig  # ← DUPLICATE SOURCE  │
    └─────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  Code Execution (Layer 2)            │
    │  app.py:411-416                      │
    │  code_executor.execute_code()        │
    └──────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  exec() runs code                    │
    │  code_executor.py:107                │
    └──────────────────────────────────────┘
           |
           v
    Namespace after execution:
    ┌─────────────────────────────────────┐
    │ namespace = {                        │
    │   'df': <DataFrame>,                 │
    │   'px': <module plotly.express>,     │
    │   'fig': <Figure object 0x7f8a4b2>  │ ← Same object
    │   'result': <Figure object 0x7f8a4b2>│ ← Same object!
    │   ...                                │
    │ }                                    │
    └─────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  _extract_results()                  │
    │  code_executor.py:281-321            │
    └──────────────────────────────────────┘
           |
           |--- First Loop (lines 286-291) ----|
           |    Checks: ['result', 'output',    |
           |             'fig', 'figure', ...]  |
           |    Found: 'fig', 'result'          |
           v                                    |
    results['fig'] = {                          |
      'type': 'plotly_figure',                  |
      'json': '<figure JSON>'                   |
    }                                           |
    results['result'] = {                       |
      'type': 'plotly_figure',                  |
      'json': '<figure JSON>'                   |
    }                                           |
           |                                    |
           |--- Second Loop (lines 294-300) ---|
           |    Iterates: ALL namespace items   |
           |    Finds figures with to_json()    |
           v                                    |
    results['plotly_figure_fig'] = {            |
      'type': 'plotly_figure',                  |
      'json': '<figure JSON>',                  | ← DUPLICATE!
      'html': '<figure HTML>'                   |
    }                                           |
    results['plotly_figure_result'] = {         |
      'type': 'plotly_figure',                  |
      'json': '<figure JSON>',                  | ← DUPLICATE!
      'html': '<figure HTML>'                   |
    }                                           |
           |                                    |
           |<-----------------------------------|
           v
    ┌──────────────────────────────────────┐
    │  Return results to app.py            │
    └──────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  Send to frontend via WebSocket      │
    │  app.py:585-588                      │
    └──────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  handleFinalResponse()               │
    │  index.html:873-890                  │
    └──────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  POST /execute-code                  │
    │  (Code executed AGAIN)               │
    │  index.html:876-881                  │
    └──────────────────────────────────────┘
           |
           v
    ┌──────────────────────────────────────┐
    │  displayVisualizations()             │
    │  index.html:892-944                  │
    └──────────────────────────────────────┘
           |
           v
    Loop through results (line 899):
    ┌─────────────────────────────────────┐
    │ Object.keys(results).forEach(key => │
    │   if (key.includes('plotly_figure')) │
    │     RENDER PLOT                      │
    │ )                                    │
    └─────────────────────────────────────┘
           |
           |--- First Iteration ---|
           v                       |
    key = 'plotly_figure_fig'      |
    ✓ includes 'plotly_figure'     |
    ✓ type === 'plotly_figure'     |
    → RENDER PLOT #1               |
           |                       |
           |--- Second Iteration --|
           v
    key = 'plotly_figure_result'
    ✓ includes 'plotly_figure'
    ✓ type === 'plotly_figure'
    → RENDER PLOT #2 (DUPLICATE!)
           |
           v
    ┌──────────────────────────────────────┐
    │  USER SEES 2 IDENTICAL PLOTS         │
    └──────────────────────────────────────┘
```

## Key Observations

### 1. Why First Loop Entries Don't Render
- `results['fig']` doesn't match `key.includes('plotly_figure')`
- `results['result']` doesn't match `key.includes('plotly_figure')`
- Only entries with 'plotly_figure_' prefix render

### 2. Why Second Loop Creates Duplicates
- Iterates through **ALL** namespace items
- Doesn't check if object was already added
- Creates separate entry for each **variable name**, not each unique **object**

### 3. Memory Reference Proof
```python
fig = px.bar(...)
result = fig

# In Python:
id(fig) == id(result)  # True!
fig is result  # True!
```
Both variables point to the **same object in memory**, but `_extract_results()` treats them as separate figures.

## The Critical Code Section

**Location**: `server/code_executor.py:294-300`

```python
# Look for any plotly figures
for name, value in namespace.items():
    if hasattr(value, 'to_json') and hasattr(value, 'show'):
        results[f'plotly_figure_{name}'] = {  # ← Creates entry per NAME
            'type': 'plotly_figure',
            'json': value.to_json(),  # ← Same JSON for same object
            'html': value.to_html(include_plotlyjs='cdn')
        }
```

**Problem**: Loop uses `name` (variable name) as key, not object ID.

## Object Identity vs Variable Identity

### Current Behavior (WRONG):
- Tracks by **variable name**: `'fig'`, `'result'`, `'figure'`
- Same object → Multiple entries

### Correct Behavior (NEEDED):
- Track by **object ID**: `id(fig)`, `id(result)` → Same ID
- Same object → Single entry

## Alternative Scenarios That Trigger Duplicates

### Scenario 1: Intermediate Variables
```python
temp = px.bar(df, x='x', y='y')
fig = temp
result = fig
```
**Result**: 3 entries! (`plotly_figure_temp`, `plotly_figure_fig`, `plotly_figure_result`)

### Scenario 2: Common Variable Names
```python
figure = px.bar(df, x='x', y='y')
fig = figure  # Both 'figure' and 'fig' in result_vars list!
```
**Result**: 2 entries (`plotly_figure_figure`, `plotly_figure_fig`)

### Scenario 3: Conditional Assignment
```python
if condition:
    plot = px.bar(df, x='x', y='y')
    fig = plot
```
**Result**: 2 entries (`plotly_figure_plot`, `plotly_figure_fig`)

## Summary

The duplicate plot issue occurs because:

1. **Backend** (`_extract_results`): Creates multiple entries for the same figure object when it's assigned to multiple variables
2. **Frontend** (`displayVisualizations`): Renders all entries that match the pattern `key.includes('plotly_figure')`
3. **Result**: Same figure rendered multiple times

The fix must ensure each unique figure object is captured only once, regardless of how many variables reference it.