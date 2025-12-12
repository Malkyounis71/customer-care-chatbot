import requests

def test_server_health():
    """Test if server is running."""
    try:
        response = requests.get("http://localhost:5002/api/health", timeout=2)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("✅ Server health check passed")
        return True
    except requests.ConnectionError:
        print("❌ Server not running")
        return False

def test_schedule_appointment():
    """Test scheduling an appointment."""
    data = {
        'service_type': 'consultation',
        'date': '2024-01-15',
        'time': '10:00',
        'customer_name': 'Test User',
        'email': 'test@example.com'
    }
    
    try:
        response = requests.post("http://localhost:5002/api/appointments", json=data, timeout=2)
        
        if response.status_code == 503:
            print("⚠️  Server simulated failure (expected 10% of time)")
            return True
        elif response.status_code == 200:
            result = response.json()
            assert result['success'] == True
            assert 'appointment_id' in result
            print(f"✅ Appointment scheduled: {result['appointment_id']}")
            return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Server not running")
        return False

if __name__ == "__main__":
    print("Testing Mock Appointment Server...")
    
    if test_server_health():
        test_schedule_appointment()
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Cannot test - server not running")
        print("Start server with: python mock_services/mock_appointment_server.py")