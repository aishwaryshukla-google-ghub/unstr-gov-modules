# Dataplex Universal Catalog Sync for GCS / SharePoint Metadata

This service synchronizes rich, nested document metadata (from SharePoint / Microsoft Graph API stored in GCS) into **Google Cloud Dataplex Universal Catalog** (formerly Knowledge Catalog).

It dynamically creates/ensures:
1. **Entry Group:** `sharepoint_documents`
2. **Aspect Types:**
   - `governance_compliance`: Security classification, SEC 38a-1 flag, approvals, compliance tags.
   - `business_taxonomy`: Multi-tenant KMH short codes, Document Type IDs, LOB lookup lists, and Term Store hierarchy.
   - `source_provenance`: SharePoint site ID, Drive ID, Item ID, version, file hash, and author/editor profiles.
3. **Entry Type:** `sharepoint_document`
4. **Entries with attached Aspects:** Registered under `projects/{project}/locations/{location}/entryGroups/{entryGroup}/entries/{entryId}`.

---

## Directory Structure

* **`main.py`**: Dual-purpose entry point:
  * **HTTP Mode**: Cloud Run / Cloud Run Function handler supporting BigQuery Remote Function batch calls (`{ "calls": [...] }`) and direct JSON POST.
  * **CLI Mode**: `python main.py <gcs_uri_or_local_file>`
* **`dataplex_catalog_manager.py`**: Core Dataplex Catalog REST API client, schema templates, and JSON parser/transformer.
* **`sample_metadata.json`**: Populated sample metadata JSON for testing.
* **`test_local.py`**: Unit test verifying JSON parsing and aspect payload mapping.
* **`remote_function.sql`**: BigQuery SQL DDL to register the remote UDF and execute batch catalog sync queries.
* **`deploy.sh`**: One-click deployment script to Cloud Run.
* **`Dockerfile`** / **`requirements.txt`**: Container definition and Python dependencies.

---

## 1. Local Testing

```bash
# Run unit test
./virtual_envs/demo_dev_venv/bin/python3 experiments/unstr-gov-modules/modules/dataplex_catalog_sync/test_local.py

# Run live Argolis test
./virtual_envs/demo_dev_venv/bin/python3 experiments/unstr-gov-modules/modules/dataplex_catalog_sync/test_live_argolis.py
```

---

## 2. Deployment to Cloud Run Function / Cloud Run Service

Run the automated deployment script:
```bash
cd experiments/unstr-gov-modules/modules/dataplex_catalog_sync
chmod +x deploy.sh
./deploy.sh databricks-playground-497321 us-central1
```

Or deploy directly via `gcloud functions deploy` (CRF Gen 2):
```bash
gcloud functions deploy dataplex-catalog-sync \
  --gen2 \
  --region=us-central1 \
  --runtime=python311 \
  --source=. \
  --entry-point=bq_remote_function_handler \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=dataplex-catalog-sync-sa@databricks-playground-497321.iam.gserviceaccount.com
```

---

## 3. Invocation via BigQuery Remote Function

Once deployed, register the function in BigQuery ([remote_function.sql](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/modules/dataplex_catalog_sync/remote_function.sql)):

```sql
-- 1. Create Remote Function
CREATE OR REPLACE FUNCTION `unstructured_governance.sync_gcs_metadata_to_dataplex`(
  gcs_metadata_uri STRING,
  project_id STRING,
  location STRING,
  entry_group_id STRING -- Optional: pass NULL to auto-derive from metadata/bucket
)
RETURNS JSON
REMOTE WITH CONNECTION `us-central1.dataplex_catalog_conn`
OPTIONS (
  endpoint = 'https://dataplex-catalog-sync-YOUR_PROJECT_ID.us-central1.run.app',
  max_batching_rows = 10
);

-- 2. Invoke over an Object Table or URI list
SELECT 
  uri AS gcs_file_uri,
  `unstructured_governance.sync_gcs_metadata_to_dataplex`(
    CONCAT(uri, '.json'),
    'databricks-playground-497321',
    'us-central1',
    NULL
  ) AS sync_response
FROM `unstructured_governance.obj_tbl_documents`;
```
