"""Build a style model from an author's corpora and score a draft against it.

What we learned doing this by hand, encoded here:

1. Measure rates per sentence and compare with binomial standard errors, but
   also keep each document's rate: "outside the range of anything you've
   written" is easier to trust than a z-score.
2. Short-form corpora (tweets) are packed into chunks of ~120 sentences so a
   chunk compares like a blog post.
3. Corpora are weighted equally by default, so 600 tweets don't drown 8 posts.
4. Only fix features where every corpus agrees on the direction ("voice").
   Where blog and tweets disagree, the difference is the format, not the author.
5. Calibrate: score each of the author's own documents against the rest.
   A draft doesn't need zero flags, just no more than the author's own work gets.
"""

from __future__ import annotations

import json
import math
import statistics as st
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from writing_style.features import FEATURES, sentence_features
from writing_style.sources import WORD, Doc

VERSION = 1
Z_OFF = 2.0  # |z| at or above this counts as off
Z_AGREE = 1.0  # every corpus must be at least this far off, same direction, to call it voice
EXAMPLES_PER_FEATURE = 4
AUTO_CHUNK = 120


@dataclass
class Stats:
    name: str
    n: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    len_sum: int = 0
    len_sq: int = 0

    def add(self, sentence: str, feats: set[str]) -> None:
        words = len(WORD.findall(sentence))
        self.n += 1
        self.len_sum += words
        self.len_sq += words * words
        for f in feats:
            self.counts[f] = self.counts.get(f, 0) + 1

    def rate(self, f: str) -> float:
        return self.counts.get(f, 0) / self.n if self.n else 0.0

    @property
    def mean_len(self) -> float:
        return self.len_sum / self.n if self.n else 0.0

    @property
    def sd_len(self) -> float:
        if not self.n:
            return 0.0
        return math.sqrt(max(self.len_sq / self.n - self.mean_len ** 2, 0.0))

    def to_json(self) -> dict:
        return {"name": self.name, "n": self.n, "counts": self.counts, "len_sum": self.len_sum, "len_sq": self.len_sq}

    @classmethod
    def from_json(cls, d: dict) -> "Stats":
        return cls(d["name"], d["n"], dict(d["counts"]), d["len_sum"], d["len_sq"])


@dataclass
class Corpus:
    name: str
    weight: float
    docs: list[Stats]
    examples: dict[str, list[str]]
    chunked: bool = False
    n_files: int = 0
    verbosity: list[dict] = field(default_factory=list)  # one per doc, aligned with docs

    @property
    def n(self) -> int:
        return sum(d.n for d in self.docs)

    def pooled(self, f: str) -> float:
        return sum(d.counts.get(f, 0) for d in self.docs) / self.n if self.n else 0.0

    @property
    def mean_len(self) -> float:
        return sum(d.len_sum for d in self.docs) / self.n if self.n else 0.0


def featurize(doc: Doc) -> list[tuple[str, set[str]]]:
    return [(s, sentence_features(s)) for s in doc.sentences]


