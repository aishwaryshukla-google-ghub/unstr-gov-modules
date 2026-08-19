import json
import logging
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

    # =========================================================================
    # Entry Group Management
    # =========================================================================

    def ensure_entry_group(
        self, project_id: str, location: str, entry_group_id: str, display_name: str = "", description: str = ""
    ) -> str:
        """Ensures that the specified Dataplex Entry Group exists, creating it if necessary."""
        parent = f"projects/{project_id}/locations/{location}"
        resource_name = f"{parent}/entryGroups/{entry_group_id}"
        headers = self._get_headers()

        # Check if exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}", headers=headers)
        if get_res.status_code == 200:
            logger.info(f"Entry Group already exists: {resource_name}")
            return resource_name

        # Create
        payload = {
            "displayName": display_name or entry_group_id,
            "description": description or f"Entry group for {entry_group_id}",
        }
        url = f"{DATAPLEX_API_BASE}/{parent}/entryGroups?entryGroupId={entry_group_id}"
        create_res = requests.post(url, headers=headers, json=payload)

        if create_res.status_code in [200, 201]:
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
        parent = f"projects/{project_id}/locations/{location}"
        resource_name = f"{parent}/aspectTypes/{aspect_type_id}"
        headers = self._get_headers()

        # Check if exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}", headers=headers)
        if get_res.status_code == 200:
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
            "aspectTypes": [{"type": at_name} for at_name in allowed_aspect_type_names],
        }
        url = f"{DATAPLEX_API_BASE}/{parent}/entryTypes?entryTypeId={entry_type_id}"
        create_res = requests.post(url, headers=headers, json=payload)

        if create_res.status_code in [200, 201]:
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
        parent = f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}"
        resource_name = f"{parent}/entries/{entry_id}"
        headers = self._get_headers()

        formatted_aspects = {}
        for aspect_type_name, aspect_data in aspects_map.items():
            formatted_aspects[aspect_type_name] = {
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
            # Update via PATCH
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
            # Create via POST
            create_url = f"{DATAPLEX_API_BASE}/{parent}/entries?entryId={entry_id}"
            create_res = requests.post(create_url, headers=headers, json=entry_payload)
            if create_res.status_code in [200, 201]:
                logger.info(f"Successfully created Entry: {resource_name}")
                return create_res.json()
            elif create_res.status_code == 409:
                # Retry with PATCH if created concurrently
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
                "type": "boolean",
                "description": "Whether the document is formally approved by governance",
            },
            {
                "name": "governance_approval_timestamp",
                "type": "datetime",
                "description": "Timestamp when governance approval was granted",
            },
            {
                "name": "data_classification",
                "type": "string",
                "description": "Data classification level (e.g. Public, Internal, Confidential, Restricted)",
            },
            {
                "name": "sec_rule_38a_1",
                "type": "boolean",
                "description": "Indicates if the document falls under SEC Rule 38a-1 requirements",
            },
            {
                "name": "certified_business_approved",
                "type": "string",
                "description": "Business certification sign-off status",
            },
            {
                "name": "compliance_tags",
                "type": "record",
                "description": "Retention and compliance tag details from M365 Purview",
                "recordFields": [
                    {"name": "tag_name", "type": "string", "description": "Retention or compliance tag name"},
                    {"name": "written_time", "type": "datetime", "description": "Timestamp when compliance tag was applied"},
                    {"name": "user_id", "type": "string", "description": "User identity that applied the compliance tag"},
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
                "description": "Multi-tenant / domain short codes (e.g. MMM, LIS)",
                "arrayItems": {"name": "code", "type": "string"},
            },
            {
                "name": "document_type_lookup_id",
                "type": "string",
                "description": "Primary document type taxonomy lookup identifier",
            },
            {
                "name": "document_sub_type_lookup_id",
                "type": "string",
                "description": "Document sub-type taxonomy lookup identifier",
            },
            {
                "name": "lob_lookups",
                "type": "array",
                "description": "Line of Business (LOB) taxonomy lookup entries",
                "arrayItems": {
                    "name": "lob_entry",
                    "type": "record",
                    "recordFields": [
                        {"name": "lookup_id", "type": "integer", "description": "Lookup ID number"},
                        {"name": "lookup_value", "type": "string", "description": "Lookup label/value"},
                    ],
                },
            },
            {
                "name": "lob_function_lookups",
                "type": "array",
                "description": "Line of Business Function lookup entries",
                "arrayItems": {
                    "name": "lob_function_entry",
                    "type": "record",
                    "recordFields": [
                        {"name": "lookup_id", "type": "integer", "description": "Function Lookup ID"},
                        {"name": "lookup_value", "type": "string", "description": "Function Lookup label"},
                    ],
                },
            },
            {
                "name": "function_term",
                "type": "record",
                "description": "Managed Metadata Term Store hierarchy",
                "recordFields": [
                    {"name": "label", "type": "string", "description": "Term display label"},
                    {"name": "term_guid", "type": "string", "description": "Term Store unique GUID"},
                    {"name": "wss_id", "type": "integer", "description": "Term Store internal WSS ID"},
                ],
            },
            {
                "name": "series",
                "type": "array",
                "description": "Taxonomy series identifier list",
                "arrayItems": {"name": "series_name", "type": "string"},
            },
            {
                "name": "in_service_sage",
                "type": "string",
                "description": "Routing or integration status with Service Sage",
            },
        ],
    }


