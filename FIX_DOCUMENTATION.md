# Duplicate Plots Issue - Fix Documentation

## Problem Summary
When sending a plotting query, the system displayed 2 identical plots instead of 1.

## Root Cause
**File**: `server/code_executor.py`
**Method**: `_extract_results()` (lines 293-318)

The second loop in this method created separate entries for each variable name that referenced a Plotly figure, even when multiple variables pointed to the same object in memory.

### Before (Buggy Code)
```python
# Look for any plotly figures
for name, value in namespace.items():
    if hasattr(value, 'to_json') and hasattr(value, 'show'):
        results[f'plotly_figure_{name}'] = {  # ← Creates entry per variable NAME
            'type': 'plotly_figure',
            'json': value.to_json(),
            'html': value.to_html(include_plotlyjs='cdn')
        }
```

**Problem**: When code like this ran:
```python
fig = px.bar(df, x='col', y='val')
result = fig  # Same object, different variable
```

It created:
- `results['plotly_figure_fig']` → Figure data
- `results['plotly_figure_result']` → **Same figure data (DUPLICATE!)**

Frontend rendered both → User saw 2 identical plots.

## The Fix

### Implementation Strategy
1. **Track figures by object ID** instead of variable name
2. **Prioritize meaningful names** ('fig', 'figure', 'plot', etc.) when multiple variables reference the same figure
3. **Minimal code change** to reduce risk of regressions

### After (Fixed Code)
```python
# Look for any plotly figures (avoid duplicates by tracking object IDs)
# Prefer variable names in priority order: fig, figure, plot, chart, result
figure_priority = ['fig', 'figure', 'plot', 'chart', 'result', 'output']
seen_figures = {}  # Maps object_id -> (priority_score, name, value)

for name, value in namespace.items():
    if hasattr(value, 'to_json') and hasattr(value, 'show'):
        fig_id = id(value)

        # Calculate priority score (lower is better)
        if name in figure_priority:
            priority = figure_priority.index(name)
        else:
            priority = len(figure_priority)  # Lowest priority for unlisted names

        # Keep the figure with the best (lowest) priority score
        if fig_id not in seen_figures or priority < seen_figures[fig_id][0]:
            seen_figures[fig_id] = (priority, name, value)

# Serialize the unique figures with their best names
for fig_id, (priority, name, value) in seen_figures.items():
    results[f'plotly_figure_{name}'] = {
        'type': 'plotly_figure',
        'json': value.to_json(),
        'html': value.to_html(include_plotlyjs='cdn')
    }
```

## How It Works

### 1. Object ID Tracking
- Uses Python's `id(value)` to uniquely identify each figure object
- Same object = Same ID, regardless of how many variables reference it

### 2. Priority System
When the same figure is assigned to multiple variables:
```python
result = px.bar(...)  # Priority: 4 (in priority list)
fig = result          # Priority: 0 (highest in priority list)
```
The system chooses `fig` because it has a higher priority (lower index).

**Priority Order**:
1. `fig` (index 0 - highest priority)
2. `figure` (index 1)
3. `plot` (index 2)
4. `chart` (index 3)
5. `result` (index 4)
6. `output` (index 5)
7. Any other name (lowest priority)

### 3. Single Entry Per Object
Each unique figure object (identified by `id()`) gets exactly one entry in the results dictionary.

## Test Results

### Before Fix
| Test Case | Entries Created | Status |
|-----------|----------------|---------|
| `fig = px.bar(...)` | 1 | OK |
| `fig = px.bar(...); result = fig` | **2** | ❌ Duplicate |
| `figure = px.bar(...); fig = figure` | **2** | ❌ Duplicate |

### After Fix
| Test Case | Entries Created | Status |
|-----------|----------------|---------|
| `fig = px.bar(...)` | 1 | ✅ Correct |
| `fig = px.bar(...); result = fig` | **1** | ✅ Fixed |
| `figure = px.bar(...); fig = figure` | **1** | ✅ Fixed |

## Comprehensive Test Coverage

Ran 8 comprehensive tests covering:

1. **Single figure, single variable** ✅ PASSED
   - Expected: 1 entry, Got: 1 entry

2. **Single figure, multiple variables** ✅ PASSED
   - Code: `fig = px.bar(...); result = fig; output = fig`
   - Expected: 1 entry, Got: 1 entry (chose 'fig')

