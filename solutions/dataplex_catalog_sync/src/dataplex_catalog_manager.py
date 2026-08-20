import os
import re
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
import google.auth
import google.auth.transport.requests
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATAPLEX_API_BASE = "https://dataplex.googleapis.com/v1"
DATALINEAGE_API_BASE = "https://datalineage.googleapis.com/v1"


def sanitize_dataplex_id(raw_id: str, max_len: int = 63) -> str:
    """
    Sanitizes a string to be a valid Dataplex resource ID.
    Must contain only lowercase letters, numbers, and hyphens.
    Length must be <= max_len (typically 63).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", str(raw_id).replace("_", "-")).lower()
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = "asset"
    return cleaned[:max_len].rstrip("-")


def sanitize_label_value(val: Any, max_len: int = 63) -> str:
    """
    Sanitizes a string value for GCP labels (lowercase, numbers, _ and -, max 63 chars).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(val)).lower()
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len].rstrip("_") or "none"


def parse_storage_uri_components(uri: str) -> Dict[str, str]:
    """
    Parses a GCS URI of the standard pattern:
    gs://<bucket_name>/<environment>/<medallion_layer>/<source_system>/<file_name>.<ext>
    or arbitrary GCS path into structured components.
    """
    if not uri or not uri.startswith("gs://"):
        return {
            "bucket": "",
            "environment": "dev",
            "medallion_layer": "bronze",
            "source_system": "unstructured",
            "folder_path": "",
            "file_name": "",
            "file_stem": "",
            "file_extension": "",
        }

    raw_path = uri[5:]
    parts = raw_path.split("/")
    bucket = parts[0]
    sub_parts = parts[1:] if len(parts) > 1 else []

    file_name = sub_parts[-1] if sub_parts else ""
    folder_parts = sub_parts[:-1] if len(sub_parts) > 1 else []

    env = "dev"
    medallion = "bronze"
    source = "unstructured"

    env_candidates = {"dev", "staging", "stage", "test", "qa", "prod", "production", "uat"}
    medallion_candidates = {"bronze", "silver", "gold", "raw", "curated", "refined", "landing", "clean"}

    if len(folder_parts) >= 3:
        if folder_parts[0].lower() in env_candidates:
            env = folder_parts[0].lower()
        if folder_parts[1].lower() in medallion_candidates:
            medallion = folder_parts[1].lower()
        source = folder_parts[2].lower()
    elif len(folder_parts) == 2:
        if folder_parts[0].lower() in medallion_candidates:
            medallion = folder_parts[0].lower()
            source = folder_parts[1].lower()
        elif folder_parts[0].lower() in env_candidates:
            env = folder_parts[0].lower()
            medallion = folder_parts[1].lower()
    elif len(folder_parts) == 1:
        if folder_parts[0].lower() in medallion_candidates:
            medallion = folder_parts[0].lower()
        else:
            source = folder_parts[0].lower()

    file_stem = file_name
    file_ext = ""
    if "." in file_name:
        dot_idx = file_name.rfind(".")
        file_stem = file_name[:dot_idx]
        file_ext = file_name[dot_idx + 1 :].lower()

    return {
        "bucket": bucket,
        "environment": env,
        "medallion_layer": medallion,
        "source_system": source,
        "folder_path": "/".join(folder_parts),
        "file_name": file_name,
        "file_stem": file_stem,
        "file_extension": file_ext,
    }


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
        allowed_aspect_type_names: Optional[List[str]] = None,
    ) -> str:
        """Ensures that the specified Dataplex Entry Type exists."""
        entry_type_id = sanitize_dataplex_id(entry_type_id)
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
    # Container / Parent Entry Management (Populates 'Entry list' tab)
    # =========================================================================

    def ensure_container_entry(
        self,
        project_id: str,
        location: str,
        entry_group_id: str,
        container_id: str,
        display_name: str,
        description: str,
    ) -> str:
        """
        Creates or ensures a parent container entry exists in the Entry Group.
        When child documents set parentEntry pointing to this container,
        the parent's 'Entry list' tab in Dataplex UI displays all child documents.
        """
        container_entry_type = self.ensure_entry_type(
            project_id=project_id,
            location=location,
            entry_type_id="storage-container",
            display_name="Storage Container",
            description="Logical container or folder for grouping document entries",
        )

        parent = f"projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}"
        resource_name = f"{parent}/entries/{container_id}"
        headers = self._get_headers()

        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}?view=BASIC", headers=headers)
        if get_res.status_code == 200:
            return resource_name

        payload = {
            "entryType": container_entry_type,
            "entrySource": {
                "displayName": display_name,
                "description": description,
            },
            "fullyQualifiedName": f"custom:container:{entry_group_id}:{container_id}",
        }
        create_url = f"{DATAPLEX_API_BASE}/{parent}/entries?entryId={container_id}"
        create_res = requests.post(create_url, headers=headers, json=payload)
        if create_res.status_code in [200, 201]:
            logger.info(f"Created container entry: {resource_name}")
            return resource_name
        elif create_res.status_code == 409:
            return resource_name
        else:
            logger.warning(f"Could not create container entry {resource_name}: {create_res.text}")
            return resource_name

    # =========================================================================
    # Entry & Aspects Management (Details, Overview, Labels & Aspects)
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
        overview_content: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        parent_entry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates or updates a Dataplex Catalog Entry with its attached Aspects,
        rich Markdown Overview, searchable Labels (under entrySource), and optional parent container link.
        """
        entry_group_id = sanitize_dataplex_id(entry_group_id)
        entry_id = sanitize_dataplex_id(entry_id)
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

        # If overview markdown is provided, attach the standard Dataplex overview aspect
        if overview_content:
            formatted_aspects["dataplex-types.global.overview"] = {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {"content": overview_content},
            }

        # Build EntrySource object (where displayName, description, and labels reside in Dataplex v1)
        entry_source_payload: Dict[str, Any] = {
            "displayName": display_name,
            "description": description,
        }

        if labels:
            entry_source_payload["labels"] = {
                sanitize_dataplex_id(k, 63): sanitize_label_value(v, 63)
                for k, v in labels.items()
                if v is not None and str(v).strip() != ""
            }

        entry_payload: Dict[str, Any] = {
            "entryType": entry_type_name,
            "fullyQualifiedName": fully_qualified_name,
            "entrySource": entry_source_payload,
            "aspects": formatted_aspects,
        }

        if parent_entry:
            entry_payload["parentEntry"] = parent_entry

        update_mask_fields = ["aspects", "entrySource"]
        if parent_entry:
            update_mask_fields.append("parentEntry")

        update_mask = ",".join(update_mask_fields)

        # Check if entry already exists
        get_res = requests.get(f"{DATAPLEX_API_BASE}/{resource_name}?view=FULL", headers=headers)
        if get_res.status_code == 200:
            logger.info(f"Entry {resource_name} exists, updating with mask: {update_mask}...")
            update_url = f"{DATAPLEX_API_BASE}/{resource_name}?updateMask={update_mask}"
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
                update_url = f"{DATAPLEX_API_BASE}/{resource_name}?updateMask={update_mask}"
                patch_res = requests.patch(update_url, headers=headers, json=entry_payload)
                return patch_res.json()
            else:
                raise RuntimeError(
                    f"Failed to create Entry {resource_name} ({create_res.status_code}): {create_res.text}"
                )

    # =========================================================================
    # Data Lineage API Integration (Populates 'Lineage' tab)
    # =========================================================================

    def publish_data_lineage_link(
        self,
        project_id: str,
        location: str,
        source_uri: str,
        target_uri: str,
        process_display_name: str = "Unstructured Ingestion & Catalog Sync",
    ) -> Optional[Dict[str, Any]]:
        """
        Publishes a data lineage process and run to Google Cloud Data Lineage API
        (datalineage.googleapis.com) connecting source_uri to target_uri.
        This enables the 'Lineage' tab graph visualization in Dataplex.
        """
        parent = f"projects/{project_id}/locations/{location}"
        headers = self._get_headers()

        process_id = sanitize_dataplex_id(process_display_name, 40)
        process_name = f"{parent}/processes/{process_id}"

        # 1. Ensure Lineage Process
        proc_payload = {"displayName": process_display_name}
        proc_res = requests.post(
            f"{DATALINEAGE_API_BASE}/{parent}/processes?processId={process_id}",
            headers=headers,
            json=proc_payload,
        )
        if proc_res.status_code not in [200, 201, 409]:
            logger.warning(f"Could not register lineage process {process_name}: {proc_res.text}")
            return None

        # 2. Create Lineage Run
        run_res = requests.post(
            f"{DATALINEAGE_API_BASE}/{process_name}/runs",
            headers=headers,
            json={"displayName": f"Run at {time.strftime('%Y-%m-%dT%H:%M:%SZ')}", "state": "COMPLETED"},
        )
        if run_res.status_code not in [200, 201]:
            logger.warning(f"Could not create lineage run: {run_res.text}")
            return None
        run_data = run_res.json()
        run_name = run_data.get("name")

        # 3. Create Lineage Event linking source to target
        event_payload = {
            "startTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "links": [
                {
                    "source": {"fullyQualifiedName": source_uri},
                    "target": {"fullyQualifiedName": target_uri},
                }
            ],
        }
        event_res = requests.post(
            f"{DATALINEAGE_API_BASE}/{run_name}/lineageEvents",
            headers=headers,
            json=event_payload,
        )
        if event_res.status_code in [200, 201]:
            logger.info(f"Published Lineage Event from {source_uri} -> {target_uri}")
            return event_res.json()
        else:
            logger.warning(f"Could not publish lineage event: {event_res.text}")
            return None


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
            {"name": "environment", "type": "string", "index": 16, "annotations": {"description": "Deployment environment (e.g. dev, prod)"}},
            {"name": "medallion_layer", "type": "string", "index": 17, "annotations": {"description": "Medallion architecture layer (bronze, silver, gold)"}},
            {"name": "bucket_name", "type": "string", "index": 18, "annotations": {"description": "GCS Bucket name hosting the document"}},
            {"name": "storage_path", "type": "string", "index": 19, "annotations": {"description": "Relative storage path inside bucket"}},
        ],
    }


# =============================================================================
# Overview & Labels Generation Logic
# =============================================================================

def generate_overview_markdown(entry_core: Dict[str, Any], aspects: Dict[str, Dict[str, Any]]) -> str:
    """
    Generates a rich, structured Markdown document for the Dataplex Entry Overview.
    This provides human-readable documentation and powers Dataplex full-text search indexing.
    """
    display_name = entry_core.get("display_name", "Document Asset")
    doc_uri = entry_core.get("gcs_document_uri", "N/A")
    meta_uri = entry_core.get("gcs_metadata_uri", "N/A")
    medallion = entry_core.get("medallion_layer", "bronze").upper()
    env = entry_core.get("environment", "dev").upper()
    system_name = entry_core.get("source_system", "unstructured").title()
    desc = entry_core.get("description", "")

    tax = aspects.get("business-taxonomy", {})
    gov = aspects.get("governance-compliance", {})
    prov = aspects.get("source-provenance", {})

    lob_list = [
        f"`{item.get('lookup_id')}` ({item.get('lookup_value')})"
        for item in tax.get("lob_lookups", [])
    ]
    lob_str = ", ".join(lob_list) if lob_list else "None specified"

    func = tax.get("function_term", {})
    func_str = func.get("label", "N/A")
    if func.get("term_guid"):
        func_str += f" *(GUID: `{func.get('term_guid')}`, WSS ID: `{func.get('wss_id')}`)*"

    created_by = prov.get("created_by", {})
    created_str = f"{created_by.get('display_name', '')} &lt;{created_by.get('email', '')}&gt;".strip() or "N/A"
    modified_by = prov.get("last_modified_by", {})
    modified_str = f"{modified_by.get('display_name', '')} &lt;{modified_by.get('email', '')}&gt;".strip() or "N/A"

    comp_tag = gov.get("compliance_tags", {})
    tag_name = comp_tag.get("tag_name", "None")

    lines = [
        f"# {display_name}",
        f"",
        f"> **Document Asset** | Medallion Layer: `{medallion}` | Environment: `{env}` | Source System: `{system_name}`",
        f"",
        f"**Description:** {desc}",
        f"",
        f"---",
        f"",
        f"### 📂 Storage & Infrastructure",
        f"* **GCS Document URI:** `{doc_uri}`",
        f"* **GCS Metadata URI:** `{meta_uri}`",
        f"* **Storage Bucket:** `{prov.get('bucket_name', 'N/A')}`",
        f"* **Storage Path:** `{prov.get('storage_path', 'N/A')}`",
        f"* **File Size:** {prov.get('file_size_bytes', 0):,} bytes (UI Version: `{prov.get('ui_version', '1.0')}`)",
        f"",
        f"---",
        f"",
        f"### 🏷️ Business Taxonomy & Lookup Codes",
        f"* **Document Type Lookup ID:** `{tax.get('document_type_lookup_id', 'N/A')}`",
        f"* **Document Sub-Type Lookup ID:** `{tax.get('document_sub_type_lookup_id', 'N/A')}`",
        f"* **Lines of Business (LOB):** {lob_str}",
        f"* **Business Function:** {func_str}",
        f"* **KMH Short Codes:** {', '.join(tax.get('kmh_short_codes', [])) or 'None'}",
        f"* **Series:** {', '.join(tax.get('series', [])) or 'None'}",
        f"* **Service Sage Routing:** `{tax.get('in_service_sage', 'NO')}`",
        f"",
        f"---",
        f"",
        f"### 🛡️ Governance & Compliance",
        f"* **Data Classification:** `{gov.get('data_classification', 'Internal')}`",
        f"* **Governance Approval Status:** {'✅ APPROVED' if gov.get('governance_approved') else '⏳ PENDING'}",
        f"* **Governance Approval Timestamp:** `{gov.get('governance_approval_timestamp', 'N/A')}`",
        f"* **Business Certified:** `{gov.get('certified_business_approved', 'N/A')}`",
        f"* **SEC Rule 38a-1 Applicable:** `{'Yes' if gov.get('sec_rule_38a_1') else 'No'}`",
        f"* **Compliance Retention Tag:** `{tag_name}`",
        f"",
        f"---",
        f"",
        f"### 👤 Source Provenance & Authors",
        f"* **Origin System:** {prov.get('source_system', system_name)}",
        f"* **SharePoint Item ID:** `{prov.get('item_id', 'N/A')}`",
        f"* **SharePoint Site ID:** `{prov.get('site_id', 'N/A')}`",
        f"* **Web URL:** [{display_name}]({prov.get('source_web_url', '#')})",
        f"* **Created By:** {created_str} at `{prov.get('source_created_time', 'N/A')}`",
        f"* **Last Modified By:** {modified_str} at `{prov.get('source_modified_time', 'N/A')}`",
    ]

    return "\n".join(lines)


def generate_entry_labels(entry_core: Dict[str, Any], aspects: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Generates sanitized key-value labels for Dataplex search and faceted filtering.
    """
    gov = aspects.get("governance-compliance", {})
    tax = aspects.get("business-taxonomy", {})
    prov = aspects.get("source-provenance", {})

    labels = {
        "environment": sanitize_label_value(entry_core.get("environment", "dev")),
        "medallion_layer": sanitize_label_value(entry_core.get("medallion_layer", "bronze")),
        "source_system": sanitize_label_value(entry_core.get("source_system", "unstructured")),
        "data_classification": sanitize_label_value(gov.get("data_classification", "internal")),
        "governance_approved": "true" if gov.get("governance_approved") else "false",
        "file_format": sanitize_label_value(prov.get("doc_icon") or entry_core.get("file_extension", "doc")),
    }

    item_id = prov.get("item_id")
    if item_id:
        labels["item_id"] = sanitize_label_value(item_id)

    doc_type_id = tax.get("document_type_lookup_id")
    if doc_type_id:
        labels["doc_type_id"] = sanitize_label_value(doc_type_id)

    return labels


