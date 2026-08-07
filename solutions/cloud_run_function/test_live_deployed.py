#!/usr/bin/env python3
"""
test_live_deployed.py

Tests the live deployed Cloud Run Function in Argolis:
URL: https://nyl-gov-cloud-run-func-ye5mmrnqfa-uk.a.run.app
"""

import sys
import json
import urllib.request
import urllib.error

# Ensure src root is in sys.path
sys.path.insert(0, "./src")
from services.auth_service import AuthService, get_ssl_context

FUNCTION_URL = "https://nyl-gov-cloud-run-func-ye5mmrnqfa-uk.a.run.app"
PROJECT_ID = "databricks-playground-497321"

def test_live_cloud_run():
    print("=" * 80)
    print(f"🚀 Testing Live Deployed Cloud Run Function in Argolis")
    print(f"   URL: {FUNCTION_URL}")
    print("=" * 80)

    # 1. Acquire Token
    token, _ = AuthService.get_bearer_token_and_project(PROJECT_ID)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Test BigQuery Batch Remote Function Mode
    md_path = "/tmp/live_test_summary.md"
    with open(md_path, "w") as f:
        f.write("# Q3 Cloud Resource Utilization\n\n| Cluster | CPU Usage | Memory Usage | Status |\n|---|---|---|---|\n| prod-databricks-01 | 78% | 64% | Healthy |\n| dev-biglake-catalog | 22% | 35% | Idle |\n")

    bq_payload = {
        "requestId": "bq-job-live-test-001",
        "caller": f"//bigquery.googleapis.com/projects/{PROJECT_ID}",
        "calls": [
            ["Extract all clusters and summarize their utilization health.", md_path]
        ]
    }

    print("\n📡 Sending BigQuery Remote UDF batch request to Cloud Run...")
    req = urllib.request.Request(
        FUNCTION_URL,
        data=json.dumps(bq_payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        ssl_ctx = get_ssl_context()
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=60) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            print("\n" + "-" * 60)
            print(f"✨ Cloud Run Function Response (HTTP {status}):")
            print("-" * 60)
            print(json.dumps(body, indent=2))
            print("-" * 60)
            print("🎉 SUCCESS: Live Cloud Run Function executed and returned extracted data!")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_live_cloud_run()
