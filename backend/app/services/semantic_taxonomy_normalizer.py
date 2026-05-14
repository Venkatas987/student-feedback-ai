# app/services/semantic_taxonomy_normalizer.py
"""
Semantic Taxonomy Normalization Service

Detects semantically similar cluster labels and normalizes them to canonical forms.
Uses deterministic semantic similarity (cosine distance on embeddings) to identify
duplicates and merge them into a single canonical label per semantic group.

This prevents duplicate institutional themes in dashboards and analytics.
"""

import logging
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class SemanticTaxonomyNormalizer:
    """
    Deterministic semantic taxonomy normalizer for cluster labels.
    
    Uses semantic embeddings to detect and merge similar labels into
    canonical forms. All operations are deterministic and reproducible.
    """
    
    # Similarity threshold (cosine distance) for considering labels as duplicates
    # Range: [0, 2]. Lower = stricter matching. 0.3 is ~moderate similarity
    SIMILARITY_THRESHOLD = 0.35
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize normalizer with semantic embedder."""
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required for SemanticTaxonomyNormalizer")
        
        self.model_name = model_name
        self.embedding_model = SentenceTransformer(model_name)
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
        self._canonical_map: Dict[str, str] = {}
        
        logger.info(f"SemanticTaxonomyNormalizer initialized with model: {model_name}")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get or compute embedding for text."""
        text_key = text.lower().strip()
        if text_key not in self._embedding_cache:
            self._embedding_cache[text_key] = self.embedding_model.encode(
                text_key,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        return self._embedding_cache[text_key]
    
    def _cosine_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine distance (1 - cosine_similarity).
        Range: [0, 2], where 0 = identical, 2 = opposite.
        """
        similarity = np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8
        )
        return float(1.0 - similarity)
    
    def compute_similarity(self, label1: str, label2: str) -> float:
        """
        Compute semantic similarity between two labels.
        Returns: cosine distance in range [0, 2].
        0 = identical, 0.5 ≈ moderate similarity, 2 = opposite.
        """
        key = (label1.lower().strip(), label2.lower().strip())
        
        if key in self._similarity_cache:
            return self._similarity_cache[key]
        
        # For same label (even different case)
        if key[0] == key[1]:
            similarity = 0.0
        else:
            emb1 = self._get_embedding(label1)
            emb2 = self._get_embedding(label2)
            similarity = self._cosine_distance(emb1, emb2)
        
        self._similarity_cache[key] = similarity
        return similarity
    
    def find_similar_labels(
        self,
        labels: List[str],
        threshold: Optional[float] = None
    ) -> List[List[str]]:
        """
        Group semantically similar labels together.
        
        Args:
            labels: List of label strings to cluster
            threshold: Similarity threshold (0.35 default, lower = stricter)
            
        Returns:
            List of clusters, each containing similar labels.
            Ordered by first occurrence in input list.
        """
        if threshold is None:
            threshold = self.SIMILARITY_THRESHOLD
        
        # Normalize labels
        unique_labels = list(dict.fromkeys(
            label.strip() for label in labels if label.strip()
        ))
        
        if len(unique_labels) <= 1:
            return [unique_labels]
        
        # Hierarchical clustering: greedily group similar labels
        clusters: List[List[str]] = []
        assigned = set()
        
        for i, label1 in enumerate(unique_labels):
            if label1 in assigned:
                continue
            
            cluster = [label1]
            assigned.add(label1)
            
            # Find all labels similar to label1
            for j, label2 in enumerate(unique_labels):
                if j <= i or label2 in assigned:
                    continue
                
                sim = self.compute_similarity(label1, label2)
                if sim <= threshold:
                    cluster.append(label2)
                    assigned.add(label2)
            
            clusters.append(cluster)
        
        return clusters
    
    def select_canonical_label(self, similar_labels: List[str]) -> str:
        """
        Select canonical label from a group of similar labels.
        
        Heuristics:
        1. Longest label (more descriptive)
        2. Alphabetically first (deterministic tie-breaker)
        """
        if not similar_labels:
            return ""
        
        if len(similar_labels) == 1:
            return similar_labels[0].strip()
        
        # Sort by length (descending), then alphabetically (ascending)
        sorted_labels = sorted(
            similar_labels,
            key=lambda x: (-len(x.strip()), x.lower().strip())
        )
        
        return sorted_labels[0].strip()
    
    def build_canonical_map(
        self,
        labels: List[str],
        threshold: Optional[float] = None
    ) -> Dict[str, str]:
        """
        Build mapping from all labels to their canonical form.
        
        Args:
            labels: List of all cluster labels
            threshold: Similarity threshold for grouping
            
        Returns:
            Dict[original_label -> canonical_label]
        """
        similar_clusters = self.find_similar_labels(labels, threshold)
        canonical_map = {}
        
        for cluster in similar_clusters:
            canonical = self.select_canonical_label(cluster)
            for label in cluster:
                canonical_map[label.strip()] = canonical
        
        self._canonical_map.update(canonical_map)
        return canonical_map
    
    def normalize_label(
        self,
        label: str,
        canonical_map: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Normalize a single label to its canonical form.
        
        Args:
            label: Label to normalize
            canonical_map: Optional pre-computed canonical map.
                          Falls back to internal map if not provided.
            
        Returns:
            Canonical label
        """
        normalized_label = label.strip() if label else ""
        
        if not normalized_label:
            return "Unclassified"
        
        # Use provided map or internal cache
        label_map = canonical_map if canonical_map is not None else self._canonical_map
        
        # Return mapped value or original if not in map
        return label_map.get(normalized_label, normalized_label)
    
    def normalize_labels(
        self,
        labels: List[str],
        canonical_map: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Normalize multiple labels."""
        return [self.normalize_label(label, canonical_map) for label in labels]
    
    def detect_duplicates(
        self,
        labels: List[str],
        threshold: Optional[float] = None
    ) -> Dict[str, List[str]]:
        """
        Detect semantically duplicate labels.
        
        Returns:
            Dict[canonical_label -> list of duplicates]
        """
        if threshold is None:
            threshold = self.SIMILARITY_THRESHOLD
        
        similar_clusters = self.find_similar_labels(labels, threshold)
        duplicates = {}
        
        for cluster in similar_clusters:
            if len(cluster) > 1:
                canonical = self.select_canonical_label(cluster)
                duplicates[canonical] = [
                    label for label in cluster if label != canonical
                ]
        
        return duplicates


# Singleton instance (lazy loaded)
_normalizer_instance: Optional[SemanticTaxonomyNormalizer] = None


def get_semantic_taxonomy_normalizer() -> SemanticTaxonomyNormalizer:
    """Get or create singleton normalizer instance."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = SemanticTaxonomyNormalizer()
    return _normalizer_instance
