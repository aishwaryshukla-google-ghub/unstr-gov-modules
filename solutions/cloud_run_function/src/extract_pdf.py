#!/usr/bin/env python3
"""
extract_pdf.py

Extracts text and structured data from local PDF files using the Vertex AI 
Google Publisher REST API endpoint (without requiring the Vertex AI SDK).
"""

import os
import sys
import json
import base64
import argparse
import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    import google.auth
    from google.auth.transport.requests import Request
except ImportError:
    google = None
    Request = None

import subprocess
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("extract_pdf")


def get_auth_token_and_project(project_id: Optional[str] = None):
    """
    Obtains OAuth2 access token and GCP Project ID using google.auth (if installed)
    or falls back to gcloud CLI.
    """
    # 1. Try google.auth if installed
    if google and Request:
        try:
            credentials, detected_proj = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            target_project = (
                project_id
                or os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("PROJECT_ID")
                or detected_proj
            )
            if target_project and credentials.token:
                return credentials.token, target_project
        except Exception as e:
            logger.debug(f"google.auth failed, trying gcloud CLI fallback: {e}")

    # 2. Zero-dependency fallback: gcloud CLI
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            text=True
        ).strip()
        
        target_project = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("PROJECT_ID")
        )
        if not target_project:
            try:
                target_project = subprocess.check_output(
                    ["gcloud", "config", "get-value", "project"],
                    text=True
                ).strip()
            except Exception:
                pass
                
        if not target_project:
            raise ValueError(
                "Could not detect GCP Project ID. Set GOOGLE_CLOUD_PROJECT or pass project_id explicitly."
            )
        return token, target_project
    except Exception as e:
        logger.error(f"Authentication failed via both google.auth and gcloud CLI: {e}")
        raise


def extract_pdf_content(
    pdf_path: str,
    prompt: str = "Extract all text, tables, and key metadata from this document into clean, structured Markdown.",
    project_id: Optional[str] = None,
    location: str = "us-central1",
    model_name: str = "gemini-3.5-flash",
    response_mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts content from a local PDF using Vertex AI publisher model REST API endpoint.

    :param pdf_path: Path to the local PDF file.
    :param prompt: Instruction prompt for Gemini.
    :param project_id: GCP project ID (defaults to ADC / env).
    :param location: Vertex AI region (e.g., 'us-central1').
    :param model_name: Publisher model name (e.g., 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash').
    :param response_mime_type: Optional MIME type (e.g., 'application/json' for JSON enforcement).
    :return: Dictionary containing the extracted text and raw response metadata.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    # 1. Read file and convert to Base64
    logger.info(f"Reading and encoding PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > 20:
            raise ValueError(
                f"File size is {file_size_mb:.2f} MB. REST inline_data base64 payload limit is ~20 MB. "
                "For files >20MB, upload to GCS and use file_uri instead."
            )
        base64_data = base64.b64encode(file_bytes).decode("utf-8")

    # 2. Acquire Google Auth Token
    token, target_project = get_auth_token_and_project(project_id)
    logger.info(f"Target GCP Project: {target_project} | Region: {location} | Model: {model_name}")

    # 3. Target Vertex AI Publisher REST Endpoint
    endpoint_url = (
        f"https://aiplatform.googleapis.com/v1/"
        f"projects/{target_project}/locations/{location}/publishers/google/models/{model_name}:generateContent"
    )

    # 4. Construct JSON Payload
    generation_config: Dict[str, Any] = {
        "temperature": 0.2,
        "maxOutputTokens": 8192,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": base64_data
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generation_config": generation_config
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 5. Execute HTTP Request (supports both requests and urllib)
    logger.info(f"Sending request to Vertex AI Publisher endpoint: {endpoint_url}")
    
    if requests:
        response = requests.post(endpoint_url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"HTTP Error {response.status_code}: {response.text}")
            response.raise_for_status()
        result_json = response.json()
    else:
        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            logger.error(f"HTTP Error {e.code}: {err_msg}")
            raise RuntimeError(f"Vertex AI API call failed with code {e.code}: {err_msg}")

    # 6. Parse Generated Text Content
    candidates = result_json.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates returned by model: {result_json}")

    extracted_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    return {
        "extracted_text": extracted_text,
        "finish_reason": candidates[0].get("finishReason"),
        "usage_metadata": result_json.get("usageMetadata", {}),
        "raw_response": result_json
    }


def main():
    default_pdf = "/Users/aishwaryshukla/Downloads/ELDORADO - JUL 26 - Permit - Vehicle Tags.pdf"
    pdf_to_process = sys.argv[1] if len(sys.argv) > 1 else default_pdf
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-3.5-flash"

    try:
        res = extract_pdf_content(
            pdf_path=pdf_to_process,
            prompt="Extract all details, tables, and metadata from this document into clean, structured Markdown.",
            project_id="databricks-playground-497321",
            location="us-central1",
            model_name=model,
            response_mime_type=None
        )
        
        print("\n" + "=" * 60)
        print(" EXTRACTED DOCUMENT OUTPUT")
        print("=" * 60 + "\n")
        print(res["extracted_text"])
        print("\n" + "=" * 60)
        print(" USAGE METADATA")
        print("=" * 60)
        print(json.dumps(res["usage_metadata"], indent=2))
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
