"""Turn files into the prose sentences a person actually wrote.

Only prose is measured. Code, tables of labels, image captions, headings, HTML
comments and front matter are dropped, because they follow their own grammar
and would drown out the author's sentences. CriticMarkup is resolved as if
every suggestion were accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

WORD = re.compile(r"[A-Za-z0-9']+")
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
# Table cells shorter than this are labels or numbers, not sentences.
MIN_CELL_WORDS = 8
# Endnotes and acknowledgements are a different register; prose stops here.
END_OF_PROSE = re.compile(r"^(\*\*|#+ *)?(Notes|Footnotes|Endnotes)(\*\*)? *$", re.I)
THANKS = re.compile(r"^(\*\*)?Thanks(\*\*)? to\b")


@dataclass
class Doc:
    name: str
    path: str
    sentences: list[str]
    kind: str  # markdown | tweet | text


# ---------------------------------------------------------------- markdown


def critic_accept(text: str) -> str:
    text = re.sub(r"\{~~(.*?)~>(.*?)~~\}", r"\2", text, flags=re.S)
    text = re.sub(r"\{\+\+(.*?)\+\+\}", r"\1", text, flags=re.S)
    text = re.sub(r"\{--(.*?)--\}", "", text, flags=re.S)
    text = re.sub(r"\{==(.*?)==\}", r"\1", text, flags=re.S)
    return re.sub(r"\{>>.*?<<\}", "", text, flags=re.S)


def strip_inline(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links keep their text
    text = re.sub(r"\[[^\]]*\]", "", text)  # [placeholder notes to self]
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def front_matter(text: str) -> tuple[str, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[4:end], text[end + 4:]
    return "", text


def markdown_units(md: str) -> list[str]:
    """Paragraphs, list items and prose table cells, each as one unit."""
    md = critic_accept(md)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"\[\d+\]", "", md)  # footnote markers
    units: list[str] = []
    para: list[str] = []

    def flush() -> None:
        if para and para[0] != "":
            units.append(" ".join(para))
        if para:
            para.clear()

    for raw in md.splitlines():
        line = raw.strip()
        if END_OF_PROSE.match(line):
            break
        if not para and THANKS.match(line):
            para.append("")  # swallow the paragraph: flushed as empty below
            continue
        if not line or line.startswith("#") or re.fullmatch(r"[-*_]{3,}", line):
            flush()
            continue
        if line.startswith("|"):
            flush()
            for cell in line.strip("|").split("|"):
                cell = strip_inline(cell)
                if len(WORD.findall(cell)) >= MIN_CELL_WORDS:
                    units.append(cell)
            continue
        item = re.match(r"^(\d+[.)]|[-*+])\s+(.*)$", line)
        if item:
            flush()
            units.append(strip_inline(item.group(2)))
            continue
        para.append(strip_inline(line.lstrip("> ")))
    flush()
    return [u for u in units if u]


# ---------------------------------------------------------------- tweets


def is_tweet(meta: str) -> bool:
    return "conversation_id:" in meta or re.search(r"^url: https://(x|twitter)\.com/", meta, re.M) is not None


def tweet_units(body: str) -> list[str]:
    """One unit per line; quoted tweets, links, @handles and 1/ numbering removed."""
    body = re.split(r"^#{1,6} Quoted", body, flags=re.M)[0]
    body = re.sub(r"https?://\S+", "", body)
    units = []
    for line in body.splitlines():
        line = re.sub(r"^(@\w+\s*)+", "", line.strip())
        line = re.sub(r"^\d+/\s*", "", line)
        if line:
            units.append(strip_inline(line))
    return units


# ---------------------------------------------------------------- sentences


def split_units(units: list[str]) -> list[str]:
    from nltk.tokenize import sent_tokenize

    from writing_style.grammar.data import ensure_data

    ensure_data()
    out = []
    for unit in units:
        unit = re.sub(r"\s+", " ", unit.translate(QUOTES)).strip()
        if not unit:
            continue
        if unit[-1] not in ".!?:":
            unit += "."
        for sent in sent_tokenize(unit):
            if len(WORD.findall(sent)) >= 2:
                out.append(sent)
    return out


def load(path: Path) -> Doc:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = front_matter(text)
    if is_tweet(meta):
        return Doc(path.name, str(path), split_units(tweet_units(body)), "tweet")
    if path.suffix.lower() in {".md", ".markdown", ".mdx"}:
        return Doc(path.name, str(path), split_units(markdown_units(body)), "markdown")
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    return Doc(path.name, str(path), split_units(paras), "text")


def expand(pattern: str) -> list[Path]:
    """A file, a directory (its .md/.txt files) or a glob, sorted."""
    p = Path(pattern).expanduser()
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if f.suffix.lower() in {".md", ".markdown", ".mdx", ".txt"}
                      and not f.name.startswith(("_", ".")))
    parts = p.parts
    i = next((k for k, part in enumerate(parts) if any(c in part for c in "*?[")), len(parts))
    if i == len(parts):
        return []  # a plain path that does not exist
    base = Path(*parts[:i]) if i else Path(".")
    return sorted(f for f in base.glob(str(Path(*parts[i:]))) if f.is_file())
