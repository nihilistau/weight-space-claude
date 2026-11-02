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

**Instrument checks re-run on this machine (beast, 8 workers)**: all 13 pass. Game scorer: Breakout 508.4 ± 7.7 (z 0.84), Seaquest 51.0 ± 1.3 (z 1.12), Asterix 53.6 ± 1.1 (z 0.29). Note the run-to-run spread: the same network scored 498.7 and 508.4 on two machines. That is what ±8 looks like.

**Harness smoke test** (`runs/_smoke/20261102T2032Z`): served model `claude-opus-5-5`, no tools offered, no MCP servers, 17 × 23 = 391. *Finding:* the model reported more context than the one line we set: Claude Code prepends "You are a Claude agent, built on Anthropic's Claude Agent SDK." and appends an environment block (temp folder, Windows version, date, model name) that also says a PowerShell/Bash tool is available. It isn't (audit: tools offered = []), and Claude answered "Tools: none". Logged as a deviation rather than hidden. Upstream's Codex harness probably adds a similar block; their logs don't show the full system prompt. Lesson: **ask the subject what it sees**. The flags said "system prompt replaced"; the model's own report showed what was actually sent.

**Predictions** (written before the first real run):

*Claude-the-assistant's predictions (the one building this lab, predicting its own model family):*
- Exp 1: 3 or 4 of 4. Breakout and Pong have distinctive input structure (paddle row/column); Pac-Man vs Freeway is where an error is likeliest.
- Exp 2: 2 or 3 of 3. Unsure whether the drawings will be outlines too: reading "edge" detectors in W1 naturally suggests outlines.
- Exp 5: Breakout well above PPO's 25 (a ball-tracking paddle is easy to hand-wire), likely 50-500, below Astra's 517. Seaquest lower than Astra's 53 (oxygen and diver management is hard to wire by hand), maybe 10-40. Asterix 20-55.
- Main risk: Exp 5 replies that are too long or malformed for the edits reader.

*Ray's predictions:* (add yours here; for this first batch, write them before looking at the results)
- Exp 1, how many of 4 will Claude get right?
- Exp 2, right shape for how many of 3? Will Claude also draw outlines instead of filled shapes?
- Exp 5, Claude's Breakout score vs Astra's 517 and PPO's 25?

---
