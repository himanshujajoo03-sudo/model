from __future__ import annotations

"""
Rule-Based Weather Event Classifier (Stage 1).
Defined in 05_AI_ML_SPEC.md §4.7, §5, §6, §7.
Calibrated confidence scores: exact canonical keyword matches >= 0.80,
multiple keywords 0.85-0.95, ambiguous matches remain moderate/low.
"""

from functools import lru_cache
from .interface import BaseClassifier
from .rules import (
    VALID_CATEGORIES,
    CATEGORY_PRIORITY,
    KEYWORD_DICT,
    canonicalize_category,
)
try:
    from ..utils.text import normalize_text
except (ImportError, ValueError):
    try:
        from utils.text import normalize_text
    except (ImportError, ValueError):
        from ml.utils.text import normalize_text
import re



NEGATION_TERMS = {"no", "not", "never", "without", "none", "neither", "nor", "नहीं", "नही", "नाही", "नसले", "नसल्याचे"}
NEGATION_PATTERNS = ("did not", "does not", "do not", "is not", "are not", "was not", "were not", "has not", "have not", "had not", "not reported", "not observed", "not occurring", "not occurred", "no evidence of", "no sign of", "no signs of", "no reports of", "without any")

def _tokens(text: str) -> list[str]:
    return text.split()

def _is_negated(tokens: list[str], start: int, end: int) -> bool:
    # Check a compact local scope before and after the matched span.
    left_tokens = tokens[max(0, start-3):start]
    left = " ".join(left_tokens)
    right = " ".join(tokens[end:min(len(tokens), end+5)])
    if any(term in left_tokens[-1:] for term in NEGATION_TERMS):
        return True
    prefix_patterns = ("no evidence of", "no sign of", "no signs of", "no reports of", "not a", "not an", "without any")
    if any(left.endswith(pattern) for pattern in prefix_patterns):
        return True
    if any(right.startswith(pattern) for pattern in NEGATION_PATTERNS):
        return True
    # Numeric/rule phrasing: 'not above 40', etc.
    if re.search(r"\bnot\s+(?:above|below|over|under|exceeding)\b", left):
        return True
    return False

def _phrase_occurrences(tokens: list[str], phrase: str):
    pt = phrase.split()
    if not pt: return []
    out=[]
    for i in range(0, len(tokens)-len(pt)+1):
        if tokens[i:i+len(pt)] == pt:
            out.append((i, i+len(pt)))
    return out

@lru_cache(maxsize=1)
def _get_normalized_keyword_dict() -> dict:
    """Pre-normalize keyword phrases and words for fast matching."""
    norm_dict = {}
    for cat, data in KEYWORD_DICT.items():
        norm_dict[cat] = {
            "phrases": [normalize_text(p) for p in data.get("phrases", []) if normalize_text(p)],
            "single": [normalize_text(w) for w in data.get("single", []) if normalize_text(w)],
        }
    return norm_dict


def score_category(normalized_text: str, category: str) -> tuple[float, int, list[str]]:
    """Score category keywords while excluding locally negated mentions."""
    norm_dict = _get_normalized_keyword_dict()
    if category not in norm_dict:
        return 0.0, 0, []
    tokens = _tokens(normalized_text)
    matched=[]; exact_phrase_hits=0; single_keyword_hits=0
    for phrase in norm_dict[category]["phrases"]:
        occurrences=_phrase_occurrences(tokens, phrase)
        if occurrences and not all(_is_negated(tokens,a,b) for a,b in occurrences):
            exact_phrase_hits += sum(1 for a,b in occurrences if not _is_negated(tokens,a,b))
            if phrase not in matched: matched.append(phrase)
    for kw in norm_dict[category]["single"]:
        # Numeric/single keywords are token based; avoid substring false positives.
        for i,tok in enumerate(tokens):
            if tok == kw and not _is_negated(tokens,i,i+1):
                single_keyword_hits += 1
                if kw not in matched: matched.append(kw)
                break
    total_hits=exact_phrase_hits+single_keyword_hits
    if total_hits==0: return 0.0,0,[]
    if exact_phrase_hits>0:
        raw=0.90+min(0.10,(exact_phrase_hits-1)*0.05+single_keyword_hits*0.02)
    else:
        raw=0.85+min(0.15,(single_keyword_hits-1)*0.05)
    return min(1.0,raw),total_hits,matched


