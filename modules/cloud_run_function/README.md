# Cloud Run Function Module (Cloud Functions 2nd Gen)

This domain module manages the creation, configuration, networking, and IAM access controls for **Cloud Run Functions (Cloud Functions 2nd Gen)** on Google Cloud Platform.

## Features

1. **Cloud Functions 2nd Gen Architecture**: Uses Eventarc and underlying Cloud Run infrastructure for higher concurrency, improved cold-starts, and longer execution timeouts.
2. **Flexible Source Package Options**: Supports source deployment directly from Cloud Storage (GCS ZIP objects) or Cloud Source Repositories.
3. **Eventarc & HTTP Triggers**: Supports both direct HTTPS invocation and event-driven trigger patterns (Pub/Sub, GCS object events, Audit Logs).
4. **VPC & Security Integrations**: Supports Serverless VPC Access connectors, custom Artifact Registry docker repositories, Secret Manager environment variables, and execution service account bindings.
5. **Declarative IAM Access Control**: Built-in `invokers` variable mapping to grant HTTP invoker roles (`roles/cloudfunctions.invoker` or `roles/run.invoker`) to specified IAM principals.

## Usage Example

```hcl
module "cloud_run_function" {
  source        = "../../modules/cloud_run_function"
  project_id    = "my-gcp-project"
  region        = "us-east4"
  function_name = "nyl-sample-function"
  description   = "Sample HTTP Cloud Run Function"
  runtime       = "python311"
  entry_point   = "hello_world"

  storage_source = {
    bucket = "my-gcp-project-function-source-bucket"
    object = "src-v1.0.0.zip"
  }

  max_instance_count = 5
  min_instance_count = 0
  available_memory   = "512Mi"

  environment_variables = {
    ENV = "production"
  }

  invokers = [
    "allUsers"
  ]

  labels = {
    environment = "prod"
    managed_by  = "terraform"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| `project_id` | GCP Project ID | `string` | n/a | yes |
| `region` | GCP Region | `string` | `"us-east4"` | no |
| `function_name` | Name of the Cloud Run function | `string` | n/a | yes |
| `description` | Description of the function | `string` | `"Managed Cloud Run Function (2nd Gen)"` | no |
| `runtime` | Function runtime | `string` | `"python311"` | no |
| `entry_point` | Code entry point function name | `string` | `"main"` | no |
| `storage_source` | Object containing GCS bucket & object details | `object` | `null` | no |
| `repo_source` | Cloud Source Repositories object | `object` | `null` | no |
| `max_instance_count` | Maximum container instances | `number` | `10` | no |
| `min_instance_count` | Minimum container instances | `number` | `0` | no |
| `available_memory` | Memory allocation (e.g., 256Mi, 512Mi) | `string` | `"256Mi"` | no |
| `timeout_seconds` | Timeout in seconds | `number` | `60` | no |
| `environment_variables` | Map of runtime environment variables | `map(string)` | `{}` | no |
| `invokers` | List of IAM principals granted invoker access | `list(string)` | `[]` | no |
| `labels` | Resource labels | `map(string)` | `{ managed_by = "terraform" }` | no |

## Outputs

| Name | Description |
|------|-------------|
| `function_id` | Resource ID of the Cloud Run function |
| `function_name` | Name of the Cloud Run function |
| `function_uri` | HTTPS Endpoint URI of the deployed function |
| `cloud_run_service_name` | Underlying Cloud Run service name |
| `service_account_email` | Service account used by the function runtime |
| `state` | Status state of the function |
