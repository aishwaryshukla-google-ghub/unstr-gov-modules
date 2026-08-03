import os
import json
import logging
import requests
import functions_framework
from flask import jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_gcp_id_token(target_audience: str = None) -> str:
    """
    Fetches an OIDC Identity Token or Access Token from the GCP Metadata Server.
    Parses the response to extract 'access_token' or token string.
    """
    if target_audience:
        metadata_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={target_audience}"
    else:
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"

    try:
        resp = requests.get(metadata_url, headers={"Metadata-Flavor": "Google"}, timeout=5)
        if resp.status_code == 200:
            try:
                data = resp.json()
                # Parse 'access_token' from JSON response if present
                if isinstance(data, dict):
                    return data.get("access_token") or data.get("id_token") or resp.text.strip()
            except Exception:
                return resp.text.strip()
    except Exception as e:
        logger.warning(f"Could not fetch GCP metadata token (running locally or metadata unavailable): {e}")
    return ""

@functions_framework.http
def retrieve_llm_result(request):
    # 1. Parse long text input (supports raw text body, JSON string/object, or query params)
    input_text = ""

    # Check raw request data first
    raw_data = request.get_data(as_text=True)
    if raw_data:
        try:
            parsed_json = json.loads(raw_data)
            if isinstance(parsed_json, dict):
                input_text = parsed_json.get("input_text") or parsed_json.get("text") or parsed_json.get("prompt") or raw_data
            elif isinstance(parsed_json, str):
                input_text = parsed_json
            else:
                input_text = str(raw_data)
        except Exception:
            input_text = raw_data

    # Fallback to request JSON or query parameters if needed
    if not input_text:
        request_json = request.get_json(silent=True) or {}
        input_text = request_json.get("input_text") or request_json.get("text") or request.args.get("text") or ""

    logger.info(f"Received input text with length: {len(input_text)} characters")

    # 2. Generate GCP Bearer Token
    target_audience = os.environ.get("TARGET_AUDIENCE") or os.environ.get("TARGET_ENDPOINT_URL")
    access_token = get_gcp_id_token(target_audience=target_audience)

    logger.info(f"Access token retrieved: {'Yes' if access_token else 'No (running outside GCP or local)'}")

    # 3. Return parsed input and token status
    return jsonify({
        "status": "token_acquired" if access_token else "token_not_available",
        "input_text_length": len(input_text),
        "input_text_preview": input_text[:120] if input_text else "",
        "has_access_token": bool(access_token)
    }), 200
