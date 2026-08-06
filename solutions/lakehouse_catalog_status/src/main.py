import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
import functions_framework
from flask import jsonify, request
import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lakehouse-status-function")

# Default Environment Configuration
PROJECT_ID = os.environ.get("PROJECT_ID", "databricks-playground-497321")
DEFAULT_REGION = os.environ.get("REGION", "us-east4")


def get_field(data: Dict[str, Any], *keys: str, default=None) -> Any:
    """Helper to look up keys across various casing conventions."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


class BigLakeStatusClient:
    """Queries BigLake Iceberg Catalogs REST API."""
    BASE_REST_URL = "https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions"

    def __init__(self, project_id: str):
        self.project_id = project_id
        try:
            self.credentials, self.detected_project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self.session = AuthorizedSession(self.credentials)
            self.auth_available = True
        except Exception as e:
            logger.warning(f"Could not load Google Auth default credentials: {e}")
            self.session = None
            self.auth_available = False

    def describe_catalog(self, catalog_name: str, location: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        proj = project_id or self.project_id
        if not self.session:
            return {
                "name": f"projects/{proj}/catalogs/{catalog_name}",
                "catalog-type": "CATALOG_TYPE_FEDERATED",
                "error": "Google Auth credentials not available in environment",
            }

        primary_url = f"{self.BASE_REST_URL}/projects/{proj}/catalogs/{catalog_name}?alt=json"
        headers = {"X-Goog-User-Project": proj, "Accept": "application/json"}

        try:
            response = self.session.get(primary_url, headers=headers, timeout=12)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                last_error = f"Catalog '{catalog_name}' not found in project '{proj}' (HTTP 404)."
            else:
                last_error = f"BigLake Iceberg API returned {response.status_code}: {response.text}"
        except Exception as e:
            last_error = str(e)

        fallback_urls = [
            f"https://biglake.googleapis.com/v1/projects/{proj}/catalogs/{catalog_name}",
            f"https://biglake.googleapis.com/v1/projects/{proj}/locations/{location}/catalogs/{catalog_name}",
        ]

        for url in fallback_urls:
            try:
                res = self.session.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    return res.json()
            except Exception:
                pass

        return {
            "name": f"projects/{proj}/catalogs/{catalog_name}",
            "error": last_error or "Failed to retrieve catalog metadata",
        }

    def list_catalogs(self, location: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        proj = project_id or self.project_id
        if not self.session:
            return []

        primary_url = f"{self.BASE_REST_URL}/projects/{proj}/catalogs?alt=json"
        headers = {"X-Goog-User-Project": proj, "Accept": "application/json"}

        try:
            response = self.session.get(primary_url, headers=headers, timeout=12)
            if response.status_code == 200:
                return response.json().get("catalogs", [])
        except Exception as e:
            logger.warning(f"Error listing catalogs via REST API: {e}")
        return []


def inspect_bigquery_access(project_id: str, location: str, catalog_name: str) -> Dict[str, Any]:
    """Inspects BigQuery query engine connectivity and schema visibility."""
    try:
        client = bigquery.Client(project=project_id, location=location)
        start_time = time.time()
        
        info_schema_query = f"SELECT schema_name FROM `{project_id}.INFORMATION_SCHEMA.SCHEMATA` LIMIT 10"
        query_job = client.query(info_schema_query, location=location)
        results = list(query_job.result(timeout=10))
        latency = round((time.time() - start_time) * 1000, 2)
        
        return {
            "accessible_via_bigquery": True,
            "namespaces_found": [row.schema_name for row in results],
            "query_latency_ms": latency,
            "error_message": None,
        }
    except Exception as e:
        return {
            "accessible_via_bigquery": False,
            "namespaces_found": [],
            "query_latency_ms": None,
            "error_message": str(e),
        }


def evaluate_catalog_diagnostics(project_id: str, location: str, catalog_name: str, catalog_data: Dict[str, Any], bq_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generates structured diagnostics, health status, and remediation hints."""
    diagnostics = []
    troubleshooting = []

    # 1. Identity / Service Account
    sa_email = get_field(catalog_data, "biglake-service-account", "biglakeServiceAccount", "biglake_service_account")
    sa_id = get_field(catalog_data, "biglake-service-account-id", "biglakeServiceAccountId", "biglake_service_account_id")

    if sa_email:
        diagnostics.append({
            "name": "BigLake Service Agent Provisioned",
            "passed": True,
            "details": f"Service Account Email: {sa_email} | Numeric ID: {sa_id}",
        })
    else:
        diagnostics.append({
            "name": "BigLake Service Agent Provisioned",
            "passed": False,
            "details": "Service Agent is pending provisioning or not yet generated.",
        })
        troubleshooting.append("BigLake service account has not yet initialized.")

    # 2. Remote Federation Options
    fed_options = get_field(catalog_data, "federated-catalog-options", "federatedCatalogOptions", "federated_catalog_options", default={})
    unity_info = get_field(fed_options, "unity-catalog-info", "unityCatalogInfo", "unity_catalog_info")
    glue_info = get_field(fed_options, "glue-catalog-info", "glueCatalogInfo", "glue_catalog_info")

    fed_type = "unknown"
    unity_config = None
    glue_config = None

    if unity_info:
        fed_type = "unity"
        unity_config = {
            "instance_name": get_field(unity_info, "instance-name", "instanceName", "instance_name"),
            "catalog_name": get_field(unity_info, "catalog-name", "catalogName", "catalog_name"),
            "service_principal_application_id": get_field(unity_info, "service-principal-application-id", "servicePrincipalApplicationId", "service_principal_application_id"),
        }
        diagnostics.append({
            "name": "Databricks Unity Federation Config",
            "passed": bool(unity_config["instance_name"] and unity_config["catalog_name"]),
            "details": f"Host: {unity_config['instance_name']} | Remote Catalog: {unity_config['catalog_name']} | Client ID: {unity_config['service_principal_application_id']}",
        })
    elif glue_info:
        fed_type = "glue"
        glue_config = {
            "aws_account_id": get_field(glue_info, "warehouse", "glue_warehouse"),
            "aws_role_arn": get_field(glue_info, "role-arn", "roleArn", "glue_aws_role_arn"),
            "aws_region": get_field(glue_info, "aws-region", "awsRegion", "glue_aws_region"),
        }
        diagnostics.append({
            "name": "AWS Glue Federation Config",
            "passed": bool(glue_config["aws_account_id"] and glue_config["aws_role_arn"]),
            "details": f"AWS Account: {glue_config['aws_account_id']} | Role: {glue_config['aws_role_arn']}",
        })

    # 3. Refresh and Synchronization Status
    refresh_status = get_field(fed_options, "refresh-status", "refreshStatus", "refresh_status", default={})
    status_inner = get_field(refresh_status, "status", default={})
    sync_code = status_inner.get("code") if isinstance(status_inner, dict) else None
    sync_msg = status_inner.get("message") if isinstance(status_inner, dict) else None

    if sync_code is None or sync_code == 0:
        diagnostics.append({
            "name": "Metadata Refresh Status",
            "passed": True,
            "details": "Background metadata synchronization is active without errors.",
        })
    else:
        diagnostics.append({
            "name": "Metadata Refresh Status",
            "passed": False,
            "details": f"Refresh Code {sync_code}: {sync_msg}",
            "remediation_hint": f"Ensure the Databricks/AWS federation trust policy grants access to BigLake Service Account ({sa_email}).",
        })
        troubleshooting.append(f"Auth/Sync Error: {sync_msg}")

    # 4. BigQuery Accessibility Check
    if bq_status:
        diagnostics.append({
            "name": "BigQuery Region Alignment & Queryability",
            "passed": bq_status.get("accessible_via_bigquery", False),
            "details": f"Region: {location} | Query Latency: {bq_status.get('query_latency_ms')}ms",
        })

    # Overall Health Determination
    if not sa_email:
        health_status = "SYNCING"
        summary = f"Catalog '{catalog_name}' is currently initializing service agents."
    elif sync_code and sync_code != 0:
        health_status = "DEGRADED"
        summary = f"Catalog '{catalog_name}' is DEGRADED: {sync_msg}"
    elif bq_status and bq_status.get("accessible_via_bigquery"):
        health_status = "HEALTHY"
        summary = f"Catalog '{catalog_name}' is HEALTHY and accessible in BigQuery region '{location}'."
    else:
        health_status = "HEALTHY"
        summary = f"Catalog '{catalog_name}' configuration is active and provisioned."

    return {
        "project_id": project_id,
        "location": location,
        "catalog_name": catalog_name,
        "health_status": health_status,
        "federated_type": fed_type,
        "unity_config": unity_config,
        "glue_config": glue_config,
        "biglake_service_account": {
            "email": sa_email,
            "id": sa_id,
            "is_provisioned": bool(sa_email),
        },
        "sync_state": "ERROR" if (sync_code and sync_code != 0) else "ACTIVE",
        "last_sync_time": get_field(catalog_data, "update-time", "updateTime"),
        "bigquery_status": bq_status,
        "diagnostics": diagnostics,
        "summary_message": summary,
        "troubleshooting_steps": troubleshooting,
    }


