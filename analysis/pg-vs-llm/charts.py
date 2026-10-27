"""Render docs/pg-vs-llm.html from results/essays.json (compute.py) and results/audit_pg.json (audit_pg.py).

    python3 analysis/pg-vs-llm/charts.py analysis/pg-vs-llm/results docs/pg-vs-llm.html

Pure standard library: one self-contained page, light and dark, tooltips, a table under every chart.
"""
import json
import statistics as st
import sys
from html import escape
from pathlib import Path

RES = Path(sys.argv[1])
OUT = Path(sys.argv[2])
D = json.loads((RES / "essays.json").read_text())
AUDIT = json.loads((RES / "audit_pg.json").read_text())

KEYS = ["pg", "claude", "codex", "grok"]
MODELS = KEYS[1:]
NAME = D["corpora"]
SLOT = {"pg": "pg", "claude": "s1", "codex": "s2", "grok": "s3"}
AUDIT_KEY = {"pg": "human_pg", "claude": "claude_opus5", "codex": "codex_terra", "grok": "grok_46"}
FP = D["fingerprint"]

SHORT = {
    "contraction": "contractions (it's, don't)",
    "short_sentence": "sentences of 5 words or fewer",
    "long_sentence": "sentences of 30+ words",
    "starts_with_conjunction": "starts with And / But / So",
    "list_of_three": "lists of three (X, Y and Z)",
    "clausal_coordination": "two clauses joined by and / but",
    "hedge": "hedges (pretty, just, I think)",
    "zero_relative_clause": "zero relative (the thing you built)",
    "purpose_infinitive": "purpose clause (… to see why)",
    "imperative_start": "starts with a verb (Skim it…)",
    "imperative": "imperative clause",
    "infinitival_complement": "wanted to / had to / tried to",
    "gerund_complement": "gerund object (started building)",
    "first_person": "I / my / we",
    "second_person": "you / your",
    "not_x_but_y": "not X but Y",
    "get_passive": "get-passive (got fired)",
    "conditional_if": "if clauses",
    "wh_question": "wh- questions",
    "polar_question": "yes/no questions",
    "colon_label": "Label: openers",
    "because_adjunct": "because clauses",
    "free_relative": "free relative (what you need)",
    "em_dash": "dash asides",
    "there_existential": "there is / there are",
    "concessive": "although / even though",
    "ditransitive": "gave them X",
    "fragment": "verbless fragments",
}


def short(f):
    return SHORT.get(f, f.replace("_", " "))


def ring(cx, cy, key, tip, r=5):
    cls = "m pg" if key == "pg" else f"m {SLOT[key]}"
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" class="{cls}" data-tip="{escape(tip)}"/>'


def legend():
    out = []
    for k in KEYS:
        out.append(f'<span class="lg"><svg viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" class="m {SLOT[k]}"/></svg>'
                   f'{escape(NAME[k])}{" (human)" if k == "pg" else ""}</span>')
    return '<div class="legend">' + "".join(out) + "</div>"


PARTS = {}  # key -> list of (w, h, body) panels, for the standalone README images


def svg(w, h, label, body, key=None):
    if key:
        PARTS.setdefault(key, []).append((w, h, "".join(body)))
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">{"".join(body)}</svg>'


def table(head, rows):
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<details><summary>Show the numbers</summary><table><tr>{th}</tr>{tr}</table></details>"


