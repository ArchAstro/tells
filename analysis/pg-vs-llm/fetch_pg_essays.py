#!/usr/bin/env python3
"""Download Paul Graham essays from paulgraham.com into human/paul_graham/.

Keeps 50 substantial essays (word-count band), writes markdown + _meta.json.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from html.parser import HTMLParser
import sys
from pathlib import Path

# where the essays go: the corpus root given as the first argument (default: ./corpus)
ROOT = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path("corpus")
OUT = ROOT / "human" / "paul_graham"
INDEX_URL = "https://www.paulgraham.com/articles.html"
UA = "writing-patterns-research/1.0 (local corpus build; +https://www.paulgraham.com)"

SKIP_SLUGS = {
    "index",
    "articles",
    "books",
    "bio",
    "rss",
    "faq",
    "raq",
    "quo",
    "lisp",
    "bel",
    "arc",
    "antispam",
    "kedrosky",
    "prop62",  # ballot advocacy, not an essay
}

# Not essays: book excerpts / off-site.
SKIP_PREFIXES = ("http://", "https://")


class _FontCollector(HTMLParser):
    """Collect text inside the first <font face=verdana> body block."""

    def __init__(self) -> None:
        super().__init__()
        self.in_font = 0
        self.started = False
        self.done = False
        self.parts: list[str] = []
        self.title_img_alt = ""
        self.page_title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        ad = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "img":
            alt = ad.get("alt", "").strip()
            if alt and not self.title_img_alt:
                self.title_img_alt = alt
            if self.in_font:
                self.parts.append(" ")
        if tag == "font":
            # Count every <font> once the verdana body has opened, so nested
            # color/size tags don't close the collector early.
            if "verdana" in ad.get("face", "").lower() or self.in_font:
                self.in_font += 1
                self.started = True
        elif self.in_font:
            if tag in {"br", "p"}:
                self.parts.append("\n")
            elif tag == "b":
                self.parts.append("**")
            elif tag in {"i", "em"}:
                self.parts.append("*")
            elif tag == "a":
                self.parts.append("[")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if self.done:
            return
        if tag == "font" and self.in_font:
            self.in_font -= 1
            if self.in_font == 0 and self.started:
                self.done = True
        elif self.in_font:
            if tag == "b":
                self.parts.append("**")
            elif tag in {"i", "em"}:
                self.parts.append("*")
            elif tag == "a":
                self.parts.append("]")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page_title += data
        if self.in_font and not self.done:
            self.parts.append(data)


def fetch(url: str) -> str:
    # System curl has a working CA bundle; this machine's Python 3.13 does not.
    proc = subprocess.run(
        ["curl", "-fsSL", "-A", UA, "--max-time", "30", url],
        check=True,
        capture_output=True,
    )
    raw = proc.stdout
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def essay_links(index_html: str) -> list[tuple[str, str]]:
    """Return [(slug, title)] in index order (newest first)."""
    # Index titles are in <a href="slug.html">Title</a>
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'<a href="([^"]+\.html)"[^>]*>([^<]+)</a>', index_html, flags=re.I
    ):
        href, title = m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
        if href.startswith(SKIP_PREFIXES):
            continue
        slug = Path(href).stem
        if slug in SKIP_SLUGS or slug in seen:
            continue
        if not re.fullmatch(r"[a-z0-9]+", slug):
            continue
        seen.add(slug)
        found.append((slug, title))
    return found


def html_to_text(html: str) -> tuple[str, str, str | None]:
    p = _FontCollector()
    p.feed(html)
    title = (p.title_img_alt or p.page_title or "").strip()
    raw = "".join(p.parts)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\[([^\]]*)\]\s*\(\s*\)", r"\1", raw)  # empty markdown links
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    # First non-empty line is often Month YYYY
    lines = [ln.rstrip() for ln in raw.split("\n")]
    date = None
    body_start = 0
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if re.fullmatch(
            r"(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{4}",
            ln.strip(),
        ):
            date = ln.strip()
            body_start = i + 1
        break
    body = "\n".join(lines[body_start:]).strip()
    body = re.sub(
        r"^Want to start a startup\?\s*Get funded by\s*Y Combinator\.?\s*",
        "",
        body,
        flags=re.I,
    )
    # Drop translation / notes footer chrome
    body = re.split(r"\nJapanese Translation\n", body, maxsplit=1)[0]
    body = re.split(r"\n\s*More Info:\n", body, maxsplit=1)[0]
    body = body.strip()
    return title, body, date


def slugify(title: str, slug: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:60].rstrip("-") or slug)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def pick_fifty(rows: list[dict]) -> list[dict]:
    """Prefer 700–3500 word essays (typical PG), newest-first, fill from neighbors."""
    mid = [r for r in rows if 700 <= r["n_words"] <= 3500]
    shortish = [r for r in rows if 500 <= r["n_words"] < 700]
    longish = [r for r in rows if 3500 < r["n_words"] <= 6000]
    chosen: list[dict] = []
    for bucket in (mid, longish, shortish):
        for r in bucket:
            if len(chosen) >= 50:
                break
            chosen.append(r)
        if len(chosen) >= 50:
            break
    return chosen[:50]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("fetching index…")
    index = fetch(INDEX_URL)
    links = essay_links(index)
    print(f"index essays: {len(links)}")

    parsed: list[dict] = []
    for i, (slug, index_title) in enumerate(links, 1):
        url = f"https://www.paulgraham.com/{slug}.html"
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  FAIL {slug}: {e}")
            continue
        title, body, date = html_to_text(html)
        title = title or index_title
        nw = word_count(body)
        parsed.append(
            {
                "slug": slug,
                "title": title,
                "date": date,
                "url": url,
                "n_words": nw,
                "body": body,
            }
        )
        print(f"  [{i:3}/{len(links)}] {nw:5}w  {slug}  {title[:50]}")
        time.sleep(0.25)

    chosen = pick_fifty(parsed)
    # wipe previous numbered files
    for p in OUT.glob("*.md"):
        p.unlink()

    files = []
    for i, r in enumerate(chosen, 1):
        fname = f"{i:03d}-{slugify(r['title'], r['slug'])}.md"
        date_line = f"date: {r['date']}\n" if r["date"] else ""
        text = (
            f"# {r['title']}\n\n"
            f"<!-- source: paulgraham.com/{r['slug']}.html\n"
            f"link: {r['url']}\n"
            f"{date_line}words: {r['n_words']} -->\n\n"
            f"{r['body']}\n"
        )
        (OUT / fname).write_text(text, encoding="utf-8")
        files.append(
            {
                "file": fname,
                "slug": r["slug"],
                "title": r["title"],
                "date": r["date"],
                "url": r["url"],
                "n_words": r["n_words"],
            }
        )

    words = [f["n_words"] for f in files]
    words_sorted = sorted(words)
    meta = {
        "source": INDEX_URL,
        "n": len(files),
        "selection": "50 essays in ~700–3500 word band, newest-first; fill from 500–6000",
        "word_count": {
            "min": min(words) if words else 0,
            "median": words_sorted[len(words_sorted) // 2] if words else 0,
            "mean": round(sum(words) / len(words), 1) if words else 0,
            "max": max(words) if words else 0,
        },
        "essays": files,
        "skipped_short_or_long": [
            {"slug": r["slug"], "title": r["title"], "n_words": r["n_words"]}
            for r in parsed
            if r["slug"] not in {f["slug"] for f in files}
        ],
    }
    (OUT / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {len(files)} essays → {OUT}  "
        f"words min/med/mean/max="
        f"{meta['word_count']['min']}/{meta['word_count']['median']}/"
        f"{meta['word_count']['mean']}/{meta['word_count']['max']}"
    )


if __name__ == "__main__":
    main()
