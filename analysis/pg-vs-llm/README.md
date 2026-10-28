# Paul Graham vs three models: does a detailed style brief close the gap?

We wanted to know if a long, careful style brief could get a model to write
like Paul Graham. So we audited the experiment in `projects/writing-patterns`
(Oct 2026) to check its claims, and we built the `pg-vs-llm` reference that
`tells check` uses from the same essays.

## The setup

1. **The human side.** We used 50 Paul Graham essays of about 650–3,500 words, newest
   first. We don't ship the texts in this repo, so to get them you'll need to
   run `fetch_pg_essays.py <corpus-root>`.
2. **The machine side.** We asked Claude Opus 5, Codex Terra and Grok 4.6 to write 25
   essays each on PG's topics, all from one long style brief (`style-brief.md`).
3. **What we measured.** We looked at surface stylometry per essay and 40 grammar
   structures per sentence, using the classifier in
   `skills/tells/lib/tells/grammar`. We then ran pairwise AUC with
   cross-validation and three nulls, because we wanted to know how far apart
   they really are.

## What the audit found

1. **The headline holds.** Even after we fixed the bugs below and dropped the
   features the brief steered, every model is still told apart from PG almost
   perfectly. These AUCs come from the original repo, and if you want to check them, you'll
   need its code. It used 16 surface
   features and 7 steered ones, so we needed to do our own check, and that's
   in the second audit below.

   | | AUC, all features | AUC, unsteered only |
   |---|---:|---:|
   | Claude Opus 5 | 1.000 | 0.996 |
   | Codex Terra | 1.000 | 0.992 |
   | Grok 4.6 | 1.000 | 1.000 |
   | null: PG newer half vs older half | 0.632 | 0.568 |
   | null: shuffled labels | 0.515 | |

2. **Curly apostrophes hid Codex's contractions.** Codex writes `’`, so its
   contraction rate read as 0. When we fixed it, Codex came out at 0.0033 per
   word against PG's 0.0353. That's still a 10x gap.
3. **PG's endnotes were counted as prose.** 39 of his 50 essays end in a
   **Notes** section. And there are "Thanks to" paragraphs and about 340 `[n]`
   markers too. We had to strip them out to measure his prose, and only word entropy
   moved much.
4. **The brief steered the features it was scored on.** It asked
   for almost no em dashes, "you" more than "I", ~15-word sentences and split
   "and" clauses. And the models overshot every one. But they went much further than asked. They used no em dashes
   at all, said "I" 0.04–0.24 times per 100 words against PG's 0.91, and
   wrote 10.8–13.6 words per sentence against his 15.7. If a model is told to do something, it does it, so I think those features
   measure obedience more than style, so the reference marks them `steered`
   and `check` never calls them AI tells.
5. **The scope is narrow.** This is one author, one brief and 25 essays a model, all on a
   shared topic list. It tells you how these models miss *this* writer. But it
   doesn't tell you how to spot AI text in general, and if you want that, you'd
   need many authors and many briefs.
6. **There were minor issues too.** If you look at the code, you'll see the
   scaler was fit before cross-validation. That's a tiny leak. And the "green list" layer uses GPT-2 token keys, so it measures
   vocabulary and not a watermark. Nobody bothered to save the grammar results. Someone had deleted the outputs from the
   working tree.
7. **Hash order made the grammar code random.** The original code gathered a word's WordNet forms in
   a Python set, and ours did too until we found it. When Python starts, it picks a new hash seed, so a set of strings iterates
   in a different order in every process, and that order decided which sense
   came first. If you ran it twice, a few sentences changed features, and rates
   moved by up to ~0.8 per 100 sentences. We fixed it by keeping the forms in
   the order WordNet gives them, and now two full runs come out byte-identical. The original repo's
   grammar audit output still has that noise, so we don't ship it, and
   `results/essays.json` comes from the fixed code.

## Where the models miss, in grammar

These are rates per 100 sentences from this repo's classifier
(`results/essays.json`). PG does more of the first group in every comparison,
and every model does more of the second.

| Structure | PG | Models |
|---|---:|---:|
| purpose infinitive (*to see why*) | 17.2 | 5–7 |
| infinitival complement (*wanted to*) | 15.2 | 6–8 |
| zero relative (*the thing ∅ you built*) | 26.1 | 12–21 |
| conditional *if* | 9.4 | 4–7 |
| *there is / there are* | 3.4 | ~1 |
| questions (yes/no + wh-) | 3.8 | 0.4–1.7 |
| concessive (*although*) | 0.8 | 0–0.1 |
| imperative | 0.8 | 1.8–3.5 |
| gerund complement (*started building*) | 1.2 | 2.7–3.2 |
| ditransitive (*gave them X*) | 1.1 | 1.8–2.2 |

