"""
Digigami Waitlist API - Simple serverless function
Deploy to: Vercel, Netlify Functions, AWS Lambda, or Cloudflare Workers

This stores signups to a JSON file. For production, replace with:
- Supabase
- Airtable
- Google Sheets API
- Your own database
"""

import json
import os
from datetime import datetime
from pathlib import Path

# For local development / simple deployment
WAITLIST_FILE = Path(__file__).parent / "waitlist_data.json"

def load_waitlist():
    if WAITLIST_FILE.exists():
        return json.loads(WAITLIST_FILE.read_text())
    return []

def save_waitlist(data):
    WAITLIST_FILE.write_text(json.dumps(data, indent=2))

def handler(event, context=None):
    """
    AWS Lambda / Netlify Functions handler
    """
    # Parse request
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', {})
    
    method = event.get('httpMethod', 'POST')
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # GET - return count (admin only, add auth in production)
    if method == 'GET':
        waitlist = load_waitlist()
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'count': len(waitlist), 'emails': [w['email'] for w in waitlist]})
        }
    
    # POST - add to waitlist
    email = body.get('email', '').strip().lower()
    source = body.get('source', 'unknown')
    
    # Validate email
    if not email or '@' not in email or '.' not in email.split('@')[1]:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid email address'})
        }
    
    # Load existing
    waitlist = load_waitlist()
    
    # Check for duplicate
    if any(w['email'] == email for w in waitlist):
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Already on waitlist', 'duplicate': True})
        }
    
    # Add new entry
    waitlist.append({
        'email': email,
        'source': source,
        'timestamp': datetime.utcnow().isoformat(),
        'ip': event.get('headers', {}).get('x-forwarded-for', 'unknown')
    })
    
    save_waitlist(waitlist)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'Successfully added to waitlist', 'position': len(waitlist)})
    }


# Flask version for local dev
def create_flask_app():
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/api/waitlist', methods=['GET', 'POST', 'OPTIONS'])
    def waitlist():
        if request.method == 'OPTIONS':
            return '', 200
        
        event = {
            'httpMethod': request.method,
            'body': request.get_json() or {},
            'headers': dict(request.headers)
        }
        result = handler(event)
        return jsonify(json.loads(result['body'])), result['statusCode']
    
    return app


if __name__ == '__main__':
    # Run Flask dev server
    app = create_flask_app()
    app.run(port=5051, debug=True)
