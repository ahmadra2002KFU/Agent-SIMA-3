"""
Comprehensive test suite for the new robust architecture.
Tests all components and the Saudi patient admission analysis use case.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

# Import new architecture components
from server.serialization_engine import serialization_engine
from server.validation_engine import validation_engine
from server.response_manager import response_manager
from server.streaming_controller import streaming_controller
from server.error_handler import error_handler


def create_test_data():
    """Create test data similar to the Saudi patient admission scenario."""
    np.random.seed(42)
    
    # Create date range for 2024 and 2025
    start_date_2024 = datetime(2024, 1, 1)
    end_date_2024 = datetime(2024, 12, 31)
    start_date_2025 = datetime(2025, 1, 1)
    end_date_2025 = datetime(2025, 12, 31)
    
    # Generate admission dates
    dates_2024 = pd.date_range(start_date_2024, end_date_2024, freq='D')
    dates_2025 = pd.date_range(start_date_2025, end_date_2025, freq='D')
    
    # Create sample data
    data = []
    
    # 2024 data (500 records)
    for i in range(500):
        admission_date = np.random.choice(dates_2024)
        nationality = np.random.choice(['Saudi', 'Non-Saudi'], p=[0.7, 0.3])
        
        # Add some NaT values to test serialization
        if i % 50 == 0:
            admission_date = pd.NaT
        
        data.append({
            'Patient_ID': f'P{i+1:04d}',
            'Admission_Date': admission_date,
            'Nationality': nationality,
            'Age': np.random.randint(18, 80),
            'Department': np.random.choice(['Emergency', 'Surgery', 'Internal Medicine', 'Pediatrics']),
            'Length_of_Stay': np.random.randint(1, 15)
        })
    
    # 2025 data (600 records - simulating increased admissions)
    for i in range(600):
        admission_date = np.random.choice(dates_2025)
        nationality = np.random.choice(['Saudi', 'Non-Saudi'], p=[0.75, 0.25])
        
        # Add some NaT values
        if i % 60 == 0:
            admission_date = pd.NaT
        
        data.append({
            'Patient_ID': f'P{i+501:04d}',
            'Admission_Date': admission_date,
            'Nationality': nationality,
            'Age': np.random.randint(18, 80),
            'Department': np.random.choice(['Emergency', 'Surgery', 'Internal Medicine', 'Pediatrics']),
            'Length_of_Stay': np.random.randint(1, 15)
        })
    
    df = pd.DataFrame(data)
    return df


def test_serialization_engine():
    """Test the enhanced serialization engine."""
    print("🧪 Testing Serialization Engine...")
    
    # Test basic types
    assert serialization_engine.serialize_value(None) is None
    assert serialization_engine.serialize_value("test") == "test"
    assert serialization_engine.serialize_value(42) == 42
    assert serialization_engine.serialize_value(True) is True
    
    # Test NaN and infinity
    assert serialization_engine.serialize_value(float('nan')) is None
    assert serialization_engine.serialize_value(float('inf')) == "Infinity"
    assert serialization_engine.serialize_value(float('-inf')) == "-Infinity"
    
    # Test pandas NaT
    assert serialization_engine.serialize_value(pd.NaT) is None
    
    # Test pandas Timestamp
    timestamp = pd.Timestamp('2024-01-01')
    result = serialization_engine.serialize_value(timestamp)
    assert isinstance(result, str)
    assert '2024-01-01' in result
    
    # Test DataFrame with NaT values
    df = create_test_data()
    result = serialization_engine.serialize_value(df)
    assert result['type'] == 'dataframe'
    assert 'shape' in result
    assert 'columns' in result
    assert 'head' in result
    
    print("✅ Serialization Engine tests passed!")
    return True


def test_validation_engine():
    """Test the validation engine."""
    print("🧪 Testing Validation Engine...")
    
    # Test valid JSON
    valid_json = '{"initial_response": "test", "generated_code": "print(1)", "result_commentary": "done"}'
    result = validation_engine.validate_json_response(valid_json)
    assert result.is_valid
    
    # Test invalid JSON with auto-fix
    invalid_json = '"initial_response": "test", "generated_code": "print(1)", "result_commentary": "done"'
    result = validation_engine.validate_json_response(invalid_json)
    assert result.is_valid or len(result.warnings) > 0  # Should be fixed or have warnings
    
    # Test valid Python code
    valid_code = "df_filtered = df[df['Nationality'] == 'Saudi']\nprint(len(df_filtered))"
    result = validation_engine.validate_python_code(valid_code)
    assert result.is_valid
    
    # Test code with escape sequence issues
    corrupted_code = "df_filtered = df[df['Nationality'] == 'Saudi']\\nprint(len(df_filtered))"
    result = validation_engine.validate_python_code(corrupted_code)
    # Should either be valid after cleaning or have warnings
    assert result.is_valid or len(result.warnings) > 0
    
    # Test dangerous code
    dangerous_code = "import os; os.system('rm -rf /')"
    result = validation_engine.validate_python_code(dangerous_code)
    assert not result.is_valid
    assert len(result.errors) > 0
    
    print("✅ Validation Engine tests passed!")
    return True


async def test_response_manager():
    """Test the response manager."""
    print("🧪 Testing Response Manager...")
    
    # Create mock LLM response generator
    async def mock_llm_generator():
        yield {"field": "initial_response", "content": "Analyzing Saudi patient data..."}
        yield {"field": "generated_code", "content": "saudi_patients = df[df['Nationality'] == 'Saudi']"}
        yield {"field": "result_commentary", "content": "Analysis complete."}
    
    # Process with response manager
    response_id = "test_response_001"
    results = []
    
    async for chunk in response_manager.process_llm_response(response_id, mock_llm_generator()):
        results.append(chunk)
    
    # Verify results
    assert len(results) > 0
    
    # Check for completion
    completion_events = [r for r in results if r.get("event") == "response_complete"]
    assert len(completion_events) > 0
    
    print("✅ Response Manager tests passed!")
    return True


async def test_error_handler():
    """Test the error handler and circuit breaker."""
    print("🧪 Testing Error Handler...")
    
    # Test successful operation
    async def successful_operation():
        return "success"
    
    result = await error_handler.execute_with_circuit_breaker(
        "test_component", successful_operation
    )
    assert result == "success"
    
    # Test failing operation
    async def failing_operation():
        raise Exception("Test failure")
    
    # Should fail but not open circuit immediately
    try:
        await error_handler.execute_with_circuit_breaker(
            "test_component", failing_operation
        )
        assert False, "Should have raised exception"
    except Exception as e:
        assert "Test failure" in str(e)
    
    # Get component health
    health = error_handler.get_component_health("test_component")
    assert health['component'] == "test_component"
    
    print("✅ Error Handler tests passed!")
    return True


async def test_saudi_patient_analysis():
    """Test the specific Saudi patient admission analysis use case."""
    print("🧪 Testing Saudi Patient Analysis Use Case...")
    
    # Create test data
    df = create_test_data()
    
    # Test serialization of the DataFrame (this was the original issue)
    serialized_df = serialization_engine.serialize_value(df)
    assert serialized_df['type'] == 'dataframe'
    
    # Test code that would have caused the original NaT error
    test_code = """
