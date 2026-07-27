import os
import functions_framework
import google.cloud.dlp_v2

PROJECT_ID = os.environ.get('PROJECT_ID', 'mhanono-mysandbox')
dlp = google.cloud.dlp_v2.DlpServiceClient(client_options={"quota_project_id": PROJECT_ID})
DLP_LOCATION = os.environ.get('DLP_LOCATION', 'global')
INSPECT_TEMPLATE_NAME = os.environ.get('INSPECT_TEMPLATE_NAME')
DEIDENTIFY_TEMPLATE_NAME = os.environ.get('DEIDENTIFY_TEMPLATE_NAME')

@functions_framework.http
def handle_request(request):
    try:
        data = request.get_json(silent=True)
        if not data or 'calls' not in data:
            return {'errorMessage': 'Invalid payload, expected "calls" array.'}, 400
            
        calls = data.get('calls', [])
        
        if not INSPECT_TEMPLATE_NAME or not DEIDENTIFY_TEMPLATE_NAME:
            return {'errorMessage': 'DLP templates not configured in environment.'}, 500

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
            
        return {'replies': replies}
    
    except Exception as e:
        return {'errorMessage': str(e)}, 400
