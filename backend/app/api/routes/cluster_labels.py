import re
import logging
from collections import defaultdict
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.services.semantic_taxonomy_normalizer import get_semantic_taxonomy_normalizer

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    TfidfVectorizer = None

# Pattern 1: Leading d + non-ASCII garbage (e.g. "d??â,? Food..." or "d??? Academic...")
# These are mojibake sequences where an emoji was encoded as Latin-1 + 'd' prefix.
_D_MOJIBAKE_RE = re.compile(r'^d[\x80-\xbf\ufffd?â\u0082\u0080-\u00bf,\s]{1,10}')
# Pattern 2: Leading pure garbage (?, â, replacement chars) without d-prefix
_LEADING_GARBAGE_RE = re.compile(r'^[^a-zA-Z\U0001F000-\U0010FFFF]+')

def sanitize_cluster_label(label: str | None) -> str:
    """Strip corrupted UTF-8 / mojibake byte sequences from cluster labels.
    
    Examples of corruption handled:
        "d??â,? Food & Cafeteria Services"  → "Food & Cafeteria Services"
        "d??? Academic Support"             → "Academic Support"
        "????? Career & Internship"         → "Career & Internship"
        "🎓 Teaching Quality"               → "🎓 Teaching Quality"  (preserved)
        "Diversity & Inclusion"             → "Diversity & Inclusion" (unchanged)
    """
    if not label:
        return ""
    text = label.strip()
    # Pass 1: strip d+garbage prefix (mojibake from 4-byte emoji stored as latin-1)
    text = _D_MOJIBAKE_RE.sub("", text)
    # Pass 2: strip any remaining leading non-alpha/non-emoji characters
    text = _LEADING_GARBAGE_RE.sub("", text)
    return text.strip() if text.strip() else label.strip()


GENERIC_CLUSTER_LABEL_RE = re.compile(r"^\s*cluster\s+-?\d+\s*$", re.IGNORECASE)
EMPTY_LABELS = {"", "none", "null", "unknown"}
PHRASE_CLEAN_RE = re.compile(r"[^a-zA-Z\s]")
SUBTHEME_STOP_PHRASES = {
    "student",
    "students",
    "feedback",
    "university",
    "college",
    "campus",
    "really",
    "just",
    "need",
    "needs",
    "like",
    "feel",
    "feels",
    "good",
    "bad",
    "issue",
    "issues",
    "problem",
    "problems",
    "able",
    "available",
    "causing",
    "lot",
    "lots",
    "offer",
    "offered",
    "offers",
    "unable",
    "wish",
    "wishes",
}
SUBTHEME_REPLACEMENTS = {
    "quality food": "Food Quality",
    "food quality": "Food Quality",
    "cafeteria food": "Cafeteria Quality",
    "dining hall": "Dining Hall",
    "mental health": "Mental Health",
    "academic workload": "Academic Workload",
    "financial aid": "Financial Aid",
    "health care": "Health Care",
    "research databases": "Research Databases",
    "databases materials": "Research Materials",
    "technology software": "Technology Software",
    "access academic": "Academic Resource Access",
    "access technology": "Technology Access",
    "limited access": "Limited Access",
    "job market": "Job Market",
    "job opportunities": "Job Opportunities",
    "finding job": "Job Search",
    "internships job": "Internship Access",
    "internships jobs": "Internship Access",
    "struggling job": "Job Search",
    "online classes": "Online Classes",
    "course materials": "Course Materials",
    "accessing course": "Course Access",
    "finding accessing": "Course Access",
    "difficulty finding": "Course Navigation",
    "technical difficulties": "Technical Difficulties",
}


def is_generic_cluster_label(label: str | None) -> bool:
    if label is None:
        return True

    normalized = str(label).strip()
    return (
        normalized.lower() in EMPTY_LABELS
        or GENERIC_CLUSTER_LABEL_RE.match(normalized) is not None
    )


def fallback_cluster_label(cluster_id: int | None) -> str:
    """When no non-generic label exists in DB, avoid inventing theme names from numeric ids."""
    if cluster_id == -1:
        return "Unclassified Institutional Feedback"

    try:
        cid = int(cluster_id)
    except (TypeError, ValueError):
        return "General Student Experience"

    return f"Semantic cluster {cid}"


