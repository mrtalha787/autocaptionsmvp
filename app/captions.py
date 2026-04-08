"""
Caption grouping and emphasis tagging.
"""

from __future__ import annotations

from typing import Iterable, List, Dict, Sequence
from collections import Counter
import heapq


def tag_emphasis(
    words: Sequence[Dict], emphasized: Iterable[str]
) -> List[Dict]:
    """Mark words that should be emphasized (case-insensitive, multi-hit)."""
    emph_set = {w.lower().rstrip(",") for w in emphasized}
    tagged = []
    for w in words:
        text = w.get("word", "").rstrip(",")
        tagged.append(
            {
                **w,
                "emphasized": text.lower() in emph_set,
            }
        )
    return tagged


_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "so",
    "because",
    "as",
    "of",
    "at",
    "to",
    "for",
    "in",
    "on",
    "with",
    "by",
    "from",
    "is",
    "are",
    "am",
    "be",
    "was",
    "were",
    "it",
    "that",
    "this",
    "these",
    "those",
    "you",
    "your",
    "yours",
    "we",
    "our",
    "ours",
    "i",
    "me",
    "my",
    "mine",
    "they",
    "them",
    "their",
    "theirs",
    "he",
    "she",
    "his",
    "her",
    "hers",
    "its",
    "not",
    "no",
    "do",
    "did",
    "does",
    "have",
    "has",
    "had",
    "will",
    "would",
    "can",
    "could",
    "should",
    "about",
    "just",
    "up",
    "down",
    "out",
    "over",
    "under",
    "again",
    "very",
}


def _clean_token(text: str) -> str:
    # Faster than regex for short words; keeps letters, digits, apostrophes.
    buf = []
    for ch in text:
        if ch.isalnum() or ch == "'":
            buf.append(ch)
    return "".join(buf)


_GENERIC_CONTENT = {
    "people",
    "person",
    "thing",
    "things",
    "stuff",
    "something",
    "someone",
    "anyone",
    "everyone",
    "everybody",
}


def detect_emphasis_words(words: Sequence[Dict], max_words: int = 6) -> List[str]:
    """
    Heuristic auto-selection of emphasis words.
    Scores words (higher for rare, meaningful terms) and returns top N unique terms.
    Tuned to avoid highlighting generic/repeated nouns like “people”.
    """
    freq: Dict[str, int] = {}
    tokens: List[tuple[str, str]] = []

    for w in words:
        token = _clean_token(w.get("word", ""))
        if not token:
            continue
        token_lower = token.lower()
        if token_lower in _STOPWORDS or token_lower in _GENERIC_CONTENT:
            continue
        freq[token_lower] = freq.get(token_lower, 0) + 1
        tokens.append((token, token_lower))

    if not tokens:
        return []

    scores: Dict[str, float] = {}
    for token, token_lower in tokens:
        f = freq[token_lower]
        # Prefer words that appear once; penalize repetitions
        score = 8 if f == 1 else max(1, 4 - f)
        # Penalize very short tokens
        if len(token) < 4:
            score -= 2
        if any(ch.isdigit() for ch in token):
            score += 3
        if len(token) >= 7:
            score += 2
        if any(ch.isdigit() for ch in token):
            score += 1  # small extra to stack lightly
        if token.isupper() and len(token) > 1:
            score += 2
        elif token[0].isupper():
            score += 1
        scores[token_lower] = max(scores.get(token_lower, 0), score)

    # Drop any words that fell below 1 after penalties
    filtered = {w: s for w, s in scores.items() if s > 1}
    top = heapq.nlargest(max_words, filtered.items(), key=lambda kv: (kv[1], kv[0]))
    return [word for word, _ in top]


def group_words(
    words: Sequence[Dict],
    max_words: int = 4,
    max_gap: float = 0.5,
) -> List[Dict]:
    """
    Group words into caption chunks.
    A new caption starts if:
      - words count exceeds max_words
      - time gap between consecutive words > max_gap seconds
    """
    captions: List[Dict] = []
    current: List[Dict] = []

    for w in words:
        if current:
            gap = w["start"] - current[-1]["end"]
            if len(current) >= max_words or gap > max_gap:
                captions.append(
                    {
                        "words": current,
                        "start": current[0]["start"],
                        "end": current[-1]["end"],
                    }
                )
                current = []
        current.append(w)

    if current:
        captions.append(
            {
                "words": current,
                "start": current[0]["start"],
                "end": current[-1]["end"],
            }
        )

    return captions
