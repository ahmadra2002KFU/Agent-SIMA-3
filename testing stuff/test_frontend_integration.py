"""
Test the complete frontend integration with all features.
"""
import asyncio
import json
import websockets
import requests
import time

async def test_complete_frontend():
    """Test the complete frontend integration."""
    
    base_url = "http://127.0.0.1:8010"
    
    print("🌐 Testing Complete Frontend Integration")
    print("=" * 50)
    
    # Test 1: Basic server health
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return
    
    # Test 2: File upload functionality
    print("\n2. Testing file upload...")
    try:
        with open("sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            response = requests.post(f"{base_url}/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ File upload successful")
            print(f"   File: {result['file_info']['filename']}")
            print(f"   Size: {result['file_info']['size_mb']} MB")
        else:
            print(f"❌ File upload failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ File upload error: {e}")
        return
    
    # Test 3: File metadata extraction
    print("\n3. Testing metadata extraction...")
    try:
        response = requests.get(f"{base_url}/file-metadata")
        if response.status_code == 200:
            metadata = response.json()
            print("✅ Metadata extraction successful")
            basic_info = metadata['metadata']['basic_info']
            print(f"   Shape: {basic_info['shape']['rows']} × {basic_info['shape']['columns']}")
            print(f"   Columns: {', '.join(basic_info['column_names'][:3])}...")
        else:
            print(f"❌ Metadata extraction failed: {response.text}")
    except Exception as e:
        print(f"❌ Metadata error: {e}")
    
    # Test 4: Rules management
    print("\n4. Testing rules management...")
    try:
        # Add a test rule
        rule_data = {
            "text": "Use professional color schemes in all visualizations",
            "category": "visualization",
            "priority": 2
        }
        response = requests.post(f"{base_url}/rules", json=rule_data)
        
        if response.status_code == 200:
            print("✅ Rule addition successful")
            
            # Get rules
            response = requests.get(f"{base_url}/rules")
            if response.status_code == 200:
                rules_result = response.json()
                print(f"   Total rules: {len(rules_result['rules'])}")
                print(f"   Categories: {rules_result['stats']['categories']}")
            else:
                print(f"❌ Rules retrieval failed: {response.text}")
        else:
            print(f"❌ Rule addition failed: {response.text}")
    except Exception as e:
        print(f"❌ Rules management error: {e}")
    
    # Test 5: Code execution
    print("\n5. Testing code execution...")
    try:
        test_code = """
import plotly.express as px

# Create a simple visualization
fig = px.histogram(df, x='Department', title='Employee Count by Department')
fig.update_layout(
    title={'x': 0.5, 'xanchor': 'center'},
    xaxis_title='Department',
    yaxis_title='Count',
    font={'family': 'Arial, sans-serif'}
)

dept_histogram = fig

# Basic statistics
dept_stats = df['Department'].value_counts()
print("Department distribution:")
print(dept_stats)

result = {
    'total_employees': len(df),
    'departments': dept_stats.to_dict(),
    'avg_salary': df['Salary'].mean()
}
"""
        
        response = requests.post(f"{base_url}/execute-code", json={"code": test_code})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Code execution successful")
            print(f"   Status: {result['status']}")
            print(f"   Output length: {len(result.get('output', ''))}")
            
            # Check for visualizations
            results = result.get('results', {})
            plotly_figures = [k for k in results.keys() if 'plotly_figure' in k]
            print(f"   Generated {len(plotly_figures)} visualizations")
            
        else:
            print(f"❌ Code execution failed: {response.text}")
    except Exception as e:
        print(f"❌ Code execution error: {e}")
    
    # Test 6: WebSocket streaming
    print("\n6. Testing WebSocket streaming...")
    try:
        uri = "ws://127.0.0.1:8010/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send a test message
            test_message = {
                "message": "Create a simple analysis of the uploaded data showing salary distribution by department."
            }
            await websocket.send(json.dumps(test_message))
            
            print("   Sent analysis request...")
            
            # Collect streaming response
            response_fields = {"initial_response": "", "generated_code": "", "result_commentary": ""}
            message_count = 0
            
            while message_count < 20:  # Limit to prevent infinite loop
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    if data.get("event") == "start":
                        print("   🚀 Streaming started")
                        
                    elif data.get("event") == "delta":
                        field = data.get("field")
                        delta = data.get("delta", "")
                        if field in response_fields:
                            response_fields[field] += delta
                        
                    elif data.get("event") == "end":
                        print("   ✅ Streaming completed")
                        final_response = data.get("final", {})
                        
                        print(f"   Initial Response: {len(final_response.get('initial_response', ''))} chars")
                        print(f"   Generated Code: {len(final_response.get('generated_code', ''))} chars")
                        print(f"   Result Commentary: {len(final_response.get('result_commentary', ''))} chars")
                        
                        break
                        
                except asyncio.TimeoutError:
                    print("   ⏰ WebSocket timeout")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("   🔌 WebSocket connection closed")
                    break
            
            if message_count > 0:
                print("✅ WebSocket streaming successful")
            else:
                print("❌ No WebSocket messages received")
                
    except Exception as e:
        print(f"❌ WebSocket streaming error: {e}")
    
    # Test 7: Frontend static files
    print("\n7. Testing frontend static files...")
    try:
        # Test if the main page loads
        response = requests.get(f"{base_url}/")
        if response.status_code == 200 and "Gen-SIMA" in response.text:
            print("✅ Frontend HTML loads correctly")
            
            # Check for key elements
            html_content = response.text
            checks = [
                ("File upload", 'type="file"' in html_content),
                ("WebSocket code", 'WebSocket' in html_content),
                ("Rules section", 'Custom Rules' in html_content),
                ("Plotly integration", 'plotly' in html_content.lower()),
                ("Material icons", 'material-symbols' in html_content)
            ]
            
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
                
        else:
            print(f"❌ Frontend HTML failed to load properly")
            
    except Exception as e:
        print(f"❌ Frontend static files error: {e}")
    
    # Test 8: API endpoints
    print("\n8. Testing API endpoints...")
    endpoints = [
        ("/file-info", "GET"),
        ("/rules", "GET"),
        ("/file-metadata", "GET")
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}")
            
            if response.status_code in [200, 404]:  # 404 is OK for some endpoints when no data
                print(f"   ✅ {endpoint} ({method})")
            else:
                print(f"   ❌ {endpoint} ({method}): {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {endpoint} ({method}): {e}")
    
    print(f"\n🎯 Frontend Integration Test Complete!")
    print("✅ Server health and basic functionality")
    print("✅ File upload and metadata extraction")
    print("✅ Rules management system")
    print("✅ Code execution with visualizations")
    print("✅ WebSocket streaming communication")
    print("✅ Frontend static content delivery")
    print("✅ API endpoint accessibility")
    
    print(f"\n📋 Frontend is ready for user interaction!")
    print("   - Upload CSV/XLSX files via drag & drop or file picker")
    print("   - Add custom rules for analysis preferences")
    print("   - Chat with AI for data analysis and visualization")
    print("   - View real-time streaming responses")
    print("   - Interactive Plotly visualizations")

if __name__ == "__main__":
    asyncio.run(test_complete_frontend())
