import os
import json
import logging
import functions_framework
from flask import jsonify, Request

from handlers.registry import registry
from services.gcs_service import GCSService
from services.model_service import ModelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("unstructured-multimodal-service")


@functions_framework.http
def process_unstructured_document(request: Request):
    """
    Unified HTTP Cloud Run Function Entrypoint for Unstructured Document & Media Processing.

    Contract:
    1. Downloads file from GCS Object URI (supports pdf, docx, xlsx, csv, md, txt, images, audio).
    2. Converts document/tabular data into standardized PDF bytes (or preserves native media for image/audio).
    3. Encodes into Base64 format.
    4. Acquires Bearer Token from GCP Metadata Server.
    5. Dispatches HTTP POST to multimodal foundation model on Vertex AI (Anthropic Messages API / Google Gemini).
    6. Returns structured JSON output.

    Sample Request Payload:
    {
      "prompt": "Extract all tabular data and summarize key entities.",
      "gcs_uri": "gs://my-governance-bucket/reports/q3_data.xlsx",
      "model_name": "claude-3-5-sonnet-v2@20241022",
      "location": "us-central1",
      "max_tokens": 4096
    }
    """
    # 1. Parse JSON or Form Data
    req_json = request.get_json(silent=True) or {}
    req_args = request.args or {}

    prompt = req_json.get("prompt") or req_args.get("prompt") or "Extract all text, tables, and key metadata into clean structured markdown."
    gcs_uri = req_json.get("gcs_uri") or req_json.get("uri") or req_args.get("gcs_uri") or req_args.get("uri")

    if not gcs_uri:
        return jsonify({
            "error": "Missing required field: 'gcs_uri' (e.g. gs://my-bucket/path/to/document.xlsx)"
        }), 400

    model_name = req_json.get("model_name") or req_args.get("model_name") or os.environ.get("DEFAULT_MODEL", "claude-3-5-sonnet-v2@20241022")
    location = req_json.get("location") or req_args.get("location") or os.environ.get("VERTEX_LOCATION", "us-central1")
    project_id = req_json.get("project_id") or req_args.get("project_id")
    max_tokens = int(req_json.get("max_tokens") or 4096)

    logger.info(f"Incoming request -> GCS URI: {gcs_uri} | Model: {model_name} | Location: {location}")

    try:
        # 2. Download File from GCS
        file_bytes, filename = GCSService.download_file_bytes(gcs_uri)
        logger.info(f"Successfully downloaded '{filename}' ({len(file_bytes)} bytes)")

        # 3. Strategy Dispatcher: Convert to PDF (or pass native media)
        handler = registry.get_handler(filename)
        processed = handler.process(file_bytes, filename)
        logger.info(f"Processed '{filename}' with {handler.__class__.__name__} -> MIME: {processed.mime_type} (converted_to_pdf: {processed.converted_to_pdf})")

        # 4. Invoke Model on Vertex AI (Claude or Gemini)
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
