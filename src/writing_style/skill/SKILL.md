---
name: writing-style
description: Check a draft against a statistical model of how its author actually writes (grammar structures, sentence length, person, hedges, fragments, dashes) and revise it toward their voice. Use when the user asks to make a draft "sound like me", match their style, check whether a post reads like them or like AI, build a model of their writing from their blog posts, tweets or emails, or runs /writing-style.
---

# Matching a draft to its author's voice

`writing-style` measures 56 features per sentence (40 grammar structures from a
WordNet-backed classifier, 16 surface habits) across the author's own writing,
then tells you which features a draft over- or under-uses.

## 0. Install

```sh
command -v writing-style || uv tool install git+https://github.com/ArchAstro/writing-style
writing-style setup        # downloads WordNet + tagger once, into ~/.cache/writing-style
```

## 1. Build the model from the author's own writing only

```sh
writing-style build -c 'blog=~/blog/posts/*.md' -c tweets=~/archive/tweets -o ~/.cache/writing-style/me.json
writing-style calibrate ~/.cache/writing-style/me.json
```

1. Only text the author wrote themselves. No drafts you helped write, no
   co-authored docs, no decks, no research notes: they pull the model toward you.
2. One `-c` per kind of writing (blog, tweets, email). Corpora are weighted
   equally, so 600 tweets don't drown 8 posts. Many short docs are packed into
   120-sentence chunks automatically.
3. Leave out the draft you're checking (`-x draft.md`) if it sits in the glob.
4. `calibrate` scores each of their own documents against the rest. Tell the user
   that band: their own work is "off" on several features too.

## 2. Check

```sh
writing-style check draft.md -m ~/.cache/writing-style/me.json
writing-style check draft.md -m me.json --json     # for a programmatic loop
```

Verdicts per feature:

| Verdict | Meaning | Do |
|---|---|---|
| `FIX` | off, and every corpus agrees on the direction | revise toward the author |
| `format` | off, but corpora disagree (blog vs tweets) | leave it: it's the medium |
| `ai` (suffix) | off in the direction machine prose leans | prioritise it |
| blank | within range | nothing |

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
7. Matching the rates is not the same as reading human. A draft can be tuned
   to zero flags and still read as generated to a person or a detector. The
   author's own concrete sentences are what carry their voice, so keep their
   words rather than rewriting them.

## 3b. Word pairs and verbosity

`check` also prints two blocks after the feature table:

1. **Word pairs.**
   - *AI pairs this draft over-uses*: pairs like *is why*, *the thing*, *the
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
why"), "wanted to / had to", questions, "if", "there is", concessives, and
over-use imperatives and gerund complements. Features the brief itself steered
(dashes, I/you, sentence length) are excluded from the `ai` mark.

## 5. Report

End with a before/after table: features off, sentences, mean words per
sentence, calibration band, and which `FIX` rows you changed. One line on
anything you deliberately left (`format` rows, placeholders).
