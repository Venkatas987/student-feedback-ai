"""Shared helpers for cleaning dataset / UI labels."""
import re


def strip_leading_decorative_prefix(label: str | None) -> str:
    """
    Remove leading emoji / punctuation so themes read cleanly in APIs and UI.
    Keeps the rest of the string (e.g. 'Research & Technology Resources').
    """
    if label is None or (isinstance(label, float) and str(label) == "nan"):
        return ""
    s = str(label).strip()
    if not s:
        return ""
    # Strip non-alphanumeric start (covers emoji + decorative chars)
    s = re.sub(r"^[^A-Za-z0-9]+", "", s).strip()
    return s or str(label).strip()
