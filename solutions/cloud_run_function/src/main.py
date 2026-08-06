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
logger = logging.getLogger("lakehouse-status-crf")


def query_biglake_catalog(catalog_name: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Queries official Google BigLake Iceberg REST Catalog extensions endpoint."""
    detected_proj = None
    session = None
    
    if google and AuthorizedSession:
        try:
            credentials, detected_proj = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            session = AuthorizedSession(credentials)
        except Exception as e:
            logger.warning(f"Could not initialize Google Auth default session: {e}")

    target_project = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
        or detected_proj
        or "nyl-pr-dbx-data-dev-01"
    )

    url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/{target_project}/catalogs/{catalog_name}?alt=json"
    headers = {
        "x-goog-user-project": target_project,
        "Accept": "application/json"
    }

    if not session:
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "project_id": target_project,
            "catalog_name": catalog_name,
            "requested_url": url,
            "http_status": 401,
            "error": "Google Cloud credentials not available in local environment",
        }

    try:
        response = session.get(url, headers=headers, timeout=15)
        try:
            api_body = response.json()
        except Exception:
            api_body = response.text if response.text else "EMPTY"

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "project_id": target_project,
            "catalog_name": catalog_name,
            "requested_url": url,
            "http_status": response.status_code,
            "official_google_api_response": api_body
        }
    except Exception as e:
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "project_id": target_project,
            "catalog_name": catalog_name,
            "requested_url": url,
            "error": str(e)
        }


@functions_framework.http
def retrieve_llm_result(request):
    """
    HTTP Entry point for Cloud Run Function:
    - Supports query parameters: ?catalog_name=nyl_silver_catalog&project_id=...
    - Supports JSON body: {"catalog_name": "nyl_silver_catalog"}
    - Supports BigQuery Remote Function batch queries: {"calls": [["nyl_silver_catalog"]]}
    """
    req_json = {}
    args = {}
    
    if hasattr(request, "get_json"):
        req_json = request.get_json(silent=True) or {}
    if hasattr(request, "args"):
        args = request.args

    # Flow A: BigQuery Remote Function Protocol
    if "calls" in req_json:
        calls = req_json.get("calls", [])
        replies = []
        for call in calls:
            cat = str(call[0]).strip("\"' ") if len(call) > 0 and call[0] else "nyl_silver_catalog"
            proj = str(call[1]).strip("\"' ") if len(call) > 1 and call[1] else None
            replies.append(query_biglake_catalog(catalog_name=cat, project_id=proj))
        return (
            json.dumps({"replies": replies}, indent=2),
            200,
            {"Content-Type": "application/json"}
        )

    # Flow B: Direct HTTP / Browser / Monitoring API
    catalog_name = (
        args.get("catalog_name")
        or req_json.get("catalog_name")
        or "nyl_silver_catalog"
    )
    project_id = args.get("project_id") or req_json.get("project_id")

    result = query_biglake_catalog(catalog_name=catalog_name, project_id=project_id)
    return (
        json.dumps(result, indent=2),
        200,
        {"Content-Type": "application/json"}
    )


# Function entry point aliases
get_catalog_status = retrieve_llm_result
get_lakehouse_catalog_status = retrieve_llm_result
