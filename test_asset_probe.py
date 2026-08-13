#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import ssl

def get_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl._create_unverified_context()

def get_bearer_token():
    adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(adc_path):
        try:
            with open(adc_path, "r") as f:
                creds = json.load(f)
            client_id = creds.get("client_id")
            client_secret = creds.get("client_secret")
            refresh_token = creds.get("refresh_token")
            if refresh_token and client_id and client_secret:
                token_url = "https://oauth2.googleapis.com/token"
                payload = urllib.parse.urlencode({
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }).encode("utf-8")
                req = urllib.request.Request(token_url, data=payload, method="POST")
                ctx = get_ssl_context()
                with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        return data.get("access_token")
        except Exception:
            pass
    return None

def test_asset_uri(resource_uri, test_asset_id="test-probe-asset"):
    token = get_bearer_token()
    project = "databricks-playground-497321"
    dp_name = f"projects/{project}/locations/us/dataProducts/patent-data-mart"
    url = f"https://dataplex.googleapis.com/v1/{dp_name}/dataAssets?dataAssetId={test_asset_id}"
    
    payload = {
        "resource": resource_uri
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    ctx = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✅ SUCCESS creating asset with URI:\n   {resource_uri}\n   Response: {json.dumps(data)}")
            # Cleanup
            delete_url = f"https://dataplex.googleapis.com/v1/{dp_name}/dataAssets/{test_asset_id}"
            del_req = urllib.request.Request(delete_url, headers={"Authorization": f"Bearer {token}"}, method="DELETE")
            urllib.request.urlopen(del_req, context=ctx, timeout=5)
            print("   Cleaned up test asset.")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        print(f"❌ FAILED for URI:\n   {resource_uri}\n   HTTP {e.code}: {err}")

def main():
    print("Testing Candidate URIs for Data Product Asset:\n")

    # Test 1: Dataplex Universal Catalog Entry format
    uri1 = "//dataplex.googleapis.com/projects/databricks-playground-497321/locations/us-central1/entryGroups/databricks/entries/federated-patent-table"
    test_asset_uri(uri1, "probe-entry-1")
    print("-" * 70)

    # Test 2: BigQuery Dataset format
    uri2 = "//bigquery.googleapis.com/projects/databricks-playground-497321/datasets/bqml_test_dtst"
    test_asset_uri(uri2, "probe-bq-dataset")
    print("-" * 70)

    # Test 3: BigQuery Table format
    uri3 = "//bigquery.googleapis.com/projects/databricks-playground-497321/datasets/bqml_test_dtst/tables/obj_tbl_pdf"
    test_asset_uri(uri3, "probe-bq-table")
    print("-" * 70)

if __name__ == "__main__":
    main()
