"""PG-relevant constructions layered on the core catalog.

Same contract as catalog.py: toks → list[Structure], precision over recall.
"""

from __future__ import annotations

from tells.grammar.catalog import (
    _content_noun,
    _has_frame,
    _hit,
    Structure,
)
from tells.grammar.tokens import (
    ADJ,
    ADV,
    AUX,
    BE,
    DET,
    INFINITIVE_FRAMES,
    NOUN,
    PREP_DATIVE_FRAMES,
    Tok,
    VERB_FIN,
    consume_np,
    next_fin_verb,
    skip_punct,
)

FREE_WH = frozenset(
    {"what", "whatever", "whoever", "whichever", "where", "wherever", "whom"}
)
NEG_FRONT = frozenset(
    {"never", "rarely", "seldom", "hardly", "scarcely", "little", "nor"}
)
DEM = frozenset({"this", "that", "these", "those"})
CC_WORDS = frozenset({"and", "or", "but"})
MOTION = "verb.motion"


def _finite_clause_end(toks: list[Tok], i: int) -> int | None:
    rest = skip_punct(toks, i)
    n = len(toks)
    if rest >= n:
        return None
    if toks[rest].pos in VERB_FIN or toks[rest].pos in {"VBN", "MD"}:
        return rest + 1
    subj = consume_np(toks, rest)
    if subj is None:
        return None
    v_i = next_fin_verb(toks, subj)
    return None if v_i is None else v_i + 1


def _prev_content(toks: list[Tok], i: int) -> int:
    j = i - 1
    while j >= 0 and toks[j].is_punct:
        j -= 1
    return j