The way I read it, PG explains why and wonders out loud, and the models tell
you what to do.

## A second audit, of this repo's own claims

Before we published, we wanted to make sure the numbers we'd put in this repo
held up, so we ran an independent pass over them. It found four problems, and we fixed all of them in
`compute.py`, the reference and the READMEs.

1. **Uniformity was mostly essay length.** I think we should have seen this one coming. PG's essays are shorter, with a
   median of 80 sentences against 96–140 for the models. So his per-essay
   rates are noisier, and that makes them look more varied. Measured raw,
   the models sat 19–32% closer to their own average. But when we cut every
   essay to 80 sentences, took 30 random subsamples and measured PG's spread
   the same way, we got PG 0.83, Claude 0.85, Grok 0.83 and Codex 0.76. So if there is a uniformity gap at all, only Codex has it. `results/essays.json` keeps both numbers, as
   `uniformity` and `uniformity_raw`.
2. **The steered set was too small.** We tried to list every feature the brief
   touched, and it turns out the brief also gave rules for hedging,
   questions, contractions and antithesis. So the reference now marks 11
   features as steered where it used to mark 6, and none of them counts as an
   AI tell or toward machine-likeness.
3. **Machine-likeness was reported in-sample and counted steered features.**
   So now it skips steered features, which leaves 15 tells, and `compute.py`
   scores every essay against a reference rebuilt without that essay. Held
   out, PG scores 0.00–0.50 and the models score 0.60–1.00. In-sample it was
   PG 0.00–0.47 and models 0.60–1.00.
4. **The headline AUC came from the original repo's 16 surface features.** So
   we had `compute.py` compute its own to test the claim directly. It runs a 5-fold cross-validated
   nearest-centroid on the 44 unsteered features, with 20 repeats, and gets an
   AUC of 1.00 for every model. And if we split PG against himself at random, it
   gets 0.47, with a range of 0.22–0.65 over 10 splits.

We also needed to fix two smaller things. When we widened the steered set, the model
identifier went from 74 of 75 right to 72. There is also a problem with the word pairs. We ranked them
from thousands of candidates without correcting for that, and some of them
echo the brief's topic list, so I'd treat them as suggestive.

## Charts

We use `charts.py` to draw these into `../../docs/pg-vs-llm.html`, using data from `compute.py`:

1. **The map** places every essay by its unsteered features, with PG on one
   side and the models on the other, overlapping each other.
2. **Uniformity** shows the length-matched spread, where PG, Claude and Grok
   come out about equal and Codex is tighter, and it uses sentence-length
   spread to show how flat the models' rhythm is.
3. **Fingerprint** shows each model's difference from PG on each feature, in
   units of PG's own spread.
4. **Accents** tries to show what tells the three models apart from each other, and the
   classifier names 72 of 75 essays correctly.
5. **Word pairs** shows PG speculating with *would be* and *at least* while the
   models define with *is a* and *the thing*.
6. **Machine-likeness** shows each essay's score when we hold it out.
7. **Told vs did** compares what the brief asked for, what each model did and
   what PG actually does.

## Reproduce

```sh
# in projects/writing-patterns, after fetching and generating the essays
PYTHONPATH=. uv run --no-project --with nltk --with numpy --with scipy --with scikit-learn \
  python path/to/audit_pg.py results/audit_pg.json
PYTHONPATH=.:path/to uv run --no-project --with nltk --with numpy --with scipy \
  python path/to/audit_grammar.py audit_grammar.json .   # original repo's grammar audit

# from this repo, in analysis/pg-vs-llm/
uv run --with numpy python compute.py ~/projects/writing-patterns results/essays.json
python3 charts.py results ../../docs/pg-vs-llm.html   # also writes docs/img/*.svg for the README

# the reference shipped with the CLI
tells reference --human 'Paul Graham=human/paul_graham' \
  --machine 'Claude Opus 5=llm/claude-opus-5/essays' \
  --machine 'Codex Terra=llm/codex-terra-high/essays' \
  --machine 'Grok 4.6=llm/grok-4.6-medium/essays' -o pg-vs-llm.json \
  --steered em_dash,first_person,second_person,long_sentence,short_sentence,clausal_coordination,hedge,polar_question,wh_question,contraction,not_x_but_y
```
