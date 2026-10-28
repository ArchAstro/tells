# tells

**Does this draft sound like the person who's supposed to have written it?**

Every writer has tells, the small habits that give them away, and so does
every model. `tells` learns yours and shows which ones a draft is missing,
and which machine tells it picked up instead.

![tells: three robots at a poker table, each giving away a tell](docs/img/tells.jpg)

Build a statistical model of how someone writes from their own posts, essays,
tweets or email. Then check any draft against it, sentence by sentence, and
see exactly which habits pull it away from their voice.

It measures 56 features in every sentence: 40 grammar structures from a
WordNet-backed classifier (*the thing ∅ you built*, *to see why*, *if X*,
*what he wants is…*) and 16 surface habits (fragments, dashes, *I* vs *you*,
hedges, *And/But* openers, lists of three).

## What we found with it

We gave Claude Opus 5, Codex Terra and Grok 4.6 the same long, careful brief
on how Paul Graham writes ([`style-brief.md`](analysis/pg-vs-llm/style-brief.md)),
had each write 25 essays on his topics, and measured all of them against 50 of
his. The brief gave explicit rules for 11 of the features (dashes, *I* vs
*you*, sentence length, *and* joins, hedging, questions, contractions,
antithesis), so those are marked *steered* and left out of every claim below
that says "unsteered".

