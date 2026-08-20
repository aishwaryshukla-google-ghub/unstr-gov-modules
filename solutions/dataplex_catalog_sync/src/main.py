import os
import json
import logging
from typing import Dict, Any
import functions_framework
from flask import jsonify, Request
from google.cloud import storage

from dataplex_catalog_manager import (
    DataplexCatalogClient,
    get_governance_compliance_template,
    get_business_taxonomy_template,
    get_source_provenance_template,
    parse_metadata_json,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dataplex-catalog-sync")


def read_gcs_or_local_json(file_path: str) -> Dict[str, Any]:
    """Reads JSON from GCS or local filesystem."""
    if file_path.startswith("gs://"):
        parts = file_path[5:].split("/", 1)
        bucket_name, blob_name = parts[0], parts[1]
        storage_client = storage.Client()
        blob = storage_client.bucket(bucket_name).blob(blob_name)
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
    Orchestrates metadata synchronization to Google Cloud Dataplex Universal Catalog:
    1. Downloads & parses the metadata JSON from GCS.
    2. Ensures Dataplex Entry Group, Aspect Types, and Entry Type exist.
    3. Creates or updates the Catalog Entry with populated Aspects.
    """
    logger.info(
        f"Syncing to Dataplex -> Meta: {gcs_metadata_uri}, Doc: {gcs_document_uri} "
        f"(Project: {project_id}, Location: {location}, Group: {entry_group_id})"
    )

    # 1. Read JSON and parse core entry & aspects
    raw_json = read_gcs_or_local_json(gcs_metadata_uri)
    entry_core, aspects_data = parse_metadata_json(
        raw_json=raw_json,
        gcs_metadata_uri=gcs_metadata_uri,
        gcs_document_uri=gcs_document_uri,
    )
    entry_id = entry_core["entry_id"]
    entry_type_id = "sharepoint-document"

    client = DataplexCatalogClient()

    # 2. Ensure Entry Group exists
    client.ensure_entry_group(
        project_id=project_id,
        location=location,
        entry_group_id=entry_group_id,
        display_name=entry_group_id.replace("-", " ").title(),
        description=f"Catalog entry group for {entry_group_id}",
    )

    # 3. Ensure Aspect Types exist
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
        description="LOB mappings, Term Store hierarchy, and document classification codes",
        metadata_template=get_business_taxonomy_template(),
    )

    prov_aspect_name = client.ensure_aspect_type(
        project_id=project_id,
        location=location,
        aspect_type_id="source-provenance",
        display_name="Source Provenance",
        description="Originating SharePoint site, drive, item IDs, authors, and file metadata",
        metadata_template=get_source_provenance_template(),
    )

    # 4. Ensure Entry Type exists
    entry_type_name = client.ensure_entry_type(
        project_id=project_id,
        location=location,
        entry_type_id=entry_type_id,
        display_name="SharePoint Document Asset",
        description="Unstructured asset type for SharePoint documents",
        allowed_aspect_type_names=[gov_aspect_name, tax_aspect_name, prov_aspect_name],
    )

    # 5. Create or Update Entry with populated Aspects
    aspects_payload = {
        gov_aspect_name: aspects_data["governance-compliance"],
        tax_aspect_name: aspects_data["business-taxonomy"],
        prov_aspect_name: aspects_data["source-provenance"],
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
        "entry_name": entry_result.get("name", f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}/entries/{entry_id}"),
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
    1. BigQuery Remote Function batch mode: {"calls": [ [meta_uri, doc_uri, project, location, group] ]}
    2. Direct REST JSON mode: {"gcs_metadata_uri": "...", "gcs_document_uri": "...", ...}
    """
    request_json = request.get_json(silent=True) or {}

    # Mode 1: BigQuery Remote Function (Batch calls contract)
    if "calls" in request_json:
        replies = []
        for call in request_json.get("calls", []):
            try:
                gcs_meta_uri = call[0]
                gcs_doc_uri = call[1]
                project_id = call[2]
                location = call[3]
                entry_group_id = call[4]

                res = sync_metadata_to_dataplex(
                    gcs_metadata_uri=gcs_meta_uri,
                    gcs_document_uri=gcs_doc_uri,
                    project_id=project_id,
                    location=location,
                    entry_group_id=entry_group_id,
                )
                replies.append(res)
            except Exception as e:
                logger.exception(f"Error processing row {call}: {e}")
                replies.append({"status": "ERROR", "error": str(e)})

        return jsonify({"replies": replies}), 200

    # Mode 2: Direct REST JSON invocation
    res = sync_metadata_to_dataplex(
        gcs_metadata_uri=request_json["gcs_metadata_uri"],
        gcs_document_uri=request_json["gcs_document_uri"],
        project_id=request_json["project_id"],
        location=request_json["location"],
        entry_group_id=request_json["entry_group_id"],
    )
    return jsonify(res), 200