# =============================================================================
# JSON Parsing and Aspect Extraction Logic
# =============================================================================

def detect_source_system(raw_json: Dict[str, Any], default: str = "unstructured") -> str:
    """
    Dynamically determines the source system name from the metadata JSON,
    environment variables, or source indicators.
    """
    custom_fields = raw_json.get("customFields") or {}
    list_item_fields = (raw_json.get("listItem") or {}).get("fields") or {}
    explicit_system = (
        raw_json.get("source_system")
        or raw_json.get("sourceSystem")
        or custom_fields.get("source_system")
        or list_item_fields.get("source_system")
    )
    if explicit_system:
        return str(explicit_system).strip().lower().replace(" ", "_").replace("-", "_")

    # Heuristic detection for SharePoint / Microsoft Graph payloads
    if raw_json.get("parentReference", {}).get("siteId") or "sharepoint" in str(raw_json.get("webUrl", "")).lower():
        return "sharepoint"

    # Environment variable override if configured
    env_system = os.environ.get("DEFAULT_SOURCE_SYSTEM") or os.environ.get("SOURCE_SYSTEM")
    if env_system:
        return env_system.strip().lower().replace(" ", "_").replace("-", "_")

    return default


def resolve_document_and_metadata_uris(
    gcs_metadata_uri: str,
    file_name: str,
    explicit_document_uri: Optional[str] = None,
    source_system: str = "unstructured",
) -> Tuple[str, str, str, Dict[str, str]]:
    """
    Resolves:
    1. doc_gcs_uri (e.g. gs://bucket/path/file.docx)
    2. meta_gcs_uri (e.g. gs://bucket/path/file.docx.json)
    3. fqn (e.g. custom:<source_system>:<bucket>:<doc_path>)
    4. path_components dictionary (bucket, environment, medallion_layer, source_system, file_stem, file_ext)
    """
    clean_system = source_system.lower().replace(" ", "_").replace("-", "_")

    if explicit_document_uri and explicit_document_uri.startswith("gs://"):
        doc_gcs_uri = explicit_document_uri
        parts = explicit_document_uri[5:].split("/", 1)
        bucket = parts[0]
        doc_path = parts[1] if len(parts) > 1 else file_name
        fqn = f"custom:{clean_system}:{bucket}:{doc_path}"
        meta_gcs_uri = gcs_metadata_uri if gcs_metadata_uri else f"{explicit_document_uri}.json"
        path_components = parse_storage_uri_components(doc_gcs_uri)
        return doc_gcs_uri, meta_gcs_uri, fqn, path_components

    if gcs_metadata_uri and gcs_metadata_uri.startswith("gs://"):
        parts = gcs_metadata_uri[5:].split("/", 1)
        bucket = parts[0]
        raw_path = parts[1] if len(parts) > 1 else file_name

        if raw_path.endswith(".metadata.json"):
            doc_path = raw_path[:-14]
            meta_path = raw_path
        elif raw_path.endswith(".json") and any(
            raw_path.endswith(f".{ext}.json") for ext in ["docx", "pdf", "xlsx", "pptx", "txt", "csv", "doc", "rtf"]
        ):
            doc_path = raw_path[:-5]
            meta_path = raw_path
        elif raw_path.endswith(".json"):
            folder = os.path.dirname(raw_path)
            doc_path = f"{folder}/{file_name}" if folder else file_name
            meta_path = raw_path
        else:
            doc_path = raw_path
            meta_path = f"{raw_path}.json"

        doc_gcs_uri = f"gs://{bucket}/{doc_path}"
        meta_gcs_uri = f"gs://{bucket}/{meta_path}"
        fqn = f"custom:{clean_system}:{bucket}:{doc_path}"
        path_components = parse_storage_uri_components(doc_gcs_uri)
        return doc_gcs_uri, meta_gcs_uri, fqn, path_components
    else:
        clean_name = file_name.replace("/", ".").replace(" ", "_")
        doc_gcs_uri = explicit_document_uri or ""
        path_components = parse_storage_uri_components(doc_gcs_uri)
        return doc_gcs_uri, gcs_metadata_uri or "", f"custom:{clean_system}:{clean_name}", path_components