![Every essay placed on a map by its unsteered features: Paul Graham's 50 essays on the left, all 75 model essays together on the right, with open ground between](docs/img/map.svg)

1. **No model got close.** On the 44 unsteered features, a cross-validated
   nearest-centroid score separates each model from PG with AUC 1.00. The
   same test on PG against himself (his essays split in half at random)
   scores 0.47.
2. **They miss him the same way.** All three under-use what he does most and
   the brief never mentioned: purpose clauses (*…to see why*), *wanted to /
   had to*, *if*, *there is*, sentences that start with *And* or *But*. All
   three over-use commands to the reader and gerund objects (*started
   building*).

   | per 100 sentences | PG | Models |
   |---|---:|---:|
   | purpose clause (*to see why*) | 17.2 | 5–7 |
   | *wanted to / had to* | 15.2 | 6–8 |
   | conditional *if* | 9.4 | 4–7 |
   | *there is / there are* | 3.4 | ~1 |
   | imperative | 0.8 | 1.8–3.5 |
   | gerund object (*started building*) | 1.2 | 2.7–3.2 |

   He also asks far more questions (3.9 vs 0.4–1.7) and hedges more, but the
   brief gave rules for both. PG explains why and wonders out loud. The models
   tell you what to do.

   ![Each model's difference from Paul Graham on 20 features, in units of his own essay-to-essay spread; most dots fall outside his normal range, and the three models usually miss in the same direction](docs/img/fingerprint.svg)
3. **Each model has its own accent.** A nearest-average classifier on the
   unsteered features, leaving each essay out, names the right model for 72 of
   75 essays (chance: 25). Claude joins clauses with *and* far more than anyone.
   Codex loves lists of three. Codex and Grok barely contract at all, about 4 of
   PG's standard deviations below him, while Claude contracts as often as he
   does.

   ![For each model, the three features where it is furthest from the other two](docs/img/accents.svg)
4. **Their essays are not much more alike than his. We got this wrong at
   first.** Measured raw, each model's essays sit 19–32% closer to their own
   average than PG's. But his essays are shorter, and rates from fewer
   sentences are noisier. Cut every essay to the same 80 sentences and the gap
   mostly goes: Claude 0.85, Grok 0.83, PG 0.83, and only Codex is tighter
   (0.76, 9% closer). Codex and Grok do keep sentence lengths flatter (median
   SD 5.4–5.8 words vs PG's 8.5).

   ![Each essay's distance from its own author's average, every essay cut to 80 sentences: Paul Graham, Claude and Grok are about the same, Codex a little tighter; and sentence-length spread, where Codex and Grok are much flatter than Paul Graham](docs/img/uniformity.svg)
5. **The models aren't wordy. They're compressed.** The usual complaint
   about AI prose is padding, but most model essays contain no filler
   phrases at all (PG: about one per 1,000 words). They repeat the previous
   sentence less, and Codex packs far more content words into each sentence.
   The brief discouraged hedging, so the filler gap is partly steered; the
   rest wasn't asked for. Clipped, dense prose is its own tell, so `check`
   flags drafts that are tighter than the author as well as wordier.

   ![Filler phrases, sentence-to-sentence repetition and content density per essay: Paul Graham has more filler and more repetition than every model, and Codex is far denser](docs/img/verbosity.svg)
6. **PG speculates; the models define.** Same topics, different word pairs.
   He hedges and looks ahead: *would be*, *it will*, *at least*, *a lot*,
   *not just*. Every model leans on *is a*, *the thing*, *the person who*,
   *the obvious*. Treat these as suggestive: they're ranked from thousands of
   candidate pairs without a multiple-comparison correction, and some
   (*the person*, *the work*) echo the brief's topic list. Run `tells pairs`
   to find the same thing for any writer.

   ![Word pairs per 10,000 words. Paul Graham uses to be, a lot, there are, would be, at least and it will far more than every model; every model uses the person, the same, the obvious, is a, the work and the thing far more than he does](docs/img/pairs.svg)
7. **One number sorts them.** Take the 15 unsteered features where all three
   models lean the same way, and ask whether an essay sits nearer the models'
   rate or PG's. The share nearer the models is its *machine-likeness*. Scored
   held out (the reference rebuilt without the essay being scored), PG's
   essays score 0.00–0.50 and every model essay 0.60–1.00. It measures how
   sentences are built, so it can't be gamed by borrowing someone's favourite
   words. `build` uses it to screen a corpus and `check` reports it for a
   draft. It is built from one human writer, so treat it as a strong hint for
   other writers, not a detector.

   ![Machine-likeness per essay, scored held out: Paul Graham's essays between 0.00 and 0.50, every model essay between 0.60 and 1.0](docs/img/machine.svg)
8. **The brief backfired where it was explicit.** Told "almost no em dashes",
   the models used none (PG uses them). Told "you more than I", they said *I*
   at about a quarter of his rate or less. Told "~15 words", they wrote
   shorter. They follow instructions harder than the writer they're imitating.

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
6. **Word pairs.** `build` finds the author's signature pairs (ones they use
   far more than the reference models: *would be*, *at least*, *a lot* for
   Paul Graham) and the AI pairs they avoid (*is a*, *the thing*, *the obvious*).
   `check` lists AI pairs the draft over-uses and signature pairs a draft
   this long would usually contain. Don't paste the missing ones in; they
   come back when the sentences are the author's.
7. **Verbosity.** Six measures per document: content density, filler
   phrases, nominalisations, sentence-to-sentence restatement, vocabulary
   variety and compressibility. `check` flags a draft that is wordier *or*
   tighter than every document the author wrote.
8. **Machine-likeness.** For each of the reference's AI tells, is the text
   nearer the machines' rate or the human's? The share of tells where it's
   nearer the machines is its machine-likeness. Steered features never count.
   Held out, Paul Graham's essays score 0.00–0.50 and every model essay
   0.60–1.00. `build` uses it to flag documents in the author's own corpus
   that an assistant probably wrote, because a model trained on a few of
   those will steer every draft toward the assistant's voice. `check` reports
   it for the draft. It measures sentence structure, so sprinkling in the
   author's favourite words doesn't move it.

## Use it

It's an agent skill. Install it with [skills](https://github.com/vercel-labs/skills):

```sh
npx skills add ArchAstro/tells
```

Then ask your agent to "check this draft against how I write" or run
`/tells`. There's no Python package to install: the skill carries its
own code, and its first run sets up a private Python environment in
`~/.cache/tells` (needs `python3` 3.9+) and fetches WordNet and the
tagger there.

The skill tells the agent to:

1. build the model from the author's own writing only;
2. fix `FIX` rows in small batches and re-check after each (rewrites overcorrect);
3. stop near the author's median and keep diversity inside their range, not chase zero;
4. leave tables, code and placeholders alone;
5. avoid the patterns that read as AI whatever the numbers say;
6. report a before/after table.

### From a shell

The same CLI is the skill's script (adjust the path to wherever your agent keeps skills):

```sh
ws=~/.claude/skills/tells/scripts/tells
$ws build -c 'blog=~/blog/*.md' -c tweets=~/archive/tweets -x '~/blog/draft*.md' -o me.json
$ws calibrate me.json
$ws check draft.md -m me.json            # or --json, --all
```

`-c name=glob[,glob][@weight]` adds a corpus. Use only writing the author did
themselves: drafts an assistant helped with pull the model toward the
assistant. Tweets are recognised by their front matter (`conversation_id:` or
an x.com `url:`); quoted tweets, links, @handles and `1/` numbering are
stripped.

### Working on it

The code lives in `skills/tells/lib/tells`. `uv run pytest`
runs the tests; `uv run tells ...` runs the CLI from the checkout.

## Lessons from using it on a real draft

We used the tool to revise a long blog post toward its author's voice, and
checked the results with an outside AI detector. This is one author and one
post, from data we can't publish, so read it as experience, not evidence:

1. **Agent-written posts in the corpus poison the model.** Three of the
   author's eight "own" posts had been drafted by an assistant. The model
   learned the assistant's clipped style and told us to add short sentences
   and fragments, so every revision drifted further from the author. Building
   from the posts the author actually published, and screening with
   machine-likeness, fixed it. `build` now warns about such documents.
2. **Zero flags doesn't mean human.** A draft tuned until nothing was off
   still scored 91% AI on the detector. Rates can be matched sentence by
   sentence while the structure stays machine-made.
3. **Borrowed words fool the counts, not the reader.** Sprinkling the
   author's signature words into assistant sentences raised the word-pair
   score to the author's level; machine-likeness and the detector didn't move.
4. **Cutting for length brings the assistant back.** An assistant's cut
   compresses: denser words, more varied vocabulary, fewer "to …" clauses,
   fewer "So" and "And" openers. If the author writes loosely, keep the
   looseness and cut whole ideas.
5. **What moved the needle was structure.** Putting back the author's
   purpose clauses and first person, and dropping punchline fragments,
   brought machine-likeness down into the range of the author's own posts,
   and a detector sample of the opening came back human.

## Find someone's word pairs

```sh
$ws pairs -a 'me=~/blog/*.md' -b 'claude=drafts/claude' -b 'gpt=drafts/gpt'
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
$ws reference --human 'me=~/essays' --machine 'claude=gen/claude' --machine 'gpt=gen/gpt' -o ref.json
$ws check draft.md -m me.json -r ref.json
```

## Limits

1. It measures rates, not meaning. A draft can hit every rate and still be bad,
   and matching the rates doesn't make it read as human to a detector.
2. The grammar classifier is heuristic (tagger plus WordNet). It is tested on
   gold sentences (`tests/test_grammar.py`), not on a treebank.
3. Small corpora give wide ranges. Eight documents is about the minimum.
4. The PG reference is one author and one brief. It shows how these models
   missed that writer, not how to detect AI text in general.
5. Machine-likeness was validated held out on the essays the reference was
   built from (one human writer, three models, one brief) and tried on one
   other author's posts. Texts under 40 sentences aren't scored, and near 40
   sentences the score is noisy. Treat 0.6 as a prompt to ask, not a verdict.
6. `check`'s z-scores treat sentences as independent. Sentences in one
   document aren't, so z runs high; that's why calibration against the
   author's own documents matters more than any one |z|.
7. Distance and diversity depend on length: a short draft looks more unusual
   than a long one. Compare drafts of similar length to the author's documents.
8. A model you build stores example sentences from the corpus so `check` can
   show them. Don't commit models built from writing you can't share
   (`*.model.json` is gitignored).

## Develop

```sh
uv sync && uv run --group dev pytest -q
```

## License

MIT, see [LICENSE](LICENSE). The Paul Graham essays and the generated essays
are not included; `analysis/pg-vs-llm/fetch_pg_essays.py` fetches his essays
from paulgraham.com for your own analysis, and only aggregate measurements are
committed.
