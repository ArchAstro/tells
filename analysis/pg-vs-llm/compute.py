"""Measure every essay with tells's 56 features and derive what the charts need.

    uv run --with numpy python analysis/pg-vs-llm/compute.py ~/projects/writing-patterns results/essays.json

Needs the corpus (see README: fetch_pg_essays.py + the generated essays). Writes only
derived numbers, never essay text.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

from tells import model as M
from tells import pairs as P
from tells.verbosity import measure as verbosity
from tells.features import FEATURES
from tells.sources import expand, load
from tells.cli import load_reference

CORPORA = {
    "pg": ("Paul Graham", "human/paul_graham"),
    "claude": ("Claude Opus 5", "llm/claude-opus-5/essays"),
    "codex": ("Codex Terra", "llm/codex-terra-high/essays"),
    "grok": ("Grok 4.6", "llm/grok-4.6-medium/essays"),
}
MODELS = ["claude", "codex", "grok"]
REF = load_reference("pg-vs-llm")
# The style brief gave rules for these, so differences there measure obedience.
STEERED = set(REF["steered"])
FEATS = list(FEATURES)
MATCH_LEN = 80  # sentences per essay for the length-matched uniformity (PG's median essay)
REPS = 30


def stats_of(name, sents):
    s = M.Stats(name)
    for t, f in sents:
        s.add(t, f)
    return s


def heldout_machine_likeness(essays):
    """Machine-likeness of each essay against a reference rebuilt without that essay."""
    out = {k: [] for k in essays}
    for k, docs in essays.items():
        for i, d in enumerate(docs):
            if d.n < 40:
                continue
            groups = {g: [x for j, x in enumerate(v) if not (g == k and j == i)] for g, v in essays.items()}
            ref = M.build_reference(M.Corpus("pg", 1.0, groups["pg"], {}),
                                    [M.Corpus(m, 1.0, groups[m], {}) for m in MODELS])
            ref["steered"] = sorted(STEERED)
            out[k].append(M.machine_likeness(d, ref))
    return out


def separation(A, B, rng, reps=20, folds=5):
    """Cross-validated AUC of a nearest-centroid score (B-like minus A-like), in pooled-sd units."""
    aucs = []
    for _ in range(reps):
        ia, ib = list(range(len(A))), list(range(len(B)))
        rng.shuffle(ia)
        rng.shuffle(ib)
        sa, sb = [], []
        for k in range(folds):
            ta, tb = set(ia[k::folds]), set(ib[k::folds])
            TA, TB = A[[i for i in ia if i not in ta]], B[[i for i in ib if i not in tb]]
            sd = np.maximum(np.vstack([TA, TB]).std(0, ddof=1), 0.01)
            ca, cb = TA.mean(0), TB.mean(0)
            def score(x):
                return float(np.linalg.norm((x - ca) / sd) - np.linalg.norm((x - cb) / sd))
            sa += [score(A[i]) for i in ta]
            sb += [score(B[i]) for i in tb]
        aucs.append(M.auc(sb, sa))
    return float(np.mean(aucs))


def main(root: Path, out: Path) -> None:
    essays, counts, verb, sents = {}, {}, {}, {}
    for key, (_, rel) in CORPORA.items():
        docs = [d for d in (load(p) for p in expand(str(root / rel))) if d.sentences]
        sents[key] = [M.featurize(d) for d in docs]
        essays[key] = [stats_of(d.name, s) for d, s in zip(docs, sents[key])]
        counts[key] = P.count(docs)
        verb[key] = [verbosity(d.sentences) for d in docs]
        print(key, len(essays[key]), file=sys.stderr)

    X = {k: np.array([[s.rate(f) for f in FEATS] for s in v]) for k, v in essays.items()}
    pg_mu, pg_sd = X["pg"].mean(0), X["pg"].std(0, ddof=1)
    sd_floor = np.maximum(pg_sd, 0.01)

    # 1. fingerprint: Glass's delta (model mean - PG mean) / PG sd, plus essay-level AUC
    fingerprint = {}
    for i, f in enumerate(FEATS):
        pg_col = list(X["pg"][:, i])
        fingerprint[f] = {
            "label": FEATURES[f].label,
            "steered": f in STEERED,
            "mean": {k: float(X[k][:, i].mean()) for k in CORPORA},
            "delta": {m: float((X[m][:, i].mean() - pg_mu[i]) / sd_floor[i]) for m in MODELS},
            "auc": {m: M.auc(list(X[m][:, i]), pg_col) for m in MODELS},
        }

    # 2. map: PCA on unsteered features, standardized by PG, fit on every essay
    keep = [i for i, f in enumerate(FEATS) if f not in STEERED and pg_sd[i] > 0]
    Z = {k: (X[k][:, keep] - pg_mu[keep]) / sd_floor[keep] for k in CORPORA}
    allz = np.vstack([Z[k] for k in CORPORA])
    center = allz.mean(0)
    _, sv, vt = np.linalg.svd(allz - center, full_matrices=False)
    explained = (sv ** 2 / (sv ** 2).sum())[:2]
    pca = {k: ((Z[k] - center) @ vt[:2].T).tolist() for k in CORPORA}
    loadings = sorted(((FEATS[keep[j]], float(vt[0, j]), float(vt[1, j])) for j in range(len(keep))),
                      key=lambda x: -(x[1] ** 2 + x[2] ** 2))[:6]

    # 3. uniformity: each essay's distance from its own group's average, in PG-sd units (RMS over features)
    def spread(k):
        mu = X[k].mean(0)
        return [float(np.sqrt((((row - mu) / sd_floor) ** 2).mean())) for row in X[k]]

    uniformity_raw = {k: spread(k) for k in CORPORA}

    # Shorter essays give noisier rates, and PG's run shorter, so the raw spread overstates his variety.
    # Length-matched: every essay of at least MATCH_LEN sentences, subsampled to MATCH_LEN, REPS times;
    # PG's sd (the unit) comes from the same subsamples. Each essay's value is its mean over the reps.
    rng = random.Random(1)
    long_ = {k: [s for s in v if len(s) >= MATCH_LEN] for k, v in sents.items()}
    acc = {k: np.zeros(len(v)) for k, v in long_.items()}
    for _ in range(REPS):
        Xs = {k: np.array([[stats_of("", rng.sample(s, MATCH_LEN)).rate(f) for f in FEATS] for s in v])
              for k, v in long_.items()}
        sd = np.maximum(Xs["pg"].std(0, ddof=1), 0.01)
        for k in CORPORA:
            acc[k] += np.sqrt((((Xs[k] - Xs[k].mean(0)) / sd) ** 2).mean(1))
    uniformity = {k: (acc[k] / REPS).tolist() for k in CORPORA}
    burst = {k: [s.sd_len for s in v] for k, v in essays.items()}
    mean_len = {k: [s.mean_len for s in v] for k, v in essays.items()}
    # burstiness relative to length, so shorter sentences don't automatically mean less spread
    cv = {k: [s.sd_len / s.mean_len if s.mean_len else 0 for s in v] for k, v in essays.items()}

    # 4. signatures: where each model is most unlike the other two, in PG-sd units
    signatures = {}
    for m in MODELS:
        others = [o for o in MODELS if o != m]
        rows = []
        for i, f in enumerate(FEATS):
            gap = (X[m][:, i].mean() - np.mean([X[o][:, i].mean() for o in others])) / sd_floor[i]
            rows.append((f, float(gap)))
        rows.sort(key=lambda r: -abs(r[1]))
        signatures[m] = [{"id": f, "label": FEATURES[f].label, "gap": g,
                          "mean": {k: float(X[k][:, FEATS.index(f)].mean()) for k in CORPORA}}
                         for f, g in rows[:4]]

    # how well can you tell the models apart from each other? nearest-centroid, leave-one-out, unsteered
    names = [m for m in MODELS for _ in range(len(Z[m]))]
    pts = np.vstack([Z[m] for m in MODELS])
    hits = 0
    confusion = {a: {b: 0 for b in MODELS} for a in MODELS}
    for i, (p, truth) in enumerate(zip(pts, names)):
        cents = {}
        for m in MODELS:
            idx = [j for j, n in enumerate(names) if n == m and j != i]
            cents[m] = pts[idx].mean(0)
        guess = min(MODELS, key=lambda m: np.linalg.norm(p - cents[m]))
        confusion[truth][guess] += 1
        hits += guess == truth

    # how well can you tell each model from PG? cross-validated, unsteered features only;
    # null: PG against PG, split at random
    srng = random.Random(2)
    XU = {k: X[k][:, keep] for k in CORPORA}
    nulls = []
    for _ in range(10):
        idx = list(range(len(XU["pg"])))
        srng.shuffle(idx)
        half = len(idx) // 2
        nulls.append(separation(XU["pg"][idx[:half]], XU["pg"][idx[half:]], srng, reps=5))
    separation_stats = {"features": len(keep), "auc": {m: separation(XU["pg"], XU[m], srng) for m in MODELS},
                        "null_pg_halves": {"mean": float(np.mean(nulls)), "min": float(min(nulls)), "max": float(max(nulls))}}

    # 5. word pairs: what PG uses more than every model, and what every model uses more than PG
    pg_vs = [P.log_odds(counts["pg"], counts[m]) for m in MODELS]
    pool = P.merge([counts[m] for m in MODELS])

    def pair_rows(rows):
        return [{"pair": " ".join(k), "z": z, "per10k": {c: counts[c].per10k(k) for c in CORPORA}} for k, z in rows[:12]]

    word_pairs = {
        "pg_more": pair_rows(P.consistent(pg_vs, counts["pg"], 8)),
        "models_more": pair_rows(P.consistent([{k: -v for k, v in z.items()} for z in pg_vs], pool, 8)),
    }

    data = {
        "corpora": {k: n for k, (n, _) in CORPORA.items()},
        "n": {k: len(v) for k, v in essays.items()},
        "fingerprint": fingerprint,
        "pca": {"points": pca, "explained": explained.tolist(), "loadings": loadings},
        "uniformity": uniformity, "uniformity_raw": uniformity_raw, "match_len": MATCH_LEN, "sd_len": burst, "mean_len": mean_len, "len_cv": cv,
        "signatures": signatures,
        "pairs": word_pairs,
        "verbosity": verb,
        "verbosity_auc": {mid: {m: M.auc([v[mid] for v in verb[m]], [v[mid] for v in verb["pg"]]) for m in MODELS}
                          for mid in verb["pg"][0]},
        "model_id": {"accuracy": hits / len(names), "confusion": confusion},
        # held out: each essay scored against a reference rebuilt without it; essays under
        # 40 sentences are skipped, as `check` and `build` skip them
        "machine_likeness": heldout_machine_likeness(essays),
        "machine_likeness_in_sample": {k: [x for x in (M.machine_likeness(s, REF) for s in v) if x is not None]
                                       for k, v in essays.items()},
        "steered": sorted(STEERED),
        "separation": separation_stats,
    }
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out}; model-vs-model nearest-centroid accuracy {hits / len(names):.2f}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]))
