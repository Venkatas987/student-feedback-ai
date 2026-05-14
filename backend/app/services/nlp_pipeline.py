# app/services/nlp_pipeline.py
# This service handles the NLP (Natural Language Processing) pipeline.
# It processes student feedback text through cleaning, tokenization, 
# stopword removal, and lemmatization.

import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from typing import List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

def verify_nltk_resources():
    """
    Verify that NLTK resources exist locally.
    Does NOT attempt to download from the internet to prevent freezing.
    """
    resources = {
        'corpora/stopwords': 'stopwords',
        'tokenizers/punkt': 'punkt',
        'corpora/wordnet': 'wordnet',
        'corpora/omw-1.4': 'omw-1.4'
    }
    
    missing = []
    for resource_path, package_name in resources.items():
        try:
            nltk.data.find(resource_path)
            logger.info(f"Verified NLTK resource: '{package_name}'")
        except LookupError:
            missing.append(package_name)
            
    if missing:
        error_msg = f"Missing NLTK resources: {missing}. Please install them manually in %APPDATA%\\nltk_data\\."
        logger.error(error_msg)
        # Raise an error to prevent the app from starting in a broken state
        raise RuntimeError(error_msg)
    else:
        logger.info("All NLTK resources verified successfully. No downloads attempted.")


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline

