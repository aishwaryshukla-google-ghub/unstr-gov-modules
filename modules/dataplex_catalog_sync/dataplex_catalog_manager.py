import os
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
import google.auth
import google.auth.transport.requests
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATAPLEX_API_BASE = "https://dataplex.googleapis.com/v1"


class DataplexCatalogClient:
    """
    Client for interacting with Google Cloud Dataplex Universal Catalog REST APIs.
    Manages Entry Groups, Aspect Types, Entry Types, and Entries.
    """

    def __init__(self, credentials=None):
        if credentials is None:
            self.credentials, self.default_project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            self.credentials = credentials
            self.default_project = getattr(credentials, "project_id", None)
        self.auth_req = google.auth.transport.requests.Request()

    def _get_headers(self) -> Dict[str, str]:
        self.credentials.refresh(self.auth_req)
        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
        }

    def _wait_for_lro(self, operation_name: str, timeout_seconds: int = 60) -> Dict[str, Any]:
        """Polls a Dataplex Long-Running Operation (LRO) until completion."""
        url = f"{DATAPLEX_API_BASE}/{operation_name}"
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            headers = self._get_headers()
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                op_data = res.json()
                if op_data.get("done"):
                    if "error" in op_data:
                        raise RuntimeError(f"Operation {operation_name} failed: {op_data['error']}")
                    return op_data.get("response", op_data)
            time.sleep(1.5)
        raise TimeoutError(f"Operation {operation_name} timed out after {timeout_seconds}s")

    # =========================================================================
    # Entry Group Management
    # =========================================================================

    def ensure_entry_group(
        self, project_id: str, location: str, entry_group_id: str, display_name: str = "", description: str = ""
    ) -> str:
        """Ensures that the specified Dataplex Entry Group exists, creating it if necessary."""
        # Sanitize ID to hyphens
        entry_group_id = entry_group_id.replace("_", "-")
        parent = f"projects/{project_id}/locations/{location}"
        resource_name = f"{parent}/entryGroups/{entry_group_id}"
        headers = self._get_headers()

        # Check if exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}", headers=headers)
        if get_res.status_code == 200:
            logger.info(f"Entry Group already exists: {resource_name}")
            return resource_name

        payload = {
            "displayName": display_name or entry_group_id,
            "description": description or f"Entry group for {entry_group_id}",
        }
        url = f"{DATAPLEX_API_BASE}/{parent}/entryGroups?entryGroupId={entry_group_id}"
        create_res = requests.post(url, headers=headers, json=payload)

        if create_res.status_code in [200, 201]:
            op_data = create_res.json()
            if "name" in op_data and "operations" in op_data["name"]:
                logger.info(f"Waiting for Entry Group creation LRO: {op_data['name']}...")
                self._wait_for_lro(op_data["name"])
            logger.info(f"Created Entry Group: {resource_name}")
            return resource_name
        elif create_res.status_code == 409:
            logger.info(f"Entry Group already exists (conflict): {resource_name}")
            return resource_name
        else:
            raise RuntimeError(
                f"Failed to create Entry Group {resource_name} ({create_res.status_code}): {create_res.text}"
            )

    # =========================================================================
    # Aspect Type Management
    # =========================================================================

    def ensure_aspect_type(
        self,
        project_id: str,
        location: str,
        aspect_type_id: str,
        display_name: str,
        description: str,
        metadata_template: Dict[str, Any],
    ) -> str:
        """Ensures that the specified Dataplex Aspect Type exists with its metadata template."""
        aspect_type_id = aspect_type_id.replace("_", "-")
        parent = f"projects/{project_id}/locations/{location}"
        resource_name = f"{parent}/aspectTypes/{aspect_type_id}"
        headers = self._get_headers()

        # Check if exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}", headers=headers)
        if get_res.status_code == 200:
            existing_data = get_res.json()
            existing_template = existing_data.get("metadataTemplate", {})
            if existing_template != metadata_template:
                logger.info(f"Aspect Type {resource_name} exists but schema changed, patching template...")
                patch_url = f"{DATAPLEX_API_BASE}/{resource_name}?updateMask=metadataTemplate"
                patch_res = requests.patch(patch_url, headers=headers, json={"metadataTemplate": metadata_template})
                if patch_res.status_code in [200, 201]:
                    op_data = patch_res.json()
                    if "name" in op_data and "operations" in op_data["name"]:
                        logger.info(f"Waiting for Aspect Type update LRO: {op_data['name']}...")
                        self._wait_for_lro(op_data["name"])
            else:
                logger.info(f"Aspect Type already exists: {resource_name}")
            return resource_name

        payload = {
            "displayName": display_name,
            "description": description,
            "metadataTemplate": metadata_template,
        }
        url = f"{DATAPLEX_API_BASE}/{parent}/aspectTypes?aspectTypeId={aspect_type_id}"
        create_res = requests.post(url, headers=headers, json=payload)

        if create_res.status_code in [200, 201]:
            op_data = create_res.json()
            if "name" in op_data and "operations" in op_data["name"]:
                logger.info(f"Waiting for Aspect Type creation LRO: {op_data['name']}...")
                self._wait_for_lro(op_data["name"])
            logger.info(f"Created Aspect Type: {resource_name}")
            return resource_name
        elif create_res.status_code == 409:
            logger.info(f"Aspect Type already exists (conflict): {resource_name}")
            return resource_name
        else:
            raise RuntimeError(
                f"Failed to create Aspect Type {resource_name} ({create_res.status_code}): {create_res.text}"
            )

    # =========================================================================
    # Entry Type Management
    # =========================================================================

    def ensure_entry_type(
        self,
        project_id: str,
        location: str,
        entry_type_id: str,
        display_name: str,
        description: str,
        allowed_aspect_type_names: list,
    ) -> str:
        """Ensures that the specified Dataplex Entry Type exists."""
        entry_type_id = entry_type_id.replace("_", "-")
        parent = f"projects/{project_id}/locations/{location}"
        resource_name = f"{parent}/entryTypes/{entry_type_id}"
        headers = self._get_headers()

        # Check if exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}", headers=headers)
        if get_res.status_code == 200:
            logger.info(f"Entry Type already exists: {resource_name}")
            return resource_name

        payload = {
            "displayName": display_name,
            "description": description,
        }
        url = f"{DATAPLEX_API_BASE}/{parent}/entryTypes?entryTypeId={entry_type_id}"
        create_res = requests.post(url, headers=headers, json=payload)

        if create_res.status_code in [200, 201]:
            op_data = create_res.json()
            if "name" in op_data and "operations" in op_data["name"]:
                logger.info(f"Waiting for Entry Type creation LRO: {op_data['name']}...")
                self._wait_for_lro(op_data["name"])
            logger.info(f"Created Entry Type: {resource_name}")
            return resource_name
        elif create_res.status_code == 409:
            logger.info(f"Entry Type already exists (conflict): {resource_name}")
            return resource_name
        else:
            raise RuntimeError(
                f"Failed to create Entry Type {resource_name} ({create_res.status_code}): {create_res.text}"
            )

    # =========================================================================
    # Entry & Aspects Management
    # =========================================================================

    def create_or_update_entry(
        self,
        project_id: str,
        location: str,
        entry_group_id: str,
        entry_id: str,
        entry_type_name: str,
        fully_qualified_name: str,
        display_name: str,
        description: str,
        aspects_map: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Creates or updates a Dataplex Catalog Entry with its attached Aspects.
        """
        entry_group_id = entry_group_id.replace("_", "-")
        parent = f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}"
        resource_name = f"{parent}/entries/{entry_id}"
        headers = self._get_headers()

        formatted_aspects = {}
        for aspect_type_name, aspect_data in aspects_map.items():
            parts = aspect_type_name.split("/")
            if len(parts) >= 6:
                map_key = f"{parts[1]}.{parts[3]}.{parts[5]}"
            else:
                map_key = f"{project_id}.{location}.{aspect_type_name.split('/')[-1]}"

            formatted_aspects[map_key] = {
                "aspectType": aspect_type_name,
                "data": aspect_data,
            }

        entry_payload = {
            "entryType": entry_type_name,
            "fullyQualifiedName": fully_qualified_name,
            "displayName": display_name,
            "description": description,
            "aspects": formatted_aspects,
        }

        # Check if entry already exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}?view=FULL", headers=headers)
        if get_res.status_code == 200:
            logger.info(f"Entry {resource_name} exists, updating...")
            update_url = f"{DATAPLEX_API_BASE}/{resource_name}?updateMask=aspects,displayName,description"
            patch_res = requests.patch(update_url, headers=headers, json=entry_payload)
            if patch_res.status_code in [200, 201]:
                logger.info(f"Successfully updated Entry: {resource_name}")
                return patch_res.json()
            else:
                raise RuntimeError(
                    f"Failed to update Entry {resource_name} ({patch_res.status_code}): {patch_res.text}"
                )
        else:
            create_url = f"{DATAPLEX_API_BASE}/{parent}/entries?entryId={entry_id}"
            create_res = requests.post(create_url, headers=headers, json=entry_payload)
            if create_res.status_code in [200, 201]:
                logger.info(f"Successfully created Entry: {resource_name}")
                return create_res.json()
            elif create_res.status_code == 409:
                update_url = f"{DATAPLEX_API_BASE}/{resource_name}?updateMask=aspects,displayName,description"
                patch_res = requests.patch(update_url, headers=headers, json=entry_payload)
                return patch_res.json()
            else:
                raise RuntimeError(
                    f"Failed to create Entry {resource_name} ({create_res.status_code}): {create_res.text}"
                )


# =============================================================================
# Aspect Type Schema Definitions
# =============================================================================

def get_governance_compliance_template() -> Dict[str, Any]:
    """Defines the MetadataTemplate schema for the Governance & Compliance Aspect Type."""
    return {
        "name": "governance_compliance",
        "type": "record",
        "recordFields": [
            {
                "name": "governance_approved",
                "type": "bool",
                "index": 1,
                "annotations": {"description": "Whether the document is formally approved by governance"},
            },
            {
                "name": "governance_approval_timestamp",
                "type": "datetime",
                "index": 2,
                "annotations": {"description": "Timestamp when governance approval was granted"},
            },
            {
                "name": "data_classification",
                "type": "string",
                "index": 3,
                "annotations": {"description": "Data classification level (Public, Internal, Confidential, Restricted)"},
            },
            {
                "name": "sec_rule_38a_1",
                "type": "bool",
                "index": 4,
                "annotations": {"description": "Indicates if the document falls under SEC Rule 38a-1 requirements"},
            },
            {
                "name": "certified_business_approved",
                "type": "string",
                "index": 5,
                "annotations": {"description": "Business certification sign-off status"},
            },
            {
                "name": "compliance_tags",
                "type": "record",
                "index": 6,
                "annotations": {"description": "Retention and compliance tag details from M365 Purview"},
                "recordFields": [
                    {"name": "tag_name", "type": "string", "index": 1, "annotations": {"description": "Retention or compliance tag name"}},
                    {"name": "written_time", "type": "datetime", "index": 2, "annotations": {"description": "Timestamp when compliance tag was applied"}},
                    {"name": "user_id", "type": "string", "index": 3, "annotations": {"description": "User identity that applied the compliance tag"}},
                ],
            },
        ],
    }


def get_business_taxonomy_template() -> Dict[str, Any]:
    """Defines the MetadataTemplate schema for the Business Taxonomy Aspect Type."""
    return {
        "name": "business_taxonomy",
        "type": "record",
        "recordFields": [
            {
                "name": "kmh_short_codes",
                "type": "array",
                "index": 1,
                "annotations": {"description": "Multi-tenant / domain short codes (e.g. MMM, LIS)"},
                "arrayItems": {"name": "code", "type": "string"},
            },
            {
                "name": "document_type_lookup_id",
                "type": "string",
                "index": 2,
                "annotations": {"description": "Primary document type taxonomy lookup identifier"},
            },
            {
                "name": "document_sub_type_lookup_id",
                "type": "string",
                "index": 3,
                "annotations": {"description": "Document sub-type taxonomy lookup identifier"},
            },
            {
                "name": "lob_lookups",
                "type": "array",
                "index": 4,
                "annotations": {"description": "Line of Business (LOB) taxonomy lookup entries"},
                "arrayItems": {
                    "name": "lob_entry",
                    "type": "record",
                    "recordFields": [
                        {"name": "lookup_id", "type": "int", "index": 1, "annotations": {"description": "Lookup ID number"}},
                        {"name": "lookup_value", "type": "string", "index": 2, "annotations": {"description": "Lookup label/value"}},
                    ],
                },
            },
            {
                "name": "lob_function_lookups",
                "type": "array",
                "index": 5,
                "annotations": {"description": "Line of Business Function lookup entries"},
                "arrayItems": {
                    "name": "lob_function_entry",
                    "type": "record",
                    "recordFields": [
                        {"name": "lookup_id", "type": "int", "index": 1, "annotations": {"description": "Function Lookup ID"}},
                        {"name": "lookup_value", "type": "string", "index": 2, "annotations": {"description": "Function Lookup label"}},
                    ],
                },
            },
            {
                "name": "function_term",
                "type": "record",
                "index": 6,
                "annotations": {"description": "Managed Metadata Term Store hierarchy"},
                "recordFields": [
                    {"name": "label", "type": "string", "index": 1, "annotations": {"description": "Term display label"}},
                    {"name": "term_guid", "type": "string", "index": 2, "annotations": {"description": "Term Store unique GUID"}},
                    {"name": "wss_id", "type": "int", "index": 3, "annotations": {"description": "Term Store internal WSS ID"}},
                ],
            },
            {
                "name": "series",
                "type": "array",
                "index": 7,
                "annotations": {"description": "Taxonomy series identifier list"},
                "arrayItems": {"name": "series_name", "type": "string"},
            },
            {
                "name": "in_service_sage",
                "type": "string",
                "index": 8,
                "annotations": {"description": "Routing or integration status with Service Sage"},
            },
        ],
    }


def get_source_provenance_template() -> Dict[str, Any]:
    """Defines the MetadataTemplate schema for the Source Provenance Aspect Type."""
    return {
        "name": "source_provenance",
        "type": "record",
        "recordFields": [
            {"name": "source_system", "type": "string", "index": 1, "annotations": {"description": "Originating source system (e.g. SharePoint)"}},
            {"name": "site_id", "type": "string", "index": 2, "annotations": {"description": "SharePoint Site ID"}},
            {"name": "drive_id", "type": "string", "index": 3, "annotations": {"description": "SharePoint Drive/Library ID"}},
            {"name": "item_id", "type": "string", "index": 4, "annotations": {"description": "SharePoint Item unique identifier"}},
            {"name": "source_web_url", "type": "string", "index": 5, "annotations": {"description": "Direct web link to source document"}},
            {"name": "ui_version", "type": "string", "index": 6, "annotations": {"description": "Document version string in source system"}},
            {"name": "doc_icon", "type": "string", "index": 7, "annotations": {"description": "Document format icon identifier (e.g. docx, pdf)"}},
            {"name": "file_size_bytes", "type": "int", "index": 8, "annotations": {"description": "File size in bytes"}},
            {"name": "quick_xor_hash", "type": "string", "index": 9, "annotations": {"description": "QuickXorHash checksum from OneDrive/SharePoint"}},
            {
                "name": "created_by",
                "type": "record",
                "index": 10,
                "annotations": {"description": "User who created the document in source system"},
                "recordFields": [
                    {"name": "email", "type": "string", "index": 1, "annotations": {"description": "User email"}},
                    {"name": "id", "type": "string", "index": 2, "annotations": {"description": "User ID"}},
                    {"name": "display_name", "type": "string", "index": 3, "annotations": {"description": "User display name"}},
                ],
            },
            {
                "name": "last_modified_by",
                "type": "record",
                "index": 11,
                "annotations": {"description": "User who last modified the document in source system"},
                "recordFields": [
                    {"name": "email", "type": "string", "index": 1, "annotations": {"description": "User email"}},
                    {"name": "id", "type": "string", "index": 2, "annotations": {"description": "User ID"}},
                    {"name": "display_name", "type": "string", "index": 3, "annotations": {"description": "User display name"}},
                ],
            },
            {"name": "source_created_time", "type": "datetime", "index": 12, "annotations": {"description": "Original creation timestamp"}},
            {"name": "source_modified_time", "type": "datetime", "index": 13, "annotations": {"description": "Last modified timestamp"}},
            {"name": "gcs_document_uri", "type": "string", "index": 14, "annotations": {"description": "GCS URI of the actual document file"}},
            {"name": "gcs_metadata_uri", "type": "string", "index": 15, "annotations": {"description": "GCS URI of the companion metadata JSON file"}},
        ],
    }


# =============================================================================
# JSON Parsing and Aspect Extraction Logic
# =============================================================================

def resolve_document_and_metadata_uris(gcs_uri: str, file_name: str) -> Tuple[str, str, str]:
    """
    Resolves:
    1. doc_gcs_uri (e.g. gs://bucket/path/file.docx)
    2. meta_gcs_uri (e.g. gs://bucket/path/file.docx.json)
    3. fqn (e.g. gcs:bucket:path/file.docx or custom:sharepoint:file.docx)
    """
    if gcs_uri.startswith("gs://"):
        parts = gcs_uri[5:].split("/", 1)
        bucket = parts[0]
        raw_path = parts[1] if len(parts) > 1 else file_name

        if raw_path.endswith(".metadata.json"):
            doc_path = raw_path[:-14]
            meta_path = raw_path
        elif raw_path.endswith(".json") and any(raw_path.endswith(f".{ext}.json") for ext in ["docx", "pdf", "xlsx", "pptx", "txt", "csv", "doc", "rtf"]):
            doc_path = raw_path[:-5]
            meta_path = raw_path
        elif raw_path.endswith(".json"):
            # Sidecar named metadata.json or similar in the same directory as the file
            folder = os.path.dirname(raw_path)
            doc_path = f"{folder}/{file_name}" if folder else file_name
            meta_path = raw_path
        else:
            doc_path = raw_path
            meta_path = f"{raw_path}.json"

        doc_gcs_uri = f"gs://{bucket}/{doc_path}"
        meta_gcs_uri = f"gs://{bucket}/{meta_path}"
        fqn = f"gcs:{bucket}:{doc_path}"
        return doc_gcs_uri, meta_gcs_uri, fqn
    else:
        clean_name = file_name.replace("/", ".").replace(" ", "_")
        return "", gcs_uri, f"custom:sharepoint:{clean_name}"


def parse_metadata_json(raw_json: Dict[str, Any], gcs_uri: str) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Parses the raw SharePoint/Graph metadata JSON into:
    1. Entry core metadata (entry_id, display_name, description, fqn, gcs_document_uri, gcs_metadata_uri)
    2. Aspects dictionary keyed by Aspect Type short name.
    """
    custom_fields = raw_json.get("customFields") or {}
    list_item = raw_json.get("listItem") or {}
    list_item_fields = list_item.get("fields") or {}

    def get_field(key: str, default: Any = ""):
        return custom_fields.get(key, list_item_fields.get(key, raw_json.get(key, default)))

    item_id = str(get_field("id") or raw_json.get("id") or "7372")
    file_name = get_field("FileLeafRef") or raw_json.get("name") or "unnamed_file"
    description = get_field("_CheckinComment") or f"SharePoint document {file_name}"
    # Entry ID must use hyphens/lowercase/numbers
    entry_id = f"sp-doc-{item_id}".lower().replace("_", "-")

    doc_gcs_uri, meta_gcs_uri, fqn = resolve_document_and_metadata_uris(gcs_uri, file_name)

    entry_core = {
        "entry_id": entry_id,
        "display_name": file_name,
        "description": description,
        "fully_qualified_name": fqn,
        "gcs_document_uri": doc_gcs_uri,
        "gcs_metadata_uri": meta_gcs_uri,
    }

    # 1. Aspect 1: Governance & Compliance
    gov_approval_time = raw_json.get("governance_approval_created")
    if gov_approval_time and not gov_approval_time.endswith("Z"):
        gov_approval_time = f"{gov_approval_time}Z"

    compliance_tag_time = get_field("_ComplianceTagWrittenTime")
    if compliance_tag_time and not compliance_tag_time.endswith("Z"):
        compliance_tag_time = f"{compliance_tag_time}Z"

    gov_aspect_data = {
        "governance_approved": bool(raw_json.get("governance_approved", False)),
        "data_classification": get_field("DataClassification") or get_field("_DisplayName") or "Internal",
        "sec_rule_38a_1": bool(get_field("SEC38a_x002d_1", False)),
        "certified_business_approved": str(get_field("CertifiedBusinessApproved", "")),
        "compliance_tags": {
            "tag_name": str(get_field("_ComplianceTag", "")),
            "user_id": str(get_field("_ComplianceTagUserId", "")),
        },
    }
    if gov_approval_time:
        gov_aspect_data["governance_approval_timestamp"] = gov_approval_time
    if compliance_tag_time:
        gov_aspect_data["compliance_tags"]["written_time"] = compliance_tag_time

    # 2. Aspect 2: Business Taxonomy
    kmh_codes = raw_json.get("kmh__short_code") or []
    if isinstance(kmh_codes, str):
        kmh_codes = [kmh_codes]

    lob_raw = get_field("LOB_LT", [])
    lob_lookups = [
        {"lookup_id": int(item.get("LookupId", 0)), "lookup_value": str(item.get("LookupValue", ""))}
        for item in lob_raw
        if isinstance(item, dict)
    ]

    lob_func_raw = get_field("LOBFunction_LT", [])
    lob_func_lookups = [
        {"lookup_id": int(item.get("LookupId", 0)), "lookup_value": str(item.get("LookupValue", ""))}
        for item in lob_func_raw
        if isinstance(item, dict)
    ]

    func_raw = get_field("Function", {})
    function_term = {
        "label": str(func_raw.get("Label", "")),
        "term_guid": str(func_raw.get("TermGuid", "")),
        "wss_id": int(func_raw.get("WssId", 0)),
    }

    series_raw = get_field("Series", [])
    if isinstance(series_raw, str):
        series_raw = [series_raw]

    taxonomy_aspect_data = {
        "kmh_short_codes": kmh_codes,
        "document_type_lookup_id": str(get_field("Document_x0020_Type1LookupId", "")),
        "document_sub_type_lookup_id": str(get_field("Document_x0020_Sub_x0020_Type1LookupId", "")),
        "lob_lookups": lob_lookups,
        "lob_function_lookups": lob_func_lookups,
        "function_term": function_term,
        "series": series_raw,
        "in_service_sage": str(get_field("DocumentInServiceSage_x003f_", "")),
    }

    # 3. Aspect 3: Source Provenance
    created_by_user = raw_json.get("createdBy", {}).get("user", {})
    modified_by_user = raw_json.get("lastModifiedBy", {}).get("user", {})
    parent_ref = raw_json.get("parentReference", {})
    file_info = raw_json.get("file", {})
    file_hashes = file_info.get("hashes", {})

    src_created = raw_json.get("createdDateTime") or get_field("Created")
    if src_created and not src_created.endswith("Z"):
        src_created = f"{src_created}Z"

    src_modified = raw_json.get("lastModifiedDateTime") or get_field("Modified")
    if src_modified and not src_modified.endswith("Z"):
        src_modified = f"{src_modified}Z"

    provenance_aspect_data = {
        "source_system": "SharePoint",
        "site_id": str(parent_ref.get("siteId", "")),
        "drive_id": str(parent_ref.get("driveId", "")),
        "item_id": item_id,
        "source_web_url": str(raw_json.get("webUrl", "")),
        "ui_version": str(get_field("_UIVersionString", "1.0")),
        "doc_icon": str(get_field("DocIcon", "")),
        "file_size_bytes": int(raw_json.get("size", 0)),
        "quick_xor_hash": str(file_hashes.get("quickXorHash", "")),
        "created_by": {
            "email": str(created_by_user.get("email", "")),
            "id": str(created_by_user.get("id", "")),
            "display_name": str(created_by_user.get("displayName", "")),
        },
        "last_modified_by": {
            "email": str(modified_by_user.get("email", "")),
            "id": str(modified_by_user.get("id", "")),
            "display_name": str(modified_by_user.get("displayName", "")),
        },
    }
    if src_created:
        provenance_aspect_data["source_created_time"] = src_created
    if src_modified:
        provenance_aspect_data["source_modified_time"] = src_modified
    if doc_gcs_uri:
        provenance_aspect_data["gcs_document_uri"] = doc_gcs_uri
    if meta_gcs_uri:
        provenance_aspect_data["gcs_metadata_uri"] = meta_gcs_uri

    aspects = {
        "governance-compliance": gov_aspect_data,
        "business-taxonomy": taxonomy_aspect_data,
        "source-provenance": provenance_aspect_data,
    }

    return entry_core, aspects


def fqn_from_gcs_uri(gcs_uri: str, default_name: str) -> str:
    """Generates a Dataplex Fully Qualified Name (FQN) from a GCS URI or custom source."""
    _, _, fqn = resolve_document_and_metadata_uris(gcs_uri, default_name)
    return fqn
