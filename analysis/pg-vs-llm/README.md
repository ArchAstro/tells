# Paul Graham vs three models: does a detailed style brief close the gap?

An audit of the experiment in `projects/writing-patterns` (Oct 2026), and the
source of the `pg-vs-llm` reference that `writing-style check` uses.

## The setup

1. **Human**: 50 Paul Graham essays (700–3,500 words, newest first), fetched by
   `fetch_pg_essays.py`. The texts are not in this repo; fetch them yourself.
2. **Machines**: 25 essays each from Claude Opus 5, Codex Terra and Grok 4.6,
   all from one long style brief (`style-brief.md`) on PG's topics.
3. **Measures**: surface stylometry per essay, 40 grammar structures per
   sentence (the classifier in `src/writing_style/grammar`), pairwise AUC with
   cross-validation, and three nulls.

## What the audit found

1. **The headline holds.** Every model is still told apart from PG almost
   perfectly, even after fixing the bugs below and dropping every feature the
   brief steered.

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
   **Notes** section, plus "Thanks to" paragraphs and 339 `[n]` markers.
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

## Where the models miss, in grammar

Per 100 sentences. PG does more of the first group in every comparison; every
model does more of the second.

| Structure | PG | Models |
|---|---:|---:|
| purpose infinitive (*to see why*) | 17.4 | 5–7 |
| infinitival complement (*wanted to*) | 15.4 | 6–8 |
| zero relative (*the thing ∅ you built*) | 26.9 | 12–21 |
| conditional *if* | 9.4 | 4–7 |
| *there is / there are* | 3.4 | ~1 |
| questions (yes/no + wh-) | 3.8 | 0.4–1.7 |
| concessive (*although*) | 0.8 | 0–0.1 |
| imperative | 0.7 | 1.8–3.5 |
| gerund complement (*started building*) | 1.2 | 2.7–3.2 |
| ditransitive (*gave them X*) | 1.1 | 1.8–2.2 |

The pattern: PG explains why and wonders aloud. The models
instruct.

## Charts

`../../docs/pg-vs-llm.html` (data from `compute.py`, drawn by `charts.py`):

1. The map: every essay placed by its features. PG spreads out; each model is its own tight patch.
2. Uniformity: each model's essays sit 19–32% closer to their own average than PG's do.
3. Fingerprint: each model's difference from PG per feature, in units of PG's own spread.
4. Accents: what tells the three models apart from each other (74 of 75 essays named correctly).
5. Told vs did: what the brief asked for, what each model produced, what PG does.

## Reproduce

```sh
# in projects/writing-patterns, after fetching and generating the essays
PYTHONPATH=. uv run --no-project --with nltk --with numpy --with scipy --with scikit-learn \
  python path/to/audit_pg.py results/audit_pg.json
PYTHONPATH=.:path/to uv run --no-project --with nltk --with numpy --with scipy \
  python path/to/audit_grammar.py results/audit_grammar.json .

# from this repo, in analysis/pg-vs-llm/
uv run --with numpy python compute.py ~/projects/writing-patterns results/essays.json
python3 charts.py results ../../docs/pg-vs-llm.html

# the reference shipped with the CLI
writing-style reference --human 'Paul Graham=human/paul_graham' \
  --machine 'Claude Opus 5=llm/claude-opus-5/essays' \
  --machine 'Codex Terra=llm/codex-terra-high/essays' \
  --machine 'Grok 4.6=llm/grok-4.6-medium/essays' -o pg-vs-llm.json
```
