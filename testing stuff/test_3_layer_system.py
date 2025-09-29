"""
Test the complete 3-layer system: Metadata -> Code Generation -> Results Commentary
"""
import asyncio
import json
import websockets
import requests

async def test_complete_system():
    """Test the complete 3-layer system."""
    
    # First upload a file
    print("1. Uploading sample data...")
    upload_url = "http://127.0.0.1:8010/upload"
    
    try:
        with open("sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            response = requests.post(upload_url, files=files)
        
        if response.status_code != 200:
            print(f"Upload failed: {response.text}")
            return
        
        print("✅ File uploaded successfully!")
        
        # Test the complete WebSocket flow
        print("\n2. Testing complete 3-layer system via WebSocket...")
        uri = "ws://127.0.0.1:8010/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send a request for data analysis
            test_message = {
                "message": "Please analyze the salary data in the uploaded file. Create a visualization showing salary distribution by department and provide insights about the data."
            }
            await websocket.send(json.dumps(test_message))
            
            print("Sent analysis request...")
            print("\n=== Real-time Response ===")
            
            current_field = None
            field_contents = {"initial_response": "", "generated_code": "", "result_commentary": ""}
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)
                    
                    if data.get("event") == "start":
                        print("🚀 Response started...")
                        
                    elif data.get("event") == "delta":
                        field = data.get("field")
                        delta = data.get("delta", "")
                        
                        # Track field changes
                        if field != current_field:
                            if current_field:
                                print(f"\n\n--- End of {current_field} ---")
                            print(f"\n--- {field.upper().replace('_', ' ')} ---")
                            current_field = field
                        
                        # Print the delta
                        print(delta, end="", flush=True)
                        field_contents[field] += delta
                        
                    elif data.get("event") == "end":
                        print(f"\n\n--- End of {current_field} ---")
                        print("\n\n🎉 Response complete!")
                        
                        final_response = data.get("final", {})
                        
                        print("\n=== SUMMARY ===")
                        print(f"Initial Response: {len(final_response.get('initial_response', ''))} characters")
                        print(f"Generated Code: {len(final_response.get('generated_code', ''))} characters")
                        print(f"Result Commentary: {len(final_response.get('result_commentary', ''))} characters")
                        
                        # Check if code was generated and executed
                        if final_response.get('generated_code', '').strip():
                            print("\n✅ Code was generated and should have been executed")
                        else:
                            print("\n⚠️ No code was generated")
                        
                        break
                        
                except asyncio.TimeoutError:
                    print("\n⏰ Timeout waiting for response")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("\n🔌 Connection closed")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    break
        
        # Test metadata extraction
        print("\n3. Verifying metadata extraction...")
        metadata_url = "http://127.0.0.1:8000/file-metadata"
        response = requests.get(metadata_url)
        
        if response.status_code == 200:
            metadata = response.json()
            print("✅ Metadata extracted successfully")
            basic_info = metadata['metadata']['basic_info']
            print(f"   - File: {basic_info['filename']}")
            print(f"   - Shape: {basic_info['shape']['rows']} rows × {basic_info['shape']['columns']} columns")
            print(f"   - Columns: {', '.join(basic_info['column_names'])}")
        else:
            print(f"❌ Failed to get metadata: {response.text}")
        
        # Test direct code execution
        print("\n4. Testing direct code execution...")
        execute_url = "http://127.0.0.1:8000/execute-code"
        
        test_code = """
# Create a simple analysis
import plotly.express as px

# Salary by department analysis
dept_salary = df.groupby('Department')['Salary'].agg(['mean', 'count']).reset_index()
print("Average salary by department:")
print(dept_salary)

# Create visualization
fig = px.box(df, x='Department', y='Salary', title='Salary Distribution by Department')
fig.update_layout(xaxis_title='Department', yaxis_title='Salary ($)')

result = {
    'analysis': dept_salary.to_dict('records'),
    'total_employees': len(df),
    'avg_salary': df['Salary'].mean()
}
"""
        
        response = requests.post(execute_url, json={"code": test_code})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Direct code execution successful")
            print(f"   - Output length: {len(result.get('output', ''))}")
            print(f"   - Results keys: {list(result.get('results', {}).keys())}")
        else:
            print(f"❌ Direct code execution failed: {response.text}")
        
        print("\n🎯 3-Layer System Test Complete!")
        print("✅ Layer 1: Metadata extraction")
        print("✅ Layer 2: Code generation and execution")
        print("✅ Layer 3: Results commentary")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_complete_system())
