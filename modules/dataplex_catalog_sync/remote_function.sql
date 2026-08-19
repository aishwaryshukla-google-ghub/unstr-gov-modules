-- =============================================================================
-- BigQuery Remote Function Definition for Dataplex Universal Catalog Sync
-- =============================================================================
-- Prerequisites:
-- 1. Cloud Run Function or Cloud Run Service deployed (e.g. https://dataplex-catalog-sync-xxxxx-uc.a.run.app)
-- 2. BigQuery Cloud Resource Connection created and granted roles/run.invoker
-- =============================================================================

-- Step 1: Create BigQuery Connection (if not already existing)
-- Run via bq CLI or SQL:
-- CREATE EXTERNAL CONNECTION `us-central1.dataplex_catalog_conn`
-- OPTIONS (type = 'CLOUD_RESOURCE');

-- Step 2: Create Dataset
CREATE SCHEMA IF NOT EXISTS `unstructured_governance`
OPTIONS (location = 'us-central1');

-- Step 3: Register the BigQuery Remote Function
CREATE OR REPLACE FUNCTION `unstructured_governance.sync_gcs_metadata_to_dataplex`(
  gcs_metadata_uri STRING,
  project_id STRING,
  location STRING
)
RETURNS JSON
REMOTE WITH CONNECTION `us-central1.dataplex_catalog_conn`
OPTIONS (
  endpoint = 'https://dataplex-catalog-sync-YOUR_PROJECT_ID.us-central1.run.app',
  max_batching_rows = 10,
  user_defined_context = [("version", "1.0")]
);

-- =============================================================================
-- USAGE EXAMPLES
-- =============================================================================

-- Example A: Sync a single metadata file
SELECT `unstructured_governance.sync_gcs_metadata_to_dataplex`(
  'gs://my-nyl-documents-bucket/metadata/NYL_Compliance_Underwriting_Policy_2026.docx.json',
  'databricks-playground-497321',
  'us-central1'
) AS sync_result;

-- Example B: Batch sync all metadata files discovered in an Object Table
SELECT 
  uri AS gcs_file_uri,
  `unstructured_governance.sync_gcs_metadata_to_dataplex`(
    CONCAT(uri, '.json'),
    'databricks-playground-497321',
    'us-central1'
  ) AS catalog_sync_response
FROM `unstructured_governance.obj_tbl_documents`
WHERE ENDS_WITH(uri, '.docx') OR ENDS_WITH(uri, '.pdf');
