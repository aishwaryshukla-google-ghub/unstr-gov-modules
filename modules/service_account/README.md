# Service Account Terraform Module

Provisions a Google Cloud Service Account with configurable project-level IAM roles.

## Usage

```hcl
module "service_account" {
  source       = "./modules/service_account"
  project_id   = "nyl-pr-dbx-data-dev-01"
  account_id   = "nyl-gov-func-sa"
  display_name = "NYL Unstructured Governance Function SA"
  description  = "Execution Service Account for NYL Unstructured Governance Cloud Run Function"

  project_roles = [
    "roles/logging.logWriter",
    "roles/bigquery.dataViewer",
    "roles/storage.objectAdmin"
  ]
}
```
