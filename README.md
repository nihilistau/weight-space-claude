# Weight-Space Claude

Asking **Claude Opus 5.5** (`claude-opus-5-5`, via Claude Code) the questions from [*Sparks of Weight-Space Programming*](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi, Teoh, Zhang, Khattab, MIT CSAIL, Nov 2026), where GPT-6 "Astra" read and wrote neural-network weights as plain text. The authors published [every prompt and answer](https://github.com/RikiyaT/lm_understand-logs); this repo reruns their prompts verbatim through a tool-free Claude Code harness and shows both side by side.

**Model under test: Claude Opus 5.5** (`claude-opus-5-5`, Claude Code 2.1.300, effort `high` for Exps 1-2 and `xhigh` for Exp 5, matching the paper's effort names). The model actually served is read from each run's event stream and recorded in its `manifest.json` / `run.json`.

**Website:** https://nihilistau.github.io/weight-space-claude/

| | Experiment | Claude Opus 5.5 vs GPT-6 Astra |
|---|---|---|
| 1 | Which game was this policy trained on? (weights as text, no tools) | Opus 5.5 4/4 · Astra 4/4 |
| 2 | What does this diffusion model generate? (no forward pass) | Opus 5.5 11/12 over 4 runs, drew filled shapes 7/11 · Astra 3/3 (n=1), outlines 3/3 |
| 5 | Write a MinAtar policy from scratch, one reply, no tools | Opus 5.5: Breakout 307 / Seaquest 24 / Asterix 33 (Astra 517 / 53 / 53; PPO-500M 25 / 89 / 55) |
| 3, 4, 6-8 | Not started (6-8 need ~300M tokens each) | |

## Quick start (Windows / any OS)

```
git clone --recurse-submodules https://github.com/nihilistau/weight-space-claude
cd weight-space-claude
uv sync
uv run wsp check       # environment pinned and clean?
uv run wsp validate    # our scorers reproduce the paper's published numbers?
uv run wsp smoke       # Claude really has no tools / extra context?
uv run wsp run exp1    # ask Claude, audit, score
uv run wsp site        # rebuild docs/data/results.json
```

Needs [uv](https://docs.astral.sh/uv/) and [Claude Code](https://claude.com/claude-code) logged in. Python 3.11 is fetched by uv.

## Where to read next

- [guide/GUIDE.md](guide/GUIDE.md): how experiments like this work, and where this repo does each part
- [NOTEBOOK.md](NOTEBOOK.md): the lab notebook: decisions, predictions, results, in order
- [CLAUDE.md](CLAUDE.md): rules for agents working in this repo
- [validation/report.json](validation/report.json): instrument checks against upstream

## Credits and licenses

Upstream logs, data and networks © the authors, CC BY 4.0; their scripts MIT; the MinAtar source inside Exp 5 prompts is GPL-3.0 (see `upstream/exp5_write_from_scratch/LICENSE-MinAtar`). This repo's code: MIT.
