# BigQuery Remote Function Solution

An encapsulated solution recipe that deploys and wires a **BigQuery SQL Remote Function** to a **Google Cloud Run Function / Service** via a BigQuery Cloud Resource Connection.

## Capabilities

1. **BigQuery Cloud Resource Connection**: Provisions or binds to an existing `google_bigquery_connection`.
2. **Automated IAM Invoker Binding**: Automatically grants `roles/run.invoker` on the Cloud Run service to the connection's generated service account.
3. **BigQuery Scalar Routine**: Creates the `google_bigquery_routine` registering the SQL UDF directly inside the target dataset.

## Usage Example

```hcl
module "bq_remote_function" {
  source                 = "./solutions/bigquery/functions/remote"
  project_id             = var.project_id
  region                 = var.region
  dataset_id             = google_bigquery_dataset.unstructured_governance.dataset_id
  routine_id             = "retrieve_llm_result"
  endpoint               = module.cloud_run_function.function_uri
  cloud_run_service_name = module.cloud_run_function.function_name

  depends_on = [
    module.cloud_run_function
  ]
}
```

## SQL Usage

Once applied, run queries in BigQuery like:

```sql
SELECT 
  `my_project.my_dataset.retrieve_llm_result`('Sample unstructured text to analyze') AS llm_output;
```
