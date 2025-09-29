"""
Comprehensive test suite for the LLM-powered chatbot web interface.
This test suite validates all components and end-to-end functionality.
"""
import asyncio
import json
import websockets
import requests
import time
import os
from pathlib import Path

class ComprehensiveTestSuite:
    """Complete test suite for the chatbot application."""
    
    def __init__(self, base_url="http://127.0.0.1:8010"):
        self.base_url = base_url
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test(self, test_name, passed, details=""):
        """Log test results."""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        self.test_results[test_name] = {"passed": passed, "details": details}
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
    
    def test_server_health(self):
        """Test basic server health and availability."""
        print("\n🏥 Server Health Tests")
        print("-" * 30)
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            self.log_test("Server responds to root endpoint", response.status_code == 200)
            
            # Test if HTML contains expected elements
            if response.status_code == 200:
                html_content = response.text
                self.log_test("HTML contains AI Sima title", "AI Sima" in html_content)
                self.log_test("HTML contains file upload", 'type="file"' in html_content)
                self.log_test("HTML contains WebSocket code", "WebSocket" in html_content)
            
        except Exception as e:
            self.log_test("Server responds to root endpoint", False, str(e))
    
    def test_file_operations(self):
        """Test file upload and metadata extraction."""
        print("\n📁 File Operations Tests")
        print("-" * 30)
        
        # Test file upload
        try:
            if os.path.exists("sample_data.csv"):
                with open("sample_data.csv", "rb") as f:
                    files = {"file": ("sample_data.csv", f, "text/csv")}
                    response = requests.post(f"{self.base_url}/upload", files=files)
                
                upload_success = response.status_code == 200
                self.log_test("File upload", upload_success)
                
                if upload_success:
                    result = response.json()
                    self.log_test("Upload returns file info", "file_info" in result)
                    
                    # Test file info endpoint
                    info_response = requests.get(f"{self.base_url}/file-info")
                    self.log_test("File info endpoint", info_response.status_code == 200)
                    
                    # Test metadata extraction
                    metadata_response = requests.get(f"{self.base_url}/file-metadata")
                    metadata_success = metadata_response.status_code == 200
                    self.log_test("Metadata extraction", metadata_success)
                    
                    if metadata_success:
                        metadata = metadata_response.json()
                        has_basic_info = "basic_info" in metadata.get("metadata", {})
                        self.log_test("Metadata contains basic info", has_basic_info)
            else:
                self.log_test("Sample data file exists", False, "sample_data.csv not found")
                
        except Exception as e:
            self.log_test("File upload", False, str(e))
    
    def test_rules_management(self):
        """Test rules management system."""
        print("\n📋 Rules Management Tests")
        print("-" * 30)
        
        try:
            # Test getting initial rules
            response = requests.get(f"{self.base_url}/rules")
            self.log_test("Get rules endpoint", response.status_code == 200)
            
            # Test adding a rule
            rule_data = {
                "text": "Test rule for comprehensive testing",
                "category": "test",
                "priority": 1
            }
            add_response = requests.post(f"{self.base_url}/rules", json=rule_data)
            add_success = add_response.status_code == 200
            self.log_test("Add rule", add_success)
            
            rule_id = None
            if add_success:
                rule_id = add_response.json()["rule"]["id"]
                
                # Test updating the rule
                update_data = {"text": "Updated test rule", "priority": 2}
                update_response = requests.put(f"{self.base_url}/rules/{rule_id}", json=update_data)
                self.log_test("Update rule", update_response.status_code == 200)
                
                # Test rule filtering by category
                cat_response = requests.get(f"{self.base_url}/rules?category=test")
                self.log_test("Filter rules by category", cat_response.status_code == 200)
                
                # Test deleting the rule
                delete_response = requests.delete(f"{self.base_url}/rules/{rule_id}")
                self.log_test("Delete rule", delete_response.status_code == 200)
            
            # Test bulk import
            import_data = {
                "text": "Rule 1\nRule 2\nRule 3",
                "category": "imported"
            }
            import_response = requests.post(f"{self.base_url}/rules/import", json=import_data)
            self.log_test("Bulk import rules", import_response.status_code == 200)
            
        except Exception as e:
            self.log_test("Rules management", False, str(e))
    
    def test_code_execution(self):
        """Test code execution functionality."""
        print("\n🐍 Code Execution Tests")
        print("-" * 30)
        
        try:
            # Test basic code execution
            basic_code = """
print("Hello, World!")
result = 2 + 2
"""
            response = requests.post(f"{self.base_url}/execute-code", json={"code": basic_code})
            basic_success = response.status_code == 200
            self.log_test("Basic code execution", basic_success)
            
            if basic_success:
                result = response.json()
                self.log_test("Code execution returns results", "results" in result)
                self.log_test("Code execution captures output", len(result.get("output", "")) > 0)
            
            # Test data analysis code (if file is uploaded)
            analysis_code = """
import pandas as pd
import plotly.express as px

if 'df' in globals():
    # Basic analysis
    summary = df.describe()
    print("Data summary:")
    print(summary)
    
    # Create visualization
    if 'Department' in df.columns and 'Salary' in df.columns:
        fig = px.box(df, x='Department', y='Salary', title='Salary by Department')
        salary_viz = fig
        
    analysis_result = {
        'rows': len(df),
        'columns': len(df.columns),
        'departments': df['Department'].nunique() if 'Department' in df.columns else 0
    }
else:
    print("No dataframe available")
    analysis_result = {"error": "No data"}
"""
            
            analysis_response = requests.post(f"{self.base_url}/execute-code", json={"code": analysis_code})
            analysis_success = analysis_response.status_code == 200
            self.log_test("Data analysis code execution", analysis_success)
            
            if analysis_success:
                result = analysis_response.json()
                # Check for Plotly figures
                plotly_figures = [k for k in result.get("results", {}).keys() if "plotly_figure" in k]
                self.log_test("Plotly visualization generation", len(plotly_figures) > 0)
            
            # Test security restrictions
            dangerous_code = """
import os
os.system("echo 'This should not work'")
"""
            
            security_response = requests.post(f"{self.base_url}/execute-code", json={"code": dangerous_code})
            # Should either fail or be blocked
            security_blocked = security_response.status_code != 200 or "not allowed" in security_response.text.lower()
            self.log_test("Security restrictions work", security_blocked)
            
        except Exception as e:
            self.log_test("Code execution", False, str(e))
    
    async def test_websocket_streaming(self):
        """Test WebSocket streaming functionality."""
        print("\n🔌 WebSocket Streaming Tests")
        print("-" * 30)
        
        try:
            uri = f"ws://127.0.0.1:8010/ws"
            
            async with websockets.connect(uri) as websocket:
                # Test basic connection
                self.log_test("WebSocket connection", True)
                
                # Send test message
                test_message = {"message": "Hello, can you help me analyze data?"}
                await websocket.send(json.dumps(test_message))
                
                # Collect responses
                responses_received = 0
                start_received = False
                end_received = False
                
                while responses_received < 10:  # Limit to prevent infinite loop
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)
                        responses_received += 1
                        
                        if data.get("event") == "start":
                            start_received = True
                        elif data.get("event") == "end":
                            end_received = True
                            break
                        elif data.get("event") == "delta":
                            # Valid streaming response
                            pass
                            
                    except asyncio.TimeoutError:
                        break
                    except websockets.exceptions.ConnectionClosed:
                        break
                
                self.log_test("WebSocket receives start event", start_received)
                self.log_test("WebSocket receives streaming deltas", responses_received > 2)
                self.log_test("WebSocket receives end event", end_received)
                
        except Exception as e:
            self.log_test("WebSocket streaming", False, str(e))
    
    def test_api_endpoints(self):
        """Test all API endpoints."""
        print("\n🌐 API Endpoints Tests")
        print("-" * 30)
        
        endpoints = [
            ("/", "GET", 200),
            ("/file-info", "GET", [200, 404]),  # 404 OK if no file
            ("/rules", "GET", 200),
            ("/file-metadata", "GET", [200, 404]),  # 404 OK if no file
        ]
        
        for endpoint, method, expected_codes in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}")
                
                if isinstance(expected_codes, list):
                    success = response.status_code in expected_codes
                else:
                    success = response.status_code == expected_codes
                
                self.log_test(f"{method} {endpoint}", success, f"Status: {response.status_code}")
                
            except Exception as e:
                self.log_test(f"{method} {endpoint}", False, str(e))
    
    def test_integration_scenarios(self):
        """Test end-to-end integration scenarios."""
        print("\n🔄 Integration Scenarios Tests")
        print("-" * 30)
        
        try:
            # Scenario 1: Complete workflow
            # 1. Upload file
            # 2. Add custom rule
            # 3. Execute analysis code
            # 4. Check results
            
            workflow_success = True
            
            # Step 1: Upload file
            if os.path.exists("sample_data.csv"):
                with open("sample_data.csv", "rb") as f:
                    files = {"file": ("sample_data.csv", f, "text/csv")}
                    upload_response = requests.post(f"{self.base_url}/upload", files=files)
                
                if upload_response.status_code != 200:
                    workflow_success = False
            else:
                workflow_success = False
            
            # Step 2: Add rule
            if workflow_success:
                rule_data = {
                    "text": "Use colorblind-friendly palettes in visualizations",
                    "category": "visualization"
                }
                rule_response = requests.post(f"{self.base_url}/rules", json=rule_data)
                if rule_response.status_code != 200:
                    workflow_success = False
            
            # Step 3: Execute analysis
            if workflow_success:
                analysis_code = """
import plotly.express as px
fig = px.histogram(df, x='Department', title='Department Distribution')
dept_chart = fig
result = {'total_employees': len(df)}
"""
                exec_response = requests.post(f"{self.base_url}/execute-code", json={"code": analysis_code})
                if exec_response.status_code != 200:
                    workflow_success = False
            
            self.log_test("Complete workflow integration", workflow_success)
            
        except Exception as e:
            self.log_test("Integration scenarios", False, str(e))
    
    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 50)
        print("Testing LLM-powered chatbot web interface")
        print("=" * 50)
        
        # Run all test categories
        self.test_server_health()
        self.test_file_operations()
        self.test_rules_management()
        self.test_code_execution()
        await self.test_websocket_streaming()
        self.test_api_endpoints()
        self.test_integration_scenarios()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n🎉 EXCELLENT! System is ready for production use.")
        elif success_rate >= 75:
            print("\n✅ GOOD! System is functional with minor issues.")
        elif success_rate >= 50:
            print("\n⚠️ FAIR! System has significant issues that need attention.")
        else:
            print("\n❌ POOR! System has major issues and needs substantial work.")
        
        # List failed tests
        failed_tests = [name for name, result in self.test_results.items() if not result["passed"]]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                details = self.test_results[test]["details"]
                print(f"   - {test}" + (f": {details}" if details else ""))
        
        return success_rate >= 75  # Return True if system is in good shape

async def main():
    """Run the comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    success = await suite.run_all_tests()
    return success

if __name__ == "__main__":
    asyncio.run(main())
