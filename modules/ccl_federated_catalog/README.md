# Cross-Cloud Lakehouse (CCL) Federated Catalog Module

This domain capability module establishes a **Google Cloud BigLake Federated Catalog** bridge to external Databricks Unity Catalog instances (hosted on AWS or Azure), with native support for routing private S3 metadata and data scans over **Partner Cross-Cloud Interconnect (CCI)** via Service Directory.

## Capabilities

1. **Private Interconnect Service Directory Wiring**:
   - Ingests a Service Directory Service resource path (`projects/<p>/locations/<l>/namespaces/<n>/services/<s>`) that maps to an internal regional load balancer Virtual IP (VIP). When specified, BigLake routes all queries through this private bridge, keeping data traffic strictly off the public internet.
2. **OIDC & Secret Authentication References**:
   - Accepts references to existing authentication secrets (`secret_name`) or secretless OIDC identity federation application IDs (`unity_service_principal_application_id`).
3. **Automated Refresh Intervals & Filtering**:
   - Manages periodic background metadata synchronization of external Hive/Iceberg tables and namespace filtering.

## Usage Example

```hcl
module "databricks_federated_catalog" {
  source                       = "../../modules/ccl_federated_catalog"
  project_id                   = "my-gcp-data-project-01"
  region                       = "us-east4" # Must align with AWS Databricks workspace region
  service_directory_service_id = "projects/my-gcp-data-project-01/locations/us-east4/namespaces/ccl-ns/services/s3-private-service"

  federated_catalogs = {
    "dev-sales-catalog" = {
      catalog_name        = "aws_databricks_sales_prod"
      unity_instance_name = "my-org.cloud.databricks.com"
      unity_catalog_name  = "sales_lakehouse"
      refresh_interval    = "300s"
      secret_name         = "projects/my-gcp-data-project-01/locations/us-east4/secrets/databricks-unity-secret"
    }
  }
}
```

## Requirements
* `gcloud` CLI (alpha track available) installed in the deploying CI/CD environment.
* Databricks Unity Catalog metastore must have **External Data Access** enabled.
* Target Unity Catalog catalogs must utilize an **External Location on AWS S3** (default managed storage is explicitly unsupported by GCP Lakehouse).
