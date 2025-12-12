

from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import random
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage
appointments = []

@app.route('/')
def home():
    return jsonify({
        'service': 'Mock Appointment Server',
        'version': '1.0.0',
        'endpoints': {
            'schedule': 'POST /api/appointments',
            'list': 'GET /api/appointments',
            'health': 'GET /api/health'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'appointments_count': len(appointments)
    })

@app.route('/api/appointments', methods=['POST'])
def schedule_appointment():
    """Mock appointment scheduling endpoint"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['service_type', 'date', 'time', 'customer_name', 'email']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Generate appointment ID
        appointment_id = f'APPT-{uuid.uuid4().hex[:6].upper()}'
        
        # Create appointment
        appointment = {
            'appointment_id': appointment_id,
            'service_type': data['service_type'],
            'date': data['date'],
            'time': data['time'],
            'customer_name': data['customer_name'],
            'email': data['email'],
            'phone': data.get('phone', ''),
            'notes': data.get('notes', ''),
            'status': 'confirmed',
            'created_at': datetime.now().isoformat(),
            'confirmation_code': str(random.randint(100000, 999999))
        }
        
        # Store appointment
        appointments.append(appointment)
        
        logger.info(f'Appointment scheduled: {appointment_id}')
        
        # Simulate random failures (10% chance)
        if random.random() < 0.1:
            return jsonify({
                'success': False,
                'error': 'Temporary service unavailable',
                'retry': True
            }), 503
        
        return jsonify({
            'success': True,
            'appointment_id': appointment_id,
            'message': 'Appointment scheduled successfully',
            'confirmation_code': appointment['confirmation_code']
        })
        
    except Exception as e:
        logger.error(f'Error scheduling appointment: {e}')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/appointments', methods=['GET'])
def list_appointments():
    """List all appointments"""
    return jsonify({
        'appointments': appointments,
        'count': len(appointments),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info('Starting Mock Appointment Server on port 5002...')
    app.run(host='0.0.0.0', port=5002, debug=True)
