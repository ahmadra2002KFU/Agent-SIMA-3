"""
Test to reproduce the duplicate plotting issue
"""
import pandas as pd
import sys
sys.path.insert(0, 'server')

from code_executor import code_executor

# Create sample data
df = pd.DataFrame({
    'Category': ['A', 'B', 'C', 'D'],
    'Values': [10, 20, 15, 25]
})

# Test 1: Single variable assignment (should create 1 plot entry)
code1 = """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
"""

print("=" * 60)
print("Test 1: Single variable (fig)")
print("=" * 60)
success, output, results = code_executor.execute_code(code1, df)
if results:
    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    print(f"Found {len(plotly_keys)} plotly figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")
    print()

# Test 2: Multiple variable assignments pointing to same figure (likely cause of duplicates)
code2 = """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
result = fig
"""

print("=" * 60)
print("Test 2: Multiple variables (fig and result)")
print("=" * 60)
success, output, results = code_executor.execute_code(code2, df)
if results:
    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    print(f"Found {len(plotly_keys)} plotly figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")

    # Check if they point to the same figure
    if len(plotly_keys) >= 2:
        fig1_json = results[plotly_keys[0]].get('json')
        fig2_json = results[plotly_keys[1]].get('json')
        if fig1_json == fig2_json:
            print("\nWARNING: Both entries contain IDENTICAL figure data!")
            print("This would cause duplicate plots to be rendered in the frontend.")
    print()

# Test 3: Using 'figure' and 'fig' together
code3 = """
import plotly.express as px
figure = px.bar(df, x='Category', y='Values')
fig = figure
"""

print("=" * 60)
print("Test 3: Multiple variables (figure and fig)")
print("=" * 60)
success, output, results = code_executor.execute_code(code3, df)
if results:
    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    print(f"Found {len(plotly_keys)} plotly figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")

    if len(plotly_keys) >= 2:
        print("\nWARNING: Multiple figure entries detected!")
        print("This would cause duplicate plots to be rendered in the frontend.")
    print()

# Test 4: Common pattern where LLM might assign to result for return value
code4 = """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
fig.update_layout(title='Test Chart')
result = fig  # Common pattern to return the figure
"""

print("=" * 60)
print("Test 4: Modified figure assigned to result")
print("=" * 60)
success, output, results = code_executor.execute_code(code4, df)
if results:
    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    print(f"Found {len(plotly_keys)} plotly figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")

    if len(plotly_keys) >= 2:
        print("\n⚠️  WARNING: Multiple figure entries detected!")
    print()

print("=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
print("\nConclusion:")
print("If any test shows MORE than 1 plotly_figure entry,")
print("that's the root cause of the duplicate plotting issue.")
print("\nThe _extract_results() method creates a separate entry")
print("for each variable name that references the same figure object.")