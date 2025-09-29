"""
Test the live backend to see if the fix is active
"""
import sys
sys.path.insert(0, 'server')

from code_executor import code_executor
import pandas as pd

# Create test data
df = pd.DataFrame({
    'Age': [25, 30, 35, 40, 45, 50, 55, 60]
})

# Test code that creates duplicate variable references
code = """
import plotly.express as px
title = 'Distribution of Patient Ages'
fig = px.histogram(df, x='Age', title=title, nbins=20)
fig.update_xaxes(title_text='Age')
fig.update_yaxes(title_text='Number of Patients')
figure = fig
"""

print("Testing backend with duplicate variable code...")
print("=" * 60)

success, output, results = code_executor.execute_code(code, df)

if results:
    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    print(f"Found {len(plotly_keys)} plotly_figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")

    if len(plotly_keys) == 1:
        print("\n✓ FIX IS ACTIVE: Only 1 entry (correct)")
    elif len(plotly_keys) == 2:
        print("\n✗ FIX NOT ACTIVE: 2 entries (bug still present)")
        print("   The server needs to be restarted!")
    else:
        print(f"\n? UNEXPECTED: {len(plotly_keys)} entries")
else:
    print("No results returned")
    print(f"Success: {success}")
    print(f"Output: {output}")