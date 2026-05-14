# app/services/semantic_nlp_pipeline.py
# Semantic embedding-based NLP pipeline for student feedback analysis.
# Uses SentenceTransformers + UMAP + HDBSCAN for superior cluster quality.

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Tuple
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
import re
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import umap
    import hdbscan
except ImportError as e:
    logger.error(f"Missing semantic NLP dependencies: {e}")
    raise

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None


class SemanticNLPPipeline:
    """
    Advanced semantic NLP pipeline using embeddings for superior clustering.

    Pipeline:
    1. Text Preprocessing (cleaning, tokenization, lemmatization)
    2. Semantic Embedding (SentenceTransformer)
    3. Dimensionality Reduction (UMAP)
    4. Density-based Clustering (HDBSCAN)
    5. Topic Extraction & Labeling
    6. VADER sentiment (raw text)
    7. Evaluation Metrics
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize semantic NLP pipeline with pretrained embeddings model."""
        logger.info(f"Initializing SemanticNLPPipeline with model: {model_name}")

        self.model_name = model_name
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        logger.info(f"Embedding model loaded. Dimensions: {self.embedding_dim}")

        # Text preprocessing
        self.stop_words = set(stopwords.words('english'))
        self.domain_stopwords = {
            'student', 'students', 'university', 'college', 'campus',
            'issue', 'problem', 'really', 'very', 'school', 'like', 'just', 'also',
            'need', 'feel', 'make', 'one', 'would', 'get', 'cant', 'time',
            'ive', 'made', 'always', 'available', 'much', 'many', 'good', 'bad',
            'lot', 'even', 'can', 'please', 'thank', 'thanks', 'regards', 'best'
        }
        self.stop_words.update(self.domain_stopwords)
        self.lemmatizer = WordNetLemmatizer()

        # Models
        self.umap_model = None
        self.hdbscan_model = None

        if SentimentIntensityAnalyzer is not None:
            self._vader = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment analyzer initialized.")
        else:
            self._vader = None
            logger.warning("vaderSentiment not installed; sentiment will default to neutral.")


    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not isinstance(text, str):
            return ""

        text = text.lower()
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text: tokenize, remove stopwords, lemmatize."""
        cleaned = self._clean_text(text)
        if not cleaned:
            return ""

        tokens = word_tokenize(cleaned)
        processed_tokens = [
            self.lemmatizer.lemmatize(word)
            for word in tokens
            if word not in self.stop_words and len(word) > 2
        ]

        return " ".join(processed_tokens)

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate semantic embeddings for a list of texts.

        Args:
            texts: List of text strings

        Returns:
            numpy array of embeddings (n_samples, embedding_dim)
        """
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        logger.info(f"Embedding model: {self.model_name}")

        embeddings = self.embedding_model.encode(
            texts,
            batch_size=128,  # Increased batch size for faster processing
            show_progress_bar=False,
            convert_to_numpy=True
        )

        logger.info(f"Embeddings generated. Shape: {embeddings.shape}")
        logger.info(f"Embedding dimensions: {self.embedding_dim}")

        return embeddings

    def reduce_dimensions(self, embeddings: np.ndarray, n_neighbors: int = 15) -> np.ndarray:
        """
        Reduce embedding dimensions using UMAP to exactly 2D.

        Constrained to n_components=2 so that:
        - Clustering space == Visualization space == Evaluation metric space
        - umap_x and umap_y ARE the full coordinate space HDBSCAN uses
        - Silhouette/DBI metrics are computed on the same 2D manifold

        Args:
            embeddings: High-dimensional embeddings (e.g. 384-dim SentenceTransformer)
            n_neighbors: UMAP n_neighbors parameter

        Returns:
            2D reduced embeddings (n_samples, 2)
        """
        logger.info(f"Reducing dimensions with UMAP to 2D (n_neighbors={n_neighbors})...")

        # Clamp n_neighbors so it never exceeds dataset size - 1
        effective_neighbors = min(n_neighbors, max(3, len(embeddings) - 1))

        logger.info(f"Effective n_neighbors: {effective_neighbors}, n_components: 2 (fixed)")

        self.umap_model = umap.UMAP(
            n_neighbors=effective_neighbors,
            n_components=2,          # Fixed: clustering, visualization, metrics all in 2D
            metric='cosine',
            random_state=42,
            init='random',
            verbose=False
        )

        reduced = self.umap_model.fit_transform(embeddings)

        logger.info(f"Dimension reduction complete. Shape: {reduced.shape}")

        return reduced

    def cluster_embeddings(
        self,
        reduced_embeddings: np.ndarray,
        min_cluster_size: int = 5,
        min_samples: int = 3
    ) -> Tuple[np.ndarray, int]:
        """
        Cluster embeddings using HDBSCAN.

        Args:
            reduced_embeddings: Dimensionally reduced embeddings
            min_cluster_size: Minimum cluster size
            min_samples: Minimum samples in neighborhood

        Returns:
            Tuple of (cluster labels, number of clusters)
        """
        logger.info(f"Clustering with HDBSCAN (min_cluster_size={min_cluster_size})...")

        # Adjust parameters for small datasets
        effective_min_cluster_size = min(min_cluster_size, max(3, len(reduced_embeddings) // 3))
        effective_min_samples = min(min_samples, max(1, effective_min_cluster_size // 2))

        logger.info(f"Effective HDBSCAN parameters: min_cluster_size={effective_min_cluster_size}, min_samples={effective_min_samples}")

        self.hdbscan_model = hdbscan.HDBSCAN(
            min_cluster_size=effective_min_cluster_size,
            min_samples=effective_min_samples,
            cluster_selection_epsilon=0.0
        )

        labels = self.hdbscan_model.fit_predict(reduced_embeddings)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_outliers = list(labels).count(-1)

        logger.info(f"Clustering complete. Clusters: {n_clusters}, Outliers: {n_outliers}")

        return labels, n_clusters

    def extract_cluster_keywords(
        self,
        texts: List[str],
        labels: np.ndarray,
        embeddings: np.ndarray,
        top_k: int = 5
    ) -> Dict[int, List[str]]:
        """
        Extract representative keywords for each cluster using embeddings.

        Args:
            texts: Original texts
            labels: Cluster labels
            embeddings: Original embeddings
            top_k: Number of keywords to extract

        Returns:
            Dictionary mapping cluster_id to list of keywords
        """
        logger.info("Extracting cluster keywords...")

        keywords_per_cluster = {}
        clusters = set(labels)
        clusters.discard(-1)  # Ignore outliers

        for cluster_id in sorted(clusters):
            mask = labels == cluster_id
            cluster_texts = [texts[i] for i in range(len(texts)) if mask[i]]
            cluster_embeddings = embeddings[mask]

            if len(cluster_texts) == 0:
                continue

            # Find centroid
            centroid = cluster_embeddings.mean(axis=0)

            # Extract words from cluster texts
            words_freq = {}
            for text in cluster_texts:
                cleaned = self._clean_text(text).lower()
                tokens = word_tokenize(cleaned)
                for token in tokens:
                    if (token not in self.stop_words and
                            len(token) > 2 and
                            token.isalpha()):
                        words_freq[token] = words_freq.get(token, 0) + 1

            # Get top keywords by frequency
            sorted_words = sorted(
                words_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]

            keywords = [word for word, _ in sorted_words]
            keywords_per_cluster[cluster_id] = keywords

            logger.debug(f"Cluster {cluster_id}: {keywords}")

        return keywords_per_cluster

    def generate_semantic_labels(
        self,
        keywords_per_cluster: Dict[int, List[str]]
    ) -> Dict[int, Tuple[str, float]]:
        """
        Generate semantic labels for clusters using keywords and predefined categories.

        Args:
            keywords_per_cluster: Dictionary of cluster_id to keywords

        Returns:
            Dictionary mapping cluster_id to (label, confidence)
        """
        logger.info("Generating semantic labels...")

        categories = {
            "Technical Support": [
                'password', 'access', 'login', 'account', 'network', 'wifi',
                'internet', 'connection', 'email', 'server', 'system'
            ],
            "Hardware & Equipment": [
                'hardware', 'laptop', 'printer', 'mouse', 'keyboard', 'monitor',
                'install', 'setup', 'cable', 'screen', 'device'
            ],
            "Procurement & Budgeting": [
                'purchase', 'buy', 'order', 'software', 'license', 'approval',
                'budget', 'cost', 'procurement', 'request'
            ],
            "Infrastructure & Connectivity": [
                'network', 'wifi', 'internet', 'speed', 'slow', 'connection',
                'eduroam', 'router', 'vpn', 'signal', 'bandwidth'
            ],
            "Communication & Services": [
                'email', 'server', 'portal', 'exchange', 'outlook', 'communication',
                'notification', 'update', 'service'
            ],
            "Academic & Learning": [
                'grade', 'mark', 'faculty', 'professor', 'exam', 'course',
                'assignment', 'syllabus', 'academic', 'study', 'learning'
            ],
            "Facilities & Environment": [
                'dorm', 'hostel', 'room', 'clean', 'bathroom', 'water',
                'maintenance', 'laundry', 'heater', 'facility', 'space'
            ],
            "Health & Wellbeing": [
                'mental', 'health', 'counseling', 'support', 'stress', 'anxiety',
                'wellness', 'therapy', 'care', 'medical'
            ],
            "Food & Dining": [
                'food', 'cafeteria', 'canteen', 'meal', 'menu', 'dining',
                'vegan', 'hygiene', 'taste', 'restaurant'
            ]
        }

        labels = {}

        for cluster_id, keywords in keywords_per_cluster.items():
            best_category = "General Feedback"
            best_score = 0.0

            for category, triggers in categories.items():
                matches = sum(1 for kw in keywords if kw in triggers)
                score = matches / len(keywords) if keywords else 0.0

                if score > best_score:
                    best_score = score
                    best_category = category

            # Fallback: create label from top keywords
            if best_score < 0.2 and keywords:
                generated_label = " & ".join([kw.capitalize() for kw in keywords[:2]])
                labels[cluster_id] = (generated_label, best_score)
            else:
                labels[cluster_id] = (best_category, best_score)

        logger.info(f"Generated {len(labels)} semantic labels")

        return labels

    def calculate_clustering_metrics(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculate clustering quality metrics.

        Args:
            embeddings: Original embeddings
            labels: Cluster labels

        Returns:
            Dictionary of metrics
        """
        logger.info("Calculating clustering metrics...")

        metrics = {}

        # Silhouette score (only for non-outliers)
        valid_mask = labels != -1
        if sum(valid_mask) > 0:
            try:
                silhouette = silhouette_score(
                    embeddings[valid_mask],
                    labels[valid_mask]
                )
                metrics['silhouette_score'] = round(float(silhouette), 4)
                logger.info(f"Silhouette score: {metrics['silhouette_score']}")
            except Exception as e:
                logger.warning(f"Could not calculate silhouette score: {e}")
                metrics['silhouette_score'] = None

        # Outlier statistics
        n_outliers = list(labels).count(-1)
        metrics['outlier_count'] = n_outliers
        metrics['outlier_percentage'] = round((n_outliers / len(labels)) * 100, 2)

        logger.info(f"Outliers: {n_outliers} ({metrics['outlier_percentage']}%)")

        # Cluster distribution
        unique_labels = set(labels)
        unique_labels.discard(-1)
        cluster_sizes = {}

        for label in sorted(unique_labels):
            size = list(labels).count(label)
            cluster_sizes[str(label)] = size

        metrics['cluster_sizes'] = cluster_sizes
        metrics['avg_cluster_size'] = round(
            sum(cluster_sizes.values()) / len(cluster_sizes)
            if cluster_sizes else 0
        )

        logger.info(f"Average cluster size: {metrics['avg_cluster_size']}")

        return metrics

    def apply_vader_sentiment(self, processed_data: pd.DataFrame) -> pd.DataFrame:
        """
        Lexicon-based sentiment on original feedback text (VADER compound score).
        """
        if self._vader is None:
            processed_data = processed_data.copy()
            processed_data['sentiment'] = 'neutral'
            processed_data['sentiment_score'] = 0.0
            return processed_data

        sentiments: List[str] = []
        compounds: List[float] = []

        for text in processed_data['Reports'].astype(str).tolist():
            compound = float(self._vader.polarity_scores(text)['compound'])
            compounds.append(round(compound, 4))
            if compound >= 0.05:
                sentiments.append('positive')
            elif compound <= -0.05:
                sentiments.append('negative')
            else:
                sentiments.append('neutral')

        out = processed_data.copy()
        out['sentiment'] = sentiments
        out['sentiment_score'] = compounds
        return out

    def process_feedback(self, data: pd.DataFrame, progress_callback=None) -> Dict[str, Any]:
        """
        Process student feedback through the semantic NLP pipeline.
        """
        import time
        logger.info("=" * 70)
        logger.info("SEMANTIC NLP PIPELINE: Starting processing")
        logger.info("=" * 70)

        if 'Reports' not in data.columns:
            if 'text' in data.columns:
                data = data.copy()
                data['Reports'] = data['text']
            else:
                return {"error": "Missing text column. Expected 'Reports' or 'text'."}

        # ─── TEXT PREPROCESSING ───────────────────────────────────────────
        t_start = time.time()
        print("[TIMING] START: Preprocessing")
        if progress_callback: progress_callback("preprocessing")

        data['processed_text'] = data['Reports'].apply(self._preprocess_text)

        original_count = len(data)
        processed_data = data[data['processed_text'].str.len() > 0].copy()
        removed_count = original_count - len(processed_data)

        if len(processed_data) < 3:
            return {"error": "Not enough valid feedback texts for clustering."}
            
        t_end = time.time()
        print(f"[TIMING] END: Preprocessing. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── SEMANTIC EMBEDDINGS ──────────────────────────────────────────
        t_start = time.time()
        print("[TIMING] START: Embedding generation")
        if progress_callback: progress_callback("embeddings")

        texts_for_embedding = processed_data['processed_text'].tolist()
        embeddings = self.generate_embeddings(texts_for_embedding)

        t_end = time.time()
        print(f"[TIMING] END: Embedding generation. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── DIMENSIONALITY REDUCTION ────────────────────────────────────
        t_start = time.time()
        print("[TIMING] START: UMAP reduction")
        if progress_callback: progress_callback("umap")

        reduced_embeddings = self.reduce_dimensions(embeddings)

        t_end = time.time()
        print(f"[TIMING] END: UMAP reduction. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── CLUSTERING ───────────────────────────────────────────────────
        t_start = time.time()
        print("[TIMING] START: HDBSCAN clustering")
        if progress_callback: progress_callback("clustering")

        min_cluster_size = max(5, len(processed_data) // 10)
        labels, n_clusters = self.cluster_embeddings(
            reduced_embeddings,
            min_cluster_size=min_cluster_size
        )

        processed_data['cluster'] = labels
        probabilities = getattr(
            self.hdbscan_model,
            'probabilities_',
            np.zeros(len(labels), dtype=float)
        )
        processed_data['cluster_confidence'] = np.round(probabilities, 4)

        t_end = time.time()
        print(f"[TIMING] END: HDBSCAN clustering. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── TOPIC EXTRACTION & SEMANTIC LABELING ──────────────────────────
        t_start = time.time()
        print("[TIMING] START: Semantic Naming")

        keywords_per_cluster = self.extract_cluster_keywords(
            texts_for_embedding,
            labels,
            embeddings,
            top_k=5
        )

        cluster_labels = self.generate_semantic_labels(keywords_per_cluster)

        cluster_names = {}
        semantic_label_scores = {}

        for cluster_id, (label, confidence) in cluster_labels.items():
            cluster_names[str(cluster_id)] = label
            semantic_label_scores[str(cluster_id)] = round(confidence, 2)

        def _row_cluster_label(cid: Any) -> str:
            try:
                ic = int(cid)
            except (TypeError, ValueError):
                return "Unclassified Institutional Feedback"
            if ic == -1:
                return "Unclassified Institutional Feedback"
            return cluster_names.get(str(ic), f"Cluster {ic}")

        processed_data['cluster_label'] = processed_data['cluster'].map(_row_cluster_label)

        t_end = time.time()
        print(f"[TIMING] END: Semantic Naming. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── SENTIMENT ─────────────────────────────
        t_start = time.time()
        print("[TIMING] START: Sentiment analysis")
        if progress_callback: progress_callback("sentiment")

        processed_data = self.apply_vader_sentiment(processed_data)

        t_end = time.time()
        print(f"[TIMING] END: Sentiment analysis. TOTAL MS: {int((t_end - t_start)*1000)}")

        # ─── EVALUATION METRICS ───────────────────────────────────────────
        logger.info("\n[METRICS] Calculating clustering metrics...")

        metrics = self.calculate_clustering_metrics(embeddings, labels)
        confidence_scores = {}
        for cluster_id in sorted(set(labels)):
            if cluster_id == -1:
                continue

            mask = labels == cluster_id
            confidence_scores[str(int(cluster_id))] = round(
                float(np.mean(probabilities[mask])) if np.any(mask) else 0.0,
                4
            )

        mean_confidence = round(float(np.mean(probabilities)) * 100, 2)

        logger.info("\n" + "=" * 70)
        logger.info("SEMANTIC NLP PIPELINE: Processing complete")
        logger.info("=" * 70)

        # ─── BUILD RESULT ────────────────────────────────────────────────
        clustering_results = {
            "optimal_clusters": n_clusters,
            "silhouette_score": metrics.get('silhouette_score'),
            "outlier_count": metrics['outlier_count'],
            "outlier_percentage": metrics['outlier_percentage'],
            "cluster_distribution": {
                str(k): v for k, v in metrics['cluster_sizes'].items()
            },
            "cluster_names": cluster_names,
            "top_keywords_per_cluster": {
                str(k): v for k, v in keywords_per_cluster.items()
            },
            "cluster_confidence_scores": confidence_scores,
            "semantic_label_scores": semantic_label_scores,
            "mean_confidence": mean_confidence,
        }

        return {
            "total_reports": original_count,
            "valid_reports": len(processed_data),
            "removed_noise": removed_count,
            "text_preview": processed_data[['Reports', 'processed_text']].head(5).to_dict(orient='records') if 'Reports' in processed_data.columns else processed_data[['processed_text']].head(5).to_dict(orient='records'),
            "embedding_stats": {
                "model": self.model_name,
                "dimensions": self.embedding_dim,
                "reduction_method": "UMAP (2D, cosine metric)",
                "clustering_method": "HDBSCAN",
                "sentiment_method": "VADER" if self._vader else "unavailable",
            },
            "clustering_results": clustering_results,
            "processed_data": processed_data,
            "reduced_embeddings": reduced_embeddings,  # 2D UMAP coords for DB persistence
            "status": "Semantic Clustering Complete"
        }
