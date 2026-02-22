#!/usr/bin/env python3
"""
test_gcs_conn.py - ForestGuard GCS Connectivity Diagnostic Script

Uploads a 1KB test file to each of the 3 ForestGuard buckets:
  1. forestguard-images
  2. forestguard-reports
  3. forestguard-certificates

Reports the exact error (403 Forbidden, 404 Not Found, etc.) for each.

Usage:
    python scripts/test_gcs_conn.py

Requirements:
    pip install google-cloud-storage python-dotenv
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing anything else
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed, rely on env vars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gcs_diag")

# ─── Configuration ───────────────────────────────────────────────────────────

BUCKETS = {
    "images": os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
    "reports": os.environ.get("STORAGE_BUCKET_REPORTS", "forestguard-reports"),
    "certificates": os.environ.get(
        "STORAGE_BUCKET_CERTIFICATES", "forestguard-certificates"
    ),
}

PROJECT_ID = os.environ.get("GCS_PROJECT_ID")
CREDENTIALS_PATH = os.environ.get("GCS_SERVICE_ACCOUNT_JSON") or os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS"
)
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "gcs")

TEST_BLOB_KEY = "_diag/gcs_conn_test_{ts}.txt"
TEST_PAYLOAD = (
    b"ForestGuard GCS connectivity test - "
    + datetime.now(timezone.utc).isoformat().encode()
    + b"\n" * 50
)[:1024]  # exactly 1 KB


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _print_env_summary():
    """Print current environment configuration."""
    print("\n" + "=" * 72)
    print("  FORESTGUARD GCS CONNECTIVITY DIAGNOSTIC")
    print("=" * 72)
    print(f"  Timestamp       : {datetime.now(timezone.utc).isoformat()}")
    print(f"  STORAGE_BACKEND : {STORAGE_BACKEND}")
    print(f"  GCS_PROJECT_ID  : {PROJECT_ID or '❌ NOT SET'}")

    creds_display = "NOT SET"
    if CREDENTIALS_PATH:
        exists = Path(CREDENTIALS_PATH).exists() if CREDENTIALS_PATH else False
        creds_display = f"{CREDENTIALS_PATH} ({'✅ exists' if exists else '❌ NOT FOUND'})"
    print(f"  CREDENTIALS     : {creds_display}")

    # Check ADC fallback
    adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    adc_win = Path(os.environ.get("APPDATA", "")) / "gcloud" / "application_default_credentials.json"
    adc_exists = adc_path.exists() or adc_win.exists()
    adc_found = adc_path if adc_path.exists() else (adc_win if adc_win.exists() else None)
    print(f"  ADC Fallback    : {adc_found or '❌ NOT FOUND'} ({'✅' if adc_exists else '⚠️ run: gcloud auth application-default login'})")

    print()
    for label, bucket_name in BUCKETS.items():
        print(f"  Bucket ({label:>12}) : {bucket_name}")
    print("=" * 72 + "\n")


def _create_client():
    """Create GCS client with explicit error handling."""
    try:
        from google.cloud import storage
    except ImportError:
        return None, "DEPENDENCY_MISSING: google-cloud-storage not installed. Run: pip install google-cloud-storage"

    try:
        if CREDENTIALS_PATH and Path(CREDENTIALS_PATH).exists():
            client = storage.Client.from_service_account_json(
                CREDENTIALS_PATH, project=PROJECT_ID
            )
            logger.info("✅ Client created from service account JSON: %s", CREDENTIALS_PATH)
        else:
            client = storage.Client(project=PROJECT_ID)
            logger.info("✅ Client created using Application Default Credentials (ADC)")
        return client, None
    except Exception as e:
        error_type = type(e).__name__
        return None, f"{error_type}: {e}"


def _test_bucket(client, bucket_name: str, label: str) -> dict:
    """Test connectivity to a single bucket."""
    result = {
        "bucket": bucket_name,
        "label": label,
        "bucket_exists": False,
        "can_list": False,
        "can_write": False,
        "can_read": False,
        "can_delete": False,
        "uploaded_key": None,
        "error": None,
        "latency_ms": None,
    }

    start = time.monotonic()

    try:
        # 1) Check bucket exists
        bucket = client.bucket(bucket_name)
        result["bucket_exists"] = bucket.exists()
        if not result["bucket_exists"]:
            result["error"] = f"404 NOT FOUND: Bucket '{bucket_name}' does not exist or is not accessible"
            return result

        # 2) List objects (test read permission)
        try:
            blobs = list(bucket.list_blobs(max_results=1, prefix="_diag/"))
            result["can_list"] = True
        except Exception as e:
            result["error"] = f"LIST_FAILED ({type(e).__name__}): {e}"
            return result

        # 3) Upload test file
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        blob_key = TEST_BLOB_KEY.format(ts=ts)
        try:
            blob = bucket.blob(blob_key)
            blob.upload_from_string(TEST_PAYLOAD, content_type="text/plain")
            result["can_write"] = True
            result["uploaded_key"] = blob_key
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                result["error"] = f"403 FORBIDDEN: No write permission on bucket '{bucket_name}'"
            elif "404" in error_msg:
                result["error"] = f"404 NOT FOUND: {error_msg}"
            else:
                result["error"] = f"WRITE_FAILED ({type(e).__name__}): {e}"
            return result

        # 4) Read back
        try:
            data = blob.download_as_bytes()
            result["can_read"] = len(data) == len(TEST_PAYLOAD)
        except Exception as e:
            result["error"] = f"READ_FAILED ({type(e).__name__}): {e}"
            return result

        # 5) Clean up
        try:
            blob.delete()
            result["can_delete"] = True
        except Exception as e:
            result["error"] = f"DELETE_FAILED ({type(e).__name__}): {e}"
            # Not critical, file uploaded anyway

    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            result["error"] = f"403 FORBIDDEN: {error_msg}"
        elif "404" in error_msg:
            result["error"] = f"404 NOT FOUND: {error_msg}"
        elif "401" in error_msg:
            result["error"] = f"401 UNAUTHORIZED: {error_msg}"
        else:
            result["error"] = f"{type(e).__name__}: {e}"

    result["latency_ms"] = round((time.monotonic() - start) * 1000)
    return result


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    _print_env_summary()

    # Pre-flight checks
    if STORAGE_BACKEND == "local":
        print("⚠️  WARNING: STORAGE_BACKEND=local  → Workers use local filesystem, NOT GCS!")
        print("   Set STORAGE_BACKEND=gcs in .env to enable GCS uploads.\n")

    if not PROJECT_ID:
        print("❌ FATAL: GCS_PROJECT_ID not set. Cannot proceed.\n")
        sys.exit(1)

    # Create client
    client, error = _create_client()
    if error:
        print(f"❌ FATAL: Cannot create GCS client → {error}\n")
        sys.exit(1)

    # Test each bucket
    results = []
    for label, bucket_name in BUCKETS.items():
        print(f"🔍 Testing bucket: {bucket_name} ({label})...")
        res = _test_bucket(client, bucket_name, label)
        results.append(res)

        if res["error"]:
            print(f"   ❌ FAIL: {res['error']}")
        else:
            print(f"   ✅ PASS: exists={res['bucket_exists']} list={res['can_list']} "
                  f"write={res['can_write']} read={res['can_read']} "
                  f"delete={res['can_delete']} ({res['latency_ms']}ms)")
        print()

    # Summary
    passed = sum(1 for r in results if not r["error"])
    total = len(results)

    print("=" * 72)
    print(f"  RESULTS: {passed}/{total} buckets passed")
    print("=" * 72)

    for r in results:
        status = "✅ PASS" if not r["error"] else "❌ FAIL"
        print(f"  {status}  {r['label']:>12} → {r['bucket']}")
        if r["error"]:
            print(f"          Error: {r['error']}")
    print()

    # Recommendations
    if passed < total:
        print("📋 RECOMMENDED ACTIONS:")
        for r in results:
            if r["error"] and "403" in r["error"]:
                print(f"  → Bucket '{r['bucket']}': Grant 'Storage Object Admin' role to your service account")
            elif r["error"] and "404" in r["error"]:
                print(f"  → Bucket '{r['bucket']}': Create the bucket in GCS console (project: {PROJECT_ID})")
            elif r["error"] and "DEPENDENCY" in r["error"]:
                print(f"  → Run: pip install google-cloud-storage")
            elif r["error"] and "Credentials" in r["error"]:
                print(f"  → Run: gcloud auth application-default login")
                print(f"  → Or set GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json in .env")
        print()

    # Save JSON report
    artifacts_dir = PROJECT_ROOT / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    report_path = artifacts_dir / "gcs_conn_report.json"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": PROJECT_ID,
        "storage_backend": STORAGE_BACKEND,
        "credentials_path": CREDENTIALS_PATH,
        "results": results,
        "passed": passed,
        "total": total,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"📄 Full report saved to: {report_path}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
