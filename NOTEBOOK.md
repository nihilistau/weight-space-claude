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

## 2026-11-03: Exp 8b, Astra's Qwen edit vs quantisation (no LLM calls)

**Question.** Astra's Exp 8 edit (run `p50c`: a loop direction removed from 64 output columns of the MLPs in layers 15 and 19 of Qwen3.5-0.8B) took MATH-500 from 7.9% to 48.1% by stopping endless repetition. (1) Does the fix survive 8/4/3/2-bit quantisation? (2) Does quantisation bring looping back by itself?

**Design.**
- Base: `Qwen/Qwen3.5-0.8B` @ `2fc0636` (the revision the edit was made on). Edited: rebuilt with upstream's own `apply_edit.rebuild`; every tensor's SHA-256 must match upstream's evaluated checkpoint.
- Both converted to GGUF F16 with llama.cpp `b12060`'s converter, then quantised to Q8_0, Q4_K_M, Q3_K_M, Q2_K (no imatrix, so both models are quantised the same way).
- 100 MATH-500 problems (seeded random subset), 1 sample each, upstream's `think35` sampling (thinking on, T 0.6, top-p 0.95, top-k 20, presence penalty 1.5, 32,768 tokens). llama.cpp's own extras switched off (min_p 0, repeat_penalty 1). Seed fixed per problem, so base and edited are **paired**. Upstream's chat template file.
- Grading: upstream's `mathqa.py` imported unchanged (a stub for its unpublished `mcqa` import; math-verify timeouts off on Windows).

**Instrument checks so far.**
- Grader: re-grading upstream's own saved sample texts gives the same verdict on **400 / 400** (200 unedited, 200 edited).
- Subset is representative: on these 100 problems upstream's vLLM runs scored 8.5% unedited and 49.8% edited (all 500: 7.9% / 48.1%).
- Lesson logged: importing upstream code wrote `__pycache__` into the pinned submodule and dirtied it. Fixed by disabling bytecode for that import.

**Deviations.** llama.cpp instead of vLLM; F16 instead of bf16 (the RTX 2060 has no bf16 support); 100 problems × 1 sample instead of 500 × 4 (SE ≈ 5 points per accuracy, smaller for the paired gain).

**Predictions (Claude-the-assistant, before any generation):**
- F16 reproduces the paper within noise: base ~5-15% with ~85-95% cut; edited ~40-55% with ~30-40% cut.
- Q8_0 ≈ F16.
- Q4_K_M: the edit survives; paired gain still ≥ 25 points.
- Q3_K_M: base loops even more; the gain shrinks but stays positive.
- Q2_K: both collapse (< 15%); the edited model still loops less, but there's not much maths left to rescue.

### Exp 8b, F16 pair (first protocol): the check partly failed, and why

| F16, 100 problems | accuracy | cut at 32,768 | notes |
|---|---|---|---|
| base | **10%** | **91%** | cut answers are loops: 88% of their tail 8-grams repeat |
| edited (Astra p50c) | **29%** | **65%** | cut answers mostly *not* verbatim loops (tail repeat 31%); median correct answer 12.3K tokens |
| paired gain | **+19 ± 4 pts** | | 21 rescued, 2 lost |
| *paper, same problems (vLLM, bf16)* | *8.5%* | *93% (all 500)* | edited: *49.8%*, *33% cut (all 500)* |

- **Base matches the paper; edited doesn't.** The instrument check is half passed, so before spending 20 more GPU-hours on quantised models I looked for a cause in our own setup.
- **Cause found (most likely):** llama.cpp applies the presence penalty only over the **last 64 tokens** (`--repeat-last-n` default 64); vLLM applies it to **every generated token**. I passed the presence penalty but not the window. For an experiment about loops this is exactly the wrong detail to miss: a repetition cycle longer than 64 tokens escapes a 64-token penalty. The base model loops either way, so it still matched; the edited model sits near the edge, where the sampler decides.
- **Prediction check:** "F16 reproduces the paper within noise" was ✔ for base and ✗ for edited (29% against a predicted 40-55%).
- **What changed:** protocols are now named. `pen64` = the run above, kept as a labelled variant (it's a real finding: a sampler default moves the edit's measured gain by perhaps 20 points). `penall` = presence penalty over the whole answer (`repeat_last_n` 34,816, confirmed on the running server's slots). All runs from here use `penall`, starting again with the F16 pair.
- **Lesson:** "same sampling settings" means *every* parameter the two engines interpret, not just the ones you name. Engines differ in defaults you never set.

### Exp 8b, F16 pair (protocol `penall`): the check passes

| F16, 100 problems | accuracy | cut at 32,768 | paired gain |
|---|---|---|---|
| base, `penall` | **11%** | **90%** | |
| edited (Astra p50c), `penall` | **46%** | **42%** | **+35 ± 5 pts** |
| *paper, same problems (vLLM)* | *8.5% / 49.8%* | *93% / 33% (all 500)* | *+41* |
| *variant `pen64` (penalty over last 64 tokens only)* | *10% / 29%* | *91% / 65%* | *+19 ± 4* |

- With the presence penalty over the whole answer (as vLLM does it), llama.cpp at F16 reproduces the paper within noise: 46% vs 49.8% edited, 11% vs 8.5% base. **The instrument check now passes**, so the quantised rows that follow measure quantisation, not the engine.
- The penalty window alone moves the edit's measured gain from +19 to +35 points: the same weights, the same problems, the same seeds. The edited model sits right at the edge where the sampler decides whether it escapes a loop. Base answers loop regardless (cut answers: 97% of their tail 8-grams repeat).
- Edited answers that still hit the limit are mostly not verbatim loops (tail repeat 41%): long, circling reasoning. The median correct edited answer is 16.2K tokens. It thinks for a long time, as the paper noted (9.2K median on practice problems).
- Prediction check: "F16 reproduces the paper within noise" ✔ (under the correct protocol).

### 2026-11-04: Exp 8b paused

Paused at Ray's request. Done under `penall`: F16 pair (published). In progress: base-Q2_K 82/100 (0 correct, 67 cut so far, unpublished). Not started: p50c-Q2_K, Q4_K_M, Q3_K_M, Q8_0.
To resume (finished answers are kept and skipped): `$env:EXP8B_PROTOCOL='penall'; uv run --group exp8 wsp 8b eval all`, then `uv run --group exp8 wsp 8b report` and `uv run wsp site`.
