"""Named grammatical constructions, licensed by WordNet where a verb/noun class matters.

Each detector is a function toks → list[Structure]. Precision over recall.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from writing_style.grammar.tokens import (
    ADJ,
    ADV,
    AUX,
    BE,
    DET,
    DITRANSITIVE_FRAMES,
    GERUND_FRAMES,
    GET,
    INFINITIVE_FRAMES,
    INTRANSITIVE_FRAMES,
    NOUN,
    REL_COMPL,
    THAT_CLAUSE_FRAMES,
    TIME_WORDS,
    Tok,
    TRANSITIVE_FRAMES,
    VERB_FIN,
    consume_np,
    look_back_non_adv,
    next_fin_verb,
    skip_punct,
    span_text,
)


@dataclass(frozen=True)
class Structure:
    id: str
    label: str
    span: str
    start: int
    end: int
    evidence: str
    wordnet: tuple[str, ...] = ()


STRUCTURES: dict[str, str] = {
    "zero_relative_clause": "relative clause with that/who/which omitted (the man I saw)",
    "that_relative_clause": "relative clause headed by that (the man that I saw)",
    "wh_relative_clause": "relative clause headed by who/which/whose/where/when",
    "sentential_relative": "non-restrictive which-clause with a clausal antecedent (…, which …)",
    "reduced_relative_clause": "participial relative with no complementizer (the man sitting…)",
    "noun_appositive_that": "content-noun + that-clause with no gap (the fact that he left)",
    "that_complement": "verb taking a that-clause (WordNet frame 26)",
    "zero_that_complement": "verb taking a finite clause with that omitted (I think he left)",
    "infinitival_complement": "verb taking (NP) to-infinitive (WordNet frames 24/28/32)",
    "gerund_complement": "verb taking a gerund (WordNet frame 33)",
    "whether_if_complement": "cognition/communication verb + if/whether clause",
    "ditransitive": "verb with two object NPs (WordNet frame 14)",
    "be_passive": "be + past participle of a WordNet-transitive verb",
    "get_passive": "get + past participle of a WordNet-transitive verb",
    "there_existential": "there + be + NP",
    "it_extraposition": "it + be + Adj + that/to clause",
    "it_cleft": "it + be + NP + that/who clause",
    "polar_question": "subject-auxiliary inversion with ?",
    "wh_question": "wh-word + auxiliary inversion with ?",
    "conditional_if": "if-clause adjunct (not an embedded whether)",
    "concessive": "although/though/even though adjunct",
    "imperative": "subjectless base-form verb (Leave. / Don't wait. / Please sit.)",
    "pseudo_cleft": "wh-clause + be + XP (What he wants is a raise)",
    "reverse_pseudo_cleft": "XP + be + wh-clause (A raise is what he wants)",
    "prepositional_dative": "theme + to/for + recipient (WordNet frame 15)",
    "purpose_infinitive": "to-infinitive adjunct of purpose (left to catch… / in order to)",
    "free_relative": "fused wh-clause used as an NP (what he said / whoever comes)",
    "comparative_than": "comparative + than (bigger than / more interesting than)",
    "equative_as": "as + Adj + as",
    "comparative_correlative": "the more… the more…",
    "because_adjunct": "because + finite clause",
    "when_adjunct": "when-clause adjunct (not a relative, not a complement)",
    "so_that_purpose": "so that + finite clause",
    "np_coordination": "NP and/or/but NP",
    "clausal_coordination": "finite clause and/but/or finite clause",
    "correlative_coordination": "both…and / either…or / neither…nor / not only…but",
    "nominal_apposition": "two NPs, second a description of the first (my friend the lawyer)",
    "negative_inversion": "fronted negative + aux + subject (Never have I…)",
    "locative_inversion": "fronted PP + motion verb + subject (Down the hill came…)",
    "object_fronting": "fronted object + subject + finite (This I cannot accept)",
}


def _hit(
    sid: str,
    toks: list[Tok],
    start: int,
    end: int,
    evidence: str,
    wn: tuple[str, ...] = (),
) -> Structure:
    return Structure(
        id=sid,
        label=STRUCTURES[sid],
        span=span_text(toks, start, end),
        start=start,
        end=end,
        evidence=evidence,
        wordnet=wn,
    )


# First-synset hypernyms that license a content that-clause (the fact that…).
_CONTENT_HYPER = frozenset(
    {
        "statement.n.01",
        "assertion.n.01",
        "information.n.01",
        "information.n.02",
        "news.n.01",
        "content.n.05",
        "cognition.n.01",
        "speech_act.n.01",
        "fact.n.01",
    }
)
_CONTENT_BLOCK = frozenset(
    {
        "publication.n.01",
        "artifact.n.01",
        "person.n.01",
        "narrative.n.01",
        "document.n.01",
        "organism.n.01",
    }
)


@lru_cache(maxsize=2048)
def _hypernym_names(syn_name: str) -> frozenset[str]:
    from nltk.corpus import wordnet as wn

    syn = wn.synset(syn_name)
    names = {syn.name()}
    for s in syn.closure(lambda x: x.hypernyms()):
        names.add(s.name())
    return frozenset(names)


def _content_clause_noun(tok: Tok) -> bool:
    """WordNet: propositional/content nouns, not books/people/artifacts."""
    if tok.first_lexname == "noun.cognition":
        return True
    if not tok.synsets:
        return False
    names = _hypernym_names(tok.synsets[0])
    if names & _CONTENT_BLOCK:
        return False
    return bool(names & _CONTENT_HYPER)


def _content_noun(tok: Tok) -> bool:
    if not tok.is_noun:
        return False
    if tok.pos in {"NNP", "NNPS"}:
        return True
    # tagged NN with no WordNet noun sense is usually a tagger miss (e.g. "distant")
    return bool(tok.synsets)


def _sent_initial_time(toks: list[Tok], i: int) -> bool:
    t = toks[i]
    if t.lower not in TIME_WORDS and "noun.time" not in t.lexnames:
        return False
    j = i - 1
    while j >= 0 and toks[j].is_punct:
        j -= 1
    if j >= 0 and toks[j].pos in DET | ADJ:
        return False
    return j < 0 or toks[j].pos in {"CC"}


def _clause_object(toks: list[Tok], verb_i: int) -> bool:
    j = skip_punct(toks, verb_i + 1)
    if j < len(toks) and toks[j].pos in ADV:
        j += 1
    end = consume_np(toks, j)
    if end is None:
        return False
    head = toks[end - 1]
    if "noun.time" in head.lexnames or head.lower in TIME_WORDS:
        return False
    return True


def _gapped_vp(toks: list[Tok], verb: Tok) -> bool:
    trans = bool(verb.frame_ids & TRANSITIVE_FRAMES)
    intrans = bool(verb.frame_ids & INTRANSITIVE_FRAMES) or not verb.frame_ids
    if not trans:
        return False
    if _clause_object(toks, verb.i):
        return False
    if intrans:
        return False
    return True


def _has_frame(tok: Tok, frames: frozenset[int]) -> bool:
    return bool(tok.frame_ids & frames)


def zero_relative_clause(toks: list[Tok]) -> list[Structure]:
    hits: list[Structure] = []
    n = len(toks)
    for i, t in enumerate(toks):
        if not _content_noun(t):
            continue
        if _sent_initial_time(toks, i):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n:
            continue
        if toks[j].word == "," or toks[j].lower in REL_COMPL:
            continue
        subj_end = consume_np(toks, j)
        if subj_end is None or subj_end <= j:
            continue
        # contact clause subject is typically a pronoun or a short NP, not the
        # start of a brand-new sentence's vocative. Reject if subject is the
        # same token as the head (shouldn't happen) or is a WH word.
        if toks[j].pos in {"WP", "WDT", "WP$", "WRB"}:
            continue
        v_i = next_fin_verb(toks, subj_end)
        if v_i is None:
            continue
        verb = toks[v_i]
        if verb.lemma in BE and v_i + 1 < n and toks[v_i + 1].pos == "VBN":
            # "the man I was given" still a zero relative; keep.
            pass
        # "my friend the lawyer left" is apposition + main verb, not a contact clause.
        # Contact clauses still have a later finite verb ("the man I saw left").
        inner_head = toks[subj_end - 1]
        later_fin = next_fin_verb(toks, v_i + 1)
        if (
            later_fin is None
            and toks[j].pos in DET
            and inner_head.pos != "PRP"
            and ("noun.person" in inner_head.lexnames or "noun.group" in inner_head.lexnames)
        ):
            continue
        wn = t.synsets[:3] + verb.synsets[:2]
        hits.append(
            _hit(
                "zero_relative_clause",
                toks,
                i,
                v_i + 1,
                f"noun {t.word!r} + subject + finite {verb.word!r}, no complementizer",
                wn,
            )
        )
    return hits


def _that_after_noun(toks: list[Tok]) -> list[Structure]:
    hits: list[Structure] = []
    n = len(toks)
    for i, t in enumerate(toks):
        if not _content_noun(t):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lower != "that":
            continue
        rest = skip_punct(toks, j + 1)
        if rest >= n:
            continue
        # subject relative: that + finite verb
        if toks[rest].pos in VERB_FIN or toks[rest].pos == "VBN":
            v_i = rest
            subj_end = rest
        else:
            subj_end = consume_np(toks, rest)
            if subj_end is None:
                continue
            v_i = next_fin_verb(toks, subj_end)
            if v_i is None:
                continue
        verb = toks[v_i]
        licensed = _content_clause_noun(t)
        gapped = _gapped_vp(toks, verb)
        if licensed and not gapped:
            sid = "noun_appositive_that"
            ev = f"content noun {t.word!r} ({t.first_lexname}) + complete that-clause"
        else:
            sid = "that_relative_clause"
            ev = f"noun {t.word!r} + that + {verb.word!r}"
        hits.append(_hit(sid, toks, i, v_i + 1, ev, t.synsets[:3] + verb.synsets[:2]))
    return hits


def that_relative_clause(toks: list[Tok]) -> list[Structure]:
    return [h for h in _that_after_noun(toks) if h.id == "that_relative_clause"]


def noun_appositive_that(toks: list[Tok]) -> list[Structure]:
    return [h for h in _that_after_noun(toks) if h.id == "noun_appositive_that"]


def wh_relative_clause(toks: list[Tok]) -> list[Structure]:
    hits: list[Structure] = []
    n = len(toks)
    wh = {"who", "whom", "which", "whose", "where", "when"}
    for i, t in enumerate(toks):
        if not _content_noun(t):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lower not in wh:
            continue
        # whose + NP then verb; others + (NP)? + verb
        k = skip_punct(toks, j + 1)
        if toks[j].lower == "whose":
            np_end = consume_np(toks, k)
            if np_end is None:
                continue
            v_i = next_fin_verb(toks, np_end)
        elif k < n and (toks[k].pos in VERB_FIN or toks[k].pos == "VBN" or toks[k].pos == "MD"):
            v_i = k
        else:
            np_end = consume_np(toks, k)
            if np_end is None:
                continue
            v_i = next_fin_verb(toks, np_end)
        if v_i is None:
            continue
        hits.append(
            _hit(
                "wh_relative_clause",
                toks,
                i,
                v_i + 1,
                f"noun {t.word!r} + {toks[j].word}",
                t.synsets[:3],
            )
        )
    return hits


def sentential_relative(toks: list[Tok]) -> list[Structure]:
    """Comma-which (or who) whose antecedent is a clause, not an NP."""
    hits: list[Structure] = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower not in {"which", "who"}:
            continue
        prev = i - 1
        if prev < 0 or toks[prev].word != ",":
            continue
        head_i = prev - 1
        while head_i >= 0 and toks[head_i].is_punct:
            head_i -= 1
        if head_i >= 0 and _content_noun(toks[head_i]):
            continue
        rest = skip_punct(toks, i + 1)
        if rest < n and (toks[rest].pos in VERB_FIN or toks[rest].pos == "VBN" or toks[rest].pos == "MD"):
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
                "sentential_relative",
                toks,
                prev,
                v_i + 1,
                f"clausal antecedent + {t.word} + {toks[v_i].word}",
                (),
            )
        )
    return hits


def reduced_relative_clause(toks: list[Tok]) -> list[Structure]:
    hits: list[Structure] = []
    n = len(toks)
    for i, t in enumerate(toks):
        if not _content_noun(t):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].pos not in {"VBG", "VBN"}:
            continue
        prev = look_back_non_adv(toks, j)
        if prev >= 0 and toks[prev].lemma in AUX:
            continue
        nxt = skip_punct(toks, j + 1)
        # demand a following PP/NP so "running water" compounds don't fire
        if nxt >= n:
            continue
        if toks[nxt].pos not in {"IN", "RP", "TO", "DT", "PRP$", "RB", "CD"} | NOUN and toks[nxt].pos != "PRP":
            continue
        hits.append(
            _hit(
                "reduced_relative_clause",
                toks,
                i,
                min(nxt + 1, n),
                f"noun {t.word!r} + participle {toks[j].word!r}",
                t.synsets[:2] + toks[j].synsets[:2],
            )
        )
    return hits


def _verb_plus_clause(toks: list[Tok], require_that: bool | None) -> list[tuple[Tok, int, int]]:
    """(verb, that_or_subject_index, verb_of_clause) for cognition/communication that-frames."""
    out = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            continue
        if not _has_frame(t, THAT_CLAUSE_FRAMES):
            continue
        if t.lemma in BE:
            continue
        j = skip_punct(toks, i + 1)
        if j >= n:
            continue
        has_that = toks[j].lower == "that"
        if require_that is True and not has_that:
            continue
        if require_that is False and has_that:
            continue
        k = skip_punct(toks, j + 1) if has_that else j
        if k >= n:
            continue
        if toks[k].pos in VERB_FIN:
            continue  # that + verb with no subject: not a complement clause we want
        subj = consume_np(toks, k)
        if subj is None:
            continue
        v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        out.append((t, j, v_i))
    return out


def that_complement(toks: list[Tok]) -> list[Structure]:
    hits = []
    for verb, j, v_i in _verb_plus_clause(toks, require_that=True):
        frames = tuple(s for s in verb.frame_strings if "CLAUSE" in s)[:2]
        hits.append(
            _hit(
                "that_complement",
                toks,
                verb.i,
                v_i + 1,
                f"{verb.lemma} licenses that-CLAUSE ({', '.join(frames) or 'frame 26'})",
                verb.synsets[:3],
            )
        )
    return hits


def zero_that_complement(toks: list[Tok]) -> list[Structure]:
    hits = []
    for verb, j, v_i in _verb_plus_clause(toks, require_that=False):
        # reject if what follows is just another NP object, not a clause:
        # already required a finite verb after the NP.
        hits.append(
            _hit(
                "zero_that_complement",
                toks,
                verb.i,
                v_i + 1,
                f"{verb.lemma} licenses that-CLAUSE and that is omitted",
                verb.synsets[:3],
            )
        )
    return hits


def infinitival_complement(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            continue
        if not _has_frame(t, INFINITIVE_FRAMES):
            continue
        # motion + to-V is purpose (stopped to rest, came to see), not a selected complement
        if t.first_lexname == "verb.motion":
            continue
        j = skip_punct(toks, i + 1)
        # optional object NP then to VB  (frame 24) or immediate to VB (28/32)
        if j < n and toks[j].lower != "to":
            np_end = consume_np(toks, j)
            if np_end is None:
                continue
            j = skip_punct(toks, np_end)
        if j >= n or toks[j].lower != "to":
            continue
        k = skip_punct(toks, j + 1)
        if k >= n or toks[k].pos not in {"VB", "VBP"}:
            continue
        hits.append(
            _hit(
                "infinitival_complement",
                toks,
                t.i,
                k + 1,
                f"{t.lemma} licenses to-INFINITIVE",
                t.synsets[:3],
            )
        )
    return hits


def gerund_complement(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB"}:
            continue
        if not _has_frame(t, GERUND_FRAMES):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].pos != "VBG":
            continue
        prev = look_back_non_adv(toks, j)
        if prev != i:
            continue
        hits.append(
            _hit(
                "gerund_complement",
                toks,
                t.i,
                j + 1,
                f"{t.lemma} licenses VERB-ing",
                t.synsets[:3],
            )
        )
    return hits


def whether_if_complement(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            continue
        comm = "verb.cognition" in t.lexnames or "verb.communication" in t.lexnames
        if not comm:
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lower not in {"if", "whether"}:
            continue
        # skip sentence-initial if handled as conditional: verb must precede if
        k = skip_punct(toks, j + 1)
        subj = consume_np(toks, k)
        if subj is None:
            continue
        v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        hits.append(
            _hit(
                "whether_if_complement",
                toks,
                t.i,
                v_i + 1,
                f"{t.lemma} ({sorted(t.lexnames & {'verb.cognition','verb.communication'})[0]}) + {toks[j].word}",
                t.synsets[:3],
            )
        )
    return hits


def ditransitive(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos not in VERB_FIN | {"VB", "VBG", "VBN"}:
            continue
        if t.lemma in BE:
            continue
        if not _has_frame(t, DITRANSITIVE_FRAMES):
            continue
        a = consume_np(toks, i + 1)
        if a is None:
            continue
        b = consume_np(toks, a)
        if b is None:
            continue
        recip = toks[a - 1]
        if recip.pos != "PRP" and "noun.person" not in recip.lexnames and "noun.group" not in recip.lexnames:
            continue
        # "a sentence I read" — I is a relative subject, not an object
        if toks[a].lower in {"i", "we", "he", "she", "they"} and next_fin_verb(toks, b):
            continue
        if toks[b - 1].lower in TIME_WORDS:
            continue
        hits.append(
            _hit(
                "ditransitive",
                toks,
                t.i,
                b,
                f"{t.lemma} licenses Somebody ----s somebody something",
                t.synsets[:3],
            )
        )
    return hits


def _passive(toks: list[Tok], aux_set: frozenset[str], sid: str) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos != "VBN":
            continue
        if not (t.frame_ids & TRANSITIVE_FRAMES):
            continue
        prev = look_back_non_adv(toks, i)
        if prev < 0:
            continue
        aux = toks[prev]
        if aux.lower == "being":
            prev2 = look_back_non_adv(toks, prev)
            if prev2 < 0 or toks[prev2].lemma not in BE:
                continue
            start = prev2
        elif aux.lemma in aux_set or aux.lower in aux_set:
            start = prev
        else:
            continue
        hits.append(
            _hit(
                sid,
                toks,
                start,
                i + 1,
                f"{aux.word} + participle {t.word} ({t.lemma} is WordNet-transitive)",
                t.synsets[:3],
            )
        )
    return hits


def be_passive(toks: list[Tok]) -> list[Structure]:
    return _passive(toks, BE, "be_passive")


def get_passive(toks: list[Tok]) -> list[Structure]:
    return _passive(toks, GET, "get_passive")


def there_existential(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.pos != "EX" and not (t.lower == "there" and i + 1 < n and toks[i + 1].lemma in BE):
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lemma not in BE:
            continue
        k = skip_punct(toks, j + 1)
        while k < n and toks[k].pos in ADV | ADJ:
            k += 1
        np_end = consume_np(toks, k)
        if np_end is None:
            continue
        hits.append(
            _hit(
                "there_existential",
                toks,
                i,
                np_end,
                "there + be + NP",
                toks[np_end - 1].synsets[:2],
            )
        )
    return hits


def it_extraposition(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "it":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lemma not in BE:
            continue
        k = skip_punct(toks, j + 1)
        while k < n and toks[k].pos in ADV:
            k += 1
        if k >= n or toks[k].pos not in ADJ:
            continue
        if "adj.all" not in toks[k].lexnames and not toks[k].synsets:
            continue
        m = skip_punct(toks, k + 1)
        if m >= n or toks[m].lower not in {"that", "to"}:
            continue
        end = m + 1
        rest = skip_punct(toks, m + 1)
        if toks[m].lower == "that":
            subj = consume_np(toks, rest)
            if subj is not None:
                v_i = next_fin_verb(toks, subj)
                if v_i is not None:
                    end = v_i + 1
        elif rest < n and toks[rest].pos in {"VB", "VBP"}:
            end = rest + 1
        hits.append(
            _hit(
                "it_extraposition",
                toks,
                i,
                end,
                f"it + be + {toks[k].word} + {toks[m].word}",
                toks[k].synsets[:2],
            )
        )
    return hits


def it_cleft(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "it":
            continue
        j = skip_punct(toks, i + 1)
        if j >= n or toks[j].lemma not in BE:
            continue
        k = skip_punct(toks, j + 1)
        np_end = consume_np(toks, k)
        if np_end is None:
            continue
        # cleft has NP, not Adj (that's extraposition)
        if k < n and toks[k].pos in ADJ and consume_np(toks, k) is None:
            continue
        m = skip_punct(toks, np_end)
        if m >= n or toks[m].lower not in {"that", "who", "which"}:
            continue
        rest = skip_punct(toks, m + 1)
        v_i = rest if rest < n and (toks[rest].pos in VERB_FIN or toks[rest].pos == "VBN") else None
        if v_i is None:
            subj = consume_np(toks, rest)
            if subj is None:
                continue
            v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        hits.append(
            _hit(
                "it_cleft",
                toks,
                i,
                v_i + 1,
                f"it + be + NP + {toks[m].word}",
                (),
            )
        )
    return hits


def polar_question(toks: list[Tok]) -> list[Structure]:
    if not toks:
        return []
    if toks[-1].word != "?":
        return []
    head = toks[0]
    if head.lower not in AUX:
        return []
    if skip_punct(toks, 1) < len(toks) and toks[skip_punct(toks, 1)].pos in {"WP", "WDT", "WP$", "WRB"}:
        return []
    return [_hit("polar_question", toks, 0, len(toks), "aux-subject inversion + ?", ())]


def wh_question(toks: list[Tok]) -> list[Structure]:
    if not toks or toks[-1].word != "?":
        return []
    head = toks[0]
    if head.pos not in {"WP", "WDT", "WP$", "WRB"} and head.lower not in {
        "what",
        "who",
        "whom",
        "whose",
        "which",
        "where",
        "when",
        "why",
        "how",
    }:
        return []
    return [_hit("wh_question", toks, 0, len(toks), f"{head.word} + inversion + ?", ())]


def conditional_if(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        if t.lower != "if":
            continue
        # embedded if after a cognition verb is whether_if_complement
        prev = look_back_non_adv(toks, i)
        if prev >= 0 and (
            "verb.cognition" in toks[prev].lexnames or "verb.communication" in toks[prev].lexnames
        ):
            continue
        rest = skip_punct(toks, i + 1)
        subj = consume_np(toks, rest)
        if subj is None:
            continue
        v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        hits.append(_hit("conditional_if", toks, i, v_i + 1, "if + finite clause", ()))
    return hits


def concessive(toks: list[Tok]) -> list[Structure]:
    hits = []
    n = len(toks)
    for i, t in enumerate(toks):
        word = t.lower
        if word not in {"although", "though", "whereas"}:
            if not (
                word == "even"
                and i + 1 < n
                and toks[i + 1].lower == "though"
            ):
                continue
        start = i
        k = i + 1
        if word == "even":
            k = i + 2
        rest = skip_punct(toks, k)
        subj = consume_np(toks, rest)
        if subj is None:
            continue
        v_i = next_fin_verb(toks, subj)
        if v_i is None:
            continue
        hits.append(_hit("concessive", toks, start, v_i + 1, f"{span_text(toks, start, k)} + finite clause", ()))
    return hits


CATALOG = (
    zero_relative_clause,
    that_relative_clause,
    wh_relative_clause,
    sentential_relative,
    reduced_relative_clause,
    noun_appositive_that,
    that_complement,
    zero_that_complement,
    infinitival_complement,
    gerund_complement,
    whether_if_complement,
    ditransitive,
    be_passive,
    get_passive,
    there_existential,
    it_extraposition,
    it_cleft,
    polar_question,
    wh_question,
    conditional_if,
    concessive,
)
