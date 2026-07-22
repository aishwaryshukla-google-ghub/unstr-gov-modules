# -----------------------------------------------------------------------------
# BIGLAKE FEDERATED CATALOG (Databricks Unity Catalog Bridge)
# Manages the creation, schedule updates, and cleanup of external federated catalogs.
# -----------------------------------------------------------------------------
resource "terraform_data" "biglake_federated_catalogs" {
  for_each = var.federated_catalogs

  triggers_replace = [
    each.value.catalog_name,
    var.region,
    var.project_id,
    each.value.unity_instance_name,
    each.value.unity_catalog_name,
    var.service_directory_service_id != null ? var.service_directory_service_id : "PUBLIC",
    each.value.secret_name != null ? each.value.secret_name : "NONE",
    each.value.unity_service_principal_application_id != null ? each.value.unity_service_principal_application_id : (each.value.service_principal_application_id != null ? each.value.service_principal_application_id : "NONE"),
    join(",", try(each.value.namespace_filters, []))
  ]

  provisioner "local-exec" {
    command = <<EOT
      # Safely evaluate optional attributes using explicit HCL ternaries to support variable naming aliases without try() blindspots
      SECRET_VAL="${each.value.secret_name != null ? each.value.secret_name : ""}"
      OIDC_VAL="${each.value.unity_service_principal_application_id != null ? each.value.unity_service_principal_application_id : (each.value.service_principal_application_id != null ? each.value.service_principal_application_id : "")}"
      SD_VAL="${var.service_directory_service_id != null ? var.service_directory_service_id : ""}"

      # Assemble Secret or OIDC authentication reference flags
      SECRET_FLAG=""
      if [ -n "$SECRET_VAL" ] && [ -z "$OIDC_VAL" ]; then
        SECRET_FLAG="--secret-name=$SECRET_VAL"
      fi

      OIDC_FLAG=""
      if [ -n "$OIDC_VAL" ]; then
        OIDC_FLAG="--unity-service-principal-application-id=$OIDC_VAL"
      fi

      # Assemble Service Directory private routing flag for Partner/Dedicated CCI
      SD_FLAG=""
      if [ -n "$SD_VAL" ]; then
        SD_FLAG="--service-directory-name=$SD_VAL"
      fi

      # Assemble namespace filters if provided
      NS_FLAG=""
      if [ -n "${join(",", try(each.value.namespace_filters, []))}" ]; then
        NS_FLAG="--namespace-filters=${join(",", try(each.value.namespace_filters, []))}"
      fi

      if gcloud alpha biglake iceberg catalogs describe ${each.value.catalog_name} --project=${var.project_id} >/dev/null 2>&1; then
        echo "Catalog ${each.value.catalog_name} already exists. Updating refresh interval..."
        gcloud alpha biglake iceberg catalogs update ${each.value.catalog_name} \
          --project=${var.project_id} \
          --refresh-interval="${try(each.value.refresh_interval, "300s")}" || true
      else
        echo "Creating new BigLake federated catalog ${each.value.catalog_name} in ${var.region}..."
        gcloud alpha biglake iceberg catalogs create ${each.value.catalog_name} \
          --project=${var.project_id} \
          --primary-location=${var.region} \
          --catalog-type="federated" \
          --federated-catalog-type="unity" \
          --unity-instance-name="${each.value.unity_instance_name}" \
          --unity-catalog-name="${each.value.unity_catalog_name}" \
          --refresh-interval="${try(each.value.refresh_interval, "300s")}" \
          $SECRET_FLAG $OIDC_FLAG $SD_FLAG $NS_FLAG
      fi
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<EOT
      gcloud alpha biglake iceberg catalogs delete ${self.triggers_replace[0]} \
        --project=${self.triggers_replace[2]} \
        --quiet || true
    EOT
  }
}
