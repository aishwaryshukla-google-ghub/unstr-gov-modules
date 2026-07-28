```markdown
# BigQuery Unstructured Data Module

# DISCLAIMER: THIS MODULE CURRENT STATE IS THOUGHT FOR LOCAL POC TESTING PURPOSES.
# IT SHOULD NOT BE PORTED AS IS TO NYL REPOSITORY! 

This module establishes the analytics bridge required to govern and query unstructured files (such as PDFs) stored in a Google Cloud Storage (GCS) bucket.
It provisions a secure Cloud Resource connection and an automated BigQuery Object Table.

## Features

* **BigQuery Dataset:** Creates a container dataset for metadata governance of unstructured documents.
* **BigQuery Connection:** Establishes a secure Cloud Resource connection to interact with GCS resources.
* **IAM Grant with Prefix Scope:** Automatically configures bucket-level `roles/storage.objectViewer` access for the connection service account.
* **BigQuery Object Table:** Provisions an external object table using a wildcard path (`*.pdf`) that automatically indexes all current and future PDF files without manual table updates.

## Usage

```hcl
module "unstructured_catalog" {
  source                = "./modules/bigquery_unstructured_data"
  project_id            = var.project_id
  region                = var.region
  bucket_name           = var.raw_docs_bucket_name
  documents_folder_path = var.raw_docs_bucket_folder_path
  dataset_id            = var.bq_raw_docs_dataset_id
  table_id              = var.bq_raw_docs_table_id
}