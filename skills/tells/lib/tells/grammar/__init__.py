"""Sentence grammar classifier: WordNet-licensed construction detectors.

Vendored from writing-patterns (analysis/grammar).
"""

from tells.grammar.catalog import STRUCTURES, Structure
from tells.grammar.classify import classify, classify_text, ids_of

__all__ = ["STRUCTURES", "Structure", "classify", "classify_text", "ids_of"]
