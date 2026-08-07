#!/usr/bin/env python3
"""
test_live.py

Live test runner for Argolis Project: databricks-playground-497321
Tests:
1. Token & Project ID acquisition (AuthService).
2. Handlers (Markdown, CSV, Excel, PDF, Image).
3. Live Vertex AI invocation (Claude streamRawPredict & Gemini generateContent).
"""

import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_live")

# Ensure src root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from handlers.registry import registry
from services.auth_service import AuthService
from services.model_service import ModelService
from handlers.base import ProcessedContent


def test_auth(project_id: str):
    print("\n" + "=" * 70)
    print(f"🔑 [STEP 1/3] Testing GCP Authentication for Argolis: {project_id}")
    print("=" * 70)
    
    token, detected_proj = AuthService.get_bearer_token_and_project(project_id)
    print(f"✅ Auth Token Acquired: {token[:12]}...{token[-6:]} (Length: {len(token)})")
    print(f"✅ Target Project ID : {detected_proj}")
    return token, detected_proj


def test_handlers():
    print("\n" + "=" * 70)
    print("🛠️  [STEP 2/3] Testing Multi-Format Handlers & Dispatcher")
    print("=" * 70)

    # 1. Test Markdown / Text
    sample_md = b"# Q3 Financial Summary\n\n| Department | Budget | Spend |\n|---|---|---|\n| Engineering | $1.2M | $1.15M |\n| Product | $500K | $480K |\n\n> Note: All budgets on track."
    md_handler = registry.get_handler("summary.md")
    processed_md = md_handler.process(sample_md, "summary.md")
    print(f"✅ Markdown Handler: is_text={processed_md.is_text} | MIME={processed_md.mime_type}")
    print(f"   Sample Extracted Text Preview:\n   {processed_md.text_content.splitlines()[0]}")

    # 2. Test CSV
    sample_csv = b"item_id,description,quantity,unit_price\n101,Cloud Server Instance,5,120.50\n102,Storage Volume 1TB,10,25.00"
    csv_handler = registry.get_handler("inventory.csv")
    processed_csv = csv_handler.process(sample_csv, "inventory.csv")
    print(f"✅ CSV Handler     : is_text={processed_csv.is_text} | MIME={processed_csv.mime_type}")

    # 3. Test PDF (Passthrough)
    sample_pdf = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\nxref\n0 1\ntrailer << /Root 1 0 R >>\n%%EOF"
    pdf_handler = registry.get_handler("contract.pdf")
    processed_pdf = pdf_handler.process(sample_pdf, "contract.pdf")
    print(f"✅ PDF Handler     : converted_to_pdf={processed_pdf.converted_to_pdf} | Base64 Length={len(processed_pdf.base64_data)}")

    return processed_md


def test_live_claude(processed: ProcessedContent, project_id: str, location: str):
    print("\n" + "=" * 70)
    print(f"🤖 [STEP 3/3] Live Vertex AI Model Invocation")
    print(f"   Project: {project_id} | Location: {location}")
    print("=" * 70)

    prompt = "Extract all tabular line items, summarize total spending, and report if any department exceeded budget."

    # 1. Test Claude on Vertex AI (streamRawPredict)
    claude_model = "claude-opus-4-7"
    claude_location = "global"
    print(f"\n📡 Calling Claude on Vertex: {claude_model} (location: {claude_location} -> :streamRawPredict)...")
    try:
        claude_res = ModelService.invoke_model(
            processed=processed,
            prompt=prompt,
            project_id=project_id,
            location=claude_location,
            model_name=claude_model,
            max_tokens=2048
        )
        print("\n" + "-" * 50)
        print(f"✨ Claude Opus 4.7 Response ({claude_res.get('endpoint')}):")
        print("-" * 50)
        print(claude_res.get("extracted_text"))
        print("-" * 50)
        print(f"📊 Usage Metrics: {json.dumps(claude_res.get('usage', {}), indent=2)}")
    except Exception as e:
        print(f"⚠️ Claude on Vertex returned error: {e}")

    # 2. Test Gemini on Vertex AI (generateContent) with user's exact global publisher endpoint
    gemini_model = "gemini-3.5-flash"
    gemini_location = "global"
    print(f"\n📡 Calling Gemini on Vertex: {gemini_model} (location: {gemini_location} -> :generateContent)...")
    try:
        gemini_res = ModelService.invoke_model(
            processed=processed,
            prompt=prompt,
            project_id=project_id,
            location=gemini_location,
            model_name=gemini_model,
            max_tokens=2048
        )
        print("\n" + "-" * 50)
        print(f"✨ Gemini 2.5 Pro Response:")
        print("-" * 50)
        print(gemini_res.get("extracted_text"))
        print("-" * 50)
        print(f"📊 Usage Metadata: {json.dumps(gemini_res.get('usage', {}), indent=2)}")
    except Exception as e:
        print(f"⚠️ Gemini on Vertex returned error: {e}")


def test_bigquery_remote_udf_contract(project_id: str, location: str):
    print("\n" + "=" * 70)
    print("📊 [STEP 4/4] Testing Live BigQuery Remote Function Batch Contract")
    print("=" * 70)

    # 1. Create sample test files
    md_path = "/tmp/argolis_budget.md"
    with open(md_path, "w") as f:
        f.write("# Argolis Cloud Spending\n\n| Service | Q1 Budget | Q1 Actual |\n|---|---|---|\n| BigQuery | $40,000 | $38,500 |\n| Cloud Run | $15,000 | $12,200 |\n")

    csv_path = "/tmp/argolis_inventory.csv"
    with open(csv_path, "w") as f:
        f.write("sku,resource_name,count,unit_cost\n101,Standard Persistent Disk,20,4.50\n102,Cloud Storage Bucket,10,2.00\n")

    # 2. Mock BigQuery Remote Function Batch Request Payload
    class MockBigQueryRequest:
        def __init__(self, json_data):
            self._json = json_data
            self.args = {}
        def get_json(self, silent=True):
            return self._json

    bq_payload = {
        "requestId": "bq-job-12345-uuid",
        "caller": f"//bigquery.googleapis.com/projects/{project_id}/jobs/job_abc123",
        "calls": [
            ["Extract all services, budget, and actuals as a structured summary.", md_path],
            ["Extract all resource SKUs and total count.", csv_path]
        ]
    }

    print(f"📡 Simulating BigQuery SQL batch invocation with {len(bq_payload['calls'])} rows...")
    from main import process_unstructured_document
    response_tuple = process_unstructured_document(MockBigQueryRequest(bq_payload))
    response_json = response_tuple[0].get_json()

    print("\n" + "-" * 50)
    print("✨ BigQuery Remote UDF Response:")
    print("-" * 50)
    print(f"HTTP Status: {response_tuple[1]}")
    print(f"Replies count: {len(response_json.get('replies', []))}")
    for idx, reply in enumerate(response_json.get("replies", [])):
        print(f"\n--- Reply for Row {idx + 1} ---")
        print(reply)
    print("-" * 50)


def main():
    project_id = "databricks-playground-497321"
    location = "global"

    print(f"🚀 Starting Live End-to-End Test for Argolis Project: {project_id}")
    
    test_auth(project_id)
    processed_doc = test_handlers()
    test_live_claude(processed_doc, project_id, location)
    test_bigquery_remote_udf_contract(project_id, location)
    
    print("\n" + "=" * 70)
    print("🎉 Live Argolis Test Completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
