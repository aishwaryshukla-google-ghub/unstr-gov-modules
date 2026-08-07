import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

try:
    import functions_framework
except ImportError:
    class MockFunctionsFramework:
        @staticmethod
        def http(f):
            return f
    functions_framework = MockFunctionsFramework()

try:
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    google = None
    AuthorizedSession = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lakehouse-status-service")


def get_auth_session():
    """Initializes and returns an AuthorizedSession using Google Cloud credentials."""
    if not (google and AuthorizedSession):
        return None, None
    try:
        credentials, detected_proj = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return AuthorizedSession(credentials), detected_proj
    except Exception as e:
        logger.warning(f"Could not initialize Google Auth default session: {e}")
        return None, None


def describe_iceberg_table(
    catalog_name: str,
    namespace: str,
    table_name: str,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries verified BigLake Iceberg REST Catalog Table Describe endpoint:
    GET https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{project_id}/catalogs/{catalog_name}/namespaces/{namespace}/tables/{table_name}
    """
    session, detected_proj = get_auth_session()
    target_project = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
        or detected_proj
        or "nyl-pr-dbx-data-dev-01"
    )

    headers = {
        "x-goog-user-project": target_project,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    table_result = {
        "catalog_name": catalog_name,
        "namespace": namespace,
        "table_name": table_name,
        "described_successfully": False,
        "table_location": None,
        "columns_count": 0,
        "columns": [],
        "partition_specs": [],
        "current_snapshot_id": None,
        "raw_metadata": {},
        "api_endpoints_called": [],
        "error": None
    }

    if not session:
        table_result["error"] = "Google Cloud runtime credentials not available in local environment."
        return table_result

    # Exact Verified URL (Primary #1)
    primary_tbl_url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{target_project}/catalogs/{catalog_name}/namespaces/{namespace}/tables/{table_name}"
    table_result["api_endpoints_called"].append({"action": "describe_table", "url": primary_tbl_url})
    
    try:
        resp = session.get(primary_tbl_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            raw_json = resp.json()
            table_result["described_successfully"] = True
            table_result["raw_metadata"] = raw_json

            # Parse Iceberg schema & columns
            metadata = raw_json.get("metadata") or raw_json
            table_result["table_location"] = metadata.get("location")
            table_result["current_snapshot_id"] = metadata.get("current-snapshot-id") or metadata.get("currentSnapshotId")
            table_result["partition_specs"] = metadata.get("partition-specs") or metadata.get("partitionSpecs") or []

            schema = metadata.get("schema") or (metadata.get("schemas", [{}])[0] if metadata.get("schemas") else {})
            fields = schema.get("fields", [])
            
            parsed_cols = []
            for f in fields:
                parsed_cols.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "type": str(f.get("type")),
                    "required": f.get("required", False),
                    "doc": f.get("doc", "")
                })
            
            table_result["columns"] = parsed_cols
            table_result["columns_count"] = len(parsed_cols)
            table_result["error"] = None
        else:
            table_result["error"] = f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        table_result["error"] = f"Exception querying {primary_tbl_url}: {str(e)}"

    return table_result


def list_catalog_namespaces_and_tables(
    catalog_name: str,
    project_id: Optional[str] = None,
    specific_namespace: Optional[str] = None,
    describe_table_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive Inspector for BigLake Iceberg REST Catalog using EXACT Verified Endpoints:
    1. Management Status:
       GET https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/{project}/catalogs/{catalog}?alt=json
    2. Namespaces List:
       GET https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{project}/catalogs/{catalog}/namespaces
    3. Tables List:
       GET https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{project}/catalogs/{catalog}/namespaces/{namespace}/tables
    4. Table Describe:
       GET https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{project}/catalogs/{catalog}/namespaces/{namespace}/tables/{table}
    """
    session, detected_proj = get_auth_session()
    
    target_project = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
        or detected_proj
        or "nyl-pr-dbx-data-dev-01"
    )

    headers = {
        "x-goog-user-project": target_project,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "project_id": target_project,
        "catalog_name": catalog_name,
        "catalog_metadata": {},
        "namespaces_count": 0,
        "namespaces": [],
        "tables_count": 0,
        "tables": {},
        "table_descriptions": {},
        "refresh_status": {},
        "api_endpoints_called": [],
        "errors": []
    }

    if not session:
        result["errors"].append("Google Cloud runtime credentials not available in local environment.")
        primary_ns = specific_namespace or "ingest_oracle_orau11_ac0101"
        target_tbl = describe_table_name or "addresses"
        result["namespaces"] = [primary_ns]
        result["namespaces_count"] = 1
        result["tables"] = {primary_ns: [target_tbl]}
        result["tables_count"] = 1
        result["table_descriptions"][f"{primary_ns}.{target_tbl}"] = {
            "catalog_name": catalog_name,
            "namespace": primary_ns,
            "table_name": target_tbl,
            "described_successfully": False,
            "columns": [],
            "error": "Google Cloud credentials not available in local environment."
        }
        return result

    # =========================================================================
    # Step 1: Query Catalog Metadata & Refresh Status (Management Extensions API)
    # =========================================================================
    cat_url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/{target_project}/catalogs/{catalog_name}?alt=json"
    result["api_endpoints_called"].append({"action": "get_catalog_management", "url": cat_url})
    
    try:
        cat_resp = session.get(cat_url, headers=headers, timeout=15)
        if cat_resp.status_code == 200:
            cat_data = cat_resp.json()
            result["catalog_metadata"] = cat_data
            
            fed_options = cat_data.get("federated-catalog-options") or cat_data.get("federatedCatalogOptions") or {}
            result["refresh_status"] = fed_options.get("refresh-status") or fed_options.get("refreshStatus") or {}
            
            refresh_scope = fed_options.get("refresh-options", {}).get("refresh-scope", {})
            if "namespace-filters" in refresh_scope and not specific_namespace:
                filters = refresh_scope.get("namespace-filters", [])
                if filters:
                    specific_namespace = filters[0]
        else:
            result["errors"].append(f"Catalog management API returned HTTP {cat_resp.status_code}: {cat_resp.text}")
    except Exception as e:
        result["errors"].append(f"Failed to query catalog metadata: {str(e)}")

    # =========================================================================
    # Step 2: Query Namespaces List API (Exact Verified URL)
    # =========================================================================
    ns_url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{target_project}/catalogs/{catalog_name}/namespaces"
    result["api_endpoints_called"].append({"action": "list_namespaces", "url": ns_url})
    
    discovered_namespaces = []
    try:
        ns_resp = session.get(ns_url, headers=headers, timeout=15)
        if ns_resp.status_code == 200:
            ns_data = ns_resp.json()
            raw_namespaces = ns_data.get("namespaces", [])
            for item in raw_namespaces:
                if isinstance(item, list) and len(item) > 0:
                    discovered_namespaces.append(str(item[0]))
                elif isinstance(item, str):
                    discovered_namespaces.append(item)
        else:
            result["errors"].append(f"Namespaces API ({ns_url}) returned HTTP {ns_resp.status_code}: {ns_resp.text}")
    except Exception as e:
        result["errors"].append(f"Failed to query namespaces API: {str(e)}")

    if not discovered_namespaces and specific_namespace:
        discovered_namespaces = [specific_namespace]
    elif not discovered_namespaces:
        discovered_namespaces = ["ingest_oracle_orau11_ac0101"]

    result["namespaces"] = list(set(discovered_namespaces))
    result["namespaces_count"] = len(result["namespaces"])

    # =========================================================================
    # Step 3: Query Tables in each Namespace (Exact Verified URL)
    # =========================================================================
    total_tables = 0
    tables_by_namespace = {}

    for ns in result["namespaces"]:
        tbl_url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{target_project}/catalogs/{catalog_name}/namespaces/{ns}/tables"
        result["api_endpoints_called"].append({
            "action": f"list_tables_in_{ns}",
            "url": tbl_url
        })
        
        tables_found = []
        try:
            tbl_resp = session.get(tbl_url, headers=headers, timeout=15)
            if tbl_resp.status_code == 200:
                tbl_data = tbl_resp.json()
                identifiers = tbl_data.get("identifiers", [])
                for ident in identifiers:
                    if isinstance(ident, dict) and "name" in ident:
                        tables_found.append(ident["name"])
                    elif isinstance(ident, str):
                        tables_found.append(ident)
            else:
                result["errors"].append(f"Tables API for namespace {ns} returned HTTP {tbl_resp.status_code}: {tbl_resp.text}")
        except Exception as e:
            result["errors"].append(f"Failed to query tables in {ns}: {str(e)}")

        tables_by_namespace[ns] = tables_found
        total_tables += len(tables_found)

    result["tables"] = tables_by_namespace
    result["tables_count"] = total_tables

    # =========================================================================
    # Step 4: Describe Target Table Schema & Columns (Exact Verified URL)
    # =========================================================================
    target_table_to_describe = describe_table_name or "addresses"
    primary_ns = specific_namespace or (result["namespaces"][0] if result["namespaces"] else "ingest_oracle_orau11_ac0101")

    desc = describe_iceberg_table(
        catalog_name=catalog_name,
        namespace=primary_ns,
        table_name=target_table_to_describe,
        project_id=target_project
    )
    result["table_descriptions"][f"{primary_ns}.{target_table_to_describe}"] = desc

    return result


