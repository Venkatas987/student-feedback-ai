#!/usr/bin/env python3
"""
Simple test to isolate semantic NLP pipeline issues.
"""

import sys
from pathlib import Path
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.semantic_nlp_pipeline import SemanticNLPPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create minimal test data
test_data = {
    'Reports': [
        "WiFi is slow and disconnects often",
        "Network connectivity is poor",
        "Internet connection keeps dropping",
        "Cannot reset my password",
        "Account is locked",
        "Login not working",
        "Great support team!",
        "Excellent service",
    ]
}

df = pd.DataFrame(test_data)

logger.info("Creating pipeline...")
pipeline = SemanticNLPPipeline()

logger.info("Processing feedback...")
try:
    result = pipeline.process_feedback(df)
    logger.info("✓ Pipeline successful!")
    logger.info(f"Clusters: {result['clustering_results'].get('optimal_clusters', 0)}")
except Exception as e:
    logger.error(f"✗ Pipeline failed: {e}", exc_info=True)
    sys.exit(1)
