"""
One-time migration: clean corrupted UTF-8/mojibake cluster labels in the predictions table.

Run with:  python fix_corrupted_labels.py

This script:
1. Finds all distinct (cluster_id, cluster_label) pairs in the DB.
2. Applies sanitize_cluster_label() to strip mojibake prefixes.
3. Bulk-updates any rows where the label changed.
4. Prints a summary of what was fixed.
"""
import asyncio
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inline the sanitizer so this script has no circular import issues
_D_MOJIBAKE_RE = re.compile(r'^d[\x80-\xbf\ufffd?â\u0082\u0080-\u00bf,\s]{1,10}')
_LEADING_GARBAGE_RE = re.compile(r'^[^a-zA-Z\U0001F000-\U0010FFFF]+')

def sanitize(label: str | None) -> str:
    if not label:
        return ""
    text = label.strip()
    text = _D_MOJIBAKE_RE.sub("", text)
    text = _LEADING_GARBAGE_RE.sub("", text)
    return text.strip() if text.strip() else label.strip()


async def main():
    from app.core.database import AsyncSessionLocal
    from app.models.prediction import Prediction
    from sqlalchemy.future import select
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        # Fetch all distinct cluster_labels
        result = await db.execute(
            select(Prediction.cluster_label).distinct()
        )
        all_labels = [row[0] for row in result.all() if row[0]]

        fixed = 0
        for label in all_labels:
            clean = sanitize(label)
            if clean != label:
                logger.info(f"  Fixing: {repr(label)!s} → {repr(clean)!s}")
                await db.execute(
                    update(Prediction)
                    .where(Prediction.cluster_label == label)
                    .values(cluster_label=clean)
                )
                fixed += 1

        await db.commit()
        logger.info(f"\n✓ Fixed {fixed} corrupted label(s) out of {len(all_labels)} distinct labels.")
        logger.info("All labels are now clean in the database.")


if __name__ == "__main__":
    asyncio.run(main())
