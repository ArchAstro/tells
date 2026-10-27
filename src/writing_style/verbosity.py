"""How many words a text spends per idea, measured per document.

Each measure is cheap and crude on its own; together they separate tight prose
from padded prose. `check` compares a draft with the range of the author's own
documents, so "verbose" means verbose for this author.
"""

from __future__ import annotations

import re
import zlib

WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
CONTENT_TAGS = ("NN", "VB", "JJ", "RB")
LIGHT_VERBS = {"be", "is", "are", "was", "were", "been", "being", "am", "have", "has", "had", "do", "does", "did",
               "'s", "'re", "'m", "'ve", "'d"}
FILLER = re.compile(r"\b(" + "|".join([
    r"in order to", r"the fact that", r"due to the fact", r"in terms of", r"when it comes to", r"at the end of the day",
    r"it(?:'s| is) worth (?:noting|mentioning|saying)", r"it(?:'s| is) important to (?:note|remember|understand)",
    r"it should be noted", r"needless to say", r"in other words", r"that being said", r"with that said",
    r"the reality is", r"the truth is", r"at its core", r"in many ways", r"a wide range of", r"a variety of",
    r"in the context of", r"the process of", r"plays? a (?:key |crucial |big |major )?role", r"in a way that",
    r"each and every", r"first and foremost", r"it turns out that", r"the idea that", r"the ability to",
    r"is able to", r"are able to", r"for the purpose of", r"on a (?:daily|regular) basis", r"at this point in time",
    r"the way (?:that )?(?:we|you|it|they)", r"the kind of", r"the sort of", r"what this means is",
]) + r")\b", re.I)
NOMINAL = re.compile(r"\b[a-z]{4,}(?:tion|sion|ment|ness|ity|ance|ence|ism)s?\b")

MEASURES = {
    # id: (label, which way is "more verbose")
    "density": ("content words per word", "lower"),
    "filler": ("filler phrases per 1,000 words", "higher"),
    "nominal": ("nominalisations per 100 words", "higher"),
    "restate": ("content overlap between neighbouring sentences", "higher"),
    "variety": ("vocabulary variety (moving type-token ratio)", "lower"),
    "redundancy": ("redundancy (1 - compressed / raw size)", "higher"),
}


def _mattr(words: list[str], window: int = 50) -> float:
    if len(words) < window:
        return len(set(words)) / max(len(words), 1)
    vals = [len(set(words[i:i + window])) / window for i in range(0, len(words) - window + 1, 10)]
    return sum(vals) / len(vals)


def _redundancy(text: str, size: int = 2000) -> float:
    raw = text.encode()
    chunks = [raw[i:i + size] for i in range(0, max(len(raw) - size // 2, 1), size)] or [raw]
    chunks = [c for c in chunks if len(c) >= size // 2] or [raw]
    return sum(1 - len(zlib.compress(c, 9)) / len(c) for c in chunks) / len(chunks)


def measure(sentences: list[str]) -> dict[str, float]:
    from nltk import pos_tag, word_tokenize

    text = " ".join(sentences)
    lower = text.lower()
    words = WORD.findall(lower)
    n = max(len(words), 1)
    content = total = 0
    prev: set[str] = set()
    overlaps = []
    for s in sentences:
        tags = [(w.lower(), t) for w, t in pos_tag(word_tokenize(s)) if w[0].isalnum() or w.startswith("'")]
        keep = {w for w, t in tags if t.startswith(CONTENT_TAGS) and w not in LIGHT_VERBS}
        total += len(tags)
        content += sum(1 for w, t in tags if t.startswith(CONTENT_TAGS) and w not in LIGHT_VERBS)
        if prev and keep:
            overlaps.append(len(prev & keep) / len(prev | keep))
        prev = keep
    return {
        "density": content / max(total, 1),
        "filler": 1000 * len(FILLER.findall(lower)) / n,
        "nominal": 100 * len(NOMINAL.findall(lower)) / n,
        "restate": sum(overlaps) / len(overlaps) if overlaps else 0.0,
        "variety": _mattr(words),
        "redundancy": _redundancy(text),
    }


def fillers(sentences: list[str]) -> list[str]:
    return [s for s in sentences if FILLER.search(s)]
