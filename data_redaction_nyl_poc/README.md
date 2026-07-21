# data_redaction_nyl_poc

This folder contains the self-contained Terraform module and application source code for the NYL Data Redaction POC.

## Client Integration Instructions

To deploy this module in the client's environment (`nyl-ws2-gcp-data-platform`), place this `data_redaction_nyl_poc` directory into the client's `modules/` folder, and add the following block to the client's root `main.tf`:

```hcl
module "data_redaction_nyl_poc" {
  source = "./modules/data_redaction_nyl_poc"

  project_id            = "nyl-pr-dbx-data-dev-01"
  region                = "us-east4"
  service_account_email = var.deploy_sa_email
  dataset_id            = "test_dtst" # Uses client's existing dataset
}
```
