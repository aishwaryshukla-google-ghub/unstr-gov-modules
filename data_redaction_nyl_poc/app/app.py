import os
import json
from flask import Flask, request, jsonify
import google.cloud.dlp

app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID', 'mhanono-mysandbox')
dlp = google.cloud.dlp_v2.DlpServiceClient(client_options={"quota_project_id": PROJECT_ID})
DLP_LOCATION = os.environ.get('DLP_LOCATION', 'global')
INSPECT_TEMPLATE_NAME = os.environ.get('INSPECT_TEMPLATE_NAME')
DEIDENTIFY_TEMPLATE_NAME = os.environ.get('DEIDENTIFY_TEMPLATE_NAME')

@app.route('/', methods=['POST'])
def handle_request():
    try:
        data = request.get_json()
        if not data or 'calls' not in data:
            return jsonify({'errorMessage': 'Invalid payload, expected "calls" array.'}), 400
            
        calls = data.get('calls', [])
        
        if not INSPECT_TEMPLATE_NAME or not DEIDENTIFY_TEMPLATE_NAME:
            return jsonify({'errorMessage': 'DLP templates not configured in environment.'}), 500

        replies = []
        for call in calls:
            input_text = call[0] if call and len(call) > 0 else ""
            
            if not input_text:
                replies.append("")
                continue

            # Call DLP API to redact the text based on our OOB templates
            response = dlp.deidentify_content(
                request={
                    "parent": f"projects/{PROJECT_ID}/locations/{DLP_LOCATION}",
                    "deidentify_template_name": DEIDENTIFY_TEMPLATE_NAME,
                    "inspect_template_name": INSPECT_TEMPLATE_NAME,
                    "item": {"value": input_text},
                }
            )
            
            replies.append(response.item.value)
            
        return jsonify({'replies': replies})
    
    except Exception as e:
        return jsonify({'errorMessage': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
