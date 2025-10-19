# Results Block Conditional Display

## Overview

The Results Block is a prominent UI component that displays the primary result from code execution. To enhance user experience and reduce interface clutter, the Results Block now intelligently hides when Plotly visualizations are present, as charts already convey the results visually.

## Feature Description

### Behavior

**When Visualization is Present:**
- Results Block is automatically hidden
- Display order: Analysis → Code → Visualization → Commentary
- Reduces redundancy since the chart shows the data visually

**When No Visualization:**
- Results Block is displayed prominently
- Display order: Analysis → Code → Results Block → Commentary
- Shows primary result (count, summary, etc.) in large, bold text

## Implementation Details

### Frontend Logic (`static/js/app.js`)

#### Detection Function

The `displayResultsBlock()` function checks for Plotly visualizations before rendering:

```javascript
function displayResultsBlock(results) {
  // Check if there are any visualizations (plots)
  let hasVisualization = false;
  Object.keys(results).forEach(key => {
    if (key.includes('plotly_figure') && results[key].type === 'plotly_figure') {
      hasVisualization = true;
      console.log('📊 Visualization detected:', key, '- Results Block will be hidden');
    }
  });

  // If there's a visualization, hide the Results Block entirely
  if (hasVisualization) {
    const resultsBlock = containers.results_block;
    const skeleton = resultsBlock.querySelector('#results-skeleton');
    const actualResults = resultsBlock.querySelector('#results-actual');
    
    // Hide all components of Results Block
    skeleton.classList.add('hidden');
    actualResults.classList.add('hidden');
    resultsBlock.classList.add('hidden');
    
    console.log('✓ Results Block hidden due to visualization presence');
    return; // Exit early, don't show results
  }
  
  // ... rest of the function displays Results Block for non-viz results
}
```

#### Key Detection Criteria

1. **Key Name Check**: `key.includes('plotly_figure')`
2. **Type Validation**: `results[key].type === 'plotly_figure'`
3. **Early Exit**: Returns immediately after hiding to prevent display

### Backend Support (`server/code_executor.py`)

The backend automatically detects and serializes Plotly figures:

- Figures assigned to `fig` or `figure` variables are captured
- Serialized as `plotly_figure_<name>` in results
- Type is set to `'plotly_figure'` for frontend detection

## Testing

### Test Case 1: Visualization Query

**Query:** "Plot current status counts (e.g., Inpatient/Outpatient/Emergency) as a bar chart."

**Expected Behavior:**
1. ✅ Analysis section appears
2. ✅ Python code block appears with Plotly code
3. ✅ Plotly bar chart is rendered
4. ✅ Results Block is **HIDDEN**
5. ✅ Commentary section appears

**Console Output:**
```
📊 Visualization detected: plotly_figure_fig - Results Block will be hidden
✓ Plotly visualization rendered: plotly_figure_fig
✓ Visualizations container displayed
✓ Results Block hidden due to visualization presence
```

### Test Case 2: Simple Result Query

**Query:** "How many Saudi patients are there?"

**Expected Behavior:**
1. ✅ Analysis section appears
2. ✅ Python code block appears with filtering code
3. ✅ No visualization rendered
4. ✅ Results Block is **VISIBLE** with count
5. ✅ Commentary section appears

**Console Output:**
```
ℹ️ No visualizations to display
✓ Results Block displayed with primary result: result = 54
```

### Test Case 3: Multiple Visualizations

**Query:** "Create a pie chart of patient nationalities and a bar chart of age distribution."

**Expected Behavior:**
1. ✅ Both charts are rendered
2. ✅ Results Block is **HIDDEN**
3. ✅ All visualizations appear in the Visualizations section

## Benefits

### User Experience
- **Reduced Clutter**: Eliminates redundant information when charts are present
- **Cleaner Interface**: Focus on the visualization without text distraction
- **Maintained Clarity**: Results Block still appears when needed for simple results

### Developer Experience
- **Clear Logging**: Console messages help debug display logic
- **Robust Detection**: Checks both key name and type for reliability
- **Graceful Handling**: Properly hides all components (skeleton + actual results)

## Edge Cases

### Case 1: Visualization + Result Variable

**Scenario:** Code generates both a chart and assigns a result variable

```python
status_counts = df['Status'].value_counts()
fig = px.bar(x=status_counts.index, y=status_counts.values)
result = len(status_counts)  # Also assigns a result
```

**Behavior:** Results Block is **HIDDEN** (visualization takes precedence)

### Case 2: Failed Visualization

**Scenario:** Code attempts to create a chart but fails

**Behavior:** Results Block is **HIDDEN** (execution failed, no results to show)

### Case 3: No Result Variable

**Scenario:** Code runs but doesn't assign to `result`, `output`, etc.

**Behavior:** Results Block is **HIDDEN** (no primary result found)

## Console Logging

The implementation includes comprehensive logging for debugging:

| Log Message | Meaning |
|------------|---------|
| `📊 Visualization detected: <key>` | Plotly figure found in results |
| `✓ Results Block hidden due to visualization presence` | Results Block successfully hidden |
| `✓ Results Block displayed with primary result: <key> = <value>` | Results Block shown with result |
| `⚠️ Results Block hidden - no primary result found` | No result variable found |
| `✓ Plotly visualization rendered: <key>` | Chart successfully rendered |
| `✓ Visualizations container displayed` | Visualization section shown |
| `ℹ️ No visualizations to display` | No charts in results |

## Future Enhancements

Potential improvements for future versions:

1. **User Preference**: Allow users to toggle Results Block visibility
2. **Smart Display**: Show Results Block for complex visualizations with summary stats
3. **Threshold Detection**: Hide Results Block only for certain chart types
4. **Animation**: Smooth fade-out transition when hiding Results Block

## Related Files

- `static/js/app.js` - Frontend display logic
- `server/code_executor.py` - Backend result serialization
- `server/serialization_engine.py` - Plotly figure serialization
- `docs/CHANGELOG.md` - Version history

## Version History

- **v2.4.1** (2025-10-19): Enhanced conditional display with improved logging
- **v2.3.x**: Initial Results Block implementation

