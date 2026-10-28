# Paul Graham vs three models: does a detailed style brief close the gap?

An audit of the experiment in `projects/writing-patterns` (Oct 2026), and the
source of the `pg-vs-llm` reference that `tells check` uses.

## The setup

1. **Human**: 50 Paul Graham essays (about 650–3,500 words, newest first), fetched by
   `fetch_pg_essays.py <corpus-root>`. The texts are not in this repo; fetch them yourself.
2. **Machines**: 25 essays each from Claude Opus 5, Codex Terra and Grok 4.6,
   all from one long style brief (`style-brief.md`) on PG's topics.
3. **Measures**: surface stylometry per essay, 40 grammar structures per
   sentence (the classifier in `skills/tells/lib/tells/grammar`), pairwise AUC with
   cross-validation, and three nulls.

## What the audit found

1. **The headline holds.** Every model is still told apart from PG almost
   perfectly, even after fixing the bugs below and dropping the features the
   brief steered. (These AUCs are the original repo's: 16 surface features,
   7 steered. This repo's own check is in the second audit below.)

   | | AUC, all features | AUC, unsteered only |
   |---|---:|---:|
   | Claude Opus 5 | 1.000 | 0.996 |
   | Codex Terra | 1.000 | 0.992 |
   | Grok 4.6 | 1.000 | 1.000 |
   | null: PG newer half vs older half | 0.632 | 0.568 |
   | null: shuffled labels | 0.515 | |

2. **Bug: curly apostrophes.** Codex writes `’`, so its contraction rate read
   as 0. Fixed, it is 0.0033 per word against PG's 0.0353: still a 10x gap.
3. **Bug: PG's endnotes were counted as prose.** 39 of 50 essays end in a
   **Notes** section, plus "Thanks to" paragraphs and about 340 `[n]` markers.
   Stripping them moved only word entropy much.
4. **Confound: the brief steered the features it was scored on.** It asked for
   almost no em dashes, "you" more than "I", ~15-word sentences and split
   "and" clauses. The models overshot: em dashes 0, "I" 0.04–0.24 per 100
   words vs PG's 0.91, sentences 10.8–13.6 words vs PG's 15.7. Those features
   measure obedience, so the reference marks them `steered` and `check` never
   calls them AI tells.
5. **Scope.** One author, one brief, 25 essays a model, a shared topic list.
   This says how these models miss *this* writer, not how to spot AI text in
   general.
6. **Minor.** The scaler was fit before cross-validation (tiny leak); the
   "green list" layer uses GPT-2 token keys, so it measures vocabulary, not a
   watermark; grammar results were never saved; outputs were deleted from the
   working tree.
7. **Hash order.** The original grammar code (and this repo's, until we found
   it) gathered a word's WordNet forms in a Python set. A set of strings
   iterates in a different order in every process, and that order decided
   which sense came first, so a few sentences changed features from run to
   run: rates moved by up to ~0.8 per 100 sentences. Fixed here by keeping
   the forms in order; two full runs are now byte-identical.
   The original repo's grammar audit output kept that noise, so it isn't
   shipped here; `results/essays.json` is from the fixed code.

## Where the models miss, in grammar

Per 100 sentences, from this repo's classifier (`results/essays.json`). PG does
more of the first group in every comparison; every model does more of the second.

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

The pattern: PG explains why and wonders aloud. The models
instruct.

## A second audit, of this repo's own claims (before publishing)

An independent pass over the numbers in this repo found four things. All are
fixed in `compute.py`, the reference and the READMEs.

1. **Uniformity was mostly essay length.** PG's essays are shorter (median
   80 sentences vs 96–140), so his per-essay rates are noisier and look more
   varied. Raw, the models sat 19–32% closer to their own average. With every
   essay cut to 80 sentences (30 random subsamples, PG's spread from the same
   subsamples): PG 0.83, Claude 0.85, Grok 0.83, Codex 0.76. Only Codex is
   tighter. `results/essays.json` keeps both (`uniformity`, `uniformity_raw`).
2. **The steered set was too small.** The brief also gave rules for hedging,
   questions, contractions and antithesis. The reference now marks 11 features
   steered (was 6), and none of them counts as an AI tell or toward
   machine-likeness.
3. **Machine-likeness was reported in-sample and counted steered features.**
   It now skips steered features (15 tells remain), and `compute.py` scores
   every essay against a reference rebuilt without it: PG 0.00–0.50, models
   0.60–1.00 (in-sample: PG 0.00–0.47, models 0.60–1.00).
4. **The headline AUC came from the original repo's 16 surface features.**
   `compute.py` now computes its own: 5-fold cross-validated nearest-centroid
   on the 44 unsteered features, 20 repeats. AUC 1.00 for every model; PG
   against himself, split at random, 0.47 (0.22–0.65 over 10 splits).

Also: model identification is 72 of 75 with the wider steered set (was 74);
word pairs are ranked from thousands of candidates without correction and some
echo the brief's topic list, so treat them as suggestive.

## Charts

`../../docs/pg-vs-llm.html` (data from `compute.py`, drawn by `charts.py`):

1. The map: every essay placed by its unsteered features. PG on one side, the models (overlapping each other) on the other.
2. Uniformity: length-matched spread (PG, Claude and Grok about equal; Codex tighter), and sentence-length spread.
3. Fingerprint: each model's difference from PG per feature, in units of PG's own spread.
4. Accents: what tells the three models apart from each other (72 of 75 essays named correctly).
5. Word pairs: PG speculates (*would be*, *at least*); the models define (*is a*, *the thing*).
6. Machine-likeness, held out.
7. Told vs did: what the brief asked for, what each model produced, what PG does.

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