def parse_metadata_json(
    raw_json: Dict[str, Any],
    gcs_metadata_uri: str,
    gcs_document_uri: Optional[str] = None,
    source_system: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Parses document metadata JSON into:
    1. Enriched Entry core metadata (entry_id, display_name, description, fqn, overview, labels, container_id)
    2. Aspects dictionary keyed by Aspect Type short name.
    """
    system_name = source_system or detect_source_system(raw_json)
    custom_fields = raw_json.get("customFields") or {}
    list_item = raw_json.get("listItem") or {}
    list_item_fields = list_item.get("fields") or {}

    def get_field(key: str, default: Any = ""):
        return custom_fields.get(key, list_item_fields.get(key, raw_json.get(key, default)))

    item_id = str(get_field("id") or raw_json.get("id") or (list_item.get("id") if isinstance(list_item, dict) else "") or "")
    file_name = get_field("FileLeafRef") or raw_json.get("name") or "unnamed_file"
    description = get_field("_CheckinComment") or f"{system_name.title()} document {file_name}"

    doc_gcs_uri, meta_gcs_uri, fqn, path_components = resolve_document_and_metadata_uris(
        gcs_metadata_uri=gcs_metadata_uri,
        file_name=file_name,
        explicit_document_uri=gcs_document_uri,
        source_system=system_name,
    )

    env = path_components.get("environment", "dev")
    medallion = path_components.get("medallion_layer", "bronze")
    bucket = path_components.get("bucket", "")
    file_ext = path_components.get("file_extension", "")
    file_stem = path_components.get("file_stem") or file_name

    prefix = "sp" if system_name == "sharepoint" else (system_name[:4] if system_name != "unstructured" else "doc")
    entry_id = sanitize_dataplex_id(f"{prefix}-{file_stem}", 63)
    container_id = sanitize_dataplex_id(f"container-{env}-{medallion}-{system_name}", 63)

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
        "source_system": "SharePoint" if system_name == "sharepoint" else system_name.title(),
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
        "environment": env,
        "medallion_layer": medallion,
        "bucket_name": bucket,
        "storage_path": path_components.get("folder_path", ""),
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

    entry_core = {
        "entry_id": entry_id,
        "container_id": container_id,
        "display_name": file_name,
        "description": description,
        "fully_qualified_name": fqn,
        "source_system": system_name,
        "environment": env,
        "medallion_layer": medallion,
        "file_extension": file_ext,
        "gcs_document_uri": doc_gcs_uri,
        "gcs_metadata_uri": meta_gcs_uri,
    }

    # Generate Overview Markdown & Search Labels
    overview_markdown = generate_overview_markdown(entry_core, aspects)
    entry_labels = generate_entry_labels(entry_core, aspects)

    entry_core["overview"] = overview_markdown
    entry_core["labels"] = entry_labels

    return entry_core, aspects


def fqn_from_gcs_uri(gcs_uri: str, default_name: str) -> str:
    """Generates a Dataplex Fully Qualified Name (FQN) from a GCS URI or custom source."""
    _, _, fqn, _ = resolve_document_and_metadata_uris(gcs_uri, default_name)
    return fqn

