import os
import io
import functions_framework
import google.cloud.dlp_v2
from google.cloud import storage
import PyPDF2
import docx

PROJECT_ID = os.environ.get('PROJECT_ID', 'mhanono-mysandbox')
dlp = google.cloud.dlp_v2.DlpServiceClient(client_options={"quota_project_id": PROJECT_ID})
storage_client = storage.Client(project=PROJECT_ID)

DLP_LOCATION = os.environ.get('DLP_LOCATION', 'global')
INSPECT_TEMPLATE_NAME = os.environ.get('INSPECT_TEMPLATE_NAME')
DEIDENTIFY_TEMPLATE_NAME = os.environ.get('DEIDENTIFY_TEMPLATE_NAME')

def extract_text_from_gcs(uri):
    """Downloads a file from GCS and extracts text based on its extension."""
    if not uri.startswith("gs://"):
        return uri
        
    bucket_name = uri.split("/")[2]
    blob_name = "/".join(uri.split("/")[3:])
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    file_bytes = blob.download_as_bytes()
    
    if uri.lower().endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
        
    elif uri.lower().endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
        
    elif uri.lower().endswith(".txt"):
        return file_bytes.decode('utf-8')
        
    else:
        return f"[UNSUPPORTED_FILE_TYPE: {uri.split('.')[-1]}]"

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

            # If input is a GCS URI, extract the text from the file first
            if input_text.startswith("gs://"):
                try:
                    input_text = extract_text_from_gcs(input_text)
                except Exception as parse_error:
                    replies.append(f"[FILE_PARSING_ERROR: {str(parse_error)}]")
                    continue

            # Call DLP API to redact the text
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
