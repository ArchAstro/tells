"""tells: build a model of how you write, then check drafts against it.

    tells setup
    tells build -c blog='~/blog/*.md' -c tweets=~/archive/tweets -o me.json
    tells calibrate me.json
    tells check draft.md -m me.json
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from tells import model as M
from tells.features import FEATURES
from tells.sources import expand, load

DEFAULT_REFERENCE = "pg-vs-llm"


def pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def parse_corpus(spec: str) -> tuple[str, list[str], float]:
    """name=glob[,glob...][@weight]"""
    if "=" not in spec:
        raise SystemExit(f"--corpus {spec!r}: expected name=glob[,glob][@weight]")
    name, rest = spec.split("=", 1)
    weight = 1.0
    if "@" in rest:
        rest, w = rest.rsplit("@", 1)
        weight = float(w)
    return name, [g for g in rest.split(",") if g], weight


def load_docs(globs: list[str], exclude: list[str]) -> list:
    paths = sorted({p for g in globs for p in expand(g)})
    skip = {p.resolve() for g in exclude for p in expand(g)}
    docs = [load(p) for p in paths if p.resolve() not in skip]
    return [d for d in docs if d.sentences]


def load_reference(name: str | None) -> dict | None:
    if not name or name == "none":
        return None
    p = Path(name).expanduser()
    if p.is_file():
        return json.loads(p.read_text())
    try:
        return json.loads(resources.files("tells.data").joinpath(f"{name}.json").read_text())
    except FileNotFoundError:
        raise SystemExit(f"no reference {name!r} (a file path, or one of: {DEFAULT_REFERENCE})")


# ---------------------------------------------------------------- commands


def cmd_setup(a) -> None:
    from tells.grammar.data import NLTK_DATA, ensure_data

    ensure_data()
    print(f"NLTK data ready in {NLTK_DATA}")


def cmd_build(a) -> None:
    from tells import pairs as P

    corpora, counts = [], []
    for spec in a.corpus:
        name, globs, weight = parse_corpus(spec)
        docs = load_docs(globs, a.exclude)
        if not docs:
            raise SystemExit(f"corpus {name}: no files with prose matched {globs}")
        print(f"{name}: {len(docs)} files, {sum(len(d.sentences) for d in docs)} sentences ...", file=sys.stderr)
        corpora.append(M.build_corpus(name, docs, weight, a.chunk))
        counts.append(P.count(docs))
    model = M.Model(corpora)
    ref = load_reference(a.reference)
    if ref and "pairs" in ref:
        model.pairs = P.author_pairs(P.merge(counts), ref["pairs"])
    model.save(Path(a.out))
    for c in corpora:
        unit = "chunks" if c.chunked else "docs"
        print(f"  {c.name:12} {c.n_files:4} files -> {len(c.docs):3} {unit}, {c.n:5} sentences, weight {c.weight:g}")
    suspects = [r for r in M.corpus_machine_likeness(model, ref) if r[2] >= M.MACHINE_LINE]
    if suspects:
        print(f"  warning: {len(suspects)} document(s) read as machine-written (machine-likeness >= {M.MACHINE_LINE}):")
        for corpus, doc, s in sorted(suspects, key=lambda r: -r[2]):
            print(f"    {s:.2f}  {corpus}: {doc}")
        print("  If an assistant drafted or heavily edited them, rebuild with -x for each: they teach the\n"
              "  model the assistant's voice, and check will then push drafts toward it.")
    if model.pairs:
        sig = ", ".join(r["pair"] for r in model.pairs["signature"][:10])
        print(f"  your word pairs: {sig} ...")
        print(f"  AI pairs you rarely use: {', '.join(r['pair'] for r in model.pairs['ai'][:10])} ...")
    print(f"wrote {a.out}")


def cmd_calibrate(a) -> None:
    model = M.Model.load(Path(a.model))
    res = M.calibrate(model)
    print(f"  {'off':>3}  {'dist':>5}  {'len sd':>6}  document")
    for r in sorted(res, key=lambda x: (x.corpus, -x.off)):
        print(f"  {r.off:3}  {r.distance:5.2f}  {r.sd_len:6.1f}  {r.corpus:10} {r.doc}")
    print(f"\nFeatures off (of {len(FEATURES)}) when each of your documents is scored against the rest:")
    for corpus, (lo, med, hi) in M.bands(res).items():
        print(f"  {corpus:10} {lo:g}-{hi:g}, median {med:g}")
    print("A draft near the median for its format reads like you; don't chase zero.")


def cmd_check(a) -> None:
    model = M.Model.load(Path(a.model))
    ref = load_reference(a.reference)
    paths = expand(a.draft)
    if not paths:
        raise SystemExit(f"{a.draft}: not found")
    doc = load(paths[0])
    stats, by_feature = M.draft_stats(doc)
    from tells import pairs as P

    pr = P.draft_report(P.count([doc]), model.pairs) if model.pairs else None
    from tells import verbosity as V

    vrows = M.verbosity_rows(V.measure(doc.sentences), model)
    held_out = model.excluding(doc.name)
    if held_out is not model:
        print(f"note: {doc.name} is in the model; scoring it against the rest.", file=sys.stderr)
        model = held_out
    rows = M.score(stats, model, ref)
    cal = [] if a.no_calibrate else M.calibrate(model)
    bands = M.bands(cal)
    dist = M.distance(stats, model)
    ml = M.machine_likeness(stats, ref)
    ml_yours = [s for _, _, s in M.corpus_machine_likeness(model, ref)]

    if a.json:
        out = {
            "draft": doc.path, "sentences": stats.n, "mean_words": stats.mean_len,
            "model_mean_words": model.mean_len(), "off": M.n_off(rows), "calibration": bands, "distance": dist, "sd_len": stats.sd_len,
            "calibration_distance": M.bands(cal, "distance"), "calibration_sd_len": M.bands(cal, "sd_len"),
            "machine_likeness": {"draft": ml, "yours": [min(ml_yours), max(ml_yours)] if ml_yours else None,
                                 "line": M.MACHINE_LINE},
            "pairs": pr, "verbosity": vrows, "filler_sentences": V.fillers(doc.sentences)[:10],
            "features": [{
                "id": r.id, "label": FEATURES[r.id].label, "draft": r.draft, "author": r.combined,
                "per_corpus": r.per_corpus, "z": r.z, "z_per_corpus": r.z_per_corpus, "range": [r.lo, r.hi],
                "count": r.count, "off": r.off, "verdict": r.verdict, "direction": r.direction,
                "ai_like": r.ai_like,
                "hint": getattr(FEATURES[r.id], r.direction) if r.off else None,
                "draft_sentences": by_feature.get(r.id, [])[:5] if r.off and r.direction == "too_many" else [],
                "author_examples": [s for c in model.corpora for s in c.examples.get(r.id, [])][:4]
                if r.off and r.direction == "too_few" else [],
            } for r in rows],
        }
        print(json.dumps(out, indent=1))
        return

    names = [c.name for c in model.corpora]
    print(f"{doc.name}: {stats.n} sentences, {stats.mean_len:.1f} words/sentence "
          f"(you: {model.mean_len():.1f})\n")
    head = f"  {'feature':26} {'draft':>6} {'you':>6}  " + "  ".join(f"{n[:8]:>8}" for n in names)
    print(head + f"  {'z':>5}  verdict")
    shown = rows if a.all else [r for r in rows if r.off or abs(r.z) >= 1.5]
    for r in shown:
        mark = {"fix": "FIX", "format": "format", "ok": ""}[r.verdict]
        if r.ai_like and r.off:
            mark += " ai"
        per = "  ".join(f"{pct(r.per_corpus[n]):>8}" for n in names)
        print(f"  {r.id:26} {pct(r.draft)} {pct(r.combined)}  {per}  {r.z:5.1f}  {mark}")

    fixes = [r for r in rows if r.verdict == "fix"]
    if fixes:
        print("\nTo fix (every corpus agrees):")
    for r in fixes:
        f = FEATURES[r.id]
        print(f"\n  {r.id}: {f.label}")
        print(f"    {getattr(f, r.direction)}")
        if r.direction == "too_many":
            for s in by_feature.get(r.id, [])[:3]:
                print(f"    - draft: {s[:140]}")
        else:
            for c in model.corpora:
                for s in c.examples.get(r.id, [])[:2]:
                    print(f"    - you ({c.name}): {s[:140]}")
    fmt = [r.id for r in rows if r.verdict == "format"]
    if fmt:
        print(f"\nLeave alone (your corpora disagree, so it's the format, not you): {', '.join(fmt)}")
    if ref:
        tells = [r.id for r in rows if r.ai_like and r.off]
        if tells:
            print(f"\nOff in the direction machine prose leans ({ref['human']} vs {', '.join(ref['machines'])}): "
                  f"{', '.join(tells)}")
    off = M.n_off(rows)
    print(f"\n{off} of {len(FEATURES)} features off.")
    if ml is not None:
        yours = f"your documents {min(ml_yours):.2f}-{max(ml_yours):.2f}; " if ml_yours else ""
        print(f"\nMachine-likeness (share of AI tells where the draft sits nearer the machines): draft {ml:.2f}"
              f"\n  {yours}machine-written text is usually {M.MACHINE_LINE}+")
        if ml >= M.MACHINE_LINE:
            print("  Reads as machine-written by its structure, whatever its words: fix the `ai` rows first.")
        if ml_yours and max(ml_yours) >= M.MACHINE_LINE:
            print("  Some of your own documents score as machine-written; see `build` and consider -x.")
    if pr:
        print_pairs(pr)
    if vrows:
        print("\nVerbosity (against the range of your own documents):")
        for r in vrows:
            rng = "; ".join(f"{c} {lo:.2f}-{hi:.2f}" for c, (lo, _, hi) in r["yours"].items())
            flag = "" if r["verdict"] == "ok" else f"  <- {r['verdict']}"
            print(f"  {r['label']:48} draft {r['draft']:6.2f}   yours: {rng}{flag}")
        fl = V.fillers(doc.sentences)
        if fl:
            print(f"  filler phrases in {len(fl)} sentences, e.g.: {fl[0][:120]}")
    if not cal:
        return
    print("Your own documents, each scored against the rest: " + "; ".join(
        f"{c} {lo:g}-{hi:g} (median {med:g})" for c, (lo, med, hi) in bands.items()))

    print("\nDiversity (real writing wanders; a draft sanded down to your average reads as generated):")
    for label, attr, value in (("distance from your average", "distance", dist),
                               ("sentence-length spread (sd, words)", "sd_len", stats.sd_len)):
        b = M.bands(cal, attr)
        parts = []
        for c, (lo, med, hi) in b.items():
            where = "below" if value < lo else "above" if value > hi else "inside"
            parts.append(f"{c} {lo:.1f}-{hi:.1f} ({where})")
        print(f"  {label:36} draft {value:5.2f}   yours: " + "; ".join(parts))
    if all(dist < lo for lo, _, _ in M.bands(cal, "distance").values()):
        print("  Too smooth: closer to your average than anything you've written. Stop tuning to the model;\n"
              "  put back your own asides, odd sentences and opinions, and vary sentence length.")


def print_pairs(pr: dict) -> None:
    s, ai = pr["signature"], pr["ai"]
    print("\nWord pairs (per 10,000 words):")
    print(f"  your pairs        draft {s['draft']:6.1f}   you {s['you']:6.1f}   machines {s['machines']:6.1f}")
    print(f"  AI pairs          draft {ai['draft']:6.1f}   you {ai['you']:6.1f}   machines {ai['machines']:6.1f}")
    if pr["over"]:
        print("  AI pairs this draft over-uses (rephrase in your own words):")
        for r in pr["over"][:8]:
            print(f"    {r['pair']:16} {r['count']:3}x  draft {r['draft']:5.1f}   you {r['you']:5.1f}   machines {r['machines']:5.1f}")
    if pr["missing"]:
        exp = ", ".join(f"{r['pair']} (~{r['you'] * pr['words'] / 1e4:.0f})" for r in pr["missing"][:8])
        print(f"  Your pairs that would usually show up by now, and don't: {exp}")
        print("  Don't paste them in; they come back when the sentences are yours.")


def cmd_reference(a) -> None:
    human_name, human_globs, _ = parse_corpus(a.human)
    human = M.build_corpus(human_name, load_docs(human_globs, a.exclude), chunk=0, examples=False)
    machines = []
    for spec in a.machine:
        name, globs, _ = parse_corpus(spec)
        machines.append(M.build_corpus(name, load_docs(globs, a.exclude), chunk=0, examples=False))
        print(f"{name}: {len(machines[-1].docs)} docs", file=sys.stderr)
    from tells import pairs as P

    ref = M.build_reference(human, machines, a.min_gap)
    human_counts = P.count(load_docs(human_globs, a.exclude))
    machine_counts = {parse_corpus(spec)[0]: P.count(load_docs(parse_corpus(spec)[1], a.exclude)) for spec in a.machine}
    ref["pairs"] = P.build_reference(human_counts, machine_counts)
    ref["note"] = a.note or ""
    ref["steered"] = [f.strip() for f in (a.steered or "").split(",") if f.strip()]
    Path(a.out).write_text(json.dumps(ref, indent=1))
    tells = {f: v["direction"] for f, v in ref["features"].items() if v["direction"]}
    print(f"wrote {a.out}: {len(tells)} features separate every machine from {human_name}")
    for f, d in sorted(tells.items(), key=lambda x: x[1]):
        print(f"  {d:8}  {f}")


def cmd_pairs(a) -> None:
    from tells import pairs as P

    a_name, a_globs, _ = parse_corpus(a.a)
    A = P.count(load_docs(a_globs, a.exclude))
    Bs = []
    for spec in a.b:
        name, globs, _ = parse_corpus(spec)
        Bs.append((name, P.count(load_docs(globs, a.exclude))))
    if not A.total or not all(b.total for _, b in Bs):
        raise SystemExit("every corpus needs some prose")
    z_ab = [P.log_odds(A, b) for _, b in Bs]
    z_ba = [{k: -v for k, v in z.items()} for z in z_ab]
    names = [n for n, _ in Bs]
    head = f"  {'pair':20} {a_name[:9]:>9} " + " ".join(f"{n[:9]:>9}" for n in names) + "   per 10k words"

    def show(title, rows, pool):
        print(f"\n{title}")
        print(head)
        for k, z in rows[:a.top]:
            print(f"  {' '.join(k):20} {A.per10k(k):9.1f} " + " ".join(f"{b.per10k(k):9.1f}" for _, b in Bs)
                  + f"   (min z {z:.1f}, in {pool.docs[k]} docs)")

    pool_b = P.merge([b for _, b in Bs])
    show(f"Pairs {a_name} uses more than {' and '.join(names)}:",
         P.consistent(z_ab, A, a.min_docs, drop_topic=not a.keep_topic), A)
    show(f"Pairs {' and '.join(names)} {'all ' if len(names) > 1 else ''}use more than {a_name}:",
         P.consistent(z_ba, pool_b, a.min_docs, drop_topic=not a.keep_topic), pool_b)


def cmd_features(a) -> None:
    for fid, f in FEATURES.items():
        print(f"  {fid:28} {f.label}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="tells", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="download the NLTK data (WordNet, tagger, tokenizer)").set_defaults(fn=cmd_setup)

    b = sub.add_parser("build", help="build a model from your own writing")
    b.add_argument("-c", "--corpus", action="append", required=True,
                   help="name=glob[,glob][@weight]; repeat for each kind of writing (blog, tweets, email)")
    b.add_argument("-x", "--exclude", action="append", default=[], help="glob of files to leave out")
    b.add_argument("--chunk", type=int, default=None,
                   help="pack sentences into chunks of N (default: automatic for many short docs)")
    b.add_argument("-o", "--out", default="style-model.json")
    b.add_argument("-r", "--reference", default=DEFAULT_REFERENCE,
                   help="machine reference for word pairs: a JSON path, pg-vs-llm (default) or none")
    b.set_defaults(fn=cmd_build)

    c = sub.add_parser("check", help="score a draft against a model")
    c.add_argument("draft")
    c.add_argument("-m", "--model", default="style-model.json")
    c.add_argument("-r", "--reference", default=DEFAULT_REFERENCE,
                   help=f"AI-tell reference: a JSON path, {DEFAULT_REFERENCE} (default) or none")
    c.add_argument("--all", action="store_true", help="show every feature, not only the off ones")
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-calibrate", action="store_true", help="skip the leave-one-out band (faster)")
    c.set_defaults(fn=cmd_check)

    k = sub.add_parser("calibrate", help="score each of your own documents against the rest")
    k.add_argument("model")
    k.set_defaults(fn=cmd_calibrate)

    r = sub.add_parser("reference", help="build an AI-tell reference from human vs machine corpora")
    r.add_argument("--human", required=True, help="name=glob")
    r.add_argument("--machine", action="append", required=True, help="name=glob; repeat")
    r.add_argument("-x", "--exclude", action="append", default=[])
    r.add_argument("--min-gap", type=float, default=0.15, help="AUC distance from 0.5 that counts")
    r.add_argument("--note", default="")
    r.add_argument("--steered", default="",
                   help="comma-separated features the machine prompt gave rules for; never used as tells")
    r.add_argument("-o", "--out", required=True)
    r.set_defaults(fn=cmd_reference)

    w = sub.add_parser("pairs", help="word pairs one corpus uses far more than others (and the reverse)")
    w.add_argument("-a", required=True, help="name=glob: the writing you care about")
    w.add_argument("-b", action="append", required=True,
                   help="name=glob to compare against; repeat, and only pairs that hold against every one are shown")
    w.add_argument("-x", "--exclude", action="append", default=[])
    w.add_argument("--top", type=int, default=20)
    w.add_argument("--min-docs", type=int, default=5, help="a pair must appear in at least this many documents")
    w.add_argument("--keep-topic", action="store_true", help="keep pairs with subject nouns (founder, product, ...)")
    w.set_defaults(fn=cmd_pairs)

    sub.add_parser("features", help="list what is measured").set_defaults(fn=cmd_features)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
