import os
import json
import argparse
import logging
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request as flask_request, jsonify
import functions_framework
from google.cloud import storage
import google.auth

from dataplex_catalog_manager import (
    DataplexCatalogClient,
    get_governance_compliance_template,
    get_business_taxonomy_template,
    get_source_provenance_template,
    parse_metadata_json,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

DEFAULT_ENTRY_GROUP_ID = "sharepoint-documents"
DEFAULT_ENTRY_TYPE_ID = "sharepoint-document"
DEFAULT_LOCATION = "us-central1"


def read_gcs_or_local_json(file_path: str) -> Dict[str, Any]:
    """Reads and parses a JSON file from GCS or local filesystem."""
    if file_path.startswith("gs://"):
        parts = file_path[5:].split("/", 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid GCS URI: {file_path}")
        bucket_name, blob_name = parts[0], parts[1]

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        content = blob.download_as_text()
        return json.loads(content)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)


def sanitize_id(raw_name: str, default: str = "unstructured-documents") -> str:
    """Sanitizes an input string to comply with Dataplex ID constraints (lowercase, numbers, hyphens)."""
    if not raw_name:
        return default
    sanitized = raw_name.lower().replace("_", "-").replace(" ", "-").replace(".", "-")
    # Keep only alphanumeric and hyphens
    sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-").strip("-")
    return sanitized or default


def sync_metadata_to_dataplex(
    gcs_uri: str,
    project_id: str,
    location: str = DEFAULT_LOCATION,
    entry_group_id: Optional[str] = None,
    entry_type_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main orchestration function:
    1. Downloads & parses the metadata JSON from GCS.
    2. Dynamically derives Entry Group and Entry Type if not explicitly passed.
    3. Ensures Dataplex Universal Catalog Entry Group, Aspect Types, and Entry Type exist.
    4. Creates or updates the Catalog Entry with populated Aspects.
    """
    logger.info(f"Starting metadata sync for GCS URI: {gcs_uri} (Project: {project_id}, Location: {location})")

    # 1. Read JSON
    raw_json = read_gcs_or_local_json(gcs_uri)

    # 2. Parse into Entry and Aspects data
    entry_core, aspects_data = parse_metadata_json(raw_json, gcs_uri)
    entry_id = entry_core["entry_id"]

    # 3. Dynamically resolve Entry Group ID
    if not entry_group_id:
        parent_ref_name = raw_json.get("parentReference", {}).get("name")
        if parent_ref_name:
            entry_group_id = sanitize_id(parent_ref_name)
        elif gcs_uri.startswith("gs://"):
            bucket_name = gcs_uri[5:].split("/")[0]
            entry_group_id = sanitize_id(bucket_name)
        else:
            entry_group_id = sanitize_id(os.environ.get("DATAPLEX_ENTRY_GROUP_ID", DEFAULT_ENTRY_GROUP_ID))
    else:
        entry_group_id = sanitize_id(entry_group_id)

    # 4. Dynamically resolve Entry Type ID
    if not entry_type_id:
        source_system = aspects_data.get("source-provenance", {}).get("source_system", "document")
        entry_type_id = sanitize_id(f"{source_system}-document", DEFAULT_ENTRY_TYPE_ID)
    else:
        entry_type_id = sanitize_id(entry_type_id)

    client = DataplexCatalogClient()

    # 5. Ensure Entry Group exists (with dynamic display name & description)
    eg_display_name = entry_group_id.replace("-", " ").title()
    client.ensure_entry_group(
        project_id=project_id,
        location=location,
        entry_group_id=entry_group_id,
        display_name=eg_display_name,
        description=f"Catalog entry group for unstructured assets in {eg_display_name}",
    )

    # 6. Ensure Aspect Types exist
    gov_aspect_name = client.ensure_aspect_type(
        project_id=project_id,
        location=location,
        aspect_type_id="governance-compliance",
        display_name="Governance & Compliance",
        description="Regulatory review, approval timestamps, and security classification metadata",
        metadata_template=get_governance_compliance_template(),
    )

    tax_aspect_name = client.ensure_aspect_type(
        project_id=project_id,
        location=location,
        aspect_type_id="business-taxonomy",
        display_name="Business Taxonomy",
        description="Line of business, taxonomy lookups, KMH short codes, and Managed Metadata terms",
        metadata_template=get_business_taxonomy_template(),
    )

    prov_aspect_name = client.ensure_aspect_type(
        project_id=project_id,
        location=location,
        aspect_type_id="source-provenance",
        display_name="Source Provenance",
        description="Upstream source system coordinates, authors, versions, and hashes",
        metadata_template=get_source_provenance_template(),
    )

    # 7. Ensure Entry Type exists
    et_display_name = entry_type_id.replace("-", " ").title()
    entry_type_name = client.ensure_entry_type(
        project_id=project_id,
        location=location,
        entry_type_id=entry_type_id,
        display_name=et_display_name,
        description=f"Unstructured asset type for {et_display_name}",
        allowed_aspect_type_names=[gov_aspect_name, tax_aspect_name, prov_aspect_name],
    )

    # 6. Map Aspect Types to their full resource names
    aspects_payload = {
        gov_aspect_name: aspects_data["governance-compliance"],
        tax_aspect_name: aspects_data["business-taxonomy"],
        prov_aspect_name: aspects_data["source-provenance"],
    }

    # 7. Create or update Entry
    entry_result = client.create_or_update_entry(
        project_id=project_id,
        location=location,
        entry_group_id=entry_group_id,
        entry_id=entry_id,
        entry_type_name=entry_type_name,
        fully_qualified_name=entry_core["fully_qualified_name"],
        display_name=entry_core["display_name"],
        description=entry_core["description"],
        aspects_map=aspects_payload,
    )

    return {
        "status": "SUCCESS",
        "entry_id": entry_id,
        "entry_name": entry_result.get("name", f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}/entries/{entry_id}"),
        "display_name": entry_core["display_name"],
        "fully_qualified_name": entry_core["fully_qualified_name"],
        "aspects_synced": list(aspects_data.keys()),
    }


# =============================================================================
# HTTP Endpoint (Cloud Run Function / BigQuery Remote Function)
# =============================================================================

@functions_framework.http
def bq_remote_function_handler(request=None):
    """
    Dual-mode HTTP handler for Cloud Run Function & BigQuery Remote Function:
    1. BigQuery Remote Function mode:
       Input:  {"calls": [ ["gs://bucket/path/file.json", "project-id", "us-central1", "entry-group"] ]}
       Output: {"replies": [ { "status": "SUCCESS", ... } ]}

    2. Direct REST JSON mode:
       Input:  {"gcs_uri": "gs://...", "project_id": "...", "location": "...", "entry_group_id": "..."}
       Output: { "status": "SUCCESS", ... }
    """
    # Resolve request object (Functions Framework passes request as param; Flask uses global)
    req = request if request is not None and hasattr(request, "get_json") else flask_request

    try:
        request_json = req.get_json(silent=True)
        if not request_json:
            return jsonify({"errorMessage": "Invalid or missing JSON payload"}), 400

        # Detect BigQuery Remote Function format
        if "calls" in request_json:
            calls = request_json.get("calls", [])
            replies = []

            # Infer default project if not passed in call
            _, default_proj = google.auth.default()
            fallback_project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or default_proj

            for call in calls:
                if not call or len(call) < 1:
                    replies.append({"status": "ERROR", "error": "Missing GCS URI argument"})
                    continue

                gcs_uri = call[0]
                project_id = call[1] if len(call) > 1 and call[1] else fallback_project
                location = call[2] if len(call) > 2 and call[2] else os.environ.get("LOCATION", DEFAULT_LOCATION)
                entry_group_id = call[3] if len(call) > 3 and call[3] else None
                entry_type_id = call[4] if len(call) > 4 and call[4] else None

                try:
                    res = sync_metadata_to_dataplex(
                        gcs_uri=gcs_uri,
                        project_id=project_id,
                        location=location,
                        entry_group_id=entry_group_id,
                        entry_type_id=entry_type_id,
                    )
                    replies.append(res)
                except Exception as e:
                    logger.exception(f"Error processing call {call}")
                    replies.append({"status": "ERROR", "gcs_uri": gcs_uri, "error": str(e)})

            return jsonify({"replies": replies})

        # Direct REST mode
        gcs_uri = request_json.get("gcs_uri")
        if not gcs_uri:
            return jsonify({"error": "gcs_uri is required"}), 400

        _, default_proj = google.auth.default()
        project_id = request_json.get("project_id") or os.environ.get("GCP_PROJECT") or default_proj
        location = request_json.get("location") or os.environ.get("LOCATION", DEFAULT_LOCATION)
        entry_group_id = request_json.get("entry_group_id")
        entry_type_id = request_json.get("entry_type_id")

        res = sync_metadata_to_dataplex(
            gcs_uri=gcs_uri,
            project_id=project_id,
            location=location,
            entry_group_id=entry_group_id,
            entry_type_id=entry_type_id,
        )
        return jsonify(res), 200

    except Exception as e:
        logger.exception("Internal server error")
        return jsonify({"errorMessage": f"Internal server error: {str(e)}"}), 500


# Register Flask routes
app.add_url_rule("/", view_func=bq_remote_function_handler, methods=["POST"])


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync GCS Metadata JSON to Dataplex Universal Catalog")
    parser.add_argument("file_path", nargs="?", help="Path to GCS URI (gs://...) or local JSON file")
    parser.add_argument("--gcs-uri", dest="gcs_uri_flag", help="GCS URI (gs://...)")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help="GCP Region/Location (e.g. us-central1)")
    parser.add_argument("--serve", action="store_true", help="Start HTTP Flask server for Cloud Run / BQ Remote Function")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)), help="Port for HTTP server")

    args = parser.parse_args()

    if args.serve or (not args.file_path and not args.gcs_uri_flag):
        logger.info(f"Starting server on port {args.port}...")
        app.run(host="0.0.0.0", port=args.port, debug=False)
    else:
        target_path = args.gcs_uri_flag or args.file_path
        proj = args.project
        if not proj:
            _, default_proj = google.auth.default()
            proj = default_proj

        result = sync_metadata_to_dataplex(
            gcs_uri=target_path,
            project_id=proj,
            location=args.location,
        )
        print(json.dumps(result, indent=2))