3. **Multiple different figures** ✅ PASSED
   - Code: `fig1 = px.bar(...); fig2 = px.line(...)`
   - Expected: 2 entries, Got: 2 entries

4. **Priority test** ✅ PASSED
   - Code: `result = px.bar(...); fig = result`
   - Correctly chose 'fig' over 'result'

5. **Non-plotly results still captured** ✅ PASSED
   - Verified that non-figure results still work correctly

6. **Figure with modifications** ✅ PASSED
   - Code: `fig = px.bar(...); fig.update_layout(...); result = fig`
   - Expected: 1 entry, Got: 1 entry

7. **Copied figures** ✅ PASSED
   - Code: `fig1 = px.bar(...); fig2 = copy.deepcopy(fig1)`
   - Expected: 2 entries (different objects), Got: 2 entries

8. **Unlisted variable name** ✅ PASSED
   - Code: `my_custom_plot = px.bar(...)`
   - Expected: 1 entry, Got: 1 entry

**Final Result**: 8/8 tests passed (100% success rate)

## Edge Cases Handled

### Case 1: Same Figure, Different Modifications
```python
fig = px.bar(df, x='x', y='y')
fig.update_layout(title='Version 1')
result = fig
result.update_layout(title='Version 2')  # Modifies same object
```
**Result**: 1 entry (same object, uses 'fig' name)

### Case 2: Deep Copy Creates New Object
```python
import copy
fig1 = px.bar(df, x='x', y='y')
fig2 = copy.deepcopy(fig1)  # New object with different ID
```
**Result**: 2 entries (different objects)

### Case 3: Priority Preference
```python
output = px.bar(df, x='x', y='y')
result = output
plot = output
fig = output
```
**Result**: 1 entry with name 'fig' (highest priority)

### Case 4: No Priority Variables
```python
my_viz = px.bar(df, x='x', y='y')
```
**Result**: 1 entry with name 'my_viz' (custom name works fine)

## Benefits of This Fix

1. **Eliminates Duplicates**: User sees exactly 1 plot per unique figure
2. **Better Names**: Prefers 'fig' over 'result' for better readability
3. **Backward Compatible**: All existing functionality preserved
4. **Efficient**: No performance impact, same serialization process
5. **Safe**: Minimal code change reduces risk of bugs

## Modified File

**File**: `server/code_executor.py`
**Lines Changed**: 293-318
**Method**: `_extract_results()`

## Verification Commands

```bash
# Test the fix
python test_duplicate_plots.py

# Comprehensive verification
python test_fix_verification.py
```

Both tests should show 100% pass rate with no duplicate entries.

## Before/After Comparison

### Before Fix (User Experience)
1. User: "Create a bar chart of sales by region"
2. System generates: `fig = px.bar(...); result = fig`
3. System creates: 2 identical plot entries
4. Frontend renders: **2 identical plots** ❌
5. User: "Why do I see duplicates?"

### After Fix (User Experience)
1. User: "Create a bar chart of sales by region"
2. System generates: `fig = px.bar(...); result = fig`
3. System creates: 1 plot entry (tracked by object ID)
4. Frontend renders: **1 plot** ✅
5. User: "Perfect!"

## Technical Details

### Why Object ID Works
- Python's `id()` returns the memory address of an object
- Same object = Same memory address = Same ID
- Different variables pointing to same object = Same ID
- Variable assignment doesn't create new objects: `result = fig` makes `result` point to the same object as `fig`

### Priority System Logic
```python
if name in figure_priority:
    priority = figure_priority.index(name)  # 0-5
else:
    priority = len(figure_priority)  # 6+ (lowest)
```

Lower priority number = Higher preference

### Iteration Order
Python 3.7+ maintains dictionary insertion order, so:
```python
for name, value in namespace.items():
```
Iterates in the order variables were defined/assigned.

## Related Files

- **Fix Implementation**: `server/code_executor.py:293-318`
- **Frontend Rendering**: `index.html:892-944`
- **Root Cause Analysis**: `DUPLICATE_PLOTS_ROOT_CAUSE_ANALYSIS.md`
- **Execution Flow**: `EXECUTION_FLOW_DIAGRAM.md`
- **Test Scripts**:
  - `test_duplicate_plots.py`
  - `test_fix_verification.py`

## Conclusion

The duplicate plotting issue has been **completely resolved** through intelligent object ID tracking and variable name prioritization. All tests pass with 100% success rate, and the fix maintains full backward compatibility while improving user experience.