terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "dataplex_data_products" {
  source        = "../../modules/dataplex/dataplex-data-product"
  project_id    = var.project_id
  data_products = var.data_products
}

module "dataplex_data_product_assets" {
  source              = "../../modules/dataplex/dataplex-data-product-asset"
  project_id          = var.project_id
  location            = var.location
  data_product_assets = var.data_product_assets
  depends_on          = [module.dataplex_data_products]
}
