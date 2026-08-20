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

* **`src/main.py`**: Functions Framework HTTP entrypoint supporting BigQuery Remote Function batch calls (`{ "calls": [...] }`) and direct JSON POST.
* **`src/dataplex_catalog_manager.py`**: Core Dataplex Catalog REST API client, schema templates, and JSON parser/transformer.
* **`sample_metadata.json`**: Populated sample metadata JSON for testing.
* **`test_local.py`**: Unit test verifying JSON parsing and aspect payload mapping.
* **`test_live_argolis.py`**: End-to-end integration test against live Dataplex in GCP.
* **`test_live_deployed.py`**: HTTP test invoking the live deployed Cloud Run Function.
* **`remote_function.sql`**: BigQuery SQL DDL and usage examples.
* **`main.tf`** / **`variables.tf`** / **`outputs.tf`**: Standalone solution recipe deploying the Cloud Run Function.

---

## 1. Testing

```bash
# Run unit test
./virtual_envs/demo_dev_venv/bin/python3 experiments/unstr-gov-modules/solutions/dataplex_catalog_sync/test_local.py

# Run live Dataplex integration test
./virtual_envs/demo_dev_venv/bin/python3 experiments/unstr-gov-modules/solutions/dataplex_catalog_sync/test_live_argolis.py
```

---

## 2. Terraform Deployment

From the root of `experiments/unstr-gov-modules`:
```bash
# Deploy Cloud Run Function and BigQuery Remote Function
terraform apply -target=module.dataplex_catalog_sync -target=module.dataplex_catalog_sync_remote_function
```

---

## 3. Invocation via BigQuery Remote Function

Once deployed, register the function in BigQuery ([remote_function.sql](file:///Users/aishwaryshukla/Desktop/projects/google_cloud/80_percent/NYL/experiments/unstr-gov-modules/solutions/dataplex_catalog_sync/remote_function.sql)):

```sql
-- 1. Create Remote Function (accepts both metadata JSON and document URI)
CREATE OR REPLACE FUNCTION `unstructured_governance.sync_gcs_metadata_to_dataplex`(
  gcs_metadata_uri STRING,
  gcs_document_uri STRING, -- Optional: pass NULL to auto-derive from metadata JSON
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

-- 2. Invoke over an Object Table
SELECT 
  uri AS gcs_document_uri,
  `unstructured_governance.sync_gcs_metadata_to_dataplex`(
    CONCAT(uri, '.json'), -- metadata JSON URI
    uri,                  -- physical document URI
    'databricks-playground-497321',
    'us-central1',
    NULL
  ) AS sync_response
FROM `unstructured_governance.obj_tbl_documents`;
```
