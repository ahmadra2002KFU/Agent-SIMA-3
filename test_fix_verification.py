"""
Verification test for the duplicate plot fix
Tests various scenarios to ensure the fix works correctly
"""
import pandas as pd
import sys
sys.path.insert(0, 'server')

from code_executor import code_executor

# Create sample data
df = pd.DataFrame({
    'Category': ['A', 'B', 'C', 'D'],
    'Values': [10, 20, 15, 25],
    'Values2': [5, 15, 10, 20]
})

def test_case(name, code, expected_count):
    """Run a test case"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    success, output, results = code_executor.execute_code(code, df)

    if not success:
        print(f"FAILED: Code execution error")
        print(f"   Error: {output}")
        return False

    plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
    actual_count = len(plotly_keys)

    print(f"Expected: {expected_count} figure(s)")
    print(f"Actual: {actual_count} figure(s)")

    if plotly_keys:
        print(f"Figure entries:")
        for key in plotly_keys:
            print(f"  - {key}")

    if actual_count == expected_count:
        print("PASSED")
        return True
    else:
        print("FAILED: Count mismatch")
        return False

# Test cases
tests_passed = 0
tests_total = 0

# Test 1: Single figure, single variable
tests_total += 1
if test_case(
    "Single figure, single variable",
    """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
""",
    expected_count=1
):
    tests_passed += 1

# Test 2: Single figure, multiple variables (duplicate scenario)
tests_total += 1
if test_case(
    "Single figure, multiple variables",
    """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
result = fig
output = fig
""",
    expected_count=1  # Should be 1, not 3!
):
    tests_passed += 1

# Test 3: Multiple different figures
tests_total += 1
if test_case(
    "Multiple different figures",
    """
import plotly.express as px
fig1 = px.bar(df, x='Category', y='Values')
fig2 = px.line(df, x='Category', y='Values2')
""",
    expected_count=2  # Should be 2 (two different figures)
):
    tests_passed += 1

# Test 4: Priority test (should prefer 'fig' over 'result')
tests_total += 1
code4 = """
import plotly.express as px
result = px.bar(df, x='Category', y='Values')
fig = result
"""
print(f"\n{'='*60}")
print(f"Test: Priority test (should prefer 'fig')")
print(f"{'='*60}")
success, output, results = code_executor.execute_code(code4, df)
plotly_keys = [k for k in results.keys() if 'plotly_figure' in k]
if plotly_keys and 'plotly_figure_fig' in plotly_keys:
    print("PASS: PASSED: Correctly chose 'fig' over 'result'")
    tests_passed += 1
else:
    print(f"FAIL: FAILED: Expected 'plotly_figure_fig', got {plotly_keys}")

# Test 5: Non-plotly results still work
tests_total += 1
if test_case(
    "Non-plotly results still captured",
    """
result = df.head(2)
summary = 'Test summary'
""",
    expected_count=0  # No plotly figures
):
    # Also check that result and summary are captured
    success, output, results = code_executor.execute_code("""
result = df.head(2)
summary = 'Test summary'
""", df)
    if 'result' in results and 'summary' in results:
        print("PASS: Non-plotly results correctly captured")
        tests_passed += 1
    else:
        print("FAIL: Non-plotly results NOT captured")

# Test 6: Figure with update_layout
tests_total += 1
if test_case(
    "Figure with modifications",
    """
import plotly.express as px
fig = px.bar(df, x='Category', y='Values')
fig.update_layout(title='Test Chart')
result = fig
""",
    expected_count=1
):
    tests_passed += 1

# Test 7: Copy a figure (should create 2 entries)
tests_total += 1
if test_case(
    "Copy a figure (should create 2 entries)",
    """
import plotly.express as px
import copy
fig1 = px.bar(df, x='Category', y='Values')
fig2 = copy.deepcopy(fig1)  # Creates a new object
""",
    expected_count=2  # Two different objects
):
    tests_passed += 1

# Test 8: Unlisted variable name (should still work)
tests_total += 1
if test_case(
    "Unlisted variable name",
    """
import plotly.express as px
my_custom_plot = px.bar(df, x='Category', y='Values')
""",
    expected_count=1
):
    tests_passed += 1

# Final summary
print(f"\n{'='*60}")
print(f"FINAL RESULTS")
print(f"{'='*60}")
print(f"Tests passed: {tests_passed}/{tests_total}")
print(f"Success rate: {tests_passed/tests_total*100:.1f}%")

if tests_passed == tests_total:
    print("\nSUCCESS: ALL TESTS PASSED! The fix works correctly!")
else:
    print(f"\nWARNING:  {tests_total - tests_passed} test(s) failed")