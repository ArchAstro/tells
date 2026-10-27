"""Every feature measured per sentence: 40 grammar structures plus surface habits.

Each feature carries a plain description and a hint for moving a draft toward
the author when it is over- or under-used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from writing_style.grammar.catalog import STRUCTURES
from writing_style.sources import WORD


@dataclass(frozen=True)
class Feature:
    id: str
    label: str
    too_many: str = "Rephrase some of these sentences."
    too_few: str = "Use this construction a little more where it fits."


SURFACE: dict[str, Feature] = {f.id: f for f in [
    Feature("fragment", "sentence with no verb (Pieces, state, invariants.)",
            "Give these fragments a subject and a verb, or fold them into the sentence before.",
            "The author uses some verbless fragments (Usually badly. Forever.). A few are fine."),
    Feature("short_sentence", "5 words or fewer",
            "Merge some short sentences into their neighbours.",
            "Break a few long sentences into one long and one very short one."),
    Feature("long_sentence", "30 words or more",
            "Split a few of the longest sentences.",
            "Let a few sentences run long, the way the author does: join two with because/so/and."),
    Feature("colon_label", "opens with a short label and a colon (Cost: …)",
            "Turn 'Label: thing' openers into full sentences."),
    Feature("ends_colon", "ends with a colon (a list lead-in)"),
    Feature("em_dash", "contains a dash aside (—)",
            "Replace some dashes with commas, parentheses or a new sentence.",
            "The author uses dash asides; one or two would fit."),
    Feature("semicolon", "contains a semicolon",
            "Replace semicolons with a full stop or 'and'/'so'."),
    Feature("parenthetical", "contains a parenthetical",
            "Cut some parenthetical asides.",
            "The author makes asides in parentheses; add one where you'd naturally aside."),
    Feature("first_person", "first person (I, my, we, our)",
            "Some of these could be about the thing, not about you.",
            "Tell it as your story: who decided, who broke it, what you saw."),
    Feature("second_person", "addresses the reader (you, your)",
            "Address the reader a little less.",
            "Talk to the reader: 'you'll see', 'if you're building this', generic 'you'."),
    Feature("contraction", "contains a contraction (it's, don't, I'm)",
            "Spell out a few contractions.",
            "Use contractions: it's, don't, I'd, you're."),
    Feature("hedge", "hedge or casual intensifier (pretty, basically, just, I think, really)",
            "Cut some hedges.",
            "Add the author's casual hedges (pretty, basically, a bit, I think)."),
    Feature("starts_with_conjunction", "starts with And/But/So/Or",
            "Start fewer sentences with a conjunction.",
            "Start a few sentences with So/But/And, the way people talk."),
    Feature("not_x_but_y", "antithesis (not X but Y / isn't X, it's Y)",
            "Drop the 'not X, but Y' framing; just say Y."),
    Feature("list_of_three", "list of three (X, Y and Z)",
            "Break up lists of three; use two items, or a sentence each.",
            "The author lists things in threes now and then."),
    Feature("imperative_start", "starts with a bare verb (Skim it…)",
            "Turn commands to the reader into statements.",
            "The author sometimes tells the reader what to do (Read it left to right)."),
]}

GRAMMAR: dict[str, Feature] = {sid: Feature(sid, label) for sid, label in STRUCTURES.items()}
GRAMMAR["clausal_coordination"] = Feature(
    "clausal_coordination", STRUCTURES["clausal_coordination"],
    "Split some 'X, and Y' sentences into two.", "Join a few related sentences with 'and'/'but'.")
GRAMMAR["np_coordination"] = Feature(
    "np_coordination", STRUCTURES["np_coordination"],
    "Fewer 'X and Y' noun pairs.", "Name things in pairs now and then (X and Y).")
GRAMMAR["when_adjunct"] = Feature(
    "when_adjunct", STRUCTURES["when_adjunct"],
    "Rewrite some 'When X, Y' openers as two sentences or 'If X, Y'.")
GRAMMAR["noun_appositive_that"] = Feature(
    "noun_appositive_that", STRUCTURES["noun_appositive_that"],
    "Rephrase 'the fact/proof/thing that …' constructions.")
GRAMMAR["wh_question"] = Feature(
    "wh_question", STRUCTURES["wh_question"], "Ask fewer questions.",
    "Ask the reader a real question (not a rhetorical setup you answer yourself).")
GRAMMAR["purpose_infinitive"] = Feature(
    "purpose_infinitive", STRUCTURES["purpose_infinitive"], "Fewer 'to do X' purpose clauses.",
    "Say why more often: 'I did X to see/get/stop Y'.")
GRAMMAR["infinitival_complement"] = Feature(
    "infinitival_complement", STRUCTURES["infinitival_complement"], "Fewer 'want to / try to' verbs.",
    "Use more 'I wanted to / had to / tried to'.")

FEATURES: dict[str, Feature] = {**GRAMMAR, **SURFACE}

CONTRACTION = re.compile(r"\b\w+'(s|re|ve|ll|d|m|t)\b|\b\w+n't\b", re.I)
HEDGE = re.compile(r"\b(pretty|basically|kind of|sort of|a bit|a little|I think|I guess|probably|"
                   r"honestly|actually|really|just)\b", re.I)
NOT_X_BUT_Y = re.compile(r"\bnot\b[^.;]{1,60}\bbut\b|\bisn't\b[^.;]{1,60}[,;] it's\b|"
                         r"\b(is|was) not\b[^.]{1,60}\. (It|This) (is|was)\b", re.I)
ITEM = r"[\w-]+(?: [\w-]+){0,2}"
# X, Y and Z; or a bare X, Y, Z closing the sentence (Pieces, state, invariants.)
LIST_OF_THREE = re.compile(rf"\b{ITEM}, {ITEM},? (and|or) [\w-]+|(^|[:;] ){ITEM}, {ITEM}, {ITEM}[.!?]?$", re.I)
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|I'll|me|my|mine|we|our|us)\b")
SECOND_PERSON = re.compile(r"\b(you|your|you're|you've|you'll|you'd)\b", re.I)
STARTS_CONJ = re.compile(r"^(And|But|So|Or)\b")
COLON_LABEL = re.compile(r"^[^:]{1,40}:\s")
VERB_TAGS = {"VB", "VBD", "VBG", "VBN", "VBP", "VBZ", "MD"}


def surface(sentence: str) -> set[str]:
    from nltk import pos_tag, word_tokenize

    words = WORD.findall(sentence)
    tags = pos_tag(word_tokenize(sentence))
    hits = set()
    if not any(t in VERB_TAGS for _, t in tags):
        hits.add("fragment")
    if len(words) <= 5:
        hits.add("short_sentence")
    if len(words) >= 30:
        hits.add("long_sentence")
    if COLON_LABEL.match(sentence) and len(WORD.findall(sentence.split(":", 1)[0])) <= 4:
        hits.add("colon_label")
    if sentence.rstrip().endswith(":"):
        hits.add("ends_colon")
    if "—" in sentence or " -- " in sentence or " - " in sentence:
        hits.add("em_dash")
    if ";" in sentence:
        hits.add("semicolon")
    if "(" in sentence:
        hits.add("parenthetical")
    if FIRST_PERSON.search(sentence):
        hits.add("first_person")
    if SECOND_PERSON.search(sentence):
        hits.add("second_person")
    if CONTRACTION.search(sentence):
        hits.add("contraction")
    if HEDGE.search(sentence):
        hits.add("hedge")
    if STARTS_CONJ.match(sentence):
        hits.add("starts_with_conjunction")
    if NOT_X_BUT_Y.search(sentence):
        hits.add("not_x_but_y")
    if LIST_OF_THREE.search(sentence):
        hits.add("list_of_three")
    if tags and tags[0][0][:1].isupper():
        # the tagger reads a capitalised first word as a name or noun; ask again in lower case
        first = pos_tag([tags[0][0].lower()] + [w for w, _ in tags[1:]])[0][1]
        if "VB" in (tags[0][1], first):
            hits.add("imperative_start")
    return hits


def sentence_features(sentence: str) -> set[str]:
    from writing_style.grammar.classify import classify

    return {h.id for h in classify(sentence)} | surface(sentence)
