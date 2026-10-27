"""writing-style: build a model of how you write, then check drafts against it.

    writing-style setup
    writing-style build -c blog='~/blog/*.md' -c tweets=~/archive/tweets -o me.json
    writing-style calibrate me.json
    writing-style check draft.md -m me.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from writing_style import model as M
from writing_style.features import FEATURES
from writing_style.sources import expand, load

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
        return json.loads(resources.files("writing_style.data").joinpath(f"{name}.json").read_text())
    except FileNotFoundError:
        raise SystemExit(f"no reference {name!r} (a file path, or one of: {DEFAULT_REFERENCE})")


# ---------------------------------------------------------------- commands


def cmd_setup(a) -> None:
    from writing_style.grammar.data import NLTK_DATA, ensure_data

    ensure_data()
    print(f"NLTK data ready in {NLTK_DATA}")


def cmd_build(a) -> None:
    corpora = []
    for spec in a.corpus:
        name, globs, weight = parse_corpus(spec)
        docs = load_docs(globs, a.exclude)
        if not docs:
            raise SystemExit(f"corpus {name}: no files with prose matched {globs}")
        print(f"{name}: {len(docs)} files, {sum(len(d.sentences) for d in docs)} sentences ...", file=sys.stderr)
        corpora.append(M.build_corpus(name, docs, weight, a.chunk))
    model = M.Model(corpora)
    model.save(Path(a.out))
    for c in corpora:
        unit = "chunks" if c.chunked else "docs"
        print(f"  {c.name:12} {c.n_files:4} files -> {len(c.docs):3} {unit}, {c.n:5} sentences, weight {c.weight:g}")
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
    held_out = model.excluding(doc.name)
    if held_out is not model:
        print(f"note: {doc.name} is in the model; scoring it against the rest.", file=sys.stderr)
        model = held_out
    rows = M.score(stats, model, ref)
    cal = [] if a.no_calibrate else M.calibrate(model)
    bands = M.bands(cal)
    dist = M.distance(stats, model)

    if a.json:
        out = {
            "draft": doc.path, "sentences": stats.n, "mean_words": stats.mean_len,
            "model_mean_words": model.mean_len(), "off": M.n_off(rows), "calibration": bands, "distance": dist, "sd_len": stats.sd_len,
            "calibration_distance": M.bands(cal, "distance"), "calibration_sd_len": M.bands(cal, "sd_len"),
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


def cmd_reference(a) -> None:
    human_name, human_globs, _ = parse_corpus(a.human)
    human = M.build_corpus(human_name, load_docs(human_globs, a.exclude), chunk=0, examples=False)
    machines = []
    for spec in a.machine:
        name, globs, _ = parse_corpus(spec)
        machines.append(M.build_corpus(name, load_docs(globs, a.exclude), chunk=0, examples=False))
        print(f"{name}: {len(machines[-1].docs)} docs", file=sys.stderr)
    ref = M.build_reference(human, machines, a.min_gap)
    ref["note"] = a.note or ""
    Path(a.out).write_text(json.dumps(ref, indent=1))
    tells = {f: v["direction"] for f, v in ref["features"].items() if v["direction"]}
    print(f"wrote {a.out}: {len(tells)} features separate every machine from {human_name}")
    for f, d in sorted(tells.items(), key=lambda x: x[1]):
        print(f"  {d:8}  {f}")


def cmd_pairs(a) -> None:
    from writing_style import pairs as P

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


def cmd_install_skill(a) -> None:
    src = resources.files("writing_style").joinpath("skill")
    dest = Path(a.dest).expanduser() / "writing-style"
    if dest.exists() or dest.is_symlink():
        if not a.force:
            raise SystemExit(f"{dest} exists; pass --force to replace it")
        shutil.rmtree(dest) if dest.is_dir() and not dest.is_symlink() else dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with resources.as_file(src) as path:
        shutil.copytree(path, dest)
    print(f"installed the skill to {dest}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="writing-style", description=__doc__,
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

    s = sub.add_parser("install-skill", help="copy the agent skill into your skills folder")
    s.add_argument("--dest", default="~/.claude/skills")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_install_skill)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
