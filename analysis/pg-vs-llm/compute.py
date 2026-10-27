"""Measure every essay with writing-style's 56 features and derive what the charts need.

    uv run --with numpy python analysis/pg-vs-llm/compute.py ~/projects/writing-patterns results/essays.json

Needs the corpus (see README: fetch_pg_essays.py + the generated essays). Writes only
derived numbers, never essay text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from writing_style import model as M
from writing_style.features import FEATURES
from writing_style.sources import expand, load

CORPORA = {
    "pg": ("Paul Graham", "human/paul_graham"),
    "claude": ("Claude Opus 5", "llm/claude-opus-5/essays"),
    "codex": ("Codex Terra", "llm/codex-terra-high/essays"),
    "grok": ("Grok 4.6", "llm/grok-4.6-medium/essays"),
}
MODELS = ["claude", "codex", "grok"]
# The style brief told the models to hit these, so differences there measure obedience.
STEERED = {"em_dash", "first_person", "second_person", "long_sentence", "short_sentence", "clausal_coordination"}
FEATS = list(FEATURES)


def main(root: Path, out: Path) -> None:
    essays = {}
    for key, (_, rel) in CORPORA.items():
        docs = [load(p) for p in expand(str(root / rel))]
        essays[key] = [M.draft_stats(d)[0] for d in docs if d.sentences]
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

    uniformity = {k: spread(k) for k in CORPORA}
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

    data = {
        "corpora": {k: n for k, (n, _) in CORPORA.items()},
        "n": {k: len(v) for k, v in essays.items()},
        "fingerprint": fingerprint,
        "pca": {"points": pca, "explained": explained.tolist(), "loadings": loadings},
        "uniformity": uniformity, "sd_len": burst, "mean_len": mean_len, "len_cv": cv,
        "signatures": signatures,
        "model_id": {"accuracy": hits / len(names), "confusion": confusion},
    }
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out}; model-vs-model nearest-centroid accuracy {hits / len(names):.2f}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]))
