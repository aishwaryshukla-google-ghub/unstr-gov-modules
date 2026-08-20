import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dataplex_catalog_manager import (
    parse_metadata_json,
    parse_storage_uri_components,
    generate_overview_markdown,
    generate_entry_labels,
    get_governance_compliance_template,
    get_business_taxonomy_template,
    get_source_provenance_template,
)


class TestDataplexCatalogParser(unittest.TestCase):
    def setUp(self):
        sample_path = os.path.join(os.path.dirname(__file__), "sample_metadata.json")
        with open(sample_path, "r", encoding="utf-8") as f:
            self.sample_json = json.load(f)
        self.gcs_uri = "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx.json"

    def test_parse_metadata(self):
        entry_core, aspects = parse_metadata_json(self.sample_json, self.gcs_uri)

        # 1. Verify Entry Core (FQN points to the actual document file)
        self.assertEqual(entry_core["entry_id"], "sp-doc-7372")
        self.assertEqual(entry_core["display_name"], "NYL_Compliance_Underwriting_Policy_2026.docx")
        self.assertEqual(entry_core["fully_qualified_name"], "custom:sharepoint:my-nyl-documents-bucket:policies/NYL_Compliance_Underwriting_Policy_2026.docx")
        self.assertEqual(entry_core["gcs_document_uri"], "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx")
        self.assertEqual(entry_core["gcs_metadata_uri"], "gs://my-nyl-documents-bucket/policies/NYL_Compliance_Underwriting_Policy_2026.docx.json")

        # 2. Verify Overview Markdown is populated
        self.assertIn("overview", entry_core)
        self.assertIn("# NYL_Compliance_Underwriting_Policy_2026.docx", entry_core["overview"])
        self.assertIn("### 🏷️ Business Taxonomy & Lookup Codes", entry_core["overview"])
        self.assertIn("Retail Life & Annuities", entry_core["overview"])
        self.assertIn("### 🛡️ Governance & Compliance", entry_core["overview"])

        # 3. Verify Labels for Search are populated
        self.assertIn("labels", entry_core)
        self.assertEqual(entry_core["labels"]["source_system"], "sharepoint")
        self.assertEqual(entry_core["labels"]["data_classification"], "confidential")
        self.assertEqual(entry_core["labels"]["governance_approved"], "true")
        self.assertEqual(entry_core["labels"]["doc_type_id"], "7")
        self.assertEqual(entry_core["labels"]["item_id"], "7372")

        # 4. Verify Governance & Compliance Aspect
        gov = aspects["governance-compliance"]
        self.assertTrue(gov["governance_approved"])
        self.assertEqual(gov["governance_approval_timestamp"], "2026-08-10T23:03:23.386874Z")
        self.assertEqual(gov["data_classification"], "Confidential")
        self.assertFalse(gov["sec_rule_38a_1"])
        self.assertEqual(gov["certified_business_approved"], "APPROVED")
        self.assertEqual(gov["compliance_tags"]["tag_name"], "NYL_FINANCIAL_RETENTION_7YR")

        # 5. Verify Business Taxonomy Aspect & Lookup Codes
        tax = aspects["business-taxonomy"]
        self.assertEqual(tax["kmh_short_codes"], ["MMM", "LIS"])
        self.assertEqual(tax["document_type_lookup_id"], "7")
        self.assertEqual(tax["document_sub_type_lookup_id"], "48")
        self.assertEqual(len(tax["lob_lookups"]), 2)
        self.assertEqual(tax["lob_lookups"][0]["lookup_id"], 17)
        self.assertEqual(tax["lob_lookups"][0]["lookup_value"], "Retail Life & Annuities")
        self.assertEqual(tax["function_term"]["label"], "Actuarial Governance")
        self.assertEqual(tax["function_term"]["wss_id"], 8)

        # 6. Verify Source Provenance Aspect
        prov = aspects["source-provenance"]
        self.assertEqual(prov["source_system"], "SharePoint")
        self.assertEqual(prov["item_id"], "7372")
        self.assertEqual(prov["ui_version"], "7.0")
        self.assertEqual(prov["file_size_bytes"], 39023)
        self.assertEqual(prov["created_by"]["email"], "jane.doe@nyl.com")
        self.assertEqual(prov["last_modified_by"]["email"], "john.smith@nyl.com")
        self.assertEqual(prov["bucket_name"], "my-nyl-documents-bucket")
        self.assertEqual(prov["storage_path"], "policies")

        print("\n[SUCCESS] Local test passed! Overview Markdown Sample:")
        print("-" * 60)
        print(entry_core["overview"][:400] + "...\n(truncated for display)")
        print("-" * 60)
        print("Search Labels:", json.dumps(entry_core["labels"], indent=2))

    def test_parse_metadata_with_explicit_doc_uri(self):
        explicit_doc = "gs://custom-archive-bucket/dev/bronze/sharepoint/underwriting_v2.docx"
        entry_core, aspects = parse_metadata_json(
            self.sample_json,
            self.gcs_uri,
            gcs_document_uri=explicit_doc
        )
        self.assertEqual(entry_core["gcs_document_uri"], explicit_doc)
        self.assertEqual(entry_core["environment"], "dev")
        self.assertEqual(entry_core["medallion_layer"], "bronze")
        self.assertEqual(entry_core["container_id"], "container-dev-bronze-sharepoint")
        self.assertEqual(entry_core["fully_qualified_name"], "custom:sharepoint:custom-archive-bucket:dev/bronze/sharepoint/underwriting_v2.docx")
        self.assertEqual(aspects["source-provenance"]["gcs_document_uri"], explicit_doc)
        self.assertEqual(aspects["source-provenance"]["bucket_name"], "custom-archive-bucket")
        self.assertEqual(aspects["source-provenance"]["medallion_layer"], "bronze")
        self.assertEqual(aspects["source-provenance"]["storage_path"], "dev/bronze/sharepoint")

    def test_parse_storage_uri_components(self):
        uri = "gs://nyl-claims-data/prod/gold/claims_system/claim_summary_8819.parquet"
        comp = parse_storage_uri_components(uri)
        self.assertEqual(comp["bucket"], "nyl-claims-data")
        self.assertEqual(comp["environment"], "prod")
        self.assertEqual(comp["medallion_layer"], "gold")
        self.assertEqual(comp["source_system"], "claims_system")
        self.assertEqual(comp["file_name"], "claim_summary_8819.parquet")
        self.assertEqual(comp["file_stem"], "claim_summary_8819")
        self.assertEqual(comp["file_extension"], "parquet")


if __name__ == "__main__":
    unittest.main()

