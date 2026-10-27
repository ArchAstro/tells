# writing-style

**Does this draft sound like the person who's supposed to have written it?**

Build a statistical model of how someone writes from their own posts, essays,
tweets or email. Then check any draft against it, sentence by sentence, and
see exactly which habits pull it away from their voice.

It measures 56 features in every sentence: 40 grammar structures from a
WordNet-backed classifier (*the thing ∅ you built*, *to see why*, *if X*,
*what he wants is…*) and 16 surface habits (fragments, dashes, *I* vs *you*,
hedges, *And/But* openers, lists of three).

## What we found with it

We gave Claude Opus 5, Codex Terra and Grok 4.6 the same long, careful brief
on how Paul Graham writes, had each write 25 essays on his topics, and
measured all of them against 50 of his.

![Every essay placed on a map by its features: Paul Graham's 50 essays spread across the left, Claude's in a tight cluster at the bottom, Codex's and Grok's in tight clusters on the right](docs/img/map.svg)

1. **No model got close.** Each one is still told apart from PG at AUC ≥ 0.99,
   even on features the brief never mentioned. Two halves of PG's own essays
   score 0.57.
2. **They miss him the same way.** All three under-use what he does most:
   purpose clauses (*…to see why*), *wanted to / had to*, hedges, *if*,
   questions, sentences that start with *And* or *But*. All three over-use
   commands to the reader and gerund objects (*started building*).

   | per 100 sentences | PG | Models |
   |---|---:|---:|
   | purpose clause (*to see why*) | 17.4 | 5–7 |
   | *wanted to / had to* | 15.4 | 6–8 |
   | conditional *if* | 9.4 | 4–7 |
   | questions | 3.8 | 0.4–1.7 |
   | imperative | 0.7 | 1.8–3.5 |
   | gerund object (*started building*) | 1.2 | 2.7–3.2 |

   PG explains why and wonders out loud. The models tell you what to do.

   ![Each model's difference from Paul Graham on 20 features, in units of his own essay-to-essay spread; most dots fall outside his normal range, and the three models usually miss in the same direction](docs/img/fingerprint.svg)
3. **Each model has its own accent.** A nearest-average classifier names the
   right model for 74 of 75 essays. Claude uses contractions as often as PG and
   joins clauses with *and* far more than anyone. Codex loves lists of three.
   Codex and Grok barely contract at all, about 4 of PG's standard deviations
   below him.

   ![For each model, the three features where it is furthest from the other two](docs/img/accents.svg)
4. **Their essays are more alike than his.** Each model's essays sit 19–32%
   closer to their own average than PG's do to his. Real writing wanders;
   generated writing clusters. `check` measures this for any draft.

   ![Each essay's distance from its own author's average: Paul Graham median 0.82, the models 0.56 to 0.66; and sentence-length spread, where Codex and Grok are much flatter than Paul Graham](docs/img/uniformity.svg)
5. **PG speculates; the models define.** Same topics, different word pairs.
   He hedges and looks ahead: *would be*, *it will*, *at least*, *a lot*,
   *not just*. Every model leans on *is a*, *the thing*, *the person who*,
   *is why*, *the obvious*. Run `writing-style pairs` to find the same thing
   for any writer.

   ![Word pairs per 10,000 words. Paul Graham uses to be, a lot, there are, would be, at least and it will far more than every model; every model uses the person, the same, the obvious, is a, the work and the thing far more than he does](docs/img/pairs.svg)
6. **The brief backfired where it was explicit.** Told "almost no em dashes",
   the models used none (PG uses them). Told "you more than I", they said *I*
   at a quarter of his rate or less. Told "~15 words", they wrote shorter.
   They follow instructions harder than the writer they're imitating.

   ![What the brief asked for against what each model did: no em dashes at all, almost no I, and shorter sentences than the 15-word target](docs/img/told.svg)

Interactive version with tooltips and tables: [`docs/pg-vs-llm.html`](docs/pg-vs-llm.html).

Audit notes, bugs we fixed in the original experiment and how to reproduce:
[`analysis/pg-vs-llm/`](analysis/pg-vs-llm/README.md).

## What it looks like

A model built from the 50 PG essays, checking the first essay Claude wrote
from the brief (trimmed):

```
001-why-the-first-ten-users-teach-a-different-lesson.md: 102 sentences, 14.3 words/sentence (you: 15.9)

  feature                     draft    you        pg      z  verdict
  ditransitive                 5.9%   1.1%      1.1%    4.6  FIX ai
  first_person                 5.9%  21.1%     21.1%   -3.8  FIX
  second_person               42.2%  25.9%     25.9%    3.8  FIX
  purpose_infinitive           3.9%  17.7%     17.7%   -3.6  FIX ai
  clausal_coordination        12.7%   5.5%      5.5%    3.2  FIX
  short_sentence              14.7%   7.6%      7.6%    2.7  FIX
  starts_with_conjunction      7.8%  16.9%     16.9%   -2.4  FIX ai

To fix (every corpus agrees):

  second_person: addresses the reader (you, your)
    Address the reader a little less.
    - draft: The first ten users tell you whether the thing should exist.
    - draft: The next thousand tell you how to run it.

  short_sentence: 5 words or fewer
    Merge some short sentences into their neighbours.
    - draft: That's not data.
    - draft: That's acquaintance.
  ...
11 of 56 features off.
Your own documents, each scored against the rest: pg 2-12 (median 5)

Diversity (real writing wanders; a draft sanded down to your average reads as generated):
  distance from your average           draft  1.11   yours: pg 0.5-3.2 (inside)
  sentence-length spread (sd, words)   draft  8.32   yours: pg 6.4-17.1 (inside)
```

The brief asked for *you* more than *I*, and Claude delivered: 42% of its
sentences talk to the reader, against PG's 26%, and only 6% mention itself.
The punchy two-word sentences ("That's acquaintance.") are a habit he barely
has. (The `ai` marks here come from a reference built on these same essays,
so treat this one as a demo, not a test.)

## How it works

```
  someone's writing ─► sentences ─► 56 features ─► model.json
  (blog, tweets…)      (prose only)  per sentence   rates per corpus, per-doc ranges,
                                                    examples of each feature
  draft ─────────────► sentences ─► features ─► compare ─► FIX / format / ok
                                                   ▲          + diversity check
                         pg-vs-llm reference ──────┘  marks the "ai" direction
```

1. **Prose only.** Code, headings, images, short table cells, HTML comments,
   front matter, endnotes and `[placeholders]` are dropped. CriticMarkup is
   read as accepted.
2. **Several corpora, weighted equally.** A blog and a tweet archive are
   different formats. Short documents (tweets) are packed into 120-sentence
   chunks so a chunk compares like a post.
3. **Verdicts.** A feature is *off* when |z| ≥ 2 against the author's pooled
   rate, or when the draft falls outside the range of every document they
   wrote.
   - `FIX`: every corpus agrees on the direction. That's their voice.
   - `format`: the corpora disagree. That's the medium, so leave it.
   - `ai`: off in the direction machine prose leans.
4. **Calibration.** Each of the author's own documents is scored against the
   rest. Real documents are "off" on several features too, so aim for their
   median and stop. A draft that's already in the model is scored against the
   rest, never against itself.
5. **Diversity.** Tuning a draft until nothing is off sands it down to the
   author's average, which reads as generated. `check` compares the draft's
   distance from the average, and the spread of its sentence lengths, with
   the author's own documents, and warns when a draft is too smooth.

## Use it

```sh
uv tool install git+https://github.com/ArchAstro/writing-style
writing-style setup          # WordNet + tagger, once, into ~/.cache/writing-style

writing-style build -c 'blog=~/blog/*.md' -c tweets=~/archive/tweets -x '~/blog/draft*.md' -o me.json
writing-style calibrate me.json
writing-style check draft.md -m me.json            # or --json, --all
```

`-c name=glob[,glob][@weight]` adds a corpus. Use only writing the author did
themselves: drafts an assistant helped with pull the model toward the
assistant. Tweets are recognised by their front matter (`conversation_id:` or
an x.com `url:`); quoted tweets, links, @handles and `1/` numbering are
stripped.

## Use it from an agent

```sh
writing-style install-skill          # copies the skill to ~/.claude/skills/writing-style
```

The skill (`src/writing_style/skill/SKILL.md`) tells the agent to:

1. build the model from the author's own writing only;
2. fix `FIX` rows in small batches and re-check after each (rewrites overcorrect);
3. stop near the author's median and keep diversity inside their range, not chase zero;
4. leave tables, code and placeholders alone;
5. avoid the patterns that read as AI whatever the numbers say;
6. report a before/after table.

## Find someone's word pairs

```sh
writing-style pairs -a 'me=~/blog/*.md' -b 'claude=drafts/claude' -b 'gpt=drafts/gpt'
```

Lists the word pairs the `-a` writing uses far more than every `-b` corpus,
and the reverse, ranked by weighted log-odds (Monroe et al. 2008) so a pair
seen twice can't top the list. Each `-b` is compared separately and only pairs
that hold against all of them are shown, which keeps most of the topic out;
obvious subject nouns (*founder*, *product*, …) are dropped unless you pass
`--keep-topic`. A writer's own pairs are a quick check on a draft: if it has
none of them, it probably isn't in their voice.

## Build your own AI reference

`check` ships the PG-vs-models reference and marks a row `ai` when a draft is
off in the direction all three models lean. Features the brief itself steered
(dashes, I/you, sentence length, *and* joins) are left out. To build one from
any human and machine corpora:

```sh
writing-style reference --human 'me=~/essays' --machine 'claude=gen/claude' --machine 'gpt=gen/gpt' -o ref.json
writing-style check draft.md -m me.json -r ref.json
```

## Limits

1. It measures rates, not meaning. A draft can hit every rate and still be bad,
   and matching the rates doesn't make it read as human to a detector.
2. The grammar classifier is heuristic (tagger plus WordNet). It is tested on
   gold sentences (`tests/test_grammar.py`), not on a treebank.
3. Small corpora give wide ranges. Eight documents is about the minimum.
4. The PG reference is one author and one brief. It shows how these models
   missed that writer, not how to detect AI text in general.

## Develop

```sh
uv sync && uv run --group dev pytest -q
```
