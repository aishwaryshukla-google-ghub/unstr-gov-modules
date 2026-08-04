# Dataplex GCS Asset & Auto-Discovery Module

This module registers an existing Google Cloud Storage (GCS) bucket into a Dataplex Lake and Zone as an Asset, enabling automatic discovery, schema inference, and metadata cataloging across unstructured files.

## Features

* **Dataplex Asset Registration:** Links external GCS buckets to a designated Dataplex Lake/Zone.
* **Automated Metadata Cataloging:** Configures discovery scanning (e.g., hourly schedules) to automatically index incoming documents in Dataplex Catalog.

## Usage

```hcl
module "kc_assets_discovery" {
  source                = "./modules/kc_assets_discovery"
  project_id            = var.project_id
  region                = var.region
  lake_name             = module.knowledge_catalog_setup.lake_id
  zone_name             = module.knowledge_catalog_setup.zone_ids["bronze"]
  bucket_name           = var.raw_docs_bucket_name
  bucket_folder_prefix  = var.raw_docs_bucket_folder_path
  asset_id              = "unstructured-raw-data-asset"

  depends_on = [ module.knowledge_catalog_setup ]
}