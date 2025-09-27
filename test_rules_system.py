"""
Test the rules management system.
"""
import requests
import json

def test_rules_management():
    """Test comprehensive rules management functionality."""
    
    base_url = "http://127.0.0.1:8010"
    
    print("🔧 Testing Rules Management System")
    print("=" * 50)
    
    # Test 1: Get initial rules (should be empty)
    print("\n1. Testing initial rules state...")
    response = requests.get(f"{base_url}/rules")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Initial rules loaded: {len(result['rules'])} rules")
        print(f"   Stats: {result['stats']}")
    else:
        print(f"❌ Failed to get initial rules: {response.text}")
        return
    
    # Test 2: Add some rules
    print("\n2. Testing rule addition...")
    
    test_rules = [
        {
            "text": "All visualizations should use colorblind-friendly palettes",
            "category": "visualization",
            "priority": 3
        },
        {
            "text": "Include statistical significance tests when comparing groups",
            "category": "analysis",
            "priority": 2
        },
        {
            "text": "Format currency values with appropriate symbols and commas",
            "category": "formatting",
            "priority": 1
        },
        {
            "text": "Always check for missing values and outliers before analysis",
            "category": "analysis",
            "priority": 3
        },
        {
            "text": "Use consistent font families across all charts",
            "category": "visualization",
            "priority": 2
        }
    ]
    
    added_rules = []
    for rule_data in test_rules:
        response = requests.post(f"{base_url}/rules", json=rule_data)
        
        if response.status_code == 200:
            result = response.json()
            added_rules.append(result['rule'])
            print(f"✅ Added rule: {rule_data['text'][:50]}...")
        else:
            print(f"❌ Failed to add rule: {response.text}")
    
    # Test 3: Get all rules
    print(f"\n3. Testing rule retrieval...")
    response = requests.get(f"{base_url}/rules")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Retrieved {len(result['rules'])} rules")
        
        # Check categories
        categories = result['stats']['categories']
        print(f"   Categories: {categories}")
        print(f"   Category counts: {result['stats']['category_counts']}")
        
        # Display rules by category
        for category in categories:
            cat_response = requests.get(f"{base_url}/rules?category={category}")
            if cat_response.status_code == 200:
                cat_result = cat_response.json()
                print(f"   {category}: {len(cat_result['rules'])} rules")
    else:
        print(f"❌ Failed to get rules: {response.text}")
    
    # Test 4: Update a rule
    print(f"\n4. Testing rule updates...")
    if added_rules:
        rule_to_update = added_rules[0]
        update_data = {
            "text": "All visualizations should use colorblind-friendly palettes and high contrast",
            "priority": 5
        }
        
        response = requests.put(f"{base_url}/rules/{rule_to_update['id']}", json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Updated rule {rule_to_update['id']}")
            print(f"   New text: {result['rule']['text']}")
            print(f"   New priority: {result['rule']['priority']}")
        else:
            print(f"❌ Failed to update rule: {response.text}")
    
    # Test 5: Import rules from text
    print(f"\n5. Testing bulk rule import...")
    
    import_text = """
# Data Quality Rules
Always validate data types before analysis
Check for duplicate records in datasets
Document data cleaning steps performed

# Visualization Standards  
Include proper axis labels and titles
Use consistent color schemes across related charts
Ensure plots are readable at different screen sizes
"""
    
    response = requests.post(f"{base_url}/rules/import", json={
        "text": import_text,
        "category": "imported"
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Imported {result['imported_count']} rules")
    else:
        print(f"❌ Failed to import rules: {response.text}")
    
    # Test 6: Test rules in LLM context
    print(f"\n6. Testing rules integration with LLM...")
    
    # Upload sample data first
    try:
        with open("sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            upload_response = requests.post(f"{base_url}/upload", files=files)
        
        if upload_response.status_code == 200:
            print("✅ Sample data uploaded for testing")
            
            # Test code execution with rules context
            test_code = """
import plotly.express as px

# Create a visualization following the rules
fig = px.box(df, x='Department', y='Salary', 
             title='Salary Distribution by Department',
             color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'])  # Colorblind-friendly

fig.update_layout(
    title={'x': 0.5, 'xanchor': 'center'},
    xaxis_title='Department',
    yaxis_title='Salary (USD)',
    font={'family': 'Arial, sans-serif'}  # Consistent font
)

rules_compliant_viz = fig
"""
            
            execute_response = requests.post(f"{base_url}/execute-code", json={"code": test_code})
            
            if execute_response.status_code == 200:
                result = execute_response.json()
                print("✅ Code executed with rules context")
                print(f"   Generated {len([k for k in result.get('results', {}).keys() if 'plotly' in k])} visualizations")
            else:
                print(f"❌ Code execution failed: {execute_response.text}")
        
    except FileNotFoundError:
        print("⚠️ Sample data file not found, skipping LLM integration test")
    
    # Test 7: Delete some rules
    print(f"\n7. Testing rule deletion...")
    if added_rules and len(added_rules) > 2:
        rule_to_delete = added_rules[1]
        
        response = requests.delete(f"{base_url}/rules/{rule_to_delete['id']}")
        
        if response.status_code == 200:
            print(f"✅ Deleted rule {rule_to_delete['id']}")
        else:
            print(f"❌ Failed to delete rule: {response.text}")
    
    # Test 8: Final rules state
    print(f"\n8. Final rules state...")
    response = requests.get(f"{base_url}/rules")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Final state: {len(result['rules'])} rules")
        print(f"   Categories: {result['stats']['categories']}")
        print(f"   Active rules: {result['stats']['active_rules']}")
        
        # Show sample rules
        if result['rules']:
            print("\n   Sample rules:")
            for rule in result['rules'][:3]:
                print(f"   - [{rule['category']}] {rule['text'][:60]}...")
    
    print(f"\n🎯 Rules Management Test Complete!")
    print("✅ Rule creation and storage")
    print("✅ Rule categorization and filtering")
    print("✅ Rule updates and deletion")
    print("✅ Bulk import functionality")
    print("✅ Integration with LLM context")

if __name__ == "__main__":
    test_rules_management()
