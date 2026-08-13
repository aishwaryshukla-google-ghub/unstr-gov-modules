#!/usr/bin/env python3
"""
Test script to check entry groups in Argolis and verify data asset attachment formats.
"""
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

def main():
    token = get_bearer_token()
    project = "databricks-playground-497321"
    location = "us-central1"
    
    # 1. Query Entry Groups in Argolis
    url = f"https://dataplex.googleapis.com/v1/projects/{project}/locations/{location}/entryGroups"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    ctx = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Entry Groups:", json.dumps(data, indent=2))
    except Exception as e:
        print("Error fetching entry groups:", e)

    # 2. Check test asset validation against Dataplex Data Products API
    dp_name = f"projects/{project}/locations/us/dataProducts/patent-data-mart"
    asset_test_url = f"https://dataplex.googleapis.com/v1/{dp_name}/dataAssets"
    req = urllib.request.Request(asset_test_url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("\nExisting Data Assets on patent-data-mart:")
            for a in data.get("dataAssets", []):
                print(f" - {a.get('name')}: {a.get('resource')}")
    except Exception as e:
        print("Error fetching data assets:", e)

if __name__ == "__main__":
    main()
