"""Tokenize, POS-tag, and attach WordNet lemmas / lexnames / verb frames."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from writing_style.grammar.data import ensure_data

PENN_TO_WN = {
    "NN": "n",
    "NNS": "n",
    "NNP": "n",
    "NNPS": "n",
    "VB": "v",
    "VBD": "v",
    "VBG": "v",
    "VBN": "v",
    "VBP": "v",
    "VBZ": "v",
    "JJ": "a",
    "JJR": "a",
    "JJS": "a",
    "RB": "r",
    "RBR": "r",
    "RBS": "r",
}

NOUN = {"NN", "NNS", "NNP", "NNPS"}
VERB_FIN = {"VBD", "VBP", "VBZ", "MD"}
VERB_ALL = VERB_FIN | {"VB", "VBG", "VBN"}
DET = {"DT", "PRP$", "PDT", "WDT"}
ADJ = {"JJ", "JJR", "JJS"}
ADV = {"RB", "RBR", "RBS"}
PUNCT = {".", ",", ":", ";", "!", "?", "``", "''", "(", ")", "--", "-"}
BE = frozenset({"be", "am", "is", "are", "was", "were", "been", "being"})
GET = frozenset({"get", "gets", "got", "gotten", "getting"})
HAVE = frozenset({"have", "has", "had", "having"})
DO = frozenset({"do", "does", "did", "doing"})
MODAL = frozenset(
    {"can", "could", "will", "would", "shall", "should", "may", "might", "must"}
)
AUX = BE | GET | HAVE | DO | MODAL
REL_COMPL = frozenset({"that", "who", "whom", "which", "whose", "where", "when"})
TIME_WORDS = frozenset({"yesterday", "today", "tomorrow", "tonight"})
TRANSITIVE_FRAMES = frozenset({8, 9, 10, 11, 14, 15, 17, 18, 19, 20, 21})
INTRANSITIVE_FRAMES = frozenset({1, 2})
THAT_CLAUSE_FRAMES = frozenset({26, 34})
INFINITIVE_FRAMES = frozenset({24, 28, 32})
GERUND_FRAMES = frozenset({33})
DITRANSITIVE_FRAMES = frozenset({14})
PREP_DATIVE_FRAMES = frozenset({15})  # Somebody ----s something to somebody


@dataclass(frozen=True)
class Tok:
    i: int
    word: str
    lower: str
    pos: str
    lemma: str
    wn_pos: str | None
    synsets: tuple[str, ...]
    first_lexname: str | None
    lexnames: frozenset[str]
    frame_ids: frozenset[int]
    frame_strings: tuple[str, ...]

    @property
    def is_noun(self) -> bool:
        return self.pos in NOUN

    @property
    def is_fin_verb(self) -> bool:
        return self.pos in VERB_FIN or (
            self.pos == "VBN" and bool(self.frame_ids)
        )

    @property
    def is_punct(self) -> bool:
        return self.pos in PUNCT or self.word in PUNCT


def _load_wn():
    ensure_data()
    from nltk.corpus import wordnet as wn

    wn.synsets("take")  # force exception map
    return wn


@lru_cache(maxsize=8192)
def _pack(word: str, penn: str) -> tuple:
    wn = _load_wn()
    wn_pos = PENN_TO_WN.get(penn)
    if wn_pos is None:
        return word, None, (), None, frozenset(), frozenset(), ()
    # ordered, not a set: synset order decides first_lex, and set order changes with every run's hash seed
    morphed = wn.morphy(word, wn_pos)
    exc = wn._exception_map.get(wn_pos, {})
    forms = list(dict.fromkeys([word, *([morphed] if morphed else []), *exc.get(word, [])]))
    syns = []
    seen = set()
    for form in forms:
        for syn in wn.synsets(form, pos=wn_pos):
            if syn.name() not in seen:
                seen.add(syn.name())
                syns.append(syn)
    lemma = morphed or (exc[word][0] if word in exc else word)
    lex = frozenset(s.lexname() for s in syns)
    first_lex = syns[0].lexname() if syns else None
    fids: set[int] = set()
    fstr: list[str] = []
    if wn_pos == "v":
        for syn in syns:
            for lem in syn.lemmas():
                fids.update(lem.frame_ids())
                for fs in lem.frame_strings():
                    if fs not in fstr:
                        fstr.append(fs)
    return lemma, wn_pos, tuple(s.name() for s in syns[:12]), first_lex, lex, frozenset(fids), tuple(fstr)


def annotate(sentence: str) -> list[Tok]:
    ensure_data()
    from nltk import pos_tag, word_tokenize

    tagged = pos_tag(word_tokenize(sentence))
    out: list[Tok] = []
    for i, (word, pos) in enumerate(tagged):
        lemma, wn_pos, syns, first_lex, lex, fids, fstr = _pack(word.lower(), pos)
        out.append(
            Tok(
                i=i,
                word=word,
                lower=word.lower(),
                pos=pos,
                lemma=lemma,
                wn_pos=wn_pos,
                synsets=syns,
                first_lexname=first_lex,
                lexnames=lex,
                frame_ids=fids,
                frame_strings=fstr,
            )
        )
    return out


def span_text(toks: list[Tok], start: int, end: int) -> str:
    return " ".join(t.word for t in toks[start:end])


def skip_punct(toks: list[Tok], i: int) -> int:
    n = len(toks)
    while i < n and toks[i].is_punct:
        i += 1
    return i


def look_back_non_adv(toks: list[Tok], i: int) -> int:
    j = i - 1
    while j >= 0 and toks[j].pos in ADV:
        j -= 1
    return j


def consume_np(toks: list[Tok], i: int) -> int | None:
    """Return exclusive end of an NP starting at i, or None."""
    n = len(toks)
    i = skip_punct(toks, i)
    if i >= n:
        return None
    t = toks[i]
    if t.pos == "PRP" or t.lower in {"there"}:
        return i + 1
    if t.pos == "EX":
        return i + 1
    j = i
    if t.pos in DET:
        j += 1
    while j < n and toks[j].pos in ADJ:
        j += 1
    if j < n and toks[j].pos == "CD":
        j += 1
    saw_noun = False
    while j < n and toks[j].pos in NOUN:
        saw_noun = True
        j += 1
    if saw_noun:
        return j
    if t.pos in NOUN:
        return i + 1
    if t.pos == "CD":
        return i + 1
    return None


def next_fin_verb(toks: list[Tok], i: int) -> int | None:
    """Index of the next finite (or past-as-VBN) verb, allowing a preverbal adverb."""
    n = len(toks)
    i = skip_punct(toks, i)
    if i >= n:
        return None
    if toks[i].pos in ADV:
        i += 1
        i = skip_punct(toks, i)
        if i >= n:
            return None
    if toks[i].pos in VERB_FIN or toks[i].pos == "VBN":
        return i
    if toks[i].pos == "MD":
        return i
    return None