class NLPPipeline:
    """
    NLP Pipeline service for processing student feedback.
    Handles cleaning, tokenization, and preparing text for ML models.
    """

    def __init__(self, max_features=1500, min_df=5, max_df=0.70):
        # We assume verify_nltk_resources() was called by FastAPI lifespan
        self.stop_words = set(stopwords.words('english'))
        
        # Custom Domain Stopwords for institutional noise reduction
        self.domain_stopwords = {
            'student', 'students', 'university', 'college', 'campus', 
            'issue', 'problem', 'really', 'very', 'school', 'like', 'just', 'also',
            'need', 'feel', 'make', 'one', 'would', 'get', 'cant', 'time',
            'ive', 'made', 'always', 'available', 'much', 'many', 'good', 'bad', 'lot', 'even', 'can',
            'please', 'thank', 'thanks', 'regards', 'best', 'hello', 'hi', 'dear', 
            'kindly', 'team', 'sir', 'madam', 'attached', 'forward', 'requesting', 'request', 'help', 'support'
        }
        self.stop_words.update(self.domain_stopwords)
        
        self.lemmatizer = WordNetLemmatizer()
        
        # Production-style TF-IDF Vectorizer (Tunable)
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            min_df=min_df,
            max_df=max_df,
            sublinear_tf=True
        )
        self.cluster_model = None
        self.lsa_pipeline = None

    def interpret_silhouette_score(self, score: float) -> str:
        """
        Interpret the silhouette score for cluster quality diagnostics.
        """
        if score >= 0.7:
            return "Excellent (Clusters are well-separated and dense)"
        elif score >= 0.5:
            return "Good (Reasonable cluster structure found)"
        elif score >= 0.25:
            return "Weak (Clusters are somewhat overlapping)"
        else:
            return "Poor (Data lacks clear cluster structure)"

    def generate_cluster_name(self, top_keywords: List[str]) -> tuple[str, float]:
        """
        Dynamically generate human-readable cluster names using semantic matching.
        Returns a tuple of (Cluster Name, Confidence Score).
        """
        # Define realistic institutional categories and their trigger words
        categories = {
            "Password & Access Issues": ['password', 'access', 'login', 'account', 'verification', 'unlock', 'reset', 'auth'],
            "Hardware Installation Requests": ['hardware', 'laptop', 'printer', 'mouse', 'keyboard', 'monitor', 'install', 'setup', 'cable', 'screen'],
            "Purchase & Procurement Requests": ['purchase', 'procurement', 'buy', 'order', 'software', 'license', 'approval', 'quote'],
            "Network Connectivity Problems": ['network', 'wifi', 'internet', 'connection', 'slow', 'speed', 'eduroam', 'disconnect', 'router', 'vpn', 'signal'],
            "Email & Server Issues": ['email', 'server', 'database', 'system', 'portal', 'exchange', 'outlook', 'down'],
            
            # Legacy Student Categories
            "Library & Learning Resources": ['library', 'book', 'study', 'print', 'journal', 'resource', 'quiet', 'hours'],
            "Cafeteria & Food Services": ['food', 'cafeteria', 'canteen', 'meal', 'menu', 'dining', 'vegan', 'hygiene', 'taste'],
            "Academic Evaluation & Workload": ['grade', 'mark', 'faculty', 'teach', 'professor', 'exam', 'academic', 'syllabus', 'assignment', 'course'],
            "Mental Health & Counseling": ['mental', 'health', 'counseling', 'support', 'stress', 'depress', 'anxiety', 'therapist', 'overwhelmed'],
            "Hostel & Facilities Maintenance": ['dorm', 'hostel', 'room', 'clean', 'bathroom', 'water', 'maintain', 'maintenance', 'laundry', 'heater'],
            "Administrative & Financial Services": ['fee', 'payment', 'financial', 'scholarship', 'admin', 'registration', 'bursar', 'office']
        }
        
        best_match = ""
        highest_score = 0.0
        
        # Calculate semantic overlap
        for category, triggers in categories.items():
            # Weigh top 3 keywords more heavily
            matches = sum(2 if i < 3 and w in triggers else (1 if w in triggers else 0) for i, w in enumerate(top_keywords))
            # Max possible score is 3*2 + 7*1 = 13 (if top 10 words)
            max_possible = sum(2 if i < 3 else 1 for i in range(len(top_keywords)))
            score = matches / max_possible
            
            if score > highest_score:
                highest_score = score
                best_match = category
                
        # Fallback to keyword summary if confidence is low (< 15% overlap)
        if highest_score < 0.15:
            fallback_name = " ".join([w.capitalize() for w in top_keywords[:3]]) + " Topics"
            return fallback_name, highest_score
            
        return best_match, highest_score

    def generate_actionable_insights(self, cluster_names_map: Dict[str, str], cluster_distribution: Dict[str, int]) -> List[str]:
        """
        Generate simple AI insights translating clusters into institutional intelligence.
        """
        insights = []
        total_reports = sum(cluster_distribution.values())
        
        # Sort clusters by volume
        sorted_clusters = sorted(cluster_distribution.items(), key=lambda item: item[1], reverse=True)
        
        if sorted_clusters:
            top_cluster_id = sorted_clusters[0][0]
            top_cluster_name = cluster_names_map[top_cluster_id]
            top_cluster_vol = cluster_distribution[top_cluster_id]
            pct = round((top_cluster_vol / total_reports) * 100, 1)
            insights.append(f"Primary Concern: '{top_cluster_name}' represents the largest segment of feedback ({pct}%).")
            
            for cid, vol in sorted_clusters:
                name = cluster_names_map[cid]
                if "WiFi & Network" in name and vol > (total_reports * 0.15):
                    insights.append("Infrastructure Alert: High volume of network complaints suggests internet instability requiring urgent IT review.")
                elif "Mental Health" in name and vol > (total_reports * 0.05):
                    insights.append("Student Wellbeing: A distinct cluster around mental health highlights the need for increased counseling visibility.")
                elif "Hostel" in name and vol > (total_reports * 0.15):
                    insights.append("Facilities: Recurring maintenance or hostel issues detected. Consider auditing dormitory living conditions.")
                elif "Academic Evaluation" in name and vol > (total_reports * 0.15):
                    insights.append("Academic Operations: Significant feedback regarding exams/grading. Suggests a review of academic workload or faculty communication.")
                    
        return insights

    def _clean_text(self, text: str) -> str:
        """
        Step 4: Basic text cleaning.
        Removes special characters, numbers, and standardizes whitespace.
        """
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Remove consecutive duplicate words (e.g., "hello hello please please" -> "hello please")
        text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text)
        
        # Remove multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _preprocess_text(self, text: str) -> str:
        """
        Steps 5-7: Full preprocessing pipeline.
        Tokenization -> Stopword Removal -> Lemmatization.
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            return ""

        # Step 5: Tokenization
        tokens = word_tokenize(cleaned)

        # Step 6 & 7: Stopword removal and Lemmatization
        processed_tokens = [
            self.lemmatizer.lemmatize(word)
            for word in tokens
            if word not in self.stop_words and len(word) > 2
        ]

        return " ".join(processed_tokens)

    def vectorize_text(self, data: pd.DataFrame) -> tuple[Any, Dict[str, Any]]:
        """
        Step 8: TF-IDF Vectorization.
        Converts processed text into a sparse matrix of numerical features.
        """
        logger.info("TF-IDF Vectorization started...")
        
        # Fit and transform the processed text into numerical vectors
        tfidf_matrix = self.vectorizer.fit_transform(data['processed_text'])
        
        # Extract feature names (the actual words/ngrams)
        feature_names = self.vectorizer.get_feature_names_out()
        vocab_size = len(feature_names)
        
        logger.info(f"TF-IDF Vectorization completed. Matrix shape: {tfidf_matrix.shape}")
        
        stats = {
            "matrix_shape": tfidf_matrix.shape,
            "vocabulary_size": vocab_size,
            "feature_names_preview": feature_names[:10].tolist() if vocab_size > 0 else []
        }
        
        return tfidf_matrix, stats

    def apply_lsa(self, tfidf_matrix) -> tuple[Any, Dict[str, Any], Any]:
        """
        Latent Semantic Analysis (LSA) - TruncatedSVD + Normalization
        Reduces dimensionality to dense semantic components.
        """
        logger.info("Applying TruncatedSVD (LSA) for dimensionality reduction...")
        
        n_components = min(100, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        if n_components < 2:
             n_components = 2
        
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        normalizer = Normalizer(copy=False)
        self.lsa_pipeline = make_pipeline(svd, normalizer)
        
        dense_matrix = self.lsa_pipeline.fit_transform(tfidf_matrix)
        explained_variance = svd.explained_variance_ratio_.sum()
        
        stats = {
            "original_dimensions": tfidf_matrix.shape[1],
            "reduced_dimensions": n_components,
            "explained_variance_ratio": round(float(explained_variance), 4)
        }
        
        return dense_matrix, stats, svd

    def cluster_data(self, data: pd.DataFrame, matrix_for_clustering, svd_model) -> Dict[str, Any]:
        """
        Step 9: Optimized KMeans Clustering on LSA-reduced Dense Matrix.
        """
        logger.info("Starting optimized cluster selection...")
        num_samples = matrix_for_clustering.shape[0]
        
        if num_samples < 3:
            return {"error": "Not enough data points to perform clustering."}
            
        # Limit search range based on institutional dataset constraints
        max_k = min(6, num_samples - 1)
        min_k = min(3, max_k)
        
        best_k = min_k
        best_score = -1.0
        best_model = None
        
        # Test realistic cluster sizes using MiniBatchKMeans
        for k in range(min_k, max_k + 1):
            # MiniBatchKMeans is used for scalability, faster convergence, and robust centroid updates
            model = MiniBatchKMeans(n_clusters=k, random_state=42, n_init=10, batch_size=256)
            labels = model.fit_predict(matrix_for_clustering)
            
            if len(set(labels)) > 1:
                score = silhouette_score(matrix_for_clustering, labels)
                logger.info(f"Testing k={k}, silhouette_score={score:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_model = model

        if best_model is None:
            return {"error": "Clustering failed to find valid clusters."}

        logger.info(f"Optimal clusters selected: {best_k} with score: {best_score:.4f}")
        self.cluster_model = best_model
        
        labels = best_model.labels_
        data['cluster'] = labels
        
        cluster_counts = data['cluster'].value_counts().to_dict()
        cluster_distribution = {str(k): int(v) for k, v in cluster_counts.items()}
        
        top_keywords_per_cluster = {}
        cluster_names = {}
        confidence_diagnostics = {}
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Inverse transform SVD centroids back to original TF-IDF vocabulary space
        original_space_centroids = svd_model.inverse_transform(best_model.cluster_centers_)
        order_centroids = original_space_centroids.argsort()[:, ::-1]
        
        for i in range(best_k):
            top_features = [feature_names[ind] for ind in order_centroids[i, :10]]
            top_keywords_per_cluster[str(i)] = top_features
            
            name, conf = self.generate_cluster_name(top_features)
            cluster_names[str(i)] = name
            
            # Confidence diagnostics per cluster
            semantic_strength = "Strong" if conf >= 0.4 else ("Moderate" if conf >= 0.15 else "Weak/Mixed")
            confidence_diagnostics[str(i)] = {
                "naming_confidence_score": round(conf, 2),
                "semantic_strength": semantic_strength,
                "density": f"{round((cluster_distribution[str(i)] / num_samples) * 100, 1)}% of reports"
            }
            
        interpretation = self.interpret_silhouette_score(best_score)
        quality_label = interpretation.split()[0]
        
        actionable_insights = self.generate_actionable_insights(cluster_names, cluster_distribution)
            
        return {
            "optimal_clusters": best_k,
            "silhouette_score": round(float(best_score), 4),
            "silhouette_interpretation": interpretation,
            "clustering_quality": quality_label,
            "cluster_distribution": cluster_distribution,
            "cluster_names": cluster_names,
            "top_keywords_per_cluster": top_keywords_per_cluster,
            "cluster_confidence_diagnostics": confidence_diagnostics,
            "actionable_insights": actionable_insights
        }

    def process_feedback(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Process the uploaded feedback data through the full NLP pipeline.
        Returns clustering results and the processed dataframe with cluster assignments.
        """
        if 'Reports' not in data.columns:
            return {"error": "Missing 'Reports' column"}

        logger.info("Starting text preprocessing...")

        # Count occurrences of domain stopwords
        domain_stopwords_count = 0
        removed_words_counter = {}
        for text in data['Reports']:
            if isinstance(text, str):
                tokens = word_tokenize(text.lower())
                for word in tokens:
                    if word in self.domain_stopwords:
                        domain_stopwords_count += 1
                        removed_words_counter[word] = removed_words_counter.get(word, 0) + 1

        top_removed = sorted(removed_words_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        top_removed_words = {k: v for k, v in top_removed}

        data['processed_text'] = data['Reports'].apply(self._preprocess_text)

        original_count = len(data)
        processed_data = data[data['processed_text'].str.len() > 0].copy()

        # Perform Vectorization
        tfidf_matrix, vector_stats = self.vectorize_text(processed_data)
        vector_stats["removed_domain_stopwords"] = domain_stopwords_count
        vector_stats["top_removed_noise_words"] = top_removed_words

        # Perform LSA (TruncatedSVD + Normalization)
        clustering_results = None
        lsa_stats = {}
        if len(processed_data) >= 3:
            dense_matrix, lsa_stats, svd_model = self.apply_lsa(tfidf_matrix)
            clustering_results = self.cluster_data(processed_data, dense_matrix, svd_model)
        else:
            clustering_results = {"error": "Not enough valid data points for clustering after preprocessing."}

        return {
            "total_reports": original_count,
            "valid_reports": len(processed_data),
            "removed_noise": original_count - len(processed_data),
            "text_preview": processed_data[['Reports', 'processed_text']].head(5).to_dict(orient='records'),
            "tfidf_stats": vector_stats,
            "lsa_diagnostics": lsa_stats,
            "clustering_results": clustering_results,
            "processed_data": processed_data,
            "status": "Clustering Complete"
        }

    def train_models(self, data: pd.DataFrame) -> None:
        pass

    def save_models(self) -> None:
        pass

    def load_models(self) -> None:
        pass