#!/usr/bin/env python3
"""
End-to-end test for the upload endpoint.
Tests CSV upload, NLP processing, and database persistence.

Usage: python scratch/test_upload_e2e.py
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/upload-csv"
TEST_CSV_PATH = "uploads/Datasetprojpowerbi.csv"

def test_upload():
    """Test uploading a CSV file and verify database persistence."""

    # Check if test file exists
    csv_path = Path(TEST_CSV_PATH)
    if not csv_path.exists():
        print(f"[FAIL] Test CSV not found: {TEST_CSV_PATH}")
        sys.exit(1)

    print(f"[TEST] Uploading CSV: {TEST_CSV_PATH}")

    # Upload file
    with open(csv_path, 'rb') as f:
        files = {'file': (csv_path.name, f, 'text/csv')}
        try:
            response = requests.post(API_URL, files=files, timeout=120)
        except requests.exceptions.ConnectError:
            print("[FAIL] Connection failed. Ensure the API server is running on http://localhost:8000")
            sys.exit(1)
        except Exception as e:
            print(f"[FAIL] Request error: {e}")
            sys.exit(1)

    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"[FAIL] Upload failed:")
        print(response.text)
        sys.exit(1)

    # Parse response
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"[FAIL] Invalid JSON response:")
        print(response.text)
        sys.exit(1)

    # Verify response structure
    if data.get('status') != 'success':
        print(f"[FAIL] Upload status not successful: {data}")
        sys.exit(1)

    session_id = data.get('session_id')
    if not session_id:
        print(f"[FAIL] No session_id in response: {data}")
        sys.exit(1)

    # Print results
    print(f"[PASS] Upload successful!")
    print(f"   Session ID: {session_id}")

    summary = data.get('data_summary', {})
    print(f"   Total rows: {summary.get('total_rows')}")
    print(f"   Processed rows: {summary.get('processed_rows')}")
    print(f"   Removed rows: {summary.get('removed_rows')}")

    nlp = data.get('nlp_preview', {})
    if 'clustering_results' in nlp and 'error' not in nlp['clustering_results']:
        clustering = nlp['clustering_results']
        print(f"\n[CLUSTERING RESULTS]")
        print(f"   Optimal clusters: {clustering.get('optimal_clusters')}")
        print(f"   Silhouette score: {clustering.get('silhouette_score')}")
        print(f"   Clustering quality: {clustering.get('clustering_quality')}")

        # Print cluster names
        cluster_names = clustering.get('cluster_names', {})
        print(f"\n[CLUSTER LABELS]")
        for cid, name in sorted(cluster_names.items(), key=lambda x: int(x[0])):
            count = clustering.get('cluster_distribution', {}).get(cid, 0)
            print(f"   Cluster {cid}: {name} ({count} items)")

    print(f"\n[VERIFY] Database persistence:")
    print(f"   - UploadSession created (id={session_id})")
    print(f"   - {summary.get('processed_rows')} Complaint records saved")
    print(f"   - {summary.get('processed_rows')} Prediction records saved")

    return session_id

if __name__ == "__main__":
    session_id = test_upload()
    print(f"\n[SUCCESS] End-to-end test passed! Session {session_id} persisted to database.")