def get_source_provenance_template() -> Dict[str, Any]:
    """Defines the MetadataTemplate schema for the Source Provenance Aspect Type."""
    return {
        "name": "source_provenance",
        "type": "record",
        "recordFields": [
            {"name": "source_system", "type": "string", "description": "Originating source system (e.g. SharePoint)"},
            {"name": "site_id", "type": "string", "description": "SharePoint Site ID"},
            {"name": "drive_id", "type": "string", "description": "SharePoint Drive/Library ID"},
            {"name": "item_id", "type": "string", "description": "SharePoint Item unique identifier"},
            {"name": "source_web_url", "type": "string", "description": "Direct web link to source document"},
            {"name": "ui_version", "type": "string", "description": "Document version string in source system"},
            {"name": "doc_icon", "type": "string", "description": "Document format icon identifier (e.g. docx, pdf)"},
            {"name": "file_size_bytes", "type": "integer", "description": "File size in bytes"},
            {"name": "quick_xor_hash", "type": "string", "description": "QuickXorHash checksum from OneDrive/SharePoint"},
            {
                "name": "created_by",
                "type": "record",
                "description": "User who created the document in source system",
                "recordFields": [
                    {"name": "email", "type": "string"},
                    {"name": "id", "type": "string"},
                    {"name": "display_name", "type": "string"},
                ],
            },
            {
                "name": "last_modified_by",
                "type": "record",
                "description": "User who last modified the document in source system",
                "recordFields": [
                    {"name": "email", "type": "string"},
                    {"name": "id", "type": "string"},
                    {"name": "display_name", "type": "string"},
                ],
            },
            {"name": "source_created_time", "type": "datetime", "description": "Original creation timestamp"},
            {"name": "source_modified_time", "type": "datetime", "description": "Last modified timestamp"},
        ],
    }


# =============================================================================
# JSON Parsing and Aspect Extraction Logic
# =============================================================================

def parse_metadata_json(raw_json: Dict[str, Any], gcs_uri: str) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Parses the raw SharePoint/Graph metadata JSON into:
    1. Entry core metadata (entry_id, display_name, description, fqn)
    2. Aspects dictionary keyed by Aspect Type short name.
    """
    # Look for customFields or fallback to listItem.fields or top-level
    custom_fields = raw_json.get("customFields") or {}
    list_item = raw_json.get("listItem") or {}
    list_item_fields = list_item.get("fields") or {}

    # Prefer customFields for enriched values
    def get_field(key: str, default: Any = ""):
        return custom_fields.get(key, list_item_fields.get(key, raw_json.get(key, default)))

    # 1. Entry Identity
    item_id = str(get_field("id") or raw_json.get("id") or "unknown_id")
    file_name = get_field("FileLeafRef") or raw_json.get("name") or "unnamed_file"
    description = get_field("_CheckinComment") or f"SharePoint document {file_name}"
    entry_id = f"sp_doc_{item_id}".replace("-", "_").replace(".", "_")

    entry_core = {
        "entry_id": entry_id,
        "display_name": file_name,
        "description": description,
        "fully_qualified_name": fqn_from_gcs_uri(gcs_uri, file_name),
    }

    # 2. Aspect 1: Governance & Compliance
    gov_approval_time = raw_json.get("governance_approval_created")
    if gov_approval_time and not gov_approval_time.endswith("Z"):
        gov_approval_time = f"{gov_approval_time}Z"

    compliance_tag_time = get_field("_ComplianceTagWrittenTime")
    if compliance_tag_time and not compliance_tag_time.endswith("Z"):
        compliance_tag_time = f"{compliance_tag_time}Z"

    gov_aspect_data = {
        "governance_approved": bool(raw_json.get("governance_approved", False)),
        "governance_approval_timestamp": gov_approval_time or None,
        "data_classification": get_field("DataClassification") or get_field("_DisplayName") or "Internal",
        "sec_rule_38a_1": bool(get_field("SEC38a_x002d_1", False)),
        "certified_business_approved": str(get_field("CertifiedBusinessApproved", "")),
        "compliance_tags": {
            "tag_name": str(get_field("_ComplianceTag", "")),
            "written_time": compliance_tag_time or None,
            "user_id": str(get_field("_ComplianceTagUserId", "")),
        },
    }

    # 3. Aspect 2: Business Taxonomy
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

    # 4. Aspect 3: Source Provenance
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
        "source_created_time": src_created or None,
        "source_modified_time": src_modified or None,
    }

    aspects = {
        "governance_compliance": gov_aspect_data,
        "business_taxonomy": taxonomy_aspect_data,
        "source_provenance": provenance_aspect_data,
    }

    return entry_core, aspects


def fqn_from_gcs_uri(gcs_uri: str, default_name: str) -> str:
    """Generates a Dataplex Fully Qualified Name (FQN) from a GCS URI."""
    if gcs_uri.startswith("gs://"):
        parts = gcs_uri[5:].split("/", 1)
        bucket = parts[0]
        path = parts[1] if len(parts) > 1 else default_name
        return f"gcs:{bucket}:{path}"
    return f"sharepoint:default:{default_name}"