# Filter for Saudi patients
saudi_patients = df[df['Nationality'] == 'Saudi']

# Extract year from admission date (this creates NaT values)
df['Admission_Year'] = df['Admission_Date'].dt.year

# Count admissions by year
admissions_2024 = len(df[(df['Admission_Year'] == 2024) & (df['Nationality'] == 'Saudi')])
admissions_2025 = len(df[(df['Admission_Year'] == 2025) & (df['Nationality'] == 'Saudi')])

# Calculate change
change = admissions_2025 - admissions_2024
change_percent = (change / admissions_2024 * 100) if admissions_2024 > 0 else 0

result = {
    'saudi_admissions_2024': admissions_2024,
    'saudi_admissions_2025': admissions_2025,
    'change': change,
    'change_percent': change_percent
}
"""
    
    # Validate the code
    validation_result = validation_engine.validate_python_code(test_code)
    assert validation_result.is_valid
    
    # Test execution namespace with NaT values
    namespace = {'df': df}
    exec(test_code, namespace)
    
    # Test serialization of results (including any NaT values)
    result = namespace.get('result', {})
    serialized_result = serialization_engine.serialize_value(result)
    
    # Should not raise JSON serialization error
    json_str = serialization_engine.serialize_execution_results({'result': result})
    assert isinstance(json_str, str)
    
    # Parse back to verify it's valid JSON
    parsed = json.loads(json_str)
    assert 'result' in parsed
    
    print("✅ Saudi Patient Analysis tests passed!")
    return True


async def run_comprehensive_tests():
    """Run all tests for the new architecture."""
    print("🚀 Starting Comprehensive Architecture Tests\n")
    
    tests = [
        ("Serialization Engine", test_serialization_engine),
        ("Validation Engine", test_validation_engine),
        ("Response Manager", test_response_manager),
        ("Error Handler", test_error_handler),
        ("Saudi Patient Analysis", test_saudi_patient_analysis),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
                
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {str(e)}\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! New architecture is ready for deployment.")
    else:
        print("⚠️ Some tests failed. Please review and fix issues before deployment.")
    
    # Print component statistics
    print("\n📈 Component Statistics:")
    print(f"Serialization Engine: {serialization_engine.get_stats()}")
    print(f"Validation Engine: {validation_engine.get_stats()}")
    print(f"Response Manager: {response_manager.get_stats()}")
    print(f"Error Handler: {error_handler.get_error_summary()}")
    
    return passed == total


if __name__ == "__main__":
    # Run the comprehensive test suite
    success = asyncio.run(run_comprehensive_tests())
    
    if success:
        print("\n🚀 New architecture is ready for production!")
        exit(0)
    else:
        print("\n❌ Architecture needs fixes before production deployment.")
        exit(1)
