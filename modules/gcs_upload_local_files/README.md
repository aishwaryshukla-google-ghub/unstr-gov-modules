# This module uploads files from a local path to the requested bucket matching the standardized folder path

```hcl
module "gcs_upload_files" {
  source = "./modules/gcs_upload_local_files"
  
  gcs_bucket_to_upload  = var.raw_docs_bucket_name
  files_folder          = "${path.root}/unstruct_data"
  environment           = var.deploy_env
  files_source          = var.source_of_files
  files_owner_team      = var.owner_team_name
}