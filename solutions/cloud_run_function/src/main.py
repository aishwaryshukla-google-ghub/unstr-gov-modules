import os
import sys
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

# Ensure current package directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import functions_framework
from flask import jsonify, Request

from handlers.registry import registry
from services.gcs_service import GCSService
from services.model_service import ModelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("unstructured-multimodal-service")


def _process_single_item(gcs_uri: str, prompt: str, model_name: str, location: str, project_id: Optional[str] = None, max_tokens: int = 4096) -> str:
    """Helper to download, convert, invoke model, and return extracted text."""
    file_bytes, filename = GCSService.download_file_bytes(gcs_uri)
    handler = registry.get_handler(filename)
    processed = handler.process(file_bytes, filename)
    
    result = ModelService.invoke_model(
        processed=processed,
        prompt=prompt,
        project_id=project_id,
        location=location,
        model_name=model_name,
        max_tokens=max_tokens
    )
    return result.get("extracted_text", "")


@functions_framework.http
def process_unstructured_document(request: Request):
    """
    Unified Cloud Run Function Entrypoint.
    Supports BOTH:
    1. BigQuery Remote Functions (batch 'calls' -> 'replies' contract).
    2. Direct HTTP / REST invocations (single 'gcs_uri' + 'prompt').
    """
    req_json = request.get_json(silent=True) or {}
    req_args = request.args or {}

    default_model = os.environ.get("DEFAULT_MODEL", "gemini-3.5-flash")
    default_location = os.environ.get("VERTEX_LOCATION", "us-central1")
    default_prompt = "Extract all text, tables, and key metadata into clean structured markdown."

    # -------------------------------------------------------------------------
    # MODE 1: BIGQUERY REMOTE FUNCTION (Batch calls contract)
    # -------------------------------------------------------------------------
    if "calls" in req_json:
        calls = req_json.get("calls", [])
        logger.info(f"BigQuery Remote Function invocation with {len(calls)} batch rows")
        
        replies = []
        for row in calls:
            try:
                # BigQuery Remote UDF passes arguments in order: (prompt, gcs_uri) or (gcs_uri, prompt)
                if len(row) == 1:
                    item_prompt, item_gcs_uri = default_prompt, row[0]
                elif len(row) >= 2:
                    # If first arg starts with gs://, it's uri first; otherwise prompt first
                    if str(row[0]).startswith("gs://"):
                        item_gcs_uri, item_prompt = row[0], row[1]
                    else:
                        item_prompt, item_gcs_uri = row[0], row[1]
                else:
                    replies.append(None)
                    continue

                extracted_text = _process_single_item(
                    gcs_uri=item_gcs_uri,
                    prompt=item_prompt,
                    model_name=default_model,
                    location=default_location
                )
                replies.append(extracted_text)

            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                replies.append(f"ERROR: {str(e)}")

        # BigQuery expects exact {"replies": [...]} format
        return jsonify({"replies": replies}), 200

    # -------------------------------------------------------------------------
    # MODE 2: DIRECT HTTP / REST / CURL INVOCATION
    # -------------------------------------------------------------------------
    prompt = req_json.get("prompt") or req_args.get("prompt") or default_prompt
    gcs_uri = req_json.get("gcs_uri") or req_json.get("uri") or req_args.get("gcs_uri") or req_args.get("uri")

    if not gcs_uri:
        return jsonify({
            "error": "Missing required field: 'gcs_uri' (e.g. gs://my-bucket/path/to/document.xlsx)"
        }), 400

    model_name = req_json.get("model_name") or req_args.get("model_name") or default_model
    location = req_json.get("location") or req_args.get("location") or default_location
    project_id = req_json.get("project_id") or req_args.get("project_id")
    max_tokens = int(req_json.get("max_tokens") or 4096)

    try:
        file_bytes, filename = GCSService.download_file_bytes(gcs_uri)
        handler = registry.get_handler(filename)
        processed = handler.process(file_bytes, filename)

        result = ModelService.invoke_model(
            processed=processed,
            prompt=prompt,
            project_id=project_id,
            location=location,
            model_name=model_name,
            max_tokens=max_tokens
        )

        return jsonify({
            "status": "success",
            "gcs_uri": gcs_uri,
            "filename": filename,
            "handler_used": handler.__class__.__name__,
            "mime_type": processed.mime_type,
            "converted_to_pdf": processed.converted_to_pdf,
            "result": result
        }), 200

    except Exception as e:
        logger.exception(f"Processing failed for {gcs_uri}: {e}")
        return jsonify({
            "status": "error",
            "gcs_uri": gcs_uri,
            "error_message": str(e)
        }), 500


# Entrypoint Aliases for Terraform deployment compatibility
retrieve_llm_result = process_unstructured_document
hello_world = process_unstructured_document