@functions_framework.http
def get_lakehouse_catalog_status(http_request):
    """
    HTTP Entry point for Lakehouse Federated Catalog Status Cloud Run Function.
    Supports GET /status?catalog_name=... and POST JSON payloads.
    """
    # 1. Parse Arguments from query params or JSON body
    req_json = http_request.get_json(silent=True) or {}
    args = http_request.args

    catalog_name = args.get("catalog_name") or req_json.get("catalog_name") or "nyl_all_data_aws_dbricks_v2"
    location = args.get("location") or req_json.get("location") or DEFAULT_REGION
    project_id = args.get("project_id") or req_json.get("project_id") or PROJECT_ID
    check_bq = args.get("check_bigquery", "false").lower() == "true" or req_json.get("check_bigquery", False)
    action = args.get("action") or req_json.get("action") or "status"

    client = BigLakeStatusClient(project_id=project_id)

    # 2. Handle Action: List Catalogs
    if action == "list":
        catalogs = client.list_catalogs(location=location, project_id=project_id)
        return jsonify({
            "project_id": project_id,
            "location": location,
            "catalogs_count": len(catalogs),
            "catalogs": catalogs,
        }), 200

    # 3. Handle Action: Describe & Diagnose Catalog Status
    catalog_data = client.describe_catalog(catalog_name=catalog_name, location=location, project_id=project_id)
    
    bq_status = None
    if check_bq:
        bq_status = inspect_bigquery_access(project_id=project_id, location=location, catalog_name=catalog_name)

    result = evaluate_catalog_diagnostics(
        project_id=project_id,
        location=location,
        catalog_name=catalog_name,
        catalog_data=catalog_data,
        bq_status=bq_status,
    )

    return jsonify(result), 200
