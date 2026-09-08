from __future__ import annotations

"""
Text Normalization and Similarity Utilities.
Supports full multilingual and Unicode Indic/World languages (§4.4, §19.4).
Full multilingual Unicode support (§4.4, §19.4) preserving all Indic and world language scripts.
"""

import re
import unicodedata


def normalize_text(text: str | None) -> str:
    """
    Normalize description text for keyword matching and feature extraction.
    - Lowercase
    - Unicode NFKC normalization
    - Strip ASCII and Unicode punctuation/symbols while strictly preserving
      all letters (L), combining marks (M), and numbers (N) across English,
      Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, etc.
    - Collapse redundant whitespace.
    """
    if text is None:
        return ""
    text = str(text)
    # NFKC normalizes compatibility characters while composing canonical forms
    text = unicodedata.normalize("NFKC", text.lower())

    # Keep all characters except Punctuation (P) and Symbols (S)
    chars = [
        c if unicodedata.category(c)[0] not in ("P", "S") else " "
        for c in text
    ]
    return " ".join("".join(chars).split())


def text_similarity(text_a: str | None, text_b: str | None) -> float:
    """
    Compute Jaccard similarity on normalized keyword/token sets (§11.3).
    Supports multilingual token sets.
    """
    norm_a = normalize_text(text_a)
    norm_b = normalize_text(text_b)

    words_a = set(norm_a.split())
    words_b = set(norm_b.split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)
