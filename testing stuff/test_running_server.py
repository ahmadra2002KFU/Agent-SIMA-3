"""
Test the RUNNING server to see if fix is active
"""
import urllib.request
import json

# Test code that would create duplicates
test_code = """
import plotly.express as px
import pandas as pd

df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
fig = px.bar(df, x='x', y='y')
figure = fig  # This creates duplicate reference
result = fig  # Another duplicate reference
"""

print("Testing RUNNING server at http://127.0.0.1:8010")
print("=" * 60)

req = urllib.request.Request(
    'http://127.0.0.1:8010/execute-code',
    data=json.dumps({'code': test_code}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode('utf-8'))
    results_dict = result.get('results', {})
    plotly_keys = [k for k in results_dict.keys() if 'plotly_figure' in k]

    print(f"Status: {result.get('status')}")
    print(f"Found {len(plotly_keys)} plotly_figure entries:")
    for key in plotly_keys:
        print(f"  - {key}")

    print()
    if len(plotly_keys) == 1:
        print("SUCCESS: Fix IS ACTIVE on running server!")
        print("Only 1 entry found (correct behavior)")
    elif len(plotly_keys) > 1:
        print("PROBLEM: Fix NOT ACTIVE on running server!")
        print(f"Found {len(plotly_keys)} entries (bug present)")
        print()
        print("ACTION REQUIRED: Server needs to be restarted!")
        print("1. Press Ctrl+C in the Run.bat window")
        print("2. Run Run.bat again")
    else:
        print("UNEXPECTED: No plotly figures found")
except urllib.error.HTTPError as e:
    print(f"ERROR: Server returned status {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"ERROR: {e}")