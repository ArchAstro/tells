# tells

[![test](https://github.com/ArchAstro/tells/actions/workflows/test.yml/badge.svg)](https://github.com/ArchAstro/tells/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Does this draft sound like the person who's supposed to have written it?**

Every writer has tells—the small habits that give them away—and it turns out
every model has them too. We built `tells` to learn yours and to show you which
ones a draft is missing and which machine tells it picked up instead.

![tells: three robots at a poker table, each giving away a tell](docs/img/tells.jpg)

You give it the posts, essays, tweets or emails someone actually wrote, and it
builds a statistical model of how they write. Then you can start checking any draft you write against
that model, sentence by sentence, to see which habits pull it away from their
voice.

It looks at 56 features in every sentence. 40 of them are grammar structures
that a WordNet-backed classifier picks out, like *the thing ∅ you built*, *to
see why*, *if X* and *what he wants is…*. The other 16 are surface habits like
fragments, dashes, *I* vs *you*, hedges, *And/But* openers and lists of three.

## What we found with it

Can a really good prompt get a model to write like a specific person? We
wanted to find out. So we gave Claude Opus 5, Codex Terra and Grok 4.6 the same
long, careful brief on how Paul Graham writes
([`style-brief.md`](analysis/pg-vs-llm/style-brief.md)), had each of them write
25 essays on his topics, and measured all 75 against 50 of his. The brief gave
explicit rules for 11 of the features — dashes, *I* vs *you*, sentence length,
*and* joins, hedging, questions, contractions and antithesis. We call those
*steered*, and we left them out of every claim below that says "unsteered".

![Every essay placed on a map by its unsteered features: Paul Graham's 50 essays on the left, all 75 model essays together on the right, with open ground between](docs/img/map.svg)

1. **No model got close.** On the 44 unsteered features, a cross-validated
   nearest-centroid score separates each model from PG with an AUC of 1.00.
   When we ran the same test on PG against himself, splitting his essays in
   half at random, it scored 0.47. That's basically a coin flip.
2. **They miss him the same way.** What do they get wrong? All three models under-use what he does
   most, and the brief never mentioned any of it: purpose clauses (*…to see
   why*), *wanted to / had to*, *if*, *there is*, and sentences that start with
   *And* or *But*. And all three over-use commands to the reader and gerund
   objects like *started building*.

   | per 100 sentences | PG | Models |
   |---|---:|---:|
   | purpose clause (*to see why*) | 17.2 | 5–7 |
   | *wanted to / had to* | 15.2 | 6–8 |
   | conditional *if* | 9.4 | 4–7 |
   | *there is / there are* | 3.4 | ~1 |
   | imperative | 0.8 | 1.8–3.5 |
   | gerund object (*started building*) | 1.2 | 2.7–3.2 |

   He also asks far more questions (3.9 vs 0.4–1.7 per 100 sentences) and
   hedges more, but the brief gave rules for both, so we don't count them. The
   way I read it, PG explains why and wonders out loud, and the models tell
   you what to do.

   ![Each model's difference from Paul Graham on 20 features, in units of his own essay-to-essay spread; most dots fall outside his normal range, and the three models usually miss in the same direction](docs/img/fingerprint.svg)
3. **Each model has its own accent.** We left each essay out in turn and used
   a nearest-average classifier on the unsteered features to guess which model
   wrote it, and it got 72 of 75 right where chance would get 25. Claude joins
   clauses with *and* far more than anyone. Codex loves lists of three. Codex
   and Grok barely contract at all, about 4 of PG's standard deviations below
   him, while Claude contracts about as often as he does.

   ![For each model, the three features where it is furthest from the other two](docs/img/accents.svg)
4. **Their essays are not much more alike than his, and we got this wrong at
   first.** When we measured it raw, each model's essays sat 19–32% closer to
   their own average than PG's did. But his essays are shorter, and rates from
   fewer sentences are noisier. So we cut every essay down to the same 80
   sentences to compare like with like, and the gap mostly went away: Claude
   came out at 0.85, Grok 0.83 and PG 0.83, with only Codex tighter at 0.76
   (9% closer). Codex and Grok do keep their sentence lengths flatter, with a
   median SD of 5.4–5.8 words against PG's 8.5.

   ![Each essay's distance from its own author's average, every essay cut to 80 sentences: Paul Graham, Claude and Grok are about the same, Codex a little tighter; and sentence-length spread, where Codex and Grok are much flatter than Paul Graham](docs/img/uniformity.svg)
5. **The models aren't wordy. They're compressed.** The usual complaint about
   AI prose is padding—I think most people expect that— but most model essays have no filler phrases at
   all, while PG uses about one per 1,000 words. They repeat the previous
   sentence less, and Codex packs far more content words into each sentence.
   The brief did discourage hedging, so the filler gap is partly steered, but
   the rest of it wasn't asked for. I think clipped, dense prose is its own
   tell. So we made `check` flag drafts that are too tight for the author as
   well as ones that are too wordy.

   ![Filler phrases, sentence-to-sentence repetition and content density per essay: Paul Graham has more filler and more repetition than every model, and Codex is far denser](docs/img/verbosity.svg)
6. **PG speculates and the models define.** They wrote on the same topics, but
   they used different word pairs. He hedges and looks ahead with *would be*,
   *it will*, *at least*, *a lot* and *not just*. Every model leans on *is a*,
   *the thing*, *the person who* and *the obvious*. I'd treat these as
   suggestive, though. We ranked them from thousands of candidate pairs without
   correcting for multiple comparisons, and a few of them, like *the person*
   and *the work*, echo the brief's topic list. You can run `tells pairs` to
   find the same thing for any writer.

   ![Word pairs per 10,000 words. Paul Graham uses to be, a lot, there are, would be, at least and it will far more than every model; every model uses the person, the same, the obvious, is a, the work and the thing far more than he does](docs/img/pairs.svg)
7. **One number sorts them.** We took the 15 unsteered features where all three
   models lean the same way and asked, for each essay, whether it sits nearer
   the models' rate or PG's on each one. The share where it's nearer the models
   is what we call its *machine-likeness*. To keep it honest we scored every
   essay against a reference rebuilt without that essay, and PG's essays came
   out at 0.00–0.50 while every model essay came out at 0.60–1.00. It measures
   how sentences are built, so you can't game it by borrowing someone's
   favourite words. `build` uses it to screen a corpus and `check` reports it
   for a draft. But it was built from one human writer, so for anyone else I'd
   treat it as a strong hint and not a detector.

   ![Machine-likeness per essay, scored held out: Paul Graham's essays between 0.00 and 0.50, every model essay between 0.60 and 1.0](docs/img/machine.svg)
8. **The brief backfired where it was explicit.** When we told them "almost no
   em dashes", the models used none at all, even though PG uses them. When we
   told them "you more than I", they said *I* at about a quarter of his rate or
   less. And when we told them "~15 words", they wrote shorter. They follow
   instructions to the letter, even when the writer they're trying to imitate
   doesn't.

   ![What the brief asked for against what each model did: no em dashes at all, almost no I, and shorter sentences than the 15-word target](docs/img/told.svg)

There is an interactive version with tooltips and tables at
[archastro.github.io/tells](https://archastro.github.io/tells/). If you want to
see the audit notes, the bugs we fixed in the original experiment, or how to
reproduce all of this, it's in [`analysis/pg-vs-llm/`](analysis/pg-vs-llm/README.md).

## What it looks like

Here's a model built from the 50 PG essays checking the first essay Claude
wrote from the brief, trimmed down:

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

The brief asked for *you* more than *I*, and Claude really delivered. 42% of
its sentences talk to the reader against PG's 26%, and only 6% mention itself.
The punchy two-word sentences like "That's acquaintance." are a habit he barely
has. The `ai` marks here come from a reference built on these same essays,
though, so I'd treat this one as a demo and not a test.

## How it works

```
  someone's writing ─► sentences ─► 56 features ─► model.json
  (blog, tweets…)      (prose only)  per sentence   rates per corpus, per-doc ranges,
                                                    examples of each feature
  draft ─────────────► sentences ─► features ─► compare ─► FIX / format / ok
                                                   ▲          + diversity check
                         pg-vs-llm reference ──────┘  marks the "ai" direction
```

1. **It only reads prose.** It drops code, headings, images, short table cells,
   HTML comments, front matter, endnotes and `[placeholders]`, and it reads
   CriticMarkup as if every suggestion were accepted.
2. **It weights several corpora equally.** A blog and a tweet archive are
   different formats, so each gets the same say. It packs short documents like
   tweets into 120-sentence chunks to make a chunk compare like a post.
3. **It gives each feature a verdict.** A feature is *off* when |z| ≥ 2 against
   the author's pooled rate, or when the draft falls outside the range of every
   document they wrote.
   - `FIX` means every corpus agrees on the direction. That's their voice.
   - `format` means the corpora disagree. That's the medium, and you should
     leave it.
   - `ai` means it's off in the direction machine prose leans.
4. **It calibrates against the author.** We score each of the author's own
   documents against the rest, and real documents turn out to be "off" on
   several features too. So the goal is to get near their median and stop. If
   a draft is already in the model, it gets scored against the rest and never
   against itself.
5. **It checks diversity.** Why does that matter? If you tune a draft until
   nothing is off, you sand
   it down to the author's average, and that reads as generated. So `check`
   compares the draft's distance from the average, and the spread of its
   sentence lengths, with the author's own documents, and it warns you when a
   draft is too smooth.
6. **It finds word pairs.** `build` finds the author's signature pairs, the
   ones they use far more than the reference models (for Paul Graham that's
   *would be*, *at least* and *a lot*), and the AI pairs they avoid, like *is
   a*, *the thing* and *the obvious*. `check` lists the AI pairs a draft
   over-uses and the signature pairs a draft this long would usually contain.
   Don't paste the missing ones in, though. They come back on their own when
   the sentences are the author's.
7. **It measures verbosity.** It looks at six things per document: content
   density, filler phrases, nominalisations, sentence-to-sentence restatement,
   vocabulary variety and compressibility. `check` flags a draft that is
   wordier *or* tighter than anything the author wrote.
8. **It scores machine-likeness.** For each of the reference's AI tells, it
   asks whether the text is nearer the machines' rate or the human's, and the
   share where it's nearer the machines is its machine-likeness. Steered
   features never count. Held out, Paul Graham's essays score 0.00–0.50 and
   every model essay scores 0.60–1.00. `build` uses it to flag documents in the
   author's own corpus that an assistant probably wrote, because a model
   trained on even a few of those will steer every draft toward the
   assistant's voice. `check` reports it for the draft too. It measures
   sentence structure, so sprinkling in the author's favourite words doesn't
   move it.

## Use it

It's an agent skill, and you can install it with
[skills](https://github.com/vercel-labs/skills):

```sh
npx skills add ArchAstro/tells
```

Then ask your agent to "check this draft against how I write", or run
`/tells`. There is no Python package to install. The skill carries its own
code, and the first time it runs it sets up a private Python environment in
`~/.cache/tells` (it needs `python3` 3.9+) and fetches WordNet and the tagger
there.

The skill tells the agent to:

1. build the model from the author's own writing only;
2. fix `FIX` rows in small batches and re-check after each (rewrites overcorrect);
3. stop near the author's median and keep diversity inside their range, not chase zero;
4. leave tables, code and placeholders alone;
5. avoid the patterns that read as AI whatever the numbers say;
6. report a before/after table.

### From a shell

The skill's script is the same CLI, so you can run it directly. You'll need to
adjust the path to wherever your agent keeps skills:

```sh
ws=~/.claude/skills/tells/scripts/tells
$ws build -c 'blog=~/blog/*.md' -c tweets=~/archive/tweets -x '~/blog/draft*.md' -o me.json
$ws calibrate me.json
$ws check draft.md -m me.json            # or --json, --all
```

You add a corpus with `-c name=glob[,glob][@weight]`. Only use writing the
author did themselves, because drafts an assistant helped with pull the model
toward the assistant. It recognises tweets by their front matter
(`conversation_id:` or an x.com `url:`), and it strips quoted tweets, links,
@handles and `1/` numbering.

### Working on it

The code lives in `skills/tells/lib/tells`. You can run the tests with
`uv run pytest`, and `uv run tells ...` runs the CLI from the checkout.

## Lessons from using it on a real draft

I used the tool to revise a long blog post toward its author's voice, and I
checked the results with an outside AI detector to see if it actually worked.
This was one author and one post, from data we can't publish, so I'd read it as
experience and not evidence.

1. **Agent-written posts in the corpus poison the model.** Three of the
   author's eight "own" posts turned out to have been drafted by an assistant.
   The model learned the assistant's clipped style and told us to add short
   sentences and fragments, so every revision drifted further from the author.
   What fixed it was building from the posts the author really published and
   screening them with machine-likeness. `build` now warns you about documents
   like that.
2. **Zero flags doesn't mean human.** I kept tuning one draft until nothing was off,
   and it still scored 91% AI on the detector. You can match the rates sentence
   by sentence while the structure stays machine-made.
3. **Borrowed words fool the counts, not the reader.** When I sprinkled the
   author's signature words into sentences the assistant wrote, the word-pair score went
   up to the author's level, but machine-likeness and the detector didn't move
   at all.
4. **Cutting for length brings the assistant back.** When an assistant cuts, it
   compresses. You get denser words, more varied vocabulary, fewer "to …"
   clauses and fewer "So" and "And" openers. If the author writes loosely, I
   think you have to keep the looseness and cut whole ideas instead.
5. **What moved the needle was structure.** Putting back the author's purpose
   clauses and first person, and dropping the punchline fragments, brought
   machine-likeness down into the range of the author's own posts, and a
   detector sample of the opening came back human.

## Find someone's word pairs

```sh
$ws pairs -a 'me=~/blog/*.md' -b 'claude=drafts/claude' -b 'gpt=drafts/gpt'
```

This lists the word pairs the `-a` writing uses far more than every `-b`
corpus, and the reverse. It ranks them by weighted log-odds (Monroe et al.
2008) to stop a pair seen twice from topping the list. It compares each `-b`
separately and only shows pairs that hold against all of them. We did that to
keep most of the topic out, and it drops obvious subject nouns like *founder* and
*product* unless you pass `--keep-topic`. I find a writer's own pairs are a
quick check on a draft. If it has none of them, it probably isn't in their
voice.

## Build your own AI reference

`check` ships with the PG-vs-models reference, and it marks a row `ai` when a
draft is off in the direction all three models lean. It leaves out the features
the brief itself steered, like dashes, I/you, sentence length and *and* joins.
If you want to build one from your own human and machine corpora, you can run:

```sh
$ws reference --human 'me=~/essays' --machine 'claude=gen/claude' --machine 'gpt=gen/gpt' -o ref.json
$ws check draft.md -m me.json -r ref.json
```

## Limits

1. It measures rates, not meaning. A draft can hit every rate and still be bad,
   and matching the rates doesn't make it read as human to a detector.
2. The grammar classifier is heuristic, built on a tagger plus WordNet. We test
   it on gold sentences in `tests/test_grammar.py`, but we haven't tested it on
   a treebank.
3. Small corpora give wide ranges, and I think eight documents is about the
   minimum.
4. The PG reference is one author and one brief. It shows how these models
   missed that writer, but it doesn't tell you how to detect AI text in
   general.
5. We validated machine-likeness held out on the essays the reference was built
   from, which means one human writer, three models and one brief, and we tried
   it on one other author's posts. It won't score texts under 40 sentences,
   and the score gets noisy near 40. So treat 0.6 as a prompt to ask, not a
   verdict.
6. `check`'s z-scores treat sentences as independent, but sentences in one
   document aren't, so z runs high. That's why calibrating against the author's
   own documents matters more to us than any one |z|.
7. Distance and diversity depend on length, because a short draft looks more
   unusual than a long one. It's best to compare drafts of a similar length
   to the author's documents.
8. A model you build stores example sentences from the corpus to let `check`
   show them to you. So don't commit models built from writing you can't
   share. `*.model.json` is gitignored for that reason.

## Develop

We'd really like issues and pull requests, including ones that challenge a
claim in the analysis. Please run the tests before you send a change:

```sh
uv sync && uv run --group dev pytest -q
```

## License

We released it under MIT, see [LICENSE](LICENSE). The Paul Graham essays and the
generated essays aren't included. `analysis/pg-vs-llm/fetch_pg_essays.py`
fetches his essays from paulgraham.com for your own analysis, and we only commit
aggregate measurements.
