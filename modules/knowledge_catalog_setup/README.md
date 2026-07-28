```markdown
# Knowledge Catalog Setup Module

This module provisions the foundational enterprise data governance and storage architecture in Google Cloud Platform (GCP).
It sets up required APIs, a centralized Dataplex Lake, Medallion architecture zones (Bronze, Silver, Gold), an Enterprise Business Glossary with standard terms, and Dataplex Aspect Types for metadata tagging.

## Features

* **API Activation:** Enables Dataplex, Data Lineage, and Data Catalog APIs.
* **Dataplex Lake & Zones:** Creates a top-level data lake domain along with **Bronze** (Raw), **Silver** (Curated/Conformed), and **Gold** (Curated/Business-ready) zones.
* **Business Glossary:** Establishes a centralized glossary containing core governance terms (`Internal` and `Sensitive`).
* **Aspect Types:** Deploys custom schema metadata templates (`data-access-classification`) to enforce governance classification constraints on datasets.

## Usage

```hcl
module "knowledge_catalog_setup" {
  source     = "./modules/knowledge_catalog_setup"
  project_id = var.project_id
  region     = var.region
}