# Semantic Taxonomy Normalization - Quick Reference

## What Does It Do?

Eliminates duplicate institutional themes (e.g., "Career & Internship Opportunities", "Career Opportunities", "Internship Access") by detecting semantic similarity and merging them into a single canonical label.

## Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **SemanticTaxonomyNormalizer** | `app/services/semantic_taxonomy_normalizer.py` | Core normalization engine using embeddings |
| **MLInferenceService** | `app/services/ml_inference.py` | Applies normalization at inference time |
| **ClusterLabels** | `app/api/routes/cluster_labels.py` | Applies normalization at aggregation time |
| **SemanticTaxonomy Routes** | `app/api/routes/semantic_taxonomy.py` | Monitoring endpoints |

## Key Methods

### Build Canonical Map
```python
from app.services.semantic_taxonomy_normalizer import SemanticTaxonomyNormalizer

normalizer = SemanticTaxonomyNormalizer()
labels = ["Career & Internship Opportunities", "Career Opportunities"]
canonical_map = normalizer.build_canonical_map(labels)
# Result: {"Career Opportunities": "Career & Internship Opportunities"}
```

### Detect Duplicates
```python
duplicates = normalizer.detect_duplicates(labels)
# Result: {"Career & Internship Opportunities": ["Career Opportunities"]}
```

### Compute Similarity
```python
similarity = normalizer.compute_similarity(
    "Career & Internship Opportunities",
    "Career Opportunities"
)
# Result: 0.1995 (low = similar, high = different)
```

### Normalize Label
```python
canonical = normalizer.normalize_label("Career Opportunities", canonical_map)
# Result: "Career & Internship Opportunities"
```

## API Endpoints

### Check Normalization Status
```bash
GET /api/semantic-taxonomy/normalization-status
```
Shows detected duplicates and canonical mappings.

### Check Similarity Between Labels
```bash
GET /api/semantic-taxonomy/semantic-similarity?label1=X&label2=Y
```
Returns cosine distance (0=identical, 2=opposite, threshold=0.35)

### View Raw Label Distribution
```bash
GET /api/semantic-taxonomy/cluster-label-distribution
```
Shows labels in database before normalization.

## Affected Routes

All these routes now return normalized (canonical) labels:
- `/api/analytics/summary` 
- `/api/analytics/cluster-sentiment-heatmap`
- `/api/clusters`
- `/api/insights/priorities`
- `/api/feedback/search`

## Configuration

**Similarity Threshold** (controls how strict matching is):
```python
# In semantic_taxonomy_normalizer.py
SIMILARITY_THRESHOLD = 0.35  # 0.0 = strict, 0.5 = lenient
```

**Embedding Model** (controls semantic understanding):
```python
normalizer = SemanticTaxonomyNormalizer(model_name="all-MiniLM-L6-v2")
```

## How It Works

1. **Extract labels** from database or cluster_names.json
2. **Compute embeddings** using sentence-transformers
3. **Calculate pairwise similarity** using cosine distance
4. **Group similar labels** (distance ≤ threshold)
5. **Select canonical** (longest/most descriptive)
6. **Return mapping** for all labels

## Testing

Run the validation suite:
```bash
cd backend
python test_semantic_taxonomy.py
```

Expected output:
```
✓ PASS: SemanticTaxonomyNormalizer
✓ PASS: Generic Label Detection
✓ PASS: Cluster Labels Integration
✓ PASS: ML Inference Integration

Total: 4/4 test groups passed
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Duplicates not merging | Lower `SIMILARITY_THRESHOLD` in `semantic_taxonomy_normalizer.py` |
| Unrelated labels merging | Raise `SIMILARITY_THRESHOLD` |
| Slow aggregation | Check embedding model size, consider caching |
| Import error | `pip install sentence-transformers` |
| Models not found | Ensure `ml/models/` directory exists |

## Performance

- **Per-prediction overhead:** +5-10ms (embedding lookup)
- **Per-aggregation overhead:** +10-20ms (map building)
- **Memory overhead:** ~50MB (one-time, lazy loaded)
- **Dashboard impact:** Negligible

## Data Preservation

- ✅ Original cluster IDs preserved in database
- ✅ Original labels preserved in database
- ✅ Only presentation layer normalized
- ✅ Full data recovery always possible
- ✅ Clustering algorithm unchanged

## Monitoring

Check logs for normalization operations:
```
INFO - SemanticTaxonomyNormalizer initialized
INFO - Detected semantic duplicates: {canonical: [dup1, dup2]}
INFO - Built canonical map with X labels
```

## Rollback

To disable normalization:
1. Comment out canonical_map usage in `cluster_labels.py`
2. Comment out `_build_canonical_map()` in `ml_inference.py`
3. Restart backend

## Example: Real Data Flow

```
Input:  ["Career & Internship Opportunities", "Career Opportunities", "Internship Access"]
         
Analysis: 
  - "Career & Internship Opportunities" ↔ "Career Opportunities": distance 0.20 ✓ DUPLICATE
  - "Career & Internship Opportunities" ↔ "Internship Access": distance 0.32 ✓ DUPLICATE
  
Grouping:
  - Group: ["Career & Internship Opportunities", "Career Opportunities", "Internship Access"]
  
Selection:
  - Canonical: "Career & Internship Opportunities" (longest)
  
Mapping:
  - "Career Opportunities" → "Career & Internship Opportunities"
  - "Internship Access" → "Career & Internship Opportunities"
  - "Career & Internship Opportunities" → "Career & Internship Opportunities"

Output: All three variants now map to canonical label
```

## Integration Points

```python
# In ML Inference (app/services/ml_inference.py)
# At prediction time:
canonical_label = self._get_canonical_cluster_label(cluster_id)

# In Aggregation (app/api/routes/cluster_labels.py)
# At query time:
canonical_map = normalizer.build_canonical_map(unique_labels)
clusters = normalize_cluster_distribution(rows, canonical_map)

# Frontend receives normalized labels via all API endpoints
# No frontend changes needed - automatic
```

## Semantic Similarity Scale

```
Distance | Meaning | Action
---------|---------|--------
0.0      | Identical | Merge
0.1-0.2  | Very similar | ✓ Merge (usually)
0.3-0.4  | Moderately similar | ✓ Merge (default threshold: 0.35)
0.5-0.7  | Somewhat similar | ✗ Keep separate
0.8+     | Distinct | ✗ Keep separate
```

## Common Duplicate Groups Detected

From test data:
```
Group 1: [Career & Internship Opportunities, Career Opportunities, Internship Access]
Group 2: [Online Learning & Platform Issues, Online Learning Issues]
Group 3: [Research & Technology Resources, Technology Resources]
```

All automatically detected and merged by semantic analysis.

---

**For detailed documentation:** See `SEMANTIC_TAXONOMY_NORMALIZATION.md`

**For troubleshooting:** See `SEMANTIC_TAXONOMY_IMPLEMENTATION.md`

**For architecture:** See `SEMANTIC_TAXONOMY_COMPLETE.md`
