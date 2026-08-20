#!/usr/bin/env python3
"""
test_live_deployed.py

Tests the live deployed Cloud Run Function in GCP:
- Automatically resolves the deployed Function URL from Terraform output or CLI argument.
- Obtains Google Cloud Auth Bearer Token.
- Tests BigQuery Remote Function batch invocation mode.
- Tests Direct REST HTTP JSON mode.
"""

import sys
import os
import json
import subprocess
import requests
import google.auth
import google.auth.transport.requests


def get_deployed_url(project_dir: str) -> str:
    """Retrieves the deployed function URL from terraform output."""
    try:
        res = subprocess.run(
            ["terraform", "output", "-raw", "dataplex_catalog_sync_function_uri"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        url = res.stdout.strip()
        if url and url.startswith("http"):
            return url
    except Exception as e:
        print(f"Warning: Could not get URL from terraform output: {e}")
    return ""


def get_auth_token(audience: str) -> str:
    """Acquires a Google OIDC ID Token for authenticating against Cloud Run."""
    try:
        from google.oauth2 import id_token
        auth_req = google.auth.transport.requests.Request()
        return id_token.fetch_id_token(auth_req, audience)
    except Exception:
        try:
            return subprocess.check_output(
                ["gcloud", "auth", "print-identity-token", f"--audiences={audience}"],
                text=True,
            ).strip()
        except Exception:
            return subprocess.check_output(
                ["gcloud", "auth", "print-identity-token"],
                text=True,
            ).strip()


def main():
    project_id = "databricks-playground-497321"
    location = "us-central1"
    entry_group_id = "shared-documents"
    sample_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_metadata.json"))

    # Resolve Function URL
    function_url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not function_url:
        root_tf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        function_url = get_deployed_url(root_tf_dir)

    if not function_url:
        print("❌ Error: Could not determine deployed Function URL. Please pass it as an argument:")
        print("   python test_live_deployed.py https://nyl-dataplex-catalog-sync-xxxxx-uc.a.run.app")
        sys.exit(1)

    print("=" * 80)
    print("🚀 TESTING LIVE DEPLOYED CLOUD RUN FUNCTION")
    print(f"   URL        : {function_url}")
    print(f"   Project    : {project_id}")
    print(f"   Location   : {location}")
    print(f"   Sample File: {sample_file}")
    print("=" * 80)

    token = get_auth_token(function_url)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # -------------------------------------------------------------------------
    # TEST 1: BigQuery Remote Function Mode (Batch Contract)
    # -------------------------------------------------------------------------
    print("\n📡 [1/2] Testing BigQuery Remote Function batch contract...")
    bq_payload = {
        "requestId": "bq-job-live-test-001",
        "caller": f"//bigquery.googleapis.com/projects/{project_id}",
        "calls": [
            [
                sample_file,
                "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx",
                project_id,
                location,
                entry_group_id,
            ]
        ],
    }

    try:
        resp = requests.post(function_url, json=bq_payload, headers=headers, timeout=120)
        print(f"✅ Response (HTTP {resp.status_code}):")
        body = resp.json()
        print(json.dumps(body, indent=2))
        assert "replies" in body, "Response missing 'replies' key"
        assert body["replies"][0].get("status") == "SUCCESS", "Batch row did not succeed"
        print("🎉 BigQuery Remote Function batch test succeeded!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # TEST 2: Direct REST JSON Mode
    # -------------------------------------------------------------------------
    print("\n📡 [2/2] Testing Direct REST JSON invocation...")
    rest_payload = {
        "gcs_metadata_uri": sample_file,
        "gcs_document_uri": "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx",
        "project_id": project_id,
        "location": location,
        "entry_group_id": entry_group_id,
    }

    try:
        resp = requests.post(function_url, json=rest_payload, headers=headers, timeout=120)
        print(f"✅ Response (HTTP {resp.status_code}):")
        body = resp.json()
        print(json.dumps(body, indent=2))
        assert body.get("status") == "SUCCESS", "REST sync did not succeed"
        print("🎉 Direct REST JSON invocation test succeeded!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✨ ALL LIVE DEPLOYED TESTS PASSED SUCCESSFULLY! ✨")
    print("=" * 80)


if __name__ == "__main__":
    main()