def compute_confidence(
    winner_score: float,
    runner_up_score: float,
    keyword_hit_count: int,
    winner_cat: str | None = None,
    runner_up_cat: str | None = None,
    source_has_structured_data: bool = False,
    category_hint_matches: bool = False
) -> float:
    """
    Compute classification confidence (0.0–1.0) per §4.7 & §7.1.
    Strong keyword match (>= 3 hits or strong phrase): 0.80–0.95
    Moderate match (1–2 hits): 0.60–0.79
    Tiers:
      High confidence (>= 0.80): Exact canonical match or multiple strong keywords.
      Medium confidence (0.60–0.79): Moderate match or slight competition.
      Low confidence (< 0.60): Conflicting / ambiguous matches across incompatible categories.
    """
    if winner_score <= 0.0:
        return 0.10

    base = winner_score * 0.92

    # Ambiguity penalty only applies if runner-up is semantically incompatible
    from .rules import categories_are_compatible
    if (
        runner_up_score > 0.0 and
        runner_up_cat and
        winner_cat and
        not categories_are_compatible(winner_cat, runner_up_cat)
    ):
        ratio = runner_up_score / winner_score
        ambiguity_penalty = 0.25 * ratio
    else:
        ambiguity_penalty = 0.0

    # Evidence reinforcement
    evidence = min(keyword_hit_count, 3) * 0.03
    structured = 0.03 if source_has_structured_data else 0.0
    hint_match = 0.03 if category_hint_matches else 0.0

    raw = base - ambiguity_penalty + evidence + structured + hint_match
    return round(min(max(raw, 0.20), 0.98), 3)


class RuleBasedClassifier(BaseClassifier):
    """Deterministic keyword-based classifier (§4.7)."""

    def predict(self, description: str, category_hint: str | None = None) -> dict:
        normalized = normalize_text(description)
        canonical_hint = canonicalize_category(category_hint, strict=False)

        # Empty description fallback
        if not normalized:
            if canonical_hint and canonical_hint in VALID_CATEGORIES:
                return {
                    "classified_category": canonical_hint,
                    "classification_confidence": 0.30,
                    "category": canonical_hint,
                    "confidence": 0.30,
                }
            return {
                "classified_category": "other",
                "classification_confidence": 0.10,
                "category": "other",
                "confidence": 0.10,
            }

        category_scores: dict[str, float] = {}
        category_hits: dict[str, int] = {}
        category_matched: dict[str, list[str]] = {}

        for cat in VALID_CATEGORIES:
            score, hits, matched = score_category(normalized, cat)
            if score > 0.0:
                category_scores[cat] = score
                category_hits[cat] = hits
                category_matched[cat] = matched

        if not category_scores:
            if canonical_hint and canonical_hint in VALID_CATEGORIES:
                return {
                    "classified_category": canonical_hint,
                    "classification_confidence": 0.30,
                    "category": canonical_hint,
                    "confidence": 0.30,
                }
            return {
                "classified_category": "other",
                "classification_confidence": 0.20,
                "category": "other",
                "confidence": 0.20,
            }

        # Priority resolution (§6.2)
        ranked = sorted(
            category_scores.items(),
            key=lambda x: (-x[1], CATEGORY_PRIORITY.index(x[0]))
        )

        winner_cat, winner_score = ranked[0]
        runner_up_cat = ranked[1][0] if len(ranked) > 1 else None
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        winner_hits = category_hits[winner_cat]

        hint_match = bool(canonical_hint and canonical_hint == winner_cat)

        confidence = compute_confidence(
            winner_score=winner_score,
            runner_up_score=runner_up_score,
            keyword_hit_count=winner_hits,
            winner_cat=winner_cat,
            runner_up_cat=runner_up_cat,
            category_hint_matches=hint_match
        )

        return {
            "classified_category": winner_cat,
            "classification_confidence": confidence,
            "category": winner_cat,
            "confidence": confidence,
        }

    def explain(self, description: str, category_hint: str | None = None) -> list[str]:
        normalized = normalize_text(description)
        canonical_hint = canonicalize_category(category_hint, strict=False)

        if not normalized:
            if canonical_hint:
                return [f"Using source adapter category hint: {canonical_hint}"]
            return ["No description provided; default to other"]

        all_matched = []
        for cat in VALID_CATEGORIES:
            _, _, matched = score_category(normalized, cat)
            all_matched.extend(matched)

        if all_matched:
            return [f"Matched keywords: {', '.join(set(all_matched))}"]
        elif canonical_hint and canonical_hint in VALID_CATEGORIES:
            return [f"No keyword matches; using source adapter hint: {canonical_hint}"]
        return ["No keyword matches found"]
