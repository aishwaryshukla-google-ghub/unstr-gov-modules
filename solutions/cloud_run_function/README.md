# Cloud Run Function Solution

This end-to-end Terraform solution provisions a **Cloud Run Function (Cloud Functions 2nd Gen)** infrastructure stack using the modular [`modules/cloud_run_function`](../../modules/cloud_run_function).

## Overview

The solution automates:
1. **Source Code Packaging**: Automatically zips the application source code in `./src` using `data.archive_file`.
2. **Artifact Staging**: Creates a secure Cloud Storage bucket (`uniform_bucket_level_access = true`) and uploads the versioned source ZIP object.
3. **Cloud Run Function Deployment**: Invokes the `cloud_run_function` module to deploy a 2nd Gen Cloud Run Function.
4. **IAM Invoker Access**: Grants HTTP invoker permissions to configured principals.

## Prerequisites

- Terraform `>= 1.3.0`
- GCP Provider `>= 7.39.0`
- Authenticated GCP credentials (`gcloud auth application-default login`) with appropriate IAM permissions:
  - `roles/cloudfunctions.developer` or `roles/cloudfunctions.admin`
  - `roles/run.admin`
  - `roles/storage.admin`
  - `roles/iam.serviceAccountUser`

## Directory Structure

```
solutions/cloud_run_function/
├── main.tf                 # Solution orchestration and module call
├── variables.tf            # Configurable solution input variables
├── outputs.tf              # Exported solution outputs
├── terraform.tfvars        # Default variables configuration
├── terraform.tfvars.sample # Sample template configuration
├── README.md               # Documentation
└── src/
    ├── main.py             # Python function handler code
    └── requirements.txt    # Python dependencies
```

## Quick Start

### 1. Initialize Terraform
```bash
terraform init
```

### 2. Review Execution Plan
```bash
terraform plan
```

### 3. Apply Configuration
```bash
terraform apply
```

### 4. Verify Deployment
Retrieve the output URL and invoke the function using `curl`:
```bash
FUNCTION_URL=$(terraform output -raw function_uri)
curl -X POST "${FUNCTION_URL}" -H "Content-Type: application/json" -d '{"name": "NYL Team"}'
```

## Customization

To deploy your custom Python, Node.js, or Go function:
1. Replace code in `./src/main.py` and dependencies in `./src/requirements.txt`.
2. Update `runtime` and `entry_point` in `terraform.tfvars`.
3. Re-run `terraform apply`.