def build_corpus(name: str, docs: list[Doc], weight: float = 1.0, chunk: int | None = None,
                 examples: bool = True) -> Corpus:
    """Featurize every sentence. Many tiny docs (tweets) are packed into chunks."""
    rows = [featurize(d) for d in docs]
    if chunk is None:
        sizes = sorted(len(r) for r in rows) or [0]
        chunk = AUTO_CHUNK if (len(docs) > 30 and sizes[len(sizes) // 2] < 20) else 0
    stats: list[Stats] = []
    texts: list[list[str]] = []
    if chunk:
        flat = [x for r in rows for x in r]
        for i in range(0, len(flat), chunk):
            part = flat[i:i + chunk]
            if len(part) < chunk // 2 and stats:  # fold a small tail into the last chunk
                target = stats[-1]
            else:
                target = Stats(f"{name} #{len(stats) + 1}")
                stats.append(target)
                texts.append([])
            for s, f in part:
                target.add(s, f)
                texts[-1].append(s)
    else:
        for d, r in zip(docs, rows):
            s_ = Stats(d.name)
            for s, f in r:
                s_.add(s, f)
            stats.append(s_)
            texts.append([s for s, _ in r])
    from writing_style.verbosity import measure

    keep = [i for i, s_ in enumerate(stats) if s_.n]
    ex: dict[str, list[str]] = {}
    if examples:
        for r in rows:
            for s, feats in r:
                if len(WORD.findall(s)) > 40:
                    continue
                for f in feats:
                    bucket = ex.setdefault(f, [])
                    if s not in bucket:
                        bucket.append(s)
        for f, bucket in ex.items():  # keep a spread, not the first few
            step = max(len(bucket) // EXAMPLES_PER_FEATURE, 1)
            ex[f] = bucket[::step][:EXAMPLES_PER_FEATURE]
    return Corpus(name, weight, [stats[i] for i in keep], ex, bool(chunk), len(docs),
                  [measure(texts[i]) for i in keep])


@dataclass
class Model:
    corpora: list[Corpus]
    created: str = ""
    pairs: dict | None = None  # writing_style.pairs.author_pairs: signature pairs and the AI pairs the author avoids

    def save(self, path: Path) -> None:
        data = {
            "version": VERSION,
            "created": self.created or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "features": list(FEATURES),
            "corpora": [{"name": c.name, "weight": c.weight, "chunked": c.chunked, "n_files": c.n_files,
                         "docs": [d.to_json() for d in c.docs], "examples": c.examples,
                         "verbosity": c.verbosity} for c in self.corpora],
            "pairs": self.pairs,
        }
        path.write_text(json.dumps(data, indent=1))

    @classmethod
    def load(cls, path: Path) -> "Model":
        data = json.loads(Path(path).read_text())
        if data.get("version") != VERSION:
            raise SystemExit(f"{path}: model version {data.get('version')} is not {VERSION}; rebuild it.")
        corpora = [Corpus(c["name"], c["weight"], [Stats.from_json(d) for d in c["docs"]], c.get("examples", {}),
                          c.get("chunked", False), c.get("n_files", 0), c.get("verbosity", []))
                   for c in data["corpora"]]
        return cls(corpora, data.get("created", ""), data.get("pairs"))

    @property
    def n(self) -> int:
        return sum(c.n for c in self.corpora)

    def combined(self, f: str) -> float:
        w = sum(c.weight for c in self.corpora)
        return sum(c.weight * c.pooled(f) for c in self.corpora) / w

    def doc_range(self, f: str) -> tuple[float, float]:
        rates = [d.rate(f) for c in self.corpora for d in c.docs]
        return min(rates), max(rates)

    def mean_len(self) -> float:
        w = sum(c.weight for c in self.corpora)
        return sum(c.weight * c.mean_len for c in self.corpora) / w

    def sd_len(self) -> float:
        return st.mean(d.sd_len for c in self.corpora for d in c.docs)

    def excluding(self, name: str) -> "Model":
        """The model without a document of this name, so a draft is never scored against itself."""
        for i, c in enumerate(self.corpora):
            for j, d in enumerate(c.docs):
                if d.name == name:
                    return self.without(i, j)
        return self

    def without(self, corpus_i: int, doc_i: int) -> "Model":
        corpora = []
        for i, c in enumerate(self.corpora):
            docs = [d for j, d in enumerate(c.docs) if not (i == corpus_i and j == doc_i)]
            verb = [v for j, v in enumerate(c.verbosity) if not (i == corpus_i and j == doc_i)]
            if docs:
                corpora.append(Corpus(c.name, c.weight, docs, c.examples, c.chunked, c.n_files, verb))
        return Model(corpora, self.created, self.pairs)


# ---------------------------------------------------------------- scoring


def zscore(rate: float, pooled: float, n_draft: int, n_model: int) -> float:
    floor = 0.5 / max(n_model, 1)
    p = min(max(pooled, floor), 1 - floor)
    return (rate - pooled) / math.sqrt(p * (1 - p) / max(n_draft, 1))


@dataclass
class Row:
    id: str
    draft: float
    combined: float
    per_corpus: dict[str, float]
    z: float
    z_per_corpus: dict[str, float]
    lo: float
    hi: float
    count: int
    ai_direction: str | None = None  # too_many / too_few: which way the AI reference leans

    @property
    def outside(self) -> bool:
        return self.draft < self.lo or self.draft > self.hi

    @property
    def off(self) -> bool:
        return abs(self.z) >= Z_OFF or self.outside

    @property
    def direction(self) -> str:
        return "too_many" if self.draft > self.combined else "too_few"

    @property
    def voice(self) -> bool:
        """Every corpus agrees the draft is off in the same direction."""
        zs = list(self.z_per_corpus.values())
        return all(z >= Z_AGREE for z in zs) or all(z <= -Z_AGREE for z in zs)

    @property
    def ai_like(self) -> bool:
        return self.ai_direction is not None and self.ai_direction == self.direction

    @property
    def verdict(self) -> str:
        if not self.off:
            return "ok"
        return "fix" if self.voice else "format"


def score(draft: Stats, model: Model, reference: dict | None = None) -> list[Row]:
    rows = []
    for f in FEATURES:
        r = draft.rate(f)
        per = {c.name: c.pooled(f) for c in model.corpora}
        zper = {c.name: zscore(r, per[c.name], draft.n, c.n) for c in model.corpora}
        comb = model.combined(f)
        lo, hi = model.doc_range(f)
        ai = None
        if reference and f not in reference.get("steered", []):
            ai = reference["features"].get(f, {}).get("direction")
        rows.append(Row(f, r, comb, per, zscore(r, comb, draft.n, model.n), zper, lo, hi, draft.counts.get(f, 0), ai))
    rows.sort(key=lambda x: -abs(x.z))
    return rows


def n_off(rows: list[Row]) -> int:
    return sum(r.off for r in rows)


def distance(draft: Stats, model: Model) -> float:
    """How far the draft sits from the author's average, in units of how much their own documents vary.

    RMS over features of (draft rate - author rate) / spread of the author's per-document rates.
    The author's own documents are never at 0: real writing wanders. A draft far below their
    band has been sanded down to the average, which reads as generated.
    """
    total = 0.0
    for f in FEATURES:
        rates = [d.rate(f) for c in model.corpora for d in c.docs]
        sd = st.pstdev(rates) if len(rates) > 1 else 0.0
        sd = max(sd, 0.01)  # rare features: a 1-point swing is not a big deal
        total += ((draft.rate(f) - model.combined(f)) / sd) ** 2
    return math.sqrt(total / len(FEATURES))


@dataclass
class Calibration:
    corpus: str
    doc: str
    off: int
    distance: float
    sd_len: float  # sentence-length spread (burstiness)


def calibrate(model: Model) -> list[Calibration]:
    """Score each of the author's own documents against the rest of the model."""
    out = []
    for i, c in enumerate(model.corpora):
        for j, d in enumerate(c.docs):
            rest = model.without(i, j)
            if rest.corpora and rest.n:
                out.append(Calibration(c.name, d.name, n_off(score(d, rest)), distance(d, rest), d.sd_len))
    return out


def bands(results: list[Calibration], attr: str = "off") -> dict[str, tuple[float, float, float]]:
    """Per corpus: (min, median, max) of one calibration measure over the author's own documents."""
    by: dict[str, list[float]] = {}
    for r in results:
        by.setdefault(r.corpus, []).append(getattr(r, attr))
    return {c: (min(v), st.median(v), max(v)) for c, v in by.items()}


def verbosity_rows(draft: dict[str, float], model: "Model") -> list[dict]:
    """The draft's verbosity measures against the range of the author's own documents, per corpus."""
    from writing_style.verbosity import MEASURES

    rows = []
    for mid, (label, verbose_when) in MEASURES.items():
        per = {}
        for c in model.corpora:
            vals = [v[mid] for v in c.verbosity if mid in v]
            if vals:
                per[c.name] = (min(vals), st.median(vals), max(vals))
        if not per:
            continue
        v = draft[mid]
        if verbose_when == "higher":
            verbose = all(v > hi for _, _, hi in per.values())
            tight = all(v < lo for lo, _, _ in per.values())
        else:
            verbose = all(v < lo for lo, _, _ in per.values())
            tight = all(v > hi for _, _, hi in per.values())
        rows.append({"id": mid, "label": label, "draft": v, "yours": per,
                     "verdict": "more verbose" if verbose else "tighter" if tight else "ok"})
    return rows


def draft_stats(doc: Doc) -> tuple[Stats, dict[str, list[str]]]:
    stats = Stats(doc.name)
    by_feature: dict[str, list[str]] = {}
    for s, feats in featurize(doc):
        stats.add(s, feats)
        for f in feats:
            by_feature.setdefault(f, []).append(s)
    return stats, by_feature


# ---------------------------------------------------------------- AI-tell reference


def build_reference(human: Corpus, machines: list[Corpus], min_auc_gap: float = 0.15) -> dict:
    """Features where every machine corpus differs from the human corpus in the same direction.

    Per feature: the essay-level AUC of each machine corpus against the human one
    (0.5 = no difference). A feature is a tell when every AUC is on the same side
    of 0.5 by at least `min_auc_gap`.
    """
    out = {}
    for f in FEATURES:
        h = [d.rate(f) for d in human.docs]
        aucs = {m.name: auc([d.rate(f) for d in m.docs], h) for m in machines}
        vals = list(aucs.values())
        if all(a >= 0.5 + min_auc_gap for a in vals):
            direction = "too_many"
        elif all(a <= 0.5 - min_auc_gap for a in vals):
            direction = "too_few"
        else:
            direction = None
        out[f] = {"human": human.pooled(f), **{m.name: m.pooled(f) for m in machines},
                  "auc": aucs, "direction": direction}
    return {"human": human.name, "machines": [m.name for m in machines], "features": out}


def auc(a: list[float], b: list[float]) -> float:
    """P(a > b) + 0.5 P(a == b): the Mann-Whitney AUC."""
    if not a or not b:
        return 0.5
    s = 0.0
    for x in a:
        for y in b:
            s += 1.0 if x > y else 0.5 if x == y else 0.0
    return s / (len(a) * len(b))
