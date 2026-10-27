"""Fetch Princeton WordNet + the NLTK tagger/tokenizer into a private data dir.

nltk.download() fails on macOS python.org builds that have no system certs, so
pull the same zips GitHub serves for nltk_data, verifying TLS with certifi.

The directory must not be writable by group/other: recent NLTK refuses to read
such a directory (with only a warning), and WordNet then silently goes missing,
which quietly turns most grammar detectors off. We create it private and fix
the mode of an existing one.
"""

from __future__ import annotations

import os
import ssl
import stat
import urllib.request
import zipfile
from pathlib import Path

NLTK_DATA = Path(
    os.environ.get("WRITING_STYLE_NLTK_DATA", Path.home() / ".cache" / "writing-style" / "nltk_data")
)
BASE = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages"
RESOURCES = (
    ("corpora/wordnet", "corpora/wordnet.zip"),
    ("taggers/averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng.zip"),
    ("tokenizers/punkt_tab", "tokenizers/punkt_tab.zip"),
)

_READY = False


def _present(rel: str) -> bool:
    return (NLTK_DATA / rel).is_dir()


def missing() -> list[str]:
    return [rel for rel, _ in RESOURCES if not _present(rel)]


def _fetch(url: str, dest: Path) -> None:
    import certifi

    dest.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=ctx) as resp, dest.open("wb") as fh:
        fh.write(resp.read())


def _make_private(root: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        paths = [dirpath, *(os.path.join(dirpath, d) for d in dirnames),
                 *(os.path.join(dirpath, f) for f in filenames)]
        for p in paths:
            mode = os.stat(p).st_mode
            if mode & (stat.S_IWGRP | stat.S_IWOTH):
                os.chmod(p, mode & ~(stat.S_IWGRP | stat.S_IWOTH))


def ensure_data() -> None:
    global _READY
    if _READY:
        return
    NLTK_DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    for rel, zip_rel in RESOURCES:
        if _present(rel):
            continue
        dest = NLTK_DATA / zip_rel
        _fetch(f"{BASE}/{zip_rel}", dest)
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(dest.parent)
        dest.unlink()
    _make_private(NLTK_DATA)
    import nltk

    if str(NLTK_DATA) not in nltk.data.path:
        nltk.data.path.insert(0, str(NLTK_DATA))
    still = missing()
    if still:
        raise RuntimeError(f"WordNet/NLTK resources missing: {still}")
    _READY = True
