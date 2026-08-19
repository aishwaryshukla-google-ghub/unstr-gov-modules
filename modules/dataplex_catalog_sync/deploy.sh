#!/usr/bin/env bash
# =============================================================================
# Deployment Script for Dataplex Catalog Sync (Cloud Run Function / BigQuery Remote Function)
# =============================================================================
set -euo pipefail

# Configuration Defaults
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || echo "databricks-playground-497321")}"
REGION="${2:-us-central1}"
SERVICE_NAME="dataplex-catalog-sync"
SERVICE_ACCOUNT_NAME="dataplex-catalog-sync-sa"
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CONNECTION_ID="dataplex_catalog_conn"
BQ_DATASET="unstructured_governance"

echo "================================================================="
echo " 🚀 Deploying Dataplex Catalog Sync (Cloud Run Function / BQ UDF)"
echo " Project:    ${PROJECT_ID}"
echo " Region:     ${REGION}"
echo " Service:    ${SERVICE_NAME}"
echo " Connection: ${CONNECTION_ID}"
echo "================================================================="

# 1. Enable Required APIs
echo "[1/6] Enabling GCP APIs..."
gcloud services enable \
  dataplex.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create Service Account if not existing
echo "[2/6] Setting up Cloud Run Service Account (${SA_EMAIL})..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Dataplex Catalog Sync Service Account" \
    --project="${PROJECT_ID}"
fi

# 3. Grant Required Roles to Service Account
echo "[3/6] Assigning Dataplex & Storage IAM roles to ${SA_EMAIL}..."
ROLES=(
  "roles/dataplex.admin"
  "roles/dataplex.catalogEditor"
  "roles/storage.objectViewer"
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None >/dev/null
done

# 4. Deploy to Cloud Run (Functions Framework / Gen 2 compatible)
echo "[4/6] Deploying Cloud Run Service / Function..."
gcloud run deploy "${SERVICE_NAME}" \
  --source="." \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},LOCATION=${REGION}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=120s

# Get Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

# 5. Setup BigQuery Cloud Resource Connection
echo "[5/6] Ensuring BigQuery Connection '${CONNECTION_ID}' exists..."
if ! bq show --connection --location="${REGION}" --project_id="${PROJECT_ID}" "${CONNECTION_ID}" >/dev/null 2>&1; then
  echo "Creating BigQuery Cloud Resource connection '${CONNECTION_ID}' in ${REGION}..."
  bq mk --connection \
    --location="${REGION}" \
    --project_id="${PROJECT_ID}" \
    --connection_type=CLOUD_RESOURCE \
    "${CONNECTION_ID}" || true
fi

# Retrieve Connection Service Account
CONN_SA=$(bq show --format=json --connection --location="${REGION}" --project_id="${PROJECT_ID}" "${CONNECTION_ID}" 2>/dev/null | grep -o '"serviceAccountId": "[^"]*' | cut -d'"' -f4 || echo "")

if [ -n "${CONN_SA}" ]; then
  echo "Granting roles/run.invoker to BigQuery Connection SA (${CONN_SA})..."
  gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${CONN_SA}" \
    --role="roles/run.invoker" >/dev/null 2>&1 || true
fi

# 6. Update and Register BigQuery Remote Function DDL
echo "[6/6] Registering BigQuery Remote Function..."
sed -i.bak "s|endpoint = '.*'|endpoint = '${SERVICE_URL}'|g" remote_function.sql && rm -f remote_function.sql.bak

# Create dataset if not exists
bq mk --dataset --location="${REGION}" --project_id="${PROJECT_ID}" "${PROJECT_ID}:${BQ_DATASET}" >/dev/null 2>&1 || true

# Execute DDL
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" --location="${REGION}" < remote_function.sql || true

echo "================================================================="
echo " 🎉 Deployment & BigQuery Remote Function Setup Complete!"
echo " Service URL:             ${SERVICE_URL}"
echo " BigQuery Connection:     ${PROJECT_ID}.${REGION}.${CONNECTION_ID}"
echo " BigQuery Remote UDF:     \`${PROJECT_ID}.${BQ_DATASET}.sync_gcs_metadata_to_dataplex\`"
echo "================================================================="
