"""Audit re-run of writing-patterns: fix measurement bugs, separate prompt-steered features.

Run from ~/projects/writing-patterns with PYTHONPATH=.
"""
import json
import re
import sys
import warnings

import numpy as np

warnings.simplefilter("ignore")
from analysis.features import surface  # noqa: E402
from analysis.load import load_all  # noqa: E402
from analysis.stats import mann_whitney_auc, pairwise_auc  # noqa: E402

OUT = sys.argv[1]
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
LLMS = {"claude_opus5": "Claude Opus 5", "codex_terra": "Codex Terra", "grok_46": "Grok 4.6"}
# features the generation prompt explicitly told the models to hit
STEERED = {"emdash_per_1k", "i_rate", "you_rate", "avg_sent_words", "sent_len_cv", "period_per_w", "and_rate"}
DROP = {"n_words", "log_words"}  # length is a separate layer


def fix(e) -> str:
    t = e.body.translate(QUOTES)
    if e.corpus == "human_pg":
        t = re.split(r"^\s*\*\*Notes\*\*\s*$", t, flags=re.M)[0]
        t = re.sub(r"\*\*Thanks\*\*\s+to[\s\S]*?(\n\s*\n|$)", "", t)
        t = re.sub(r"\[\d+\]", "", t)
    return t


if __name__ != "__main__":
    corp = None
else:
    corp = load_all()
    feats = {"orig": {}, "fixed": {}}
    for name, essays in corp.items():
        feats["orig"][name] = [surface(e.body) for e in essays]
        feats["fixed"][name] = [surface(fix(e)) for e in essays]
    keys = [k for k in feats["orig"]["human_pg"][0] if k not in DROP]
    unsteered = [k for k in keys if k not in STEERED]


    def mat(rows, ks):
        return np.array([[r[k] for k in ks] for r in rows], dtype=float)


    res = {"keys": keys, "steered": sorted(STEERED), "one_d": {}, "multi": {}, "means": {}}
    pg = "human_pg"
    for v in ("orig", "fixed"):
        for llm in LLMS:
            res["one_d"].setdefault(llm, {})[v] = {
                k: mann_whitney_auc([r[k] for r in feats[v][llm]], [r[k] for r in feats[v][pg]]) for k in keys}
            res["multi"].setdefault(llm, {})[v] = {
                "all": pairwise_auc(mat(feats[v][llm], keys), mat(feats[v][pg], keys))["mean"],
                "unsteered": pairwise_auc(mat(feats[v][llm], unsteered), mat(feats[v][pg], unsteered))["mean"],
            }
        for name in corp:
            res["means"].setdefault(v, {})[name] = {k: float(np.mean([r[k] for r in feats[v][name]])) for k in keys}

    # human-vs-human null: PG split into newer half vs older half (index order is newest first)
    h = feats["fixed"][pg]
    res["null_pg_halves"] = {
        "all": pairwise_auc(mat(h[:25], keys), mat(h[25:], keys))["mean"],
        "unsteered": pairwise_auc(mat(h[:25], unsteered), mat(h[25:], unsteered))["mean"],
    }
    # label-permutation null for one pair
    rng = np.random.default_rng(0)
    X = np.vstack([mat(feats["fixed"]["claude_opus5"], keys), mat(h, keys)])
    perm = []
    for i in range(20):
        idx = rng.permutation(len(X))
        perm.append(pairwise_auc(X[idx[:25]], X[idx[25:]], seed=i)["mean"])
    res["null_permuted_labels"] = float(np.mean(perm))

    # per-essay values for charts
    res["per_essay"] = {name: [{k: r[k] for k in keys} for r in feats["fixed"][name]] for name in corp}
    json.dump(res, open(OUT, "w"), indent=1)

    print("multi-feature AUC vs PG (orig -> fixed; all / unsteered features)")
    for llm, lab in LLMS.items():
        m = res["multi"][llm]
        print(f"  {lab:14} all {m['orig']['all']:.3f} -> {m['fixed']['all']:.3f}   "
              f"unsteered {m['orig']['unsteered']:.3f} -> {m['fixed']['unsteered']:.3f}")
    print(f"  null PG newer vs older half: all {res['null_pg_halves']['all']:.3f}  "
          f"unsteered {res['null_pg_halves']['unsteered']:.3f}")
    print(f"  null permuted labels (Claude+PG): {res['null_permuted_labels']:.3f}")
    print("\n1D AUC changes > 0.1 after fixes:")
    for llm, lab in LLMS.items():
        for k in keys:
            a, b = res["one_d"][llm]["orig"][k], res["one_d"][llm]["fixed"][k]
            if abs(a - b) > 0.1:
                print(f"  {lab:14} {k:20} {a:.3f} -> {b:.3f}")
    print("\nmeans (fixed): feature | PG | Claude | Codex | Grok  (* = prompt-steered)")
    for k in keys:
        row = [res["means"]["fixed"][n][k] for n in ("human_pg", *LLMS)]
        print(f"  {'*' if k in STEERED else ' '}{k:20} " + "  ".join(f"{x:8.4f}" for x in row))
