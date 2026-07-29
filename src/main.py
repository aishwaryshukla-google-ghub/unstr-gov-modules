import os
import json
import logging
import requests
import functions_framework
from flask import jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_gcp_id_token(target_audience: str) -> str:
    """Fetches an OIDC Identity Token from the GCP Metadata Server when running in Cloud Run/Functions."""
    metadata_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={target_audience}"
    try:
        resp = requests.get(metadata_url, headers={"Metadata-Flavor": "Google"}, timeout=3)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        logger.warning(f"Could not fetch metadata ID token (running locally or metadata unavailable): {e}")
    return ""

@functions_framework.http
def hello_world(request):
    """HTTP Cloud Run Function entry point.
    Accepts an 'input_text' parameter and forwards it via HTTP request to a target endpoint using the 'requests' library.
    
    Query Params / JSON Payload:
    - input_text (str): The text payload to process/forward.
    - target_url (str, optional): The target HTTP URL to forward the request to.
    """
    request_json = request.get_json(silent=True) or {}
    request_args = request.args or {}

    # 1. Parse input_text
    input_text = request_json.get("input_text") or request_args.get("input_text") or request_json.get("text") or "Default Governance Sample Text"

    # 2. Parse target_url (from request or environment variable)
    target_url = request_json.get("target_url") or request_args.get("target_url") or os.environ.get("TARGET_ENDPOINT_URL", "https://httpbin.org/post")

    logger.info(f"Processing input_text: '{input_text[:50]}...' -> Target URL: '{target_url}'")

    # 3. Prepare Payload and Headers
    payload = {
        "input_text": input_text,
        "source": "NYL Unstructured Governance Cloud Run Function",
        "env": os.environ.get("APP_ENV", "dev")
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "NYL-Governance-Function/1.0"
    }

    # Automatically attach GCP OIDC Identity Token if calling another Cloud Run / Function endpoint
    if "run.app" in target_url or "cloudfunctions.net" in target_url:
        id_token = get_gcp_id_token(target_url)
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"

    # 4. Execute HTTP POST Request using 'requests' library
    target_response_data = None
    target_status_code = None

    try:
        resp = requests.post(target_url, json=payload, headers=headers, timeout=10)
        target_status_code = resp.status_code
        try:
            target_response_data = resp.json()
        except Exception:
            target_response_data = resp.text
    except Exception as e:
        target_status_code = 500
        target_response_data = str(e)
        logger.error(f"Failed to connect to target endpoint {target_url}: {e}")

    # 5. Return JSON Response
    return jsonify({
        "status": "success" if target_status_code and 200 <= target_status_code < 300 else "forward_failed",
        "input_text": input_text,
        "target_url": target_url,
        "target_status_code": target_status_code,
        "target_response": target_response_data,
        "service": "NYL Unstructured Governance Cloud Run Function"
    }), 200 if target_status_code and 200 <= target_status_code < 300 else 502
