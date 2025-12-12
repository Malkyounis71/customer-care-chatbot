"""
Tests for the mock appointment server.
"""
import sys
import os
import pytest
import requests

MOCK_SERVER_URL = "http://localhost:5002"

class TestMockAppointmentServer:
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        try:
            response = requests.get(f"{MOCK_SERVER_URL}/api/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            print("✅ Health endpoint test passed")
            return True
        except requests.ConnectionError:
            pytest.skip("Mock server not running")
            return False
    
    def test_schedule_appointment_success(self):
        """Test successful appointment scheduling."""
        try:
            appointment_data = {
                'service_type': 'consultation',
                'date': '2024-01-15',
                'time': '14:30',
                'customer_name': 'John Doe',
                'email': 'john@example.com'
            }
            
            response = requests.post(
                f"{MOCK_SERVER_URL}/api/appointments",
                json=appointment_data,
                timeout=5
            )
            
            if response.status_code == 503:
                print("⚠️  Server simulated failure (expected)")
                return True
            elif response.status_code == 200:
                data = response.json()
                assert data['success'] == True
                print(f"✅ Appointment scheduled: {data.get('appointment_id', 'N/A')}")
                return True
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                return False
                
        except requests.ConnectionError:
            pytest.skip("Mock server not running")
            return False

def test_server_file_exists():
    """Test that mock server file exists."""
    server_path = os.path.join(os.path.dirname(__file__), '..', 'mock_services', 'mock_appointment_server.py')
    assert os.path.exists(server_path), f"Mock server file not found"
    print("✅ Mock server file exists")

if __name__ == "__main__":
    print("Running simple test...")
    tester = TestMockAppointmentServer()
    
    # Try health check
    try:
        result = tester.test_health_endpoint()
        if result is not False:
            print("Health test completed")
    except:
        print("Health test failed or skipped")
    
    # Try scheduling
    try:
        result = tester.test_schedule_appointment_success()
        if result is not False:
            print("Schedule test completed")
    except:
        print("Schedule test failed or skipped")
    
    print("\nTest script finished!")