def jitter(i, n=7):
    return ((i * 37) % n - n // 2) / (n // 2)


# ---------------------------------------------------------------- 1. the map
pts = D["pca"]["points"]
allx = [p[0] for k in KEYS for p in pts[k]]
ally = [p[1] for k in KEYS for p in pts[k]]
W, H, L, R, T, B = 720, 470, 24, 24, 24, 44
xlo, xhi = min(allx) - 0.5, max(allx) + 0.5
ylo, yhi = min(ally) - 0.5, max(ally) + 0.5


def mx(v):
    return L + (v - xlo) / (xhi - xlo) * (W - L - R)


def my(v):
    return H - B - (v - ylo) / (yhi - ylo) * (H - T - B)


g = [f'<rect x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}" class="frame"/>',
     f'<text x="{L}" y="{H - 14}" class="axis">← contractions, And/But openers, "to" purpose clauses</text>',
     f'<text x="{W - R}" y="{H - 14}" class="axis" text-anchor="end">commands, lists of three →</text>']
cent = {}
for k in KEYS:
    xs, ys = [p[0] for p in pts[k]], [p[1] for p in pts[k]]
    cent[k] = (st.mean(xs), st.mean(ys))
    for i, (x, y) in enumerate(pts[k]):
        g.append(ring(mx(x), my(y), k, f"{NAME[k]}, essay {i + 1}", 5 if k == "pg" else 4.5))
for k in KEYS:
    cx = cent[k][0]
    ys = [p[1] for p in pts[k]]
    # label just outside the cluster: above for PG and Codex, below for Claude and Grok
    if k in ("pg", "codex"):
        ly, dy = my(max(ys)), -10
    else:
        ly, dy = my(min(ys)), 20
    g.append(f'<text x="{mx(cx)}" y="{ly + dy}" class="dl" text-anchor="middle">{escape(NAME[k])}</text>')
chart_map = svg(W, H, "Map of every essay by writing features", g, "map")
ex = D["pca"]["explained"]
table_map = table(["Group", "Essays", "Centre (x, y)"],
                  [[escape(NAME[k]), D["n"][k], f"{cent[k][0]:.2f}, {cent[k][1]:.2f}"] for k in KEYS])

# ---------------------------------------------------------------- 2. uniformity
panels = [
    ("How far each essay sits from its own author's average", "uniformity", 1,
     "distance in units of PG's essay-to-essay spread (RMS over 56 features)", 0, None),
    ("How much sentence length varies inside each essay", "sd_len", 1, "standard deviation of words per sentence", 0, None),
]
uni_svgs, uni_rows = [], []
PW, PH, PL, PR = 720, 170, 120, 40
for title, key, mult, unit, lo, hi in panels:
    vals = {k: [v * mult for v in D[key][k]] for k in KEYS}
    hi = hi or max(max(v) for v in vals.values()) * 1.05

    def px(v, lo=lo, hi=hi):
        return PL + (v - lo) / (hi - lo) * (PW - PL - PR)

    g = [f'<text x="0" y="14" class="ptitle">{escape(title)}</text>']
    steps = 4
    for i in range(steps + 1):
        t = lo + (hi - lo) * i / steps
        g.append(f'<line x1="{px(t)}" x2="{px(t)}" y1="26" y2="{PH - 26}" class="grid"/>'
                 f'<text x="{px(t)}" y="{PH - 10}" class="tick" text-anchor="middle">{t:.1f}</text>')
    for r, k in enumerate(KEYS):
        y = 44 + r * 30
        g.append(f'<text x="{PL - 12}" y="{y + 4}" class="tick" text-anchor="end">{escape(NAME[k])}</text>')
        for i, v in enumerate(vals[k]):
            g.append(ring(px(v), y + jitter(i) * 8, k, f"{NAME[k]}, essay {i + 1}: {v:.2f}", 3.6))
        m = st.median(vals[k])
        g.append(f'<line x1="{px(m)}" x2="{px(m)}" y1="{y - 12}" y2="{y + 12}" class="med"/>'
                 f'<text x="{PW - PR + 6}" y="{y + 4}" class="val">{m:.2f}</text>')
    g.append(f'<text x="{PW - PR + 6}" y="30" class="note">median</text>')
    uni_svgs.append(svg(PW, PH, title, g, "uniformity") + f'<p class="unit">{escape(unit)}</p>')
    uni_rows.append([escape(title)] + [f"{st.median(vals[k]):.2f}" for k in KEYS])
table_uni = table(["Measure (median)"] + [NAME[k] for k in KEYS], uni_rows)
u = {k: st.median(D["uniformity"][k]) for k in KEYS}

# ---------------------------------------------------------------- 3. fingerprint
unsteered = sorted((f for f in FP if not FP[f]["steered"]),
                   key=lambda f: -max(abs(v) for v in FP[f]["delta"].values()))[:14]
steered = sorted((f for f in FP if FP[f]["steered"]), key=lambda f: -max(abs(v) for v in FP[f]["delta"].values()))
FW, FL, FR, RH = 720, 250, 20, 24
lo, hi = -5, 5
FH = 60 + (len(unsteered) + len(steered)) * RH + 40


def fx(v):
    return FL + (max(min(v, hi), lo) - lo) / (hi - lo) * (FW - FL - FR)


g = [f'<rect x="{fx(-1)}" y="30" width="{fx(1) - fx(-1)}" height="{FH - 60}" class="band"/>',
     f'<text x="{fx(0)}" y="22" class="note" text-anchor="middle">Paul Graham ± one essay-to-essay spread</text>']
for t in range(lo, hi + 1):
    g.append(f'<line x1="{fx(t)}" x2="{fx(t)}" y1="30" y2="{FH - 30}" class="{"zero" if t == 0 else "grid"}"/>'
             f'<text x="{fx(t)}" y="{FH - 14}" class="tick" text-anchor="middle">{t:+d}</text>')
g.append(f'<text x="{fx(lo)}" y="{FH}" class="axis">← uses it less than PG</text>'
         f'<text x="{fx(hi)}" y="{FH}" class="axis" text-anchor="end">uses it more than PG →</text>')
y = 44
fp_rows = []
for group, feats in (("", unsteered), ("The brief told the models to change these", steered)):
    if group:
        y += 8
        g.append(f'<text x="0" y="{y}" class="ptitle">{escape(group)}</text>')
        y += 18
    for f in feats:
        d = FP[f]["delta"]
        vals = list(d.values())
        g.append(f'<line x1="{FL}" x2="{FW - FR}" y1="{y}" y2="{y}" class="row"/>'
                 f'<line x1="{fx(min(vals))}" x2="{fx(max(vals))}" y1="{y}" y2="{y}" class="span"/>'
                 f'<text x="{FL - 12}" y="{y + 4}" class="tick" text-anchor="end">{escape(short(f))}</text>')
        for m in MODELS:
            pg_rate = FP[f]["mean"]["pg"] * 100
            tip = (f"{NAME[m]}: {FP[f]['mean'][m] * 100:.1f} per 100 sentences vs PG {pg_rate:.1f} "
                   f"({d[m]:+.1f} PG spreads; AUC {FP[f]['auc'][m]:.2f})")
            g.append(ring(fx(d[m]), y, m, tip, 5.5))
        fp_rows.append([escape(short(f)) + (" *" if FP[f]["steered"] else "")]
                       + [f"{FP[f]['mean'][k] * 100:.1f}" for k in KEYS] + [f"{d[m]:+.1f}" for m in MODELS])
        y += RH
chart_fp = svg(FW, FH + 6, "Feature differences from Paul Graham", g, "fingerprint")
table_fp = table(["Feature (per 100 sentences)"] + [NAME[k] for k in KEYS] + [f"{NAME[m]} Δ" for m in MODELS], fp_rows)

# ---------------------------------------------------------------- 4. signatures
SW, SL, SR = 230, 4, 40
sig_cards = []
sig_rows = []
for m in MODELS:
    g = []
    yy = 8
    for s in D["signatures"][m][:3]:
        vals = {k: s["mean"][k] * 100 for k in KEYS}
        top = max(vals.values()) * 1.1 or 1

        def sx(v, top=top):
            return SL + v / top * (SW - SL - SR)

        g.append(f'<text x="{SL}" y="{yy + 12}" class="tick">{escape(short(s["id"]))}</text>')
        yy += 26
        g.append(f'<line x1="{SL}" x2="{SW - SR}" y1="{yy}" y2="{yy}" class="row"/>')
        for k in KEYS:
            r = 6.5 if k == m else 4.5
            g.append(ring(sx(vals[k]), yy, k, f"{NAME[k]}: {vals[k]:.1f} per 100 sentences", r))
        g.append(f'<text x="{SW - SR + 8}" y="{yy + 4}" class="val">{vals[m]:.1f}</text>')
        yy += 22
        sig_rows.append([escape(NAME[m]), escape(short(s["id"]))] + [f"{vals[k]:.1f}" for k in KEYS])
    sig_cards.append(f'<div class="sig"><h3><svg viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" class="m {SLOT[m]}"/>'
                     f'</svg>{escape(NAME[m])}</h3>{svg(SW, yy, NAME[m] + " signature", g, "accents")}</div>')
table_sig = table(["Model", "Feature (per 100 sentences)"] + [NAME[k] for k in KEYS], sig_rows)
acc = D["model_id"]["accuracy"]
conf = D["model_id"]["confusion"]
right = sum(conf[m][m] for m in MODELS)

# ---------------------------------------------------------------- 4b. verbosity
verb_svgs, verb_rows = [], []
for mid, title, unit in (("filler", "Filler phrases (in order to, the fact that, when it comes to…)", "per 1,000 words"),
                         ("restate", "How much each sentence repeats the one before", "content-word overlap"),
                         ("density", "Content words per word", "share of words")):
    vals = {k: [v[mid] for v in D["verbosity"][k]] for k in KEYS}
    lo = min(min(v) for v in vals.values())
    lo = 0 if mid != "density" else round(lo - 0.01, 2)
    hi = max(max(v) for v in vals.values()) * 1.05

    def px(v, lo=lo, hi=hi):
        return PL + (v - lo) / (hi - lo) * (PW - PL - PR)

    g = [f'<text x="0" y="14" class="ptitle">{escape(title)}</text>',
         f'<text x="{PW - PR}" y="14" class="note" text-anchor="end">{escape(unit)}</text>']
    for i in range(5):
        t = lo + (hi - lo) * i / 4
        g.append(f'<line x1="{px(t)}" x2="{px(t)}" y1="26" y2="{PH - 26}" class="grid"/>'
                 f'<text x="{px(t)}" y="{PH - 10}" class="tick" text-anchor="middle">{t:.2f}</text>')
    for r, k in enumerate(KEYS):
        y = 44 + r * 30
        g.append(f'<text x="{PL - 12}" y="{y + 4}" class="tick" text-anchor="end">{escape(NAME[k])}</text>')
        for i, v in enumerate(vals[k]):
            g.append(ring(px(v), y + jitter(i) * 8, k, f"{NAME[k]}, essay {i + 1}: {v:.3f}", 3.6))
        m = st.median(vals[k])
        g.append(f'<line x1="{px(m)}" x2="{px(m)}" y1="{y - 12}" y2="{y + 12}" class="med"/>'
                 f'<text x="{PW - PR + 6}" y="{y + 4}" class="val">{m:.2f}</text>')
    verb_svgs.append(svg(PW, PH, title, g, "verbosity"))
    verb_rows.append([escape(title)] + [f"{st.median(vals[k]):.3f}" for k in KEYS])
table_verb = table(["Measure (median)"] + [NAME[k] for k in KEYS], verb_rows)

# ---------------------------------------------------------------- 5. word pairs
pair_svgs, pair_rows = [], []
for title, rows in (("Paul Graham uses these more than every model", D["pairs"]["pg_more"][:12]),
                    ("Every model uses these more than Paul Graham", D["pairs"]["models_more"][:12])):
    top = -(-max(max(r["per10k"].values()) for r in rows) // 10) * 10  # round up to a multiple of 10
    QL, QR, QH = 120, 40, 34 + len(rows) * 24 + 30

    def qx(v, top=top):
        return QL + v / top * (PW - QL - QR)

    g = [f'<text x="0" y="14" class="ptitle">{escape(title)}</text>',
         f'<text x="{PW - QR}" y="14" class="note" text-anchor="end">per 10,000 words</text>']
    step = 10 if top <= 60 else 20
    for t in range(0, int(top) + 1, step):
        g.append(f'<line x1="{qx(t)}" x2="{qx(t)}" y1="24" y2="{QH - 26}" class="grid"/>'
                 f'<text x="{qx(t)}" y="{QH - 10}" class="tick" text-anchor="middle">{t}</text>')
    for r_i, r in enumerate(rows):
        y = 38 + r_i * 24
        v = r["per10k"]
        mv = [v[m] for m in MODELS]
        lo_, hi_ = min(mv + [v["pg"]]), max(mv + [v["pg"]])
        g.append(f'<text x="{QL - 12}" y="{y + 4}" class="tick pairlbl" text-anchor="end">{escape(r["pair"])}</text>'
                 f'<line x1="{QL}" x2="{PW - QR}" y1="{y}" y2="{y}" class="row"/>'
                 f'<line x1="{qx(lo_)}" x2="{qx(hi_)}" y1="{y}" y2="{y}" class="span"/>')
        for k in MODELS + ["pg"]:
            g.append(ring(qx(v[k]), y, k, f"{NAME[k]}: '{r['pair']}' {v[k]:.1f} per 10,000 words", 5.5 if k == "pg" else 5))
        pair_rows.append([escape(title.split(" uses")[0]), escape(r["pair"])] + [f"{v[k]:.1f}" for k in KEYS])
    pair_svgs.append(svg(PW, QH, title, g, "pairs"))
table_pairs = table(["Side", "Word pair"] + [NAME[k] for k in KEYS], pair_rows)

# ---------------------------------------------------------------- 6. told vs did
told = [
    ("Em dashes per 1,000 characters", "emdash_per_1k", 1, 'Brief: "almost no em dashes (~0.2)"', 0.2, 0, 0.5),
    ('"I" per 100 words', "i_rate", 100, 'Brief: "you more than I"', None, 0, 1.2),
    ("Average words per sentence", "avg_sent_words", 1, 'Brief: "median ~15 words"', 15, 8, 18),
]
told_svgs, told_rows = [], []
for title, key, mult, said, target, lo_, hi_ in told:
    def px(v, lo_=lo_, hi_=hi_):
        return PL + (min(max(v, lo_), hi_) - lo_) / (hi_ - lo_) * (PW - PL - PR)

    g = [f'<text x="0" y="14" class="ptitle">{escape(title)}</text>',
         f'<text x="{PW - PR}" y="14" class="note" text-anchor="end">{escape(said)}</text>']
    for i in range(5):
        t = lo_ + (hi_ - lo_) * i / 4
        g.append(f'<line x1="{px(t)}" x2="{px(t)}" y1="24" y2="{PH - 30}" class="grid"/>'
                 f'<text x="{px(t)}" y="{PH - 14}" class="tick" text-anchor="middle">{t:g}</text>')
    if target is not None:
        g.append(f'<line x1="{px(target)}" x2="{px(target)}" y1="24" y2="{PH - 30}" class="ref"/>')
    row = [escape(title), escape(said)]
    for r, k in enumerate(KEYS):
        yv = 40 + r * 26
        v = st.mean(e[key] * mult for e in AUDIT["per_essay"][AUDIT_KEY[k]])
        g.append(f'<text x="{PL - 12}" y="{yv + 4}" class="tick" text-anchor="end">{escape(NAME[k])}</text>'
                 f'<line x1="{PL}" x2="{PW - PR}" y1="{yv}" y2="{yv}" class="row"/>')
        g.append(ring(px(v), yv, k, f"{NAME[k]}: {v:.2f}", 6))
        g.append(f'<text x="{px(v) + 11}" y="{yv + 4}" class="val">{v:.2f}</text>')
        row.append(f"{v:.2f}")
    told_svgs.append(svg(PW, PH, title, g, "told"))
    told_rows.append(row)
table_told = table(["Measure", "What the brief said"] + [NAME[k] for k in KEYS], told_rows)

multi = AUDIT["multi"]
nulls = AUDIT["null_pg_halves"]
fd = {m: FP["contraction"]["delta"][m] for m in MODELS}

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Three Models, One Brief</title>
<style>
:root {{ color-scheme: light;
  --surface:#fcfcfb; --page:#f4f3ef; --text:#0b0b0b; --text2:#52514e; --muted:#898781; --grid:#e4e3dd; --axis:#c3c2b7;
  --band:#ecebe5; --pg:#0b0b0b; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --ref:#52514e; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark;
  --surface:#1a1a19; --page:#121211; --text:#f0efec; --text2:#c3c2b7; --muted:#898781; --grid:#2a2a28; --axis:#383835;
  --band:#242422; --pg:#f0efec; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --ref:#c3c2b7; }} }}
:root[data-theme="dark"] {{ color-scheme: dark;
  --surface:#1a1a19; --page:#121211; --text:#f0efec; --text2:#c3c2b7; --muted:#898781; --grid:#2a2a28; --axis:#383835;
  --band:#242422; --pg:#f0efec; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --ref:#c3c2b7; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--page); color:var(--text); font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:800px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:30px; line-height:1.15; margin:0 0 10px; letter-spacing:-.01em; }}
h2 {{ font-size:19px; line-height:1.3; margin:0 0 6px; }}
h3 {{ font-size:14px; margin:0 0 4px; display:flex; align-items:center; gap:6px; }}
h3 svg {{ width:14px; height:14px; }}
p {{ margin:0 0 12px; color:var(--text2); }}
.lede {{ font-size:16px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:20px 0; }}
.stat {{ background:var(--surface); border:1px solid var(--grid); border-radius:10px; padding:14px; }}
.stat b {{ display:block; font-size:26px; line-height:1.1; font-variant-numeric:tabular-nums; }}
.stat span {{ font-size:13px; color:var(--text2); }}
.card {{ background:var(--surface); border:1px solid var(--grid); border-radius:10px; padding:20px; margin:24px 0; overflow-x:auto; }}
svg {{ width:100%; height:auto; display:block; overflow:visible; }}
.card > svg, .wide {{ min-width:600px; }}
.sigs {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:8px; }}
.frame {{ fill:none; stroke:var(--grid); }}
.grid {{ stroke:var(--grid); stroke-width:1; }} .row {{ stroke:var(--grid); stroke-width:1; }}
.zero {{ stroke:var(--pg); stroke-width:1.5; }} .band {{ fill:var(--band); }}
.ref {{ stroke:var(--ref); stroke-width:1.5; stroke-dasharray:4 4; }}
.span {{ stroke:var(--axis); stroke-width:2; }} .med {{ stroke:var(--text); stroke-width:2; }}
.tick {{ fill:var(--text2); font-size:12px; }} .pairlbl {{ font-style:italic; font-size:13px; }} .axis {{ fill:var(--muted); font-size:12px; }}
.note {{ fill:var(--muted); font-size:12px; }} .val {{ fill:var(--text2); font-size:12px; font-variant-numeric:tabular-nums; }}
.unit {{ font-size:12px; color:var(--muted); margin:2px 0 14px; }}
.ptitle {{ fill:var(--text); font-size:13px; font-weight:600; }}
.dl {{ fill:var(--text); font-size:13px; font-weight:650; paint-order:stroke; stroke:var(--surface); stroke-width:4px; }}
.m {{ stroke:var(--surface); stroke-width:1.5; fill-opacity:.85; }}
.m.pg {{ fill:none; stroke:var(--pg); stroke-width:1.8; }}
.m.s1 {{ fill:var(--s1); }} .m.s2 {{ fill:var(--s2); }} .m.s3 {{ fill:var(--s3); }}
.m:hover {{ stroke:var(--text); stroke-width:2.5; }}
.legend {{ display:flex; flex-wrap:wrap; gap:16px; margin:8px 0 12px; font-size:13px; color:var(--text2); }}
.lg {{ display:inline-flex; align-items:center; gap:6px; }} .lg svg {{ width:14px; height:14px; flex:none; }}
details {{ margin-top:12px; font-size:13px; color:var(--text2); }} summary {{ cursor:pointer; }}
table {{ border-collapse:collapse; width:100%; margin-top:8px; font-variant-numeric:tabular-nums; }}
th,td {{ text-align:left; padding:4px 8px; border-bottom:1px solid var(--grid); }}
#tip {{ position:fixed; pointer-events:none; background:var(--surface); color:var(--text); border:1px solid var(--axis);
  border-radius:6px; padding:6px 8px; font-size:12px; box-shadow:0 4px 14px rgb(0 0 0/.15); display:none; max-width:300px; z-index:10; }}
ol li {{ margin:6px 0; color:var(--text2); }}
</style></head><body><main>
<h1>Three models, one style brief, and none of them write like Paul Graham</h1>
<p class="lede">We gave Claude Opus 5, Codex Terra and Grok 4.6 the same long, careful brief on how Paul Graham writes,
and had each write 25 essays on his topics. Then we measured all 125 essays, sentence by sentence, on 56 grammar and
style features.</p>
<div class="stats">
<div class="stat"><b>≥ {min(multi[m]['fixed']['unsteered'] for m in AUDIT['multi']):.2f}</b><span>AUC separating each model from PG, even ignoring everything the brief steered (PG vs PG: {nulls['unsteered']:.2f})</span></div>
<div class="stat"><b>{right} of {sum(D['n'][m] for m in MODELS)}</b><span>model essays a simple classifier assigns to the right model</span></div>
<div class="stat"><b>{min(u[m] for m in MODELS):.2f}–{max(u[m] for m in MODELS):.2f} vs {u['pg']:.2f}</b><span>how much each model's essays vary from each other, vs PG's</span></div>
</div>

<section class="card">
<h2>Every essay, placed by how it's written</h2>
<p>Each dot is one essay, positioned by the two strongest patterns across the features the brief left alone. Paul Graham spreads
across the map. Each model sits in its own tight patch; only one of his 50 essays strays near a model.</p>
{legend()}
{chart_map}
<p class="unit">Principal components of features standardised against Paul Graham; the axes explain {ex[0] * 100:.0f}% and
{ex[1] * 100:.0f}% of the variation. Labels name the features that load most on the horizontal axis.</p>
{table_map}
</section>

<section class="card">
<h2>The models' essays are more alike than Paul Graham's</h2>
<p>A person's essays wander: different moods, different years, different arguments. Each model's essays sit
{(1 - max(u[m] for m in MODELS) / u['pg']) * 100:.0f}–{(1 - min(u[m] for m in MODELS) / u['pg']) * 100:.0f}% closer to
their own average than Paul Graham's do to his. Codex and Grok also keep their sentence lengths more even; Claude
varies its sentences about as much as he does.</p>
{legend()}
<div class="wide">{"".join(uni_svgs)}</div>
{table_uni}
</section>

<section class="card">
<h2>Where each model differs from Paul Graham</h2>
<p>The shaded band is how much Paul Graham's own essays vary. A dot outside it is further from him than he usually
is from himself. All three models leave out the same things he does a lot: purpose clauses, "wanted to", hedges,
sentences that start with And or But. Where they differ from each other is often more interesting. Claude matches his
contractions; Codex and Grok sit about {abs(fd['codex']):.0f} spreads below.</p>
{legend()}
{chart_fp}
{table_fp}
</section>

<section class="card">
<h2>Each model has its own accent</h2>
<p>These are the features where each model is furthest from the other two. Together they're enough to name the model
for {right} of {sum(D['n'][m] for m in MODELS)} essays, using nothing more than distance to each model's average.</p>
{legend()}
<div class="sigs">{"".join(sig_cards)}</div>
{table_sig}
</section>

<section class="card">
<h2>The models aren't wordy. They're compressed.</h2>
<p>The usual complaint about AI prose is padding. Here it's the other way round. Most model essays contain no filler
phrases at all, where Paul Graham averages about one per thousand words. The models repeat the previous sentence less,
and Codex packs far more content words into each sentence. (The brief did discourage hedging and throat-clearing, so the filler
gap is partly steered; the rest wasn't asked for.) Clipped, dense prose is its own tell.</p>
{legend()}
<div class="wide">{"".join(verb_svgs)}</div>
{table_verb}
</section>

<section class="card">
<h2>Paul Graham speculates; the models define</h2>
<p>Word pairs that every model uses more than Paul Graham, or he uses more than every model, in at least 8 essays
(subject nouns like "the founder" left out). He hedges and looks ahead: <i>would be</i>, <i>it will</i>, <i>at least</i>,
<i>a lot</i>. The models pin things down: <i>is a</i>, <i>the thing</i>, <i>the person who</i>, <i>is why</i>,
<i>the obvious</i>.</p>
{legend()}
<div class="wide">{"".join(pair_svgs)}</div>
{table_pairs}
</section>

<section class="card">
<h2>Where the brief gave a rule, the models overshot it</h2>
<p>The dashed line is what the brief asked for. Told "almost no em dashes", the models used none, though Paul Graham
does. Told "you more than I", they all but stopped saying I. Told "~15 words", they came in shorter.</p>
{legend()}
<div class="wide">{"".join(told_svgs)}</div>
{table_told}
</section>

<section class="card">
<h2>How this was measured, and what to doubt</h2>
<ol>
<li><b>Data.</b> 50 Paul Graham essays (700–3,500 words) and 25 essays each from three models given one detailed style
brief and a shared topic list. Endnotes, "Thanks to" paragraphs and [n] markers are stripped; curly apostrophes are
normalised.</li>
<li><b>Features.</b> 40 grammar structures from a WordNet-backed classifier plus 16 surface habits, each measured as a
share of sentences. Differences are in units of Paul Graham's essay-to-essay standard deviation.</li>
<li><b>Steered features.</b> The brief gave explicit rules for dashes, I/you, sentence length and "and" joins, so those
measure obedience, not style. They are shown separately and left out of the map and the classifiers.</li>
<li><b>Uniformity.</b> PG's essays span about 20 years; the models wrote all theirs at once from one topic list. Some of
his spread is time and topic, so read the gap as an upper bound.</li>
<li><b>Scope.</b> One writer, one brief, 25 essays a model. This shows how these models missed this writer, not how to
detect AI text in general.</li>
</ol>
</section>
<div id="tip" role="tooltip"></div>
</main>
<script>
const tip = document.getElementById("tip");
document.addEventListener("pointerover", e => {{
  const t = e.target.closest("[data-tip]"); if (!t) return;
  tip.textContent = t.dataset.tip; tip.style.display = "block";
}});
document.addEventListener("pointermove", e => {{
  if (tip.style.display !== "block") return;
  tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px";
  tip.style.top = (e.clientY + 14) + "px";
}});
document.addEventListener("pointerout", e => {{ if (e.target.closest("[data-tip]")) tip.style.display = "none"; }});
</script>
</body></html>"""
OUT.write_text(html)
print("wrote", OUT)

# ---------------------------------------------------------------- standalone SVGs for the README
CSS = html[html.index("<style>") + 7:html.index("</style>")].replace("{{", "{").replace("}}", "}")
CSS = CSS.split("* {")[0]  # just the colour tokens
CSS += """
svg { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
.bg { fill:var(--surface); stroke:var(--grid); } .title { fill:var(--text); font-size:17px; font-weight:650; }
.sub { fill:var(--text2); font-size:13px; } .lgt { fill:var(--text2); font-size:12px; }
.frame { fill:none; stroke:var(--grid); } .grid, .row { stroke:var(--grid); stroke-width:1; }
.zero { stroke:var(--pg); stroke-width:1.5; } .band { fill:var(--band); }
.ref { stroke:var(--ref); stroke-width:1.5; stroke-dasharray:4 4; }
.span { stroke:var(--axis); stroke-width:2; } .med { stroke:var(--text); stroke-width:2; }
.tick { fill:var(--text2); font-size:12px; } .pairlbl { font-style:italic; font-size:13px; }
.axis, .note { fill:var(--muted); font-size:12px; } .val { fill:var(--text2); font-size:12px; }
.ptitle { fill:var(--text); font-size:13px; font-weight:600; }
.dl { fill:var(--text); font-size:13px; font-weight:650; paint-order:stroke; stroke:var(--surface); stroke-width:4px; }
.m { stroke:var(--surface); stroke-width:1.5; fill-opacity:.85; } .m.pg { fill:none; stroke:var(--pg); stroke-width:1.8; }
.m.s1 { fill:var(--s1); } .m.s2 { fill:var(--s2); } .m.s3 { fill:var(--s3); }
"""
IMG = OUT.parent / "img"
IMG.mkdir(exist_ok=True)
TITLES = {
    "map": ("Every essay, placed by how it's written", "PG spreads out; each model sits in its own tight patch."),
    "uniformity": ("The models' essays are more alike than PG's", "Each dot is an essay; the bar is the median."),
    "fingerprint": ("Where each model differs from Paul Graham", "In units of PG's own essay-to-essay spread."),
    "accents": ("Each model has its own accent", "Where each model is furthest from the other two (per 100 sentences)."),
    "verbosity": ("The models aren't wordy. They're compressed.", "Each dot is an essay; the bar is the median."),
    "pairs": ("Paul Graham speculates; the models define", "Word pairs per 10,000 words, in at least 8 essays."),
    "told": ("Where the brief gave a rule, the models overshot it", "Dashed line: what the brief asked for."),
}


def standalone(key, side_by_side=False, gap=16, pad=20):
    panels = PARTS[key]
    scale = 1.0
    if side_by_side:
        width = sum(w for w, _, _ in panels) + gap * (len(panels) - 1)
        scale = min(1.0, 720 / width)
    head = 74
    x, y = pad, pad + head
    inner = []
    if side_by_side:
        for w, h, body in panels:
            inner.append(f'<svg x="{x}" y="{y}" width="{w * scale}" height="{h * scale}" viewBox="0 0 {w} {h}" '
                         f'overflow="visible">{body}</svg>')
            x += (w + gap) * scale
        W_ = 720 + 2 * pad
        H_ = y + max(h for _, h, _ in panels) * scale + pad
    else:
        for w, h, body in panels:
            inner.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 {w} {h}" overflow="visible">{body}</svg>')
            y += h + gap
        W_ = max(w for w, _, _ in panels) + 2 * pad
        H_ = y - gap + pad
    t, sub = TITLES[key]
    lg, lx = [], pad
    for k in KEYS:
        lab = NAME[k] + (" (human)" if k == "pg" else "")
        lg.append(f'<circle cx="{lx + 6}" cy="{pad + 54}" r="5" class="m {SLOT[k]}"/>'
                  f'<text x="{lx + 16}" y="{pad + 58}" class="lgt">{escape(lab)}</text>')
        lx += 22 + len(lab) * 6.6
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_:.0f}" height="{H_:.0f}" viewBox="0 0 {W_:.0f} {H_:.0f}">'
           f'<style>{CSS}</style><rect x=".5" y=".5" width="{W_ - 1:.0f}" height="{H_ - 1:.0f}" rx="10" class="bg"/>'
           f'<text x="{pad}" y="{pad + 16}" class="title">{escape(t)}</text>'
           f'<text x="{pad}" y="{pad + 36}" class="sub">{escape(sub)}</text>{"".join(lg)}{"".join(inner)}</svg>')
    (IMG / f"{key}.svg").write_text(out)


for key in ("map", "uniformity", "fingerprint", "verbosity", "pairs", "told"):
    standalone(key)
standalone("accents", side_by_side=True)
print("wrote", IMG)
