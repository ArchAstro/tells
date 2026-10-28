---
name: tells
description: Check a draft against a statistical model of how its author actually writes (grammar structures, sentence length, person, hedges, fragments, dashes) and revise it toward their voice. Use when the user asks to make a draft "sound like me", match their style, check whether a post reads like them or like AI, build a model of their writing from their blog posts, tweets or emails, or runs /tells.
---

# Matching a draft to its author's voice

`tells` measures 56 features per sentence (40 grammar structures from a
WordNet-backed classifier, 16 surface habits) across the author's own writing,
then tells you which features a draft over- or under-uses.

## 0. Running it

Everything ships inside this skill; there is nothing to install. Run the CLI
through the script in this skill's base directory:

```sh
bash <skill-dir>/scripts/tells --help
```

`<skill-dir>` is this skill's base directory (shown when the skill loads).
The commands below write `tells` for short; always run them as
`bash <skill-dir>/scripts/tells ...`.

The first run makes a private Python environment in
`~/.cache/tells/venv` (needs `python3` 3.9+, takes ~20 s), and the
first command that reads text fetches WordNet and the tagger into
`~/.cache/tells/nltk_data`. Both happen once, by themselves.

## 1. Build the model from the author's own writing only

```sh
tells build -c 'blog=~/blog/posts/*.md' -c tweets=~/archive/tweets -o ~/.cache/tells/me.json
tells calibrate ~/.cache/tells/me.json
```

1. Only text the author wrote themselves. No drafts you helped write, no
   co-authored docs, no decks, no research notes: they pull the model toward you.
   Prefer what they actually published (a live blog, a newsletter archive) over
   local drafts, which may have been agent-written or agent-edited.
   - `build` scores every document's *machine-likeness* and warns about any at
     0.6 or above. Show the user that list and ask whether an assistant wrote
     or heavily edited those; if so, rebuild with `-x` for each. Don't skip
     this: a few agent-written posts teach the model the assistant's voice,
     and `check` will then tell you to write more like the assistant (more
     short sentences and fragments, fewer purpose clauses), and every revision
     drifts further from the author.
2. One `-c` per kind of writing (blog, tweets, email). Corpora are weighted
   equally, so 600 tweets don't drown 8 posts. Many short docs are packed into
   120-sentence chunks automatically.
3. Leave out the draft you're checking (`-x draft.md`) if it sits in the glob.
4. `calibrate` scores each of their own documents against the rest. Tell the user
   that band: their own work is "off" on several features too.

## 2. Check

```sh
tells check draft.md -m ~/.cache/tells/me.json
tells check draft.md -m me.json --json     # for a programmatic loop
```

Verdicts per feature:

| Verdict | Meaning | Do |
|---|---|---|
| `FIX` | off, and every corpus agrees on the direction | revise toward the author |
| `format` | off, but corpora disagree (blog vs tweets) | leave it: it's the medium |
| `ai` (suffix) | off in the direction machine prose leans | prioritise it |
| blank | within range | nothing |

`check` also prints the draft's **machine-likeness**: the share of known AI
tells where it sits nearer machine prose than human prose, next to the range of
the author's own documents. Machine-written text is usually 0.6+. It looks at
structure, not vocabulary, so sprinkling in the author's favourite words won't
move it; rewriting sentences the way the author builds them will.

## 3. Revise in small batches

1. Fix only `FIX` rows. Start with the largest |z|.
2. Change a handful of sentences per feature, re-run `check`, repeat. Rewrites
   overcorrect easily: splitting sentences to cut `, and` joins will push short
   sentences and fragments off the other way.
3. Stop near the calibration median for the draft's format (blog, tweets). Don't
   chase zero: the author's own posts never score zero, and `check` warns when a
   draft is smoother than anything they wrote. Past that point you are sanding
   off their edges. Watch the Diversity block: distance from their average and
   sentence-length spread should sit inside their own band, not below it.
4. Use the author's examples the tool prints (`- you (blog): ...`) as the
   pattern, not generic advice.
5. Leave tables, code, quotes, headings and `[placeholders]` alone; they are
   excluded from measurement anyway.
6. If the user edits in an editor that takes suggestions, propose the
   changes as suggestions, not direct edits.
7. Never add fragments or very short sentences to hit a `short_sentence` or
   `fragment` target ("Every time." "Not once." "Ouch."). Punchline fragments
   are one of the most recognisable AI patterns. If those rows say "too few",
   first check the corpus: short-form writing (tweets) and agent-written posts
   both inflate them. Let a long-form draft follow the author's long-form
   corpus.
8. Never paste the author's signature words or favourite word pairs into
   sentences you wrote. It fools the pair counts, not
   readers, and machine-likeness won't move.
9. Cutting for length is where an assistant's voice creeps back in: it
   compresses into dense, varied, clipped sentences. If the author's prose is
   loose (repeats words, explains why with "to ..." clauses, starts with "So"
   and "And"), keep that looseness and cut whole sentences or ideas instead.
10. Matching the rates is not the same as reading human. A draft can be tuned
   to zero flags and still read as generated to a person or a detector. The
   author's own concrete sentences are what carry their voice, so keep their
   words rather than rewriting them.

## 3b. Word pairs and verbosity

`check` also prints two blocks after the feature table:

1. **Word pairs.**
   - *AI pairs this draft over-uses*: pairs like *is a*, *the thing*, *the
     obvious*, *is a*, *the person who*. Rephrase those sentences the way the
     author would say them; don't swap in a synonym of the same shape.
   - *Your pairs that would usually show up*: the author's own markers. Never paste them in. They
     come back when the sentences are the author's, so treat a missing pair as
     a sign the passage needs their words, not a word.
   - The two per-10k-word rates (your pairs, AI pairs) should sit near the
     author's, not near the machines'.
2. **Verbosity.** Six measures against the author's own range. Flags go both
   ways: *more verbose* (filler, restatement, nominalisations) or *tighter*
   (too dense, too little repetition). Models usually err tight: clipped,
   dense, no filler. When a draft is tighter than everything the author
   wrote, let sentences breathe the way the author does instead of cutting
   further.

## 4. Things that read as AI, whatever the model says

Readers spot these quickly. Avoid them even if the numbers are fine:

1. Clipped verbless fragments as section openers: "Pieces, state, invariants."
2. Stacked imperatives to the reader: "Skim it now, come back to it later."
3. "Not X, but Y" / "X isn't A. It's B." reframes.
4. Lists of exactly three, over and over.
5. Colon labels as sentence openers ("Cost: ...", "The fix: ...").

The bundled `pg-vs-llm` reference (Paul Graham vs Claude, Codex, Grok given one
detailed style brief) found the models under-use purpose clauses ("to see
why"), "wanted to / had to", "if", "there is", concessives, and over-use
imperatives and gerund complements. Features the brief itself gave rules for
(dashes, I/you, sentence length, "and" joins, hedges, questions, contractions,
antithesis) are excluded from the `ai` mark and from machine-likeness.

## 5. Report

End with a before/after table: features off, machine-likeness, sentences,
mean words per sentence, calibration band, and which `FIX` rows you changed. One line on
anything you deliberately left (`format` rows, placeholders).
