import json, re, sys, warnings, collections
warnings.simplefilter("ignore")
sys.path.insert(0, sys.argv[2])
from analysis.load import load_all
from analysis.grammar_run import split_sentences
from analysis.grammar.classify import classify
from analysis.grammar.catalog import STRUCTURES
from analysis.stats import mann_whitney_auc
from audit_pg import fix  # same cleaning as the surface re-run
out = {}
lens = {}
for name, essays in load_all().items():
    rows = []
    lens[name] = []
    for e in essays:
        sents = split_sentences(fix(e))
        c = collections.Counter()
        for s in sents:
            c.update({h.id for h in classify(s)})
            lens[name].append(len(re.findall(r"[A-Za-z0-9']+", s)))
        rows.append({k: c[k] / len(sents) for k in STRUCTURES})
    out[name] = rows
auc = {m: {k: mann_whitney_auc([r[k] for r in out[m]], [r[k] for r in out["human_pg"]]) for k in STRUCTURES}
       for m in out if m != "human_pg"}
json.dump({"per_essay": out, "auc": auc, "sent_lens": lens}, open(sys.argv[1], "w"))
mean = lambda m, k: sum(r[k] for r in out[m]) / len(out[m])
print(f"{'structure':26} {'PG':>6} {'Claude':>6} {'Codex':>6} {'Grok':>6}   AUC(C/X/G)")
for k in sorted(STRUCTURES, key=lambda k: -abs(sum(auc[m][k] - .5 for m in auc))):
    print(f"{k:26} " + " ".join(f"{mean(m,k)*100:6.1f}" for m in out) + "   " + " ".join(f"{auc[m][k]:.2f}" for m in auc))