def imperative(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[-1].word == "?":
        return []
    i = 0
    if toks[0].lower == "please":
        i = skip_punct(toks, 1)
        if i >= len(toks):
            return []
    t = toks[i]
    if t.lower == "do":
        j = skip_punct(toks, i + 1)
        if j < len(toks) and toks[j].lower in {"n't", "not"}:
            j = skip_punct(toks, j + 1)
            if j < len(toks) and toks[j].pos == "PRP":
                return []
            if j < len(toks) and toks[j].pos in {"VB", "VBP"}:
                return [
                    _hit(
                        "imperative",
                        toks,
                        0,
                        j + 1,
                        "don't + base verb, no subject",
                        toks[j].synsets[:2],
                    )
                ]
        return []
    if t.pos == "VB" and t.lower not in AUX:
        return [
            _hit(
                "imperative",
                toks,
                0,
                min(i + 2, len(toks)),
                f"base verb {t.word!r} at left edge, no subject",
                t.synsets[:3],
            )
        ]
    return []


def pseudo_cleft(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[-1].word == "?":
        return []
    if toks[0].lower not in {"what", "who", "where", "when", "why", "how"}:
        return []
    j = skip_punct(toks, 1)
    if j >= len(toks) or toks[j].lower in AUX:
        return []
    subj = consume_np(toks, j)
    if subj is None:
        return []
    v_i = next_fin_verb(toks, subj)
    if v_i is None:
        return []
    k = skip_punct(toks, v_i + 1)
    if k >= len(toks) or toks[k].lemma not in BE:
        return []
    rest = skip_punct(toks, k + 1)
    if rest >= len(toks) or toks[rest].is_punct:
        return []
    end = len(toks) - 1 if toks[-1].is_punct else len(toks)
    return [
        _hit(
            "pseudo_cleft",
            toks,
            0,
            end,
            f"{toks[0].word}-clause + {toks[k].word} + XP",
            (),
        )
    ]


def reverse_pseudo_cleft(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[-1].word == "?":
        return []
    np_end = consume_np(toks, 0)
    if np_end is None:
        return []
    j = skip_punct(toks, np_end)
    if j >= len(toks) or toks[j].lemma not in BE:
        return []
    k = skip_punct(toks, j + 1)
    if k >= len(toks) or toks[k].lower not in {"what", "who", "where", "when"}:
        return []
    end = _finite_clause_end(toks, k + 1)
    if end is None:
        return []
    return [
        _hit(
            "reverse_pseudo_cleft",
            toks,
            0,
            end,
            f"XP + {toks[j].word} + {toks[k].word}-clause",
            (),
        )
    ]


def prepositional_dative(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            continue
        if t.lemma in BE:
            continue
        if not _has_frame(t, PREP_DATIVE_FRAMES):
            continue
        theme_end = consume_np(toks, i + 1)
        if theme_end is None:
            continue
        j = skip_punct(toks, theme_end)
        if j >= n or toks[j].lower not in {"to", "for"}:
            continue
        k = skip_punct(toks, j + 1)
        if k < n and toks[k].pos in {"VB", "VBP"}:
            continue  # infinitive, not a recipient PP
        rec_end = consume_np(toks, k)
        if rec_end is None:
            continue
        recip = toks[rec_end - 1]
        if recip.pos != "PRP" and "noun.person" not in recip.lexnames and "noun.group" not in recip.lexnames:
            continue
        hits.append(
            _hit(
                "prepositional_dative",
                toks,
                t.i,
                rec_end,
                f"{t.lemma} licenses something to somebody",
                t.synsets[:3],
            )
        )
    return hits


def purpose_infinitive(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        in_order = t.lower == "order" and i > 0 and toks[i - 1].lower == "in"
        if t.lower != "to" and not in_order:
            continue
        to_i = i
        start = i
        if in_order:
            start = i - 1
            j = skip_punct(toks, i + 1)
            if j >= n or toks[j].lower != "to":
                continue
            to_i = j
        k = skip_punct(toks, to_i + 1)
        if k >= n or toks[k].pos not in {"VB", "VBP"}:
            continue
        if in_order:
            hits.append(
                _hit(
                    "purpose_infinitive",
                    toks,
                    start,
                    k + 1,
                    "in order to + base verb",
                    toks[k].synsets[:2],
                )
            )
            continue
        p = to_i - 1
        while p >= 0 and toks[p].pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            p -= 1
        if p < 0:
            continue
        verb = toks[p]
        motion = verb.first_lexname == MOTION
        if _has_frame(verb, INFINITIVE_FRAMES) and not motion:
            continue
        hits.append(
            _hit(
                "purpose_infinitive",
                toks,
                verb.i,
                k + 1,
                f"{verb.lemma} ({verb.first_lexname}) + to-{toks[k].word} adjunct",
                verb.synsets[:2] + toks[k].synsets[:1],
            )
        )
    return hits


def free_relative(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    if toks and toks[-1].word == "?":
        return []
    for i, t in enumerate(toks):
        word = t.lower
        if word not in FREE_WH:
            continue
        prev = _prev_content(toks, i)
        if prev >= 0 and _content_noun(toks[prev]):
            continue
        # sentence-initial what + clause + be → pseudo-cleft, not a free relative hit
        if i == 0 and word in {"what", "who", "where"}:
            end_probe = _finite_clause_end(toks, 1)
            if end_probe is not None:
                k = skip_punct(toks, end_probe)
                if k < n and toks[k].lemma in BE:
                    continue
        rest = skip_punct(toks, i + 1)
        if rest < n and (toks[rest].pos in VERB_FIN or toks[rest].pos == "MD"):
            v_i = rest
        else:
            subj = consume_np(toks, rest)
            if subj is None:
                continue
            v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        hits.append(
            _hit(
                "free_relative",
                toks,
                i,
                v_i + 1,
                f"fused {t.word}-clause as NP",
                (),
            )
        )
    return hits


def comparative_than(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "than":
            continue
        prev = _prev_content(toks, i)
        if prev < 0:
            continue
        start = prev
        if toks[prev].pos in {"JJR", "RBR"}:
            pass
        elif toks[prev].pos in ADJ | {"NN", "VBG"}:
            pre2 = _prev_content(toks, prev)
            if pre2 < 0 or toks[pre2].lower not in {"more", "less"}:
                continue
            start = pre2
        else:
            continue
        rest = skip_punct(toks, i + 1)
        if rest >= n:
            continue
        end = consume_np(toks, rest) or _finite_clause_end(toks, rest) or rest + 1
        hits.append(
            _hit(
                "comparative_than",
                toks,
                start,
                end,
                f"{span_from(toks, start, i + 1)} than",
                toks[prev].synsets[:2],
            )
        )
    return hits


def span_from(toks: list[Tok], a: int, b: int) -> str:
    return " ".join(t.word for t in toks[a:b])


def equative_as(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "as":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].pos not in ADJ | ADV:
            continue
        k = skip_punct(toks, j + 1)
        if k >= n or toks[k].lower != "as":
            continue
        end = consume_np(toks, k + 1) or _finite_clause_end(toks, k + 1) or k + 1
        hits.append(
            _hit(
                "equative_as",
                toks,
                i,
                end,
                f"as {toks[j].word} as",
                toks[j].synsets[:2],
            )
        )
    return hits


def comparative_correlative(toks: list[Tok]) -> list[Structure]:
    marks = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "the":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n:
            continue
        if toks[j].lower in {"more", "less"} or toks[j].pos in {"JJR", "RBR"}:
            marks.append(i)
    if len(marks) < 2:
        return []
    a, b = marks[0], marks[1]
    end = _finite_clause_end(toks, b + 2) or min(b + 4, n)
    return [
        _hit(
            "comparative_correlative",
            toks,
            a,
            end,
            "the more/less … the more/less …",
            (),
        )
    ]


def because_adjunct(toks: list[Tok]) -> list[Structure]:
    hits = []
    for i, t in enumerate(toks):
        if t.lower != "because":
            continue
        end = _finite_clause_end(toks, i + 1)
        if end is None:
            continue
        hits.append(_hit("because_adjunct", toks, i, end, "because + finite clause", ()))
    return hits


def when_adjunct(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "when":
            continue
        prev = _prev_content(toks, i)
        if prev >= 0 and _content_noun(toks[prev]):
            continue
        if prev >= 0 and (
            "verb.cognition" in toks[prev].lexnames or "verb.communication" in toks[prev].lexnames
        ):
            continue
        end = _finite_clause_end(toks, i + 1)
        if end is None:
            continue
        hits.append(_hit("when_adjunct", toks, i, end, "when-clause adjunct", ()))
    return hits


def so_that_purpose(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "so":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lower != "that":
            continue
        end = _finite_clause_end(toks, j + 1)
        if end is None:
            continue
        hits.append(_hit("so_that_purpose", toks, i, end, "so that + finite clause", ()))
    return hits


def np_coordination(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower not in CC_WORDS or t.pos != "CC":
            continue
        if i == 0:
            continue
        left = toks[i - 1]
        if not _content_noun(left):
            continue
        right_end = consume_np(toks, i + 1)
        if right_end is None:
            continue
        right_head = toks[right_end - 1]
        if not _content_noun(right_head):
            continue
        # walk left over a short NP (det/adj/noun)
        start = i - 1
        while start > 0 and toks[start - 1].pos in DET | ADJ | NOUN | {"PRP$"}:
            start -= 1
        hits.append(
            _hit(
                "np_coordination",
                toks,
                start,
                right_end,
                f"NP {t.word} NP",
                left.synsets[:1] + right_head.synsets[:1],
            )
        )
    return hits


def clausal_coordination(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower not in CC_WORDS or t.pos != "CC":
            continue
        left_v = None
        for j in range(i - 1, max(-1, i - 7), -1):
            if toks[j].pos in VERB_FIN or toks[j].pos == "MD":
                left_v = j
                break
            if toks[j].pos == "CC":
                break
        if left_v is None:
            continue
        end = _finite_clause_end(toks, i + 1)
        if end is None:
            continue
        hits.append(
            _hit(
                "clausal_coordination",
                toks,
                left_v,
                end,
                f"finite clause {t.word} finite clause",
                (),
            )
        )
    return hits


def correlative_coordination(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    pairs = (
        ("both", "and"),
        ("either", "or"),
        ("neither", "nor"),
    )
    lower = [t.lower for t in toks]
    for a, b in pairs:
        if a in lower and b in lower:
            i = lower.index(a)
            j = lower.index(b, i + 1) if b in lower[i + 1 :] else -1
            if j < 0:
                continue
            end = consume_np(toks, j + 1) or _finite_clause_end(toks, j + 1) or j + 1
            hits.append(
                _hit(
                    "correlative_coordination",
                    toks,
                    i,
                    end,
                    f"{a} … {b}",
                    (),
                )
            )
    # not only … but
    for i, t in enumerate(toks):
        if t.lower != "not":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lower != "only":
            continue
        rest = [x.lower for x in toks[j + 1 :]]
        if "but" not in rest:
            continue
        k = j + 1 + rest.index("but")
        end = _finite_clause_end(toks, k + 1) or min(k + 3, n)
        hits.append(
            _hit(
                "correlative_coordination",
                toks,
                i,
                end,
                "not only … but",
                (),
            )
        )
    return hits


def nominal_apposition(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if not _content_noun(t):
            continue
        j = skip_punct(toks, i + 1)
        comma = j < n and toks[j].word == ","
        if comma:
            j = skip_punct(toks, j + 1)
        if j >= n:
            continue
        # second NP must have a determiner (blocks coffee-cup compounds)
        if toks[j].pos not in DET | {"PRP$"}:
            continue
        end = consume_np(toks, j)
        if end is None:
            continue
        head2 = toks[end - 1]
        if not _content_noun(head2):
            continue
        personish = (
            t.pos in {"NNP", "NNPS"}
            or "noun.person" in t.lexnames
            or "noun.group" in t.lexnames
        )
        if not personish and not comma:
            continue
        hits.append(
            _hit(
                "nominal_apposition",
                toks,
                i,
                end,
                f"{t.word} ≈ {span_from(toks, j, end)}",
                t.synsets[:2] + head2.synsets[:1],
            )
        )
    return hits


def negative_inversion(toks: list[Tok]) -> list[Structure]:
    if not toks:
        return []
    i = 0
    if toks[0].lower == "not" and len(toks) > 1 and toks[1].lower == "only":
        i = 2
    elif toks[0].lower in NEG_FRONT:
        i = 1
    else:
        return []
    i = skip_punct(toks, i)
    if i >= len(toks) or toks[i].lower not in AUX:
        return []
    rest = skip_punct(toks, i + 1)
    subj = consume_np(toks, rest)
    if subj is None:
        return []
    # inverted: aux before subject. Confirm subject is not before the aux.
    return [
        _hit(
            "negative_inversion",
            toks,
            0,
            subj,
            f"{span_from(toks, 0, i)} + aux + subject",
            (),
        )
    ]


def locative_inversion(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[0].pos != "IN":
        return []
    if toks[0].lower in {"if", "because", "although", "though", "when", "while", "as"}:
        return []
    np_end = consume_np(toks, 1)
    if np_end is None:
        return []
    v_i = skip_punct(toks, np_end)
    if v_i >= len(toks) or toks[v_i].pos not in VERB_FIN:
        return []
    if toks[v_i].first_lexname != MOTION:
        return []
    subj_end = consume_np(toks, v_i + 1)
    if subj_end is None:
        return []
    return [
        _hit(
            "locative_inversion",
            toks,
            0,
            subj_end,
            f"fronted PP + motion {toks[v_i].word} + subject",
            toks[v_i].synsets[:2],
        )
    ]


def object_fronting(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[-1].word == "?":
        return []
    if toks[0].lower not in DEM:
        return []
    j = skip_punct(toks, 1)
    if j >= len(toks) or toks[j].pos != "PRP":
        return []
    k = skip_punct(toks, j + 1)
    if k >= len(toks):
        return []
    if toks[k].pos not in VERB_FIN | {"MD"} and toks[k].lower not in AUX:
        return []
    if toks[k].lemma in BE:
        return []  # This is a book
    return [
        _hit(
            "object_fronting",
            toks,
            0,
            min(k + 2, len(toks)),
            f"fronted {toks[0].word} + {toks[j].word} + finite",
            (),
        )
    ]


CATALOG = (
    imperative,
    pseudo_cleft,
    reverse_pseudo_cleft,
    prepositional_dative,
    purpose_infinitive,
    free_relative,
    comparative_than,
    equative_as,
    comparative_correlative,
    because_adjunct,
    when_adjunct,
    so_that_purpose,
    np_coordination,
    clausal_coordination,
    correlative_coordination,
    nominal_apposition,
    negative_inversion,
    locative_inversion,
    object_fronting,
)
