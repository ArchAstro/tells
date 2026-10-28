"""Sentence → grammatical structures."""

from __future__ import annotations

import re

from tells.grammar.catalog import CATALOG as CORE, STRUCTURES, Structure
from tells.grammar.essay import CATALOG as ESSAY
from tells.grammar.tokens import annotate

CATALOG = CORE + ESSAY

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def classify(sentence: str) -> list[Structure]:
    text = sentence.strip()
    if not text:
        return []
    toks = annotate(text)
    hits: list[Structure] = []
    for detector in CATALOG:
        hits.extend(detector(toks))
    hits.sort(key=lambda s: (s.start, s.end, s.id))
    return hits


def classify_text(text: str) -> list[tuple[str, list[Structure]]]:
    """Split a paragraph into sentences and classify each."""
    chunks = [c.strip() for c in _SENT_SPLIT.split(text.strip()) if c.strip()]
    if not chunks:
        return []
    return [(c, classify(c)) for c in chunks]


def ids_of(sentence: str) -> list[str]:
    return [s.id for s in classify(sentence)]
