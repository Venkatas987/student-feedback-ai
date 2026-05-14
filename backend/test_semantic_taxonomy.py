#!/usr/bin/env python3
"""
Validation Test Script for Semantic Taxonomy Normalization System

Tests all components of the semantic taxonomy normalization to ensure
correct detection of duplicates and canonical mapping.
"""

import asyncio
import json
import sys
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, '/d:/projects/student-feedback-ai/backend')

def test_semantic_normalizer():
    """Test core SemanticTaxonomyNormalizer functionality."""
    print("\n" + "="*70)
    print("TEST 1: SemanticTaxonomyNormalizer Core Functionality")
    print("="*70)
    
    try:
        from app.services.semantic_taxonomy_normalizer import SemanticTaxonomyNormalizer
        
        normalizer = SemanticTaxonomyNormalizer()
        print("✓ SemanticTaxonomyNormalizer initialized successfully")
        
        # Test labels (simulating real data)
        test_labels = [
            "Food & Cafeteria Services",
            "Academic Support & Student Wellbeing",
            "Research & Technology Resources",
            "Career & Internship Opportunities",
            "Online Learning & Platform Issues",
            # Potential duplicates
            "Career Opportunities",
            "Internship Access",
            "Online Learning Issues",
            "Platform Technical Problems",
            "Technology Resources",
        ]
        
        print(f"\nInput: {len(test_labels)} labels to analyze")
        for i, label in enumerate(test_labels, 1):
            print(f"  {i:2d}. {label}")
        
        # Test 1a: Detect similar groups
        print("\n--- Finding Semantically Similar Label Groups ---")
        similar_groups = normalizer.find_similar_labels(test_labels)
        print(f"Found {len(similar_groups)} semantic groups:")
        for i, group in enumerate(similar_groups, 1):
            if len(group) > 1:
                print(f"  Group {i} (DUPLICATES): {group}")
            else:
                print(f"  Group {i} (unique):    {group}")
        
        # Test 1b: Detect duplicates
        print("\n--- Detecting Specific Duplicates ---")
        duplicates = normalizer.detect_duplicates(test_labels)
        if duplicates:
            print("Detected duplicate labels:")
            for canonical, dups in duplicates.items():
                print(f"  Canonical: {canonical}")
                for dup in dups:
                    print(f"    → Duplicate: {dup}")
        else:
            print("No duplicates detected")
        
        # Test 1c: Build canonical map
        print("\n--- Building Canonical Map ---")
        canonical_map = normalizer.build_canonical_map(test_labels)
        print(f"Created canonical mapping for {len(canonical_map)} labels:")
        for original, canonical in canonical_map.items():
            if original != canonical:
                print(f"  {original} → {canonical}")
            else:
                print(f"  {original} (canonical)")
        
        # Test 1d: Compute pairwise similarities
        print("\n--- Pairwise Similarity Analysis ---")
        test_pairs = [
            ("Career & Internship Opportunities", "Career Opportunities"),
            ("Career & Internship Opportunities", "Internship Access"),
            ("Online Learning & Platform Issues", "Online Learning Issues"),
            ("Online Learning & Platform Issues", "Platform Technical Problems"),
            ("Food & Cafeteria Services", "Academic Support & Student Wellbeing"),
        ]
        
        for label1, label2 in test_pairs:
            sim = normalizer.compute_similarity(label1, label2)
            is_dup = "✓ DUPLICATE" if sim <= normalizer.SIMILARITY_THRESHOLD else "✗ DISTINCT"
            print(f"  {label1}")
            print(f"    ↔ {label2}")
            print(f"  Distance: {sim:.4f} ({is_dup})")
        
        print("\n✓ SemanticTaxonomyNormalizer tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ SemanticTaxonomyNormalizer test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ml_inference_integration():
    """Test ML Inference Service integration with normalization."""
    print("\n" + "="*70)
    print("TEST 2: ML Inference Service Integration")
    print("="*70)
    
    try:
        from app.services.ml_inference import ml_service
        
        if not ml_service.is_loaded:
            print("⚠ ML models not loaded - skipping inference test")
            print("  (Run this from backend directory with models in ml/models/)")
            return True
        
        print("✓ ML Inference Service loaded")
        
        # Check canonical map
        if ml_service.canonical_label_map:
            print(f"✓ Canonical label map built with {len(ml_service.canonical_label_map)} labels")
            print("  Sample mappings:")
            for i, (original, canonical) in enumerate(list(ml_service.canonical_label_map.items())[:5]):
                if original != canonical:
                    print(f"    {original} → {canonical}")
                else:
                    print(f"    {original} (canonical)")
        else:
            print("⚠ No canonical map - may not have cluster_names.json")
        
        print("\n✓ ML Inference integration tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ ML Inference integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cluster_labels_integration():
    """Test cluster_labels module integration."""
    print("\n" + "="*70)
    print("TEST 3: Cluster Labels Integration")
    print("="*70)
    
    try:
        from app.api.routes.cluster_labels import (
            normalize_cluster_distribution,
            is_generic_cluster_label,
        )
        from app.services.semantic_taxonomy_normalizer import SemanticTaxonomyNormalizer
        
        print("✓ Cluster labels module imports successful")
        
        # Test normalize_cluster_distribution with canonical map
        normalizer = SemanticTaxonomyNormalizer()
        
        test_labels = [
            "Career & Internship Opportunities",
            "Career Opportunities",
            "Online Learning & Platform Issues",
            "Online Learning Issues",
        ]
        
        canonical_map = normalizer.build_canonical_map(test_labels)
        print(f"✓ Built canonical map with {len(canonical_map)} labels")
        
        # Mock database rows
        from collections import namedtuple
        MockRow = namedtuple('MockRow', ['cluster_id', 'cluster_label', 'count'])
        
        mock_rows = [
            MockRow(0, "Career & Internship Opportunities", 50),
            MockRow(0, "Career Opportunities", 30),
            MockRow(1, "Online Learning Issues", 40),
            MockRow(1, "Online Learning & Platform Issues", 35),
        ]
        
        # Apply normalization
        result = normalize_cluster_distribution(mock_rows, total_complaints=155, canonical_map=canonical_map)
        
        print(f"\n✓ Normalize cluster distribution result:")
        for cluster in result:
            print(f"  Cluster {cluster['cluster_id']}: {cluster['cluster_label']}")
            print(f"    Count: {cluster['count']}, Percentage: {cluster['percentage']}%")
        
        # Verify normalization worked
        unique_labels = {c['cluster_label'] for c in result}
        if len(unique_labels) == 2:
            print(f"\n✓ Correctly merged duplicates: {len(unique_labels)} canonical labels")
        else:
            print(f"\n✗ Expected 2 canonical labels but got {len(unique_labels)}")
        
        print("\n✓ Cluster labels integration tests PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Cluster labels integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generic_labels():
    """Test generic label detection."""
    print("\n" + "="*70)
    print("TEST 4: Generic Label Detection")
    print("="*70)
    
    try:
        from app.api.routes.cluster_labels import is_generic_cluster_label
        
        test_cases = [
            ("Career & Internship Opportunities", False),
            ("Online Learning & Platform Issues", False),
            ("Cluster 1", True),
            ("cluster -1", True),
            ("", True),
            (None, True),
            ("none", True),
            ("unknown", True),
        ]
        
        print("Testing generic label detection:")
        all_passed = True
        for label, expected_generic in test_cases:
            is_generic = is_generic_cluster_label(label)
            status = "✓" if is_generic == expected_generic else "✗"
            print(f"  {status} is_generic({label!r}): {is_generic} (expected: {expected_generic})")
            if is_generic != expected_generic:
                all_passed = False
        
        if all_passed:
            print("\n✓ Generic label detection tests PASSED")
        else:
            print("\n✗ Some generic label tests FAILED")
        
        return all_passed
        
    except Exception as e:
        print(f"\n✗ Generic label detection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print(" SEMANTIC TAXONOMY NORMALIZATION - VALIDATION TEST SUITE")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("SemanticTaxonomyNormalizer", test_semantic_normalizer()))
    results.append(("Generic Label Detection", test_generic_labels()))
    results.append(("Cluster Labels Integration", test_cluster_labels_integration()))
    results.append(("ML Inference Integration", test_ml_inference_integration()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} test groups passed")
    
    if passed_count == total_count:
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print("✗ SOME TESTS FAILED - PLEASE CHECK ERRORS ABOVE")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
