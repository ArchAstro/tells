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

from tells.sources import Doc

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


# ---------------------------------------------------------------- reference, model and draft


def key(pair: tuple[str, str]) -> str:
    return " ".join(pair)


def unkey(s: str) -> tuple[str, str]:
    a, b = s.split(" ", 1)
    return a, b


def build_reference(human: Counts, machines: dict[str, Counts], top_ai: int = 60, keep: int = 6000,
                    min_docs: int = 8) -> dict:
    """AI pairs (every machine uses them more than the human) plus pooled machine counts to compare anyone against."""
    pool = merge(list(machines.values()))
    against = [{k: -v for k, v in log_odds(human, m).items()} for m in machines.values()]
    ai = [{"pair": key(k), "human": human.per10k(k), "machines": {n: m.per10k(k) for n, m in machines.items()},
           "z": z} for k, z in consistent(against, pool, min_docs)[:top_ai]]
    common = dict(pool.pairs.most_common(keep))
    return {"ai": ai, "machine_counts": {key(k): v for k, v in common.items()}, "machine_total": pool.total}


def machine_counts(ref_pairs: dict) -> Counts:
    pairs = Counter({unkey(k): v for k, v in ref_pairs["machine_counts"].items()})
    # only the most common pairs are stored; pad the total so rates stay right
    pairs[("", "")] = ref_pairs["machine_total"] - sum(pairs.values())
    return Counts(pairs, Counter(), 0)


def author_pairs(author: Counts, ref_pairs: dict, top: int = 25, min_docs: int = 4) -> dict:
    """The author's signature pairs (used far more than the machines) and the AI pairs they rarely use."""
    machine = machine_counts(ref_pairs)
    sig = consistent([log_odds(author, machine)], author, min_docs)[:top]
    signature = [{"pair": key(k), "you": author.per10k(k), "machines": machine.per10k(k)} for k, _ in sig]
    ai = []
    for row in ref_pairs["ai"]:
        k = unkey(row["pair"])
        m_rate = sum(row["machines"].values()) / len(row["machines"])
        you = author.per10k(k)
        if you < m_rate / 2:
            ai.append({"pair": row["pair"], "you": you, "machines": m_rate})
    return {"words": author.total, "signature": signature, "ai": ai}


def draft_report(draft: Counts, ap: dict) -> dict:
    """How a draft uses the author's signature pairs and the AI pairs they avoid."""
    words = draft.total

    def rate(rows, col):
        return sum(r[col] for r in rows)

    sig_draft = sum(draft.pairs[unkey(r["pair"])] for r in ap["signature"]) * 1e4 / max(words, 1)
    ai_draft = sum(draft.pairs[unkey(r["pair"])] for r in ap["ai"]) * 1e4 / max(words, 1)
    missing = [r for r in ap["signature"] if draft.pairs[unkey(r["pair"])] == 0 and r["you"] * words / 1e4 >= 1.5]
    over = []
    for r in ap["ai"]:
        n = draft.pairs[unkey(r["pair"])]
        if n >= 2 and n * 1e4 / max(words, 1) > 2 * r["you"]:
            over.append({**r, "count": n, "draft": n * 1e4 / words})
    over.sort(key=lambda r: -(r["draft"] - r["you"]))
    return {
        "words": words,
        "signature": {"draft": sig_draft, "you": rate(ap["signature"], "you"), "machines": rate(ap["signature"], "machines")},
        "ai": {"draft": ai_draft, "you": rate(ap["ai"], "you"), "machines": rate(ap["ai"], "machines")},
        "missing": missing, "over": over,
    }
