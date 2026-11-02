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

## 2026-11-03: First Claude runs (Exps 1, 2, 5)

Runs: `runs/exp1/20261102T2033Z_opus-high`, `runs/exp2/20261102T2041Z_opus-high`, `runs/exp5/20261102T2047Z_opus-xhigh`. Model served: `claude-opus-5-5` in every turn. All 10 turns passed the tool-free audit. Code at commit `aab1beb`. One attempt per case (n = 1, as upstream).

### Exp 1: which game? **Claude 4/4, Astra 4/4**

| Game | Claude | conf. | Astra conf. | Claude out / thinking tokens |
|---|---|---|---|---|
| Breakout | right | 80% | 99% | 13,860 / 12,496 |
| Pong | right | 60% | 96% | 6,720 / 5,309 |
| Pac-Man | right | 72% | 96% | 11,340 / 9,620 |
| Freeway | right ("Freeway or Frogger") | 80% | 97% | 21,141 / 19,544 |

Same accuracy, consistently lower stated confidence, and ~4-20x more output tokens than Astra (~1.7K). Whether Claude is better *calibrated* can't be told from 4 right answers: calibration needs wrong answers too.

### Exp 2: which shape? **Claude 3/3, Astra 3/3, but the drawings differ**

| Shape | Claude | conf. | Claude's drawing | Astra's drawing |
|---|---|---|---|---|
| circle | right | 55% | outline (fill 0.35) | outline (0.32) |
| square | right | 55% | **solid** (fill 1.0) | outline (0.44) |
| triangle | right | 50% | **solid** (fill 1.0) | outline (0.49) |

The paper's notable failure was that Astra drew every shape as an outline while the models generate filled shapes. Claude drew two of three filled, matching what the models actually produce. With n = 1 this is a hint, not a finding: a repeat run (`wsp run exp2 --repeat 3`, ~$7 API-equivalent) would show whether it holds.

### Exp 5: write a network from scratch (1,000 episodes, mean ± SE)

| Game | PPO 100M | PPO 500M | Astra | **Claude** | Claude out / thinking tokens | time |
|---|---|---|---|---|---|---|
| Breakout | 15.8 | 25.3 | 517.4 | **306.6 ± 7.9** | 111,917 / 108,548 | 18 min |
| Seaquest | 5.6 | 88.9 | 53.1 | **24.5 ± 0.8** | 130,304 / 125,296 | 22 min |
| Asterix | 25.8 | 55.2 | 53.2 | **33.1 ± 0.8** | 117,031 / 112,222 | 19 min |

- Every reply parsed with zero errors (80 / 138 / 151 statements). Claude beats PPO-100M on all three games and beats PPO-500M on Breakout by 12x, but trails Astra on all three.
- Breakout: like Astra, Claude hand-wired a ball-landing predictor including the wall reflection. Best single episode 841 (Astra's best: 800); the mean is lower because more episodes end early.
- Seaquest: the reply has no design description, only the edits block, although the prompt asked for both.
- **Cost of thinking:** ~110-125K thinking tokens per reply against Astra's 17-26K. Claude at xhigh thinks ~5x longer here for a lower score.

### Predictions vs outcome (Claude-the-assistant's)
- Exp 1 "3 or 4": 4. ✔
- Exp 2 "2 or 3; unsure about outlines": 3, and mostly *not* outlines. ✔ / surprise
- Exp 5 Breakout "50-500, below Astra": 307. ✔. Seaquest "10-40": 24.5 ✔. Asterix "20-55": 33 ✔.

### Harness findings
- The output cap `CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000` did **not** bind: replies reached 130K output tokens. Thinking appears to be budgeted separately. Harmless here (all replies ended with `end_turn`, nothing cut off), but the manifest's `max_output_tokens: 64000` is not the effective limit. Note for later: don't trust a setting you haven't seen take effect.
- API-equivalent cost reported by Claude Code: **$12.67** for all 10 turns (Exp 1 $2.65, Exp 2 $2.33, Exp 5 $7.70). Run on the subscription.

### Next ideas
1. Repeats (`--repeat 3`) for Exp 2, to see whether the solid-vs-outline difference is stable.
2. Exp 5 at `max` effort, or `high`, to see whether score tracks thinking.
3. Exp 4 (fix the car policy: one reply, ~355K-token prompt): the last single-turn, no-tool experiment.

## 2026-11-03: Labelling, and Exp 2 repeats

- README and site now name the model explicitly (**Claude Opus 5.5**, `claude-opus-5-5`), taken from the served-model field in each run's event stream rather than typed by hand, so a future Sonnet/Fable run labels itself. Experiment pages get an "All runs" table.
- **Exp 2 × 3 repeats** (same prompts, fresh conversations, effort `high`), to check whether the first run's solid square and triangle hold up or were luck.
  *Prediction (Claude-the-assistant):* shape identification stays 3/3 in every repeat. Drawings: the square drawn solid in at least 2 of 3; the circle mostly an outline; the triangle a coin flip.

### Exp 2 repeats: results

Runs `20261102T2226Z_opus-high_r1`, `..._2235Z_..._r2`, `..._2239Z_..._r3`, plus the first run `20261102T2041Z`. Claude Opus 5.5, effort `high`, all tool-free.

| Run | circle | square | triangle |
|---|---|---|---|
| first | ✓ 55% · outline (0.35) | ✓ 55% · **solid** | ✓ 50% · **solid** |
| r1 | ✓ 50% · outline (0.35) | ✓ 55% · **solid** | ✓ 45% · **solid** |
| r2 | ✓ 55% · outline (0.39) | ✓ 55% · outline (0.49) | ✓ 45% · **solid** |
| r3 | ✓ 45% · **solid** | ✓ 45% · **solid** | ✗ 60% · "digit 2" |
| *Astra (paper, n=1)* | ✓ 84% · outline | ✓ 77% · outline | ✓ 88% · outline |

- **Identification: 11 / 12.** The miss (r3, triangle model): Claude answered *handwritten white digit "2"s*, described as a rounded top arc, a diagonal stroke to the lower left and a flat base. The scorer's `guess` field says "circle" because its upstream-style keyword list counts "round" as circle. The case is wrong either way; the label is a scorer artefact, left unchanged because the scorer is the validated one. Worth noticing that this wrong answer came with Claude's **highest** confidence on that model (60%).
- **Drawings: filled 7 of 11 correct answers** (square 3/4, triangle 3/3, circle 1/4), against Astra's 0 of 3. The difference from Astra holds up across repeats. The circle is the shape Claude most often draws as a ring.
- **Confidence** stays 45-60% throughout, against Astra's 77-88%: consistently more hedged, yet not well calibrated either (the wrong answer was the most confident).
- **Prediction check:** "3/3 every repeat": ✗ (one miss). "Square solid in ≥2 of 3 repeats": ✔ (2/3). "Circle mostly outline": ✔ (2/3). "Triangle coin flip": ✗, solid every time it was identified.
- Lesson: the first run's 3/3 was real but not the whole story. One repeat in four found a failure that a single run would have hidden.
