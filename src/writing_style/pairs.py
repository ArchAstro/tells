"""Word pairs one body of writing uses far more than another.

Weighted log-odds with an informative Dirichlet prior (Monroe, Colaresi & Quinn
2008), so rare pairs don't top the list on a count of two. Topic leaks into any
two-corpus comparison ("the founder" says more about the subject than the
writer), so `consistent` keeps only pairs that win several independent
comparisons, and `TOPIC` drops obvious subject nouns.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from writing_style.sources import Doc

TOK = re.compile(r"[a-z]+(?:'[a-z]+)?")
# Subject matter, not style: dropped from pair lists by default.
TOPIC = {
    "product", "products", "company", "companies", "founder", "founders", "customer", "customers", "user", "users",
    "startup", "startups", "investor", "investors", "software", "feature", "features", "market", "money", "team",
}


@dataclass
class Counts:
    pairs: Counter
    docs: Counter  # how many documents use each pair
    n_docs: int

    @property
    def total(self) -> int:
        return sum(self.pairs.values())

    def per10k(self, pair: tuple[str, str]) -> float:
        return 1e4 * self.pairs[pair] / self.total if self.total else 0.0


def count(docs: list[Doc]) -> Counts:
    pairs: Counter = Counter()
    seen_in: Counter = Counter()
    for d in docs:
        seen = set()
        for s in d.sentences:
            words = TOK.findall(s.lower().replace("’", "'"))
            for p in zip(words, words[1:]):
                pairs[p] += 1
                seen.add(p)
        seen_in.update(seen)
    return Counts(pairs, seen_in, len(docs))


def merge(counts: list[Counts]) -> Counts:
    pairs: Counter = Counter()
    docs: Counter = Counter()
    for c in counts:
        pairs += c.pairs
        docs += c.docs
    return Counts(pairs, docs, sum(c.n_docs for c in counts))


def log_odds(a: Counts, b: Counts, alpha: float = 0.01) -> dict[tuple[str, str], float]:
    """z-score of each pair being more frequent in a than in b (negative: more in b)."""
    prior = a.pairs + b.pairs
    a0 = sum(prior.values()) * alpha
    na, nb = a.total, b.total
    out = {}
    for k, v in prior.items():
        ak = v * alpha
        ya, yb = a.pairs[k], b.pairs[k]
        delta = math.log((ya + ak) / (na + a0 - ya - ak)) - math.log((yb + ak) / (nb + a0 - yb - ak))
        out[k] = delta / math.sqrt(1 / (ya + ak) + 1 / (yb + ak))
    return out


def consistent(comparisons: list[dict[tuple[str, str], float]], pool: Counts, min_docs: int = 5,
               z: float = 1.96, drop_topic: bool = True) -> list[tuple[tuple[str, str], float]]:
    """Pairs that are over-used (z above threshold) in every comparison, weakest z first-ranked by min z."""
    out = []
    for k in pool.pairs:
        if pool.docs[k] < min_docs or (drop_topic and any(w in TOPIC for w in k)):
            continue
        zs = [c.get(k, 0.0) for c in comparisons]
        if all(v > z for v in zs):
            out.append((k, min(zs)))
    out.sort(key=lambda r: -r[1])
    return out
