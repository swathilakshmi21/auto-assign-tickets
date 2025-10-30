"""Webhook server to receive ServiceNow incident notifications"""
from flask import Flask, request, jsonify
import json
import time
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Webhook flag file location
WEBHOOK_DIR = Path("outputs")
WEBHOOK_DIR.mkdir(exist_ok=True)
FLAG_FILE = WEBHOOK_DIR / "webhook_flag.txt"
INCIDENTS_FILE = WEBHOOK_DIR / "webhook_incidents.json"

@app.route('/webhook/incident', methods=['POST'])
def incident_webhook():
    """Receive webhook from ServiceNow when incident is created/updated"""
    try:
        data = request.json or {}
        
        # Extract incident data
        incident_data = {
            'sys_id': data.get('sys_id', ''),
            'short_description': data.get('short_description', ''),
            'description': data.get('description', ''),
            'category': data.get('category', ''),
            'subcategory': data.get('subcategory', ''),
            'priority': data.get('priority', 'P3'),
            'cmdb_ci': data.get('cmdb_ci', ''),
            'opened_at': data.get('opened_at', datetime.now().isoformat()),
            'state': data.get('state', '1'),
            'received_at': datetime.now().isoformat()
        }
        
        # Load existing incidents or create new list
        if INCIDENTS_FILE.exists():
            try:
                with open(INCIDENTS_FILE, 'r') as f:
                    incidents = json.load(f)
            except:
                incidents = []
        else:
            incidents = []
        
        # Add new incident (avoid duplicates by sys_id)
        existing_ids = [inc.get('sys_id') for inc in incidents]
        if incident_data['sys_id'] not in existing_ids:
            incidents.append(incident_data)
            
            # Keep only last 100 incidents (to avoid file growing too large)
            if len(incidents) > 100:
                incidents = incidents[-100:]
        
        # Save incidents to file
        with open(INCIDENTS_FILE, 'w') as f:
            json.dump(incidents, f, indent=2)
        
        # Write flag file with timestamp (triggers Streamlit reload)
        current_time = time.time()
        FLAG_FILE.write_text(str(current_time))
        
        print(f"✅ Webhook received: {incident_data['sys_id']} - {incident_data['short_description'][:50]}")
        
        return jsonify({
            "status": "success",
            "message": "Incident received",
            "sys_id": incident_data['sys_id']
        }), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/webhook/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "webhook_server",
        "flag_file": str(FLAG_FILE),
        "flag_exists": FLAG_FILE.exists()
    }), 200

@app.route('/webhook/status', methods=['GET'])
def status():
    """Get webhook status and recent incidents"""
    try:
        flag_time = None
        if FLAG_FILE.exists():
            flag_time = float(FLAG_FILE.read_text())
        
        incident_count = 0
        if INCIDENTS_FILE.exists():
            with open(INCIDENTS_FILE, 'r') as f:
                incidents = json.load(f)
                incident_count = len(incidents)
        
        return jsonify({
            "status": "running",
            "flag_file_time": flag_time,
            "total_incidents_received": incident_count,
            "flag_file_path": str(FLAG_FILE)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    
    print(f"🚀 Starting webhook server on {host}:{port}")
    print(f"📁 Flag file: {FLAG_FILE}")
    print(f"📁 Incidents file: {INCIDENTS_FILE}")
    
    app.run(host=host, port=port, debug=False)

