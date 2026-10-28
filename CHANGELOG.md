# Changelog

## 0.1.0 (2026-10-28)

First public release.

- `tells` CLI and agent skill: `build`, `calibrate`, `check`, `pairs`,
  `reference`, `features`. Installs with `npx skills add ArchAstro/tells`; the
  skill bootstraps its own Python environment on first run.
- 56 per-sentence features: 40 WordNet-backed grammar structures and 16
  surface habits. Word pairs, verbosity and machine-likeness.
- Bundled `pg-vs-llm` reference: 50 Paul Graham essays vs 25 each from Claude
  Opus 5, Codex Terra and Grok 4.6 given one style brief.
- Pre-release audit: deterministic classifier (no hash-seed dependence), 11
  steered features excluded from every AI tell, machine-likeness reported held
  out, uniformity length-matched, separation cross-validated in this repo.
