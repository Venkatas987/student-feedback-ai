# app/api/routes/semantic_taxonomy.py
"""
Semantic Taxonomy Management Endpoints

Exposes information about detected semantic duplicates and the canonical
taxonomy normalization system. Used for monitoring and debugging.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.routes.cluster_labels import get_cluster_label_count_rows
from app.services.semantic_taxonomy_normalizer import get_semantic_taxonomy_normalizer
from app.services.ml_inference import ml_service

router = APIRouter()


@router.get("/normalization-status")
async def normalization_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get status of semantic taxonomy normalization system.
    
    Shows:
    - Detected semantic duplicates
    - Canonical label mappings
    - Cluster coverage
    """
    try:
        rows = await get_cluster_label_count_rows(db)
        
        # Extract all unique labels from database
        all_labels = list(dict.fromkeys(
            str(row.cluster_label or "").strip()
            for row in rows
            if row.cluster_label
        ))
        
        # Detect duplicates and build maps
        normalizer = get_semantic_taxonomy_normalizer()
        duplicates = normalizer.detect_duplicates(all_labels)
        canonical_map = normalizer.build_canonical_map(all_labels)
        
        return {
            "status": "active",
            "total_unique_labels": len(all_labels),
            "detected_duplicates": {
                canonical: duplicates_list
                for canonical, duplicates_list in duplicates.items()
                if duplicates_list
            },
            "canonical_map": canonical_map,
            "similarity_threshold": normalizer.SIMILARITY_THRESHOLD,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/semantic-similarity")
async def semantic_similarity(
    label1: str,
    label2: str,
) -> Dict[str, Any]:
    """
    Compute semantic similarity between two labels.
    
    Query params:
    - label1: First label
    - label2: Second label
    
    Returns:
    - similarity: Distance score (0=identical, 2=opposite)
    - are_duplicates: True if similarity <= threshold
    - threshold: Configured similarity threshold
    """
    normalizer = get_semantic_taxonomy_normalizer()
    similarity = normalizer.compute_similarity(label1, label2)
    
    return {
        "label1": label1,
        "label2": label2,
        "similarity_distance": round(similarity, 4),
        "are_duplicates": similarity <= normalizer.SIMILARITY_THRESHOLD,
        "threshold": normalizer.SIMILARITY_THRESHOLD,
    }


@router.get("/cluster-label-distribution")
async def cluster_label_distribution(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get distribution of raw cluster labels from database.
    Shows how many feedback items have each label before normalization.
    """
    rows = await get_cluster_label_count_rows(db)
    
    distribution = {}
    total = 0
    for row in rows:
        label = str(row.cluster_label or "").strip()
        count = int(row.count or 0)
        if label:
            distribution[label] = distribution.get(label, 0) + count
            total += count
    
    return {
        "total_feedback": total,
        "unique_labels": len(distribution),
        "label_distribution": distribution,
    }
