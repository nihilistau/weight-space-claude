# Lab notebook

Newest entries at the bottom. Write predictions **before** a run and commit them; write what happened after. Never rewrite an old entry: add a correction below it.

---

## 2026-11-03: Setup

**Goal.** Ask Claude the questions from *Sparks of Weight-Space Programming* (Takehi, Teoh, Zhang, Khattab, MIT CSAIL, 2 Nov 2026) and compare with GPT-6 Astra. Starting with the three cheap, single-turn, no-tool experiments: 1 (which game), 2 (which shape), 5 (write a MinAtar policy from scratch).

**Decisions.**
- Upstream logs pinned as a submodule at `4d09ba6`. Prompts are used verbatim from there, never copied or edited.
- Harness: `claude -p` with `--tools ""`, `--strict-mcp-config`, `--safe-mode`, upstream's one-line system prompt, fresh conversation per case, run from an empty temp folder. Every turn's stream is audited.
- Model `opus` (Claude Code's alias for the current Opus), effort matched by name: `high` for Exps 1-2, `xhigh` for Exp 5.
- Exp 5 output cap raised to 64K tokens (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`): Astra used 20-29K output tokens per reply and a cut-off reply would score as a broken network.
- Runs through the Claude subscription (Claude Code login), not the API. The stream still reports an API-equivalent cost.

**Instrument checks** (`wsp validate`; upstream didn't publish its Exp 5 reader or scorer, so we wrote both):
- Exp 1/2 keyword scorers reproduce all 7 of upstream's labels and confidences.
- Exp 5 edits reader rebuilds all three of Astra's networks bit-for-bit.
- Exp 5 game scorer, on Astra's networks, 1,000 episodes: Asterix 53.8 ± 1.0 (published 53.2), Seaquest 55.8 ± 1.4 (53.1), Breakout 498.7 ± 7.8 (517.4). All within noise (|z| < 2).

**Predictions** (fill in before the first real run):
- Exp 1, how many of 4 will Claude get right?
- Exp 2, right shape for how many of 3? Will Claude also draw outlines instead of filled shapes?
- Exp 5, Claude's Breakout score vs Astra's 517 and PPO's 25?

---