@functions_framework.http
def retrieve_llm_result(request):
    """
    Cloud Run HTTP Entry Point:
    - Direct HTTP: ?catalog_name=lkhse_dev_builder_dataingestion_silver&namespace=ingest_oracle_orau11_ac0101&table_name=addresses
    - BigQuery SQL Remote Function: {"calls": [["lkhse_dev_builder_dataingestion_silver", "ingest_oracle_orau11_ac0101", "addresses"]]}
    """
    req_json = {}
    args = {}
    
    if hasattr(request, "get_json"):
        req_json = request.get_json(silent=True) or {}
    if hasattr(request, "args"):
        args = request.args

    # Flow A: BigQuery Remote Function Protocol (Batched SQL Queries)
    if "calls" in req_json:
        calls = req_json.get("calls", [])
        replies = []
        for call in calls:
            cat = str(call[0]).strip("\"' ") if len(call) > 0 and call[0] else "lkhse_dev_builder_dataingestion_silver"
            ns = str(call[1]).strip("\"' ") if len(call) > 1 and call[1] else "ingest_oracle_orau11_ac0101"
            tbl = str(call[2]).strip("\"' ") if len(call) > 2 and call[2] else "addresses"
            proj = str(call[3]).strip("\"' ") if len(call) > 3 and call[3] else None
            
            res = list_catalog_namespaces_and_tables(
                catalog_name=cat,
                project_id=proj,
                specific_namespace=ns,
                describe_table_name=tbl
            )
            replies.append(res)
            
        return (
            json.dumps({"replies": replies}, indent=2),
            200,
            {"Content-Type": "application/json"}
        )

    # Flow B: Direct HTTP REST API / Browser
    catalog_name = (
        args.get("catalog_name")
        or req_json.get("catalog_name")
        or "lkhse_dev_builder_dataingestion_silver"
    )
    namespace = args.get("namespace") or req_json.get("namespace") or "ingest_oracle_orau11_ac0101"
    table_name = args.get("table_name") or req_json.get("table_name") or "addresses"
    project_id = args.get("project_id") or req_json.get("project_id")

    result = list_catalog_namespaces_and_tables(
        catalog_name=catalog_name,
        project_id=project_id,
        specific_namespace=namespace,
        describe_table_name=table_name
    )
    
    return (
        json.dumps(result, indent=2),
        200,
        {"Content-Type": "application/json"}
    )


# Function entry point aliases
get_catalog_status = retrieve_llm_result
get_lakehouse_catalog_status = retrieve_llm_result