def choose_cluster_label(cluster_id: int | None, label_counts: dict[str, int]) -> str:
    semantic_labels = [
        (sanitize_cluster_label(label), count)
        for label, count in label_counts.items()
        if not is_generic_cluster_label(label)
    ]
    # Re-filter after sanitization (some labels may become empty/generic after stripping corruption)
    semantic_labels = [
        (lbl, cnt) for lbl, cnt in semantic_labels
        if lbl and not is_generic_cluster_label(lbl)
    ]

    if semantic_labels:
        semantic_labels.sort(key=lambda item: (-item[1], item[0]))
        return semantic_labels[0][0]

    return fallback_cluster_label(cluster_id)


def format_subtheme(phrase: str) -> str:
    replacement = SUBTHEME_REPLACEMENTS.get(phrase.strip().lower())
    if replacement:
        return replacement

    words = [
        word
        for word in PHRASE_CLEAN_RE.sub(" ", phrase.lower()).split()
        if word not in SUBTHEME_STOP_PHRASES and len(word) > 2
    ]
    return " ".join(words[:4]).title()


def extract_subthemes_from_texts(texts: list[str], max_subthemes: int = 6) -> list[str]:
    clean_texts = [
        text.strip()
        for text in texts
        if isinstance(text, str) and len(text.strip()) > 0
    ]

    if not clean_texts:
        return []

    min_df = 2 if len(clean_texts) >= 8 else 1
    candidates: list[str] = []

    if TfidfVectorizer is not None:
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(2, 3),
                min_df=min_df,
                max_features=80,
                lowercase=True,
                token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b",
            )
            matrix = vectorizer.fit_transform(clean_texts)
            scores = matrix.sum(axis=0).A1
            terms = vectorizer.get_feature_names_out()
            ranked_terms = sorted(
                zip(terms, scores),
                key=lambda item: item[1],
                reverse=True,
            )
            candidates = [term for term, _ in ranked_terms]
        except ValueError:
            candidates = []

    if not candidates:
        phrase_counts: defaultdict[str, int] = defaultdict(int)
        for text in clean_texts:
            words = [
                word
                for word in PHRASE_CLEAN_RE.sub(" ", text.lower()).split()
                if word not in SUBTHEME_STOP_PHRASES and len(word) > 2
            ]
            for size in (2, 3):
                for index in range(0, max(0, len(words) - size + 1)):
                    phrase_counts[" ".join(words[index:index + size])] += 1

        candidates = [
            phrase
            for phrase, _ in sorted(
                phrase_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    subthemes = []
    seen = set()
    for candidate in candidates:
        subtheme = format_subtheme(candidate)
        normalized = subtheme.lower()

        if len(subtheme.split()) < 2 or normalized in seen:
            continue

        if any(normalized in existing or existing in normalized for existing in seen):
            continue

        subthemes.append(subtheme)
        seen.add(normalized)

        if len(subthemes) >= max_subthemes:
            break

    return subthemes


async def get_cluster_subthemes(db: AsyncSession) -> dict[int | None, list[str]]:
    # LIMIT to 3 000 rows — sufficient for TF-IDF keyword extraction across any
    # realistic cluster count.  Without this, a full-table scan on a large DB
    # takes 30-60 s and blows the HTTP timeout on every cold-cache request.
    result = await db.execute(
        select(
            Prediction.cluster_id,
            Complaint.raw_text,
            Complaint.processed_text,
        )
        .join(Complaint, Complaint.id == Prediction.complaint_id)
        .limit(3000)
    )

    texts_by_cluster: dict[int | None, list[str]] = defaultdict(list)
    for row in result.all():
        text = row.raw_text or row.processed_text
        if text:
            texts_by_cluster[row.cluster_id].append(text)

    return {
        cluster_id: extract_subthemes_from_texts(texts)
        for cluster_id, texts in texts_by_cluster.items()
    }


async def get_cluster_label_count_rows(db: AsyncSession) -> list[Any]:
    result = await db.execute(
        select(
            Prediction.cluster_id,
            Prediction.cluster_label,
            func.count(Prediction.id).label("count"),
        ).group_by(Prediction.cluster_id, Prediction.cluster_label)
    )
    return result.all()


def normalize_cluster_distribution(
    rows: list[Any],
    total_complaints: int | None = None,
    canonical_map: Optional[Dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """
    Normalize cluster distribution with semantic taxonomy normalization.
    
    Args:
        rows: Raw cluster label count rows from database
        total_complaints: Total number of complaints (for percentage calculation)
        canonical_map: Optional pre-computed canonical label mapping
        
    Returns:
        List of normalized cluster distributions with canonical labels
    """
    grouped: dict[int | None, dict[str, Any]] = {}

    for row in rows:
        cluster_id = row.cluster_id
        count = int(row.count or 0)
        label = str(row.cluster_label or "").strip()

        if cluster_id not in grouped:
            grouped[cluster_id] = {
                "cluster_id": cluster_id,
                "count": 0,
                "label_counts": defaultdict(int),
            }

        grouped[cluster_id]["count"] += count
        grouped[cluster_id]["label_counts"][label] += count

    denominator = total_complaints
    if denominator is None:
        denominator = sum(group["count"] for group in grouped.values())

    normalized = []
    for group in grouped.values():
        count = group["count"]
        
        # Choose best label for this cluster and sanitize any corrupted chars
        chosen_label = choose_cluster_label(
            group["cluster_id"],
            group["label_counts"],
        )
        chosen_label = sanitize_cluster_label(chosen_label)

        # Apply semantic normalization if canonical map provided
        if canonical_map:
            chosen_label = canonical_map.get(chosen_label, chosen_label)
        
        normalized.append(
            {
                "cluster_id": group["cluster_id"],
                "cluster_label": chosen_label,
                "count": count,
                "percentage": round((count / denominator * 100), 2)
                if denominator and denominator > 0
                else 0,
            }
        )

    return sorted(
        normalized,
        key=lambda item: (
            item["cluster_id"] is None,
            item["cluster_id"] if item["cluster_id"] is not None else 0,
        ),
    )


async def get_normalized_cluster_distribution(
    db: AsyncSession,
    total_complaints: int | None = None,
    include_subthemes: bool = False,
) -> list[dict[str, Any]]:
    """
    Get normalized cluster distribution with semantic taxonomy normalization.
    
    Detects and merges semantically similar cluster labels, ensuring no
    duplicate institutional themes in the results.
    """
    rows = await get_cluster_label_count_rows(db)
    
    # Extract all unique labels for semantic analysis
    all_labels = [
        str(row.cluster_label or "").strip()
        for row in rows
        if row.cluster_label
    ]
    unique_labels = list(dict.fromkeys(all_labels))  # Remove duplicates, preserve order
    
    # Build semantic canonical map
    canonical_map: Dict[str, str] = {}
    if unique_labels:
        try:
            normalizer = get_semantic_taxonomy_normalizer()
            canonical_map = normalizer.build_canonical_map(unique_labels)
            logger.info(f"Built semantic canonical map for {len(unique_labels)} labels")
        except Exception as e:
            logger.warning(f"Failed to build semantic canonical map: {e}. Proceeding without normalization.")
    
    # Apply normalization
    clusters = normalize_cluster_distribution(rows, total_complaints, canonical_map)

    if include_subthemes:
        subthemes_by_cluster = await get_cluster_subthemes(db)
        for cluster in clusters:
            cluster["subthemes"] = subthemes_by_cluster.get(
                cluster["cluster_id"],
                [],
            )

    # ── Post-normalization deduplication ──────────────────────────────────────
    # After sanitization + canonical mapping, different cluster_ids may share
    # the same label (e.g. cluster 3 and cluster 6 both → "Career & Internship").
    # Merge them so no duplicate themes appear in the dashboard.
    seen_labels: dict[str, dict] = {}
    total_for_pct = total_complaints or sum(c["count"] for c in clusters)
    for cluster in clusters:
        lbl = cluster["cluster_label"]
        if lbl not in seen_labels:
            seen_labels[lbl] = dict(cluster)  # copy
        else:
            existing = seen_labels[lbl]
            existing["count"] += cluster["count"]
            existing["percentage"] = round(
                existing["count"] / total_for_pct * 100, 2
            ) if total_for_pct else 0
            # Merge subthemes, deduplicate
            combined = existing.get("subthemes", []) + cluster.get("subthemes", [])
            seen: set = set()
            merged_themes = []
            for s in combined:
                if s.lower() not in seen:
                    seen.add(s.lower())
                    merged_themes.append(s)
            existing["subthemes"] = merged_themes[:6]
            # Keep the representative cluster_id as the lower of the two
            if cluster["cluster_id"] != -1:
                existing["cluster_id"] = min(
                    existing["cluster_id"] if existing["cluster_id"] != -1 else 9999,
                    cluster["cluster_id"],
                )

    merged_clusters = list(seen_labels.values())
    return sorted(
        merged_clusters,
        key=lambda item: (
            item["cluster_id"] is None,
            item["cluster_id"] if item["cluster_id"] is not None else 0,
        ),
    )


async def get_normalized_cluster_label_map(db: AsyncSession) -> dict[int | None, str]:
    clusters = await get_normalized_cluster_distribution(db)
    return {cluster["cluster_id"]: cluster["cluster_label"] for cluster in clusters}
