"""Sentence grammar classifier: WordNet-licensed construction detectors.

Vendored from writing-patterns (analysis/grammar).
"""

from writing_style.grammar.catalog import STRUCTURES, Structure
from writing_style.grammar.classify import classify, classify_text, ids_of

__all__ = ["STRUCTURES", "Structure", "classify", "classify_text", "ids_of"]
