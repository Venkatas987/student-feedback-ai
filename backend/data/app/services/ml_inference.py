import os
import joblib
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.services.nlp_pipeline import NLPPipeline
from app.core.config import settings
from app.services.semantic_taxonomy_normalizer import get_semantic_taxonomy_normalizer

logger = logging.getLogger(__name__)

# Resolve base directory for model paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class MLInferenceService:
    """
    Inference-only service for processing student feedback using pre-trained models.
    
    Includes semantic taxonomy normalization to ensure consistent canonical labels
    and prevent duplicate institutional themes.
    """
    def __init__(self):
        self.pipeline = NLPPipeline()
        self.vectorizer = None
        self.svd = None
        self.kmeans = None
        self.cluster_names = {}
        self.canonical_label_map: Dict[str, str] = {}
        self.is_loaded = False
        
        self.model_path = os.path.join(BASE_DIR, "ml", "models")
        self._load_assets()

    def _load_assets(self):
        """
        Load pre-trained ML assets from the filesystem and build semantic canonical map.
        """
        try:
            vectorizer_path = os.path.join(self.model_path, "tfidf_vectorizer.pkl")
            svd_path = os.path.join(self.model_path, "svd_model.pkl")
            kmeans_path = os.path.join(self.model_path, "kmeans_model.pkl")
            cluster_names_path = os.path.join(self.model_path, "cluster_names.json")

            if not all(os.path.exists(p) for p in [vectorizer_path, svd_path, kmeans_path, cluster_names_path]):
                logger.error("One or more ML assets are missing in backend/ml/models/")
                return

            self.vectorizer = joblib.load(vectorizer_path)
            self.svd = joblib.load(svd_path)
            self.kmeans = joblib.load(kmeans_path)
            
            with open(cluster_names_path, "r") as f:
                self.cluster_names = json.load(f)
            
            # Build semantic canonical map to detect and merge duplicate themes
            self._build_canonical_map()
            
            self.is_loaded = True
            logger.info("ML assets loaded successfully for inference.")
        except Exception as e:
            logger.error(f"Failed to load ML assets: {str(e)}")
    
    def _build_canonical_map(self):
        """
        Build canonical map from cluster labels to detect semantic duplicates.
        Maps each label to its canonical form to prevent duplicate institutional themes.
        """
        try:
            # Extract all unique labels from cluster_names
            labels = [
                info.get("label", "")
                for info in self.cluster_names.values()
                if isinstance(info, dict) and info.get("label")
            ]
            
            if not labels:
                logger.warning("No labels found in cluster_names.json")
                return
            
            # Build semantic canonical map
            normalizer = get_semantic_taxonomy_normalizer()
            self.canonical_label_map = normalizer.build_canonical_map(labels)
            
            # Log detected duplicates for monitoring
            duplicates = normalizer.detect_duplicates(labels)
            if duplicates:
                logger.info(f"Detected semantic duplicates: {duplicates}")
            
            logger.info(f"Built canonical map with {len(self.canonical_label_map)} labels")
        except Exception as e:
            logger.warning(f"Failed to build canonical map: {str(e)}. Proceeding without semantic normalization.")

    def _get_canonical_cluster_label(self, cluster_id: int) -> str:
        """
        Get canonical cluster label for a cluster ID.
        Applies semantic normalization to prevent duplicate themes.
        
        Args:
            cluster_id: The cluster ID from prediction
            
        Returns:
            Canonical cluster label
        """
        # Get raw label from cluster_names
        raw_label = self.cluster_names.get(str(cluster_id), f"Cluster {cluster_id}")
        
        # Extract the actual label string
        if isinstance(raw_label, dict):
            raw_label = raw_label.get("label", f"Cluster {cluster_id}")
        
        # Apply canonical mapping if available
        canonical_label = self.canonical_label_map.get(
            str(raw_label).strip(),
            raw_label
        )
        
        return canonical_label

    def predict_single(self, text: str) -> Dict[str, Any]:
        """
        Predict cluster for a single text input with semantic normalization.
        
        Returns predictions with canonical cluster labels to prevent
        duplicate institutional themes in dashboards.
        """
        if not self.is_loaded:
            raise RuntimeError("ML models not loaded correctly.")

        # 1. Preprocess
        processed_text = self.pipeline._preprocess_text(text)
        if not processed_text:
            return {
                "cluster_id": -1,
                "cluster_label": "Unclassified",
                "confidence_score": 0.0,
                "processed_text": ""
            }

        # 2. Vectorize
        tfidf_vec = self.vectorizer.transform([processed_text])

        # 3. Dimensionality Reduction (SVD)
        dense_vec = self.svd.transform(tfidf_vec)

        # 4. Predict
        cluster_id = int(self.kmeans.predict(dense_vec)[0])
        
        # 5. Confidence Score (Distance-based)
        distances = self.kmeans.transform(dense_vec)[0]
        exp_dists = np.exp(-distances)
        confidence = float(exp_dists[cluster_id] / np.sum(exp_dists))
        
        # 6. Get canonical label (with semantic normalization)
        canonical_label = self._get_canonical_cluster_label(cluster_id)

        return {
            "cluster_id": cluster_id,
            "cluster_label": canonical_label,
            "confidence_score": round(confidence, 4),
            "processed_text": processed_text
        }

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Predict clusters for a batch of text inputs.
        """
        if not self.is_loaded:
            raise RuntimeError("ML models not loaded correctly.")

        results = []
        for text in texts:
            results.append(self.predict_single(text))
        return results

# Singleton instance
ml_service = MLInferenceService()
