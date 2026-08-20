"""
Dataplex Universal Catalog Sync - Cloud Run Function

This module acts as the HTTP handler for synchronizing document metadata
stored in Google Cloud Storage (GCS) directly into Google Cloud Dataplex
Universal Catalog (formerly Knowledge Catalog).

It supports two invocation modes:
1. BigQuery Remote Function (batch evaluation via {"calls": [...]})
2. Direct REST HTTP POST (single document payload)
"""

import os
import json
import logging
from typing import Any, Dict
from flask import Request, jsonify
import functions_framework
from google.cloud import storage

from dataplex_catalog_manager import (
    DataplexCatalogClient,
    get_business_taxonomy_template,
    get_governance_compliance_template,
    get_source_provenance_template,
    parse_metadata_json,
)

# Disable mTLS probes to ensure compatibility across client environments
os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dataplex-catalog-sync")

# Reusable Cloud Storage client instance
_storage_client = None


def get_storage_client() -> storage.Client:
    """Returns a cached instance of the Google Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def read_json_payload(file_path: str) -> Dict[str, Any]:
    """
    Reads and parses a JSON file from either GCS (gs://...) or the local filesystem.
    """
    if file_path.startswith("gs://"):
        bucket_name, blob_name = file_path[5:].split("/", 1)
        blob = get_storage_client().bucket(bucket_name).blob(blob_name)
        return json.loads(blob.download_as_text())

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_metadata_to_dataplex(
    gcs_metadata_uri: str,
    gcs_document_uri: str,
    project_id: str,
    location: str,
    entry_group_id: str,
) -> Dict[str, Any]:
    """
    Core sync workflow:
    1. Reads metadata JSON from GCS and parses entry core & aspect dictionaries.
    2. Ensures the Entry Group exists in Dataplex.
    3. Ensures the three core Aspect Types exist (Governance, Taxonomy, Provenance).
    4. Ensures the Entry Type exists.
    5. Publishes/updates the Entry with attached aspect data.
    """
    logger.info(
        f"Syncing document to Dataplex: Meta={gcs_metadata_uri}, Doc={gcs_document_uri} "
        f"[Project: {project_id}, Location: {location}, Group: {entry_group_id}]"
    )

    # 1. Read JSON and parse core entry attributes & aspects
    raw_json = read_json_payload(gcs_metadata_uri)
    entry_core, aspects_data = parse_metadata_json(
        raw_json=raw_json,
        gcs_metadata_uri=gcs_metadata_uri,
        gcs_document_uri=gcs_document_uri,
    )
    entry_id = entry_core["entry_id"]

    client = DataplexCatalogClient()

    # 2. Ensure target Entry Group exists
    client.ensure_entry_group(
        project_id=project_id,
        location=location,
        entry_group_id=entry_group_id,
        display_name=entry_group_id.replace("-", " ").title(),
        description=f"Catalog entry group for {entry_group_id}",
    )

    # 3. Define and ensure all Aspect Types exist
    aspect_definitions = [
        (
            "governance-compliance",
            "Governance & Compliance",
            "Regulatory review, approval timestamps, and security classification metadata",
            get_governance_compliance_template(),
        ),
        (
            "business-taxonomy",
            "Business Taxonomy",
            "LOB mappings, Term Store hierarchy, and document classification codes",
            get_business_taxonomy_template(),
        ),
        (
            "source-provenance",
            "Source Provenance",
            "Originating SharePoint site, drive, item IDs, authors, and file metadata",
            get_source_provenance_template(),
        ),
    ]

    aspect_names = {}
    for aspect_id, display_name, description, template in aspect_definitions:
        aspect_names[aspect_id] = client.ensure_aspect_type(
            project_id=project_id,
            location=location,
            aspect_type_id=aspect_id,
            display_name=display_name,
            description=description,
            metadata_template=template,
        )

    # 4. Ensure the Entry Type exists and allows these aspects
    source_sys = entry_core.get("source_system", "sharepoint")
    entry_type_id = f"{source_sys.lower().replace('_', '-')}-document"
    entry_type_name = client.ensure_entry_type(
        project_id=project_id,
        location=location,
        entry_type_id=entry_type_id,
        display_name=f"{source_sys.title()} Document Asset",
        description=f"Unstructured asset type for {source_sys.title()} documents",
        allowed_aspect_type_names=list(aspect_names.values()),
    )

    # 5. Build aspects payload and publish/update the entry
    aspects_payload = {
        aspect_name: aspects_data[aspect_id]
        for aspect_id, aspect_name in aspect_names.items()
    }

    entry_result = client.create_or_update_entry(
        project_id=project_id,
        location=location,
        entry_group_id=entry_group_id,
        entry_id=entry_id,
        entry_type_name=entry_type_name,
        display_name=entry_core["display_name"],
        description=entry_core["description"],
        fully_qualified_name=entry_core["fully_qualified_name"],
        aspects_map=aspects_payload,
    )

    return {
        "status": "SUCCESS",
        "entry_id": entry_id,
        "entry_name": entry_result.get(
            "name",
            f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}/entries/{entry_id}",
        ),
        "display_name": entry_core["display_name"],
        "fully_qualified_name": entry_core["fully_qualified_name"],
        "gcs_document_uri": entry_core.get("gcs_document_uri"),
        "gcs_metadata_uri": gcs_metadata_uri,
        "aspects_synced": list(aspects_data.keys()),
    }


# =============================================================================
# HTTP Entrypoint for Cloud Run Function (Functions Framework Gen 2)
# =============================================================================

@functions_framework.http
def bq_remote_function_handler(request: Request):
    """
    Unified HTTP handler for Cloud Run Function & BigQuery Remote Function.

    Supported Contracts:
    - BigQuery Remote Function (batch):
        {"calls": [ [meta_uri, doc_uri, project_id, location, entry_group_id], ... ]}
        -> returns {"replies": [ {...}, ... ]}

    - Direct REST JSON:
        {"gcs_metadata_uri": "...", "gcs_document_uri": "...", "project_id": "...", "location": "...", "entry_group_id": "..."}
        -> returns {...}
    """
    request_json = request.get_json(silent=True) or {}

    # Mode 1: BigQuery Remote Function batch evaluation
    if "calls" in request_json:
        replies = []
        for call in request_json.get("calls", []):
            try:
                res = sync_metadata_to_dataplex(
                    gcs_metadata_uri=call[0],
                    gcs_document_uri=call[1],
                    project_id=call[2],
                    location=call[3],
                    entry_group_id=call[4],
                )
                replies.append(res)
            except Exception as e:
                logger.exception(f"Error syncing batch row {call}: {e}")
                replies.append({"status": "ERROR", "error": str(e)})

        return jsonify({"replies": replies}), 200

    # Mode 2: Direct REST JSON POST
    res = sync_metadata_to_dataplex(
        gcs_metadata_uri=request_json["gcs_metadata_uri"],
        gcs_document_uri=request_json["gcs_document_uri"],
        project_id=request_json["project_id"],
        location=request_json["location"],
        entry_group_id=request_json["entry_group_id"],
    )
    return jsonify(res), 200


