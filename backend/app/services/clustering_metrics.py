import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import silhouette_score, davies_bouldin_score
import logging

logger = logging.getLogger(__name__)

class ClusteringMetricsService:
    """Service to compute real clustering evaluation metrics dynamically."""

    @staticmethod
    def calculate_metrics(points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute clustering evaluation metrics using UMAP coordinates and HDBSCAN labels.
        
        Args:
            points: List of dicts containing 'umap_x', 'umap_y', 'cluster_id', 'confidence_score'
        """
        logger.info(f"Computing ML evaluation metrics for {len(points)} points...")

        if not points:
            return ClusteringMetricsService._empty_metrics()

        # Extract vectors
        coords = []
        labels = []
        confidences = []

        noise_count = 0
        total_points = len(points)
        valid_points = 0
        
        cluster_sizes = {}

        for p in points:
            # We must have valid coordinates
            if p.get("umap_x") is None or p.get("umap_y") is None:
                continue

            cid = int(p.get("cluster_id", -1))
            conf = float(p.get("confidence_score", 0.0))

            coords.append([p["umap_x"], p["umap_y"]])
            labels.append(cid)
            
            # HDBSCAN noise is -1
            if cid == -1:
                noise_count += 1
            else:
                confidences.append(conf)
                cluster_sizes[cid] = cluster_sizes.get(cid, 0) + 1
            
            valid_points += 1

        if valid_points == 0:
            return ClusteringMetricsService._empty_metrics()

        X = np.array(coords)
        y = np.array(labels)
        
        # Valid semantic points mask (exclude noise for metrics that require it)
        core_mask = y != -1
        X_core = X[core_mask]
        y_core = y[core_mask]

        # 1. Silhouette Score & 2. Davies-Bouldin Index (DBI)
        silhouette = None
        dbi = None
        
        if len(set(y_core)) > 1 and len(X_core) > 2:
            try:
                # Downsample for pairwise distance metrics (O(N^2)) to prevent freezing
                MAX_SAMPLES = 5000
                if len(X_core) > MAX_SAMPLES:
                    indices = np.random.choice(len(X_core), MAX_SAMPLES, replace=False)
                    X_sample = X_core[indices]
                    y_sample = y_core[indices]
                else:
                    X_sample = X_core
                    y_sample = y_core

                silhouette = float(silhouette_score(X_sample, y_sample))
                dbi = float(davies_bouldin_score(X_sample, y_sample))
            except Exception as e:
                logger.warning(f"Failed to compute clustering metrics: {e}")

        # 3. Noise Ratio
        noise_ratio = (noise_count / total_points) * 100 if total_points > 0 else 0.0

        # 4. Cluster Count
        cluster_count = len(set(y_core))

        # 5. Confidence Stats
        if confidences:
            conf_arr = np.array(confidences)
            mean_conf = float(np.mean(conf_arr)) * 100
            min_conf = float(np.min(conf_arr)) * 100
            max_conf = float(np.max(conf_arr)) * 100
            std_conf = float(np.std(conf_arr)) * 100
        else:
            mean_conf = min_conf = max_conf = std_conf = 0.0

        # 6. Cluster Size Distribution
        if cluster_sizes:
            sizes = list(cluster_sizes.values())
            largest_cluster = max(sizes)
            smallest_cluster = min(sizes)
            mean_cluster_size = float(np.mean(sizes))
        else:
            largest_cluster = smallest_cluster = mean_cluster_size = 0

        # Interpretation Helpers
        # Silhouette: > 0.5 Excellent, > 0.25 Good, > 0.0 Acceptable, < 0.0 Weak
        sil_label = "Weak"
        if silhouette is not None:
            if silhouette >= 0.5: sil_label = "Excellent"
            elif silhouette >= 0.25: sil_label = "Good"
            elif silhouette >= 0.0: sil_label = "Acceptable"
            
        # DBI: < 0.5 Excellent, < 1.0 Good, < 1.5 Acceptable, > 1.5 Weak (Lower is better)
        dbi_label = "Weak"
        if dbi is not None:
            if dbi <= 0.5: dbi_label = "Excellent"
            elif dbi <= 1.0: dbi_label = "Good"
            elif dbi <= 1.5: dbi_label = "Acceptable"

        return {
            "silhouette_score": round(silhouette, 4) if silhouette is not None else None,
            "silhouette_label": sil_label,
            "davies_bouldin_index": round(dbi, 4) if dbi is not None else None,
            "dbi_label": dbi_label,
            "noise_ratio": round(noise_ratio, 2),
            "cluster_count": cluster_count,
            "mean_confidence": round(mean_conf, 2),
            "min_confidence": round(min_conf, 2),
            "max_confidence": round(max_conf, 2),
            "confidence_std": round(std_conf, 2),
            "largest_cluster": largest_cluster,
            "smallest_cluster": smallest_cluster,
            "mean_cluster_size": round(mean_cluster_size, 1),
            "total_evaluated_points": total_points,
            "core_points": int(np.sum(core_mask))
        }

    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        return {
            "silhouette_score": None,
            "silhouette_label": "N/A",
            "davies_bouldin_index": None,
            "dbi_label": "N/A",
            "noise_ratio": 0.0,
            "cluster_count": 0,
            "mean_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "confidence_std": 0.0,
            "largest_cluster": 0,
            "smallest_cluster": 0,
            "mean_cluster_size": 0.0,
            "total_evaluated_points": 0,
            "core_points": 0
        }
