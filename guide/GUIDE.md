# How experiments like this work

A field guide written alongside this lab. Each section names one idea, says why it matters, and points to where this repo does it. None of it is specific to ML: it is ordinary experimental practice, applied to asking a model a question.

---

## 1. Say exactly what is being claimed

The paper's claim is not "LLMs understand weights". It is narrower and testable: *given these exact prompts, under these exact restrictions, Astra produced these answers, and they scored this way.* Before running anything, write the claim you are testing in that form. Ours:

> Given upstream's prompts verbatim, with no tools, does Claude (a) name the right game / shape from raw weights, and (b) write a MinAtar policy that scores comparably to Astra and PPO?

**Words that get mixed up:**

| Term | Meaning | Here |
|---|---|---|
| Reproduction | same code, same data, same model: do you get the same numbers? | our instrument checks (section 4) reproduce upstream's *scoring* |
| Replication | same question, new run, often a new subject | asking **Claude** the same questions |
| Generalisation | does it hold on new cases? | a later step: new networks, new games |

This lab is a **cross-model replication**: the protocol is held fixed and the model is swapped.

## 2. The anatomy of an experiment

- **What you change (independent variable):** the model, Astra → Claude. Later maybe effort level, or repeats.
- **What you hold constant (controls):** the prompt text (byte-for-byte, checked by hash), the system prompt (one line), no tools, one fresh conversation per case, the scorer, the episode count.
- **What you measure (dependent variables):** right/wrong and confidence (Exp 1, 2); mean game score (Exp 5); plus tokens and time.
- **Baselines:** something to compare against so a number means something. Exp 5 has PPO trained for 100M and 500M steps. Exp 1's README gives a random policy's return too. A score of 50 means nothing until you know random gets ~1 and PPO gets 55.
- **Blinding:** the model must not get the answer through a side door. Upstream names networks by random IDs (`a9f535cc`), never "breakout". In our code the answer key is read only by `scoring.py`, never by `runner.py`.

## 3. The harness is part of the experiment

How the model is called changes the result, so the harness gets the same scrutiny as the scorer. Upstream switched off every Codex tool and audited each turn's event stream. We do the same with `claude -p` (see `wsp/runner.py`):

- `--tools ""` and `--strict-mcp-config`: nothing to call.
- `--safe-mode`: no CLAUDE.md, memory, skills, plugins or hooks leaking in. Your own `~/.claude` setup would otherwise be part of the "prompt".
- `--system-prompt "Answer the user's request."`: upstream's exact line, replacing Claude Code's long default.
- Run from an empty temp folder, `--no-session-persistence`: every case is a fresh conversation.

**Trust, then verify.** Flags can be ignored or change between versions, so `wsp smoke` asks Claude directly what tools and instructions it sees, and every real run is audited from the raw stream: no tools offered, no tool calls. A run that fails the audit is kept (it is still data about the harness) but is never scored.

## 4. Validate your instruments before you use them

Upstream published Exp 5's networks and scores but **not** the code that reads a reply into weights or the code that plays the games. We wrote both. Anything we write ourselves is a measuring instrument, and an unvalidated instrument makes every number it produces suspect.

The test: run our instruments on **upstream's own published answers** and check we get **upstream's published numbers**.

- Edits reader: rebuilding Astra's three networks from `answer.md` must give *bit-identical* `hand.npz`. (It does.)
- Game scorer: re-scoring Astra's networks must land within noise of 517.4 / 53.1 / 53.2. (It does: see the "Instrument checks" tab.)
- Exp 1/2 keyword scorers: must map Astra's answers to the same labels and confidences as upstream's `scores.json`. (They do.)

Only after this do we ask Claude anything. If Claude then scores 3, we know it is Claude and not our scorer.

## 5. Noise, and how many runs you need

A model's answer is a sample, not a fact. Run the same prompt twice and you get two different replies. The game scores are random too (sampled actions, sticky actions, random starts).

- **Standard error (SE):** how much a mean would wobble if you re-ran the episodes. Exp 5 reports mean ± SE over 1,000 episodes.
- **z-score:** difference ÷ combined SE. |z| < 2 is "can't tell apart"; |z| > 3 is a real difference. Our validation uses |z| < 3.
- **n = 1 per case** is what upstream did. That is fine for "can it ever do this?" (an existence proof) and weak for "how often?". `wsp run exp1 --repeat 3` gives three independent attempts; for Exps 1 and 2 that costs little.
- **Chance level:** Exp 1 is open-answer with no list, so a guess has no fixed chance rate, but "4 out of 4" on a well-known set of games is less surprising than it sounds. Worth thinking about when you read any 4/4.

## 6. Provenance: can anyone trace a number back to its cause?

Every result must answer: *which code, which prompt, which model, which settings, when?*

- **Pinned source:** `upstream/` is a git submodule locked to one commit. `wsp check` fails if it moves or is edited.
- **Commit before running:** `wsp run` refuses to start with uncommitted changes, because otherwise "the code that produced this" doesn't exist anywhere. `--allow-dirty` exists for throwaway trials, and those runs are flagged "trial" everywhere.
- **The manifest:** `runs/<exp>/<run_id>/manifest.json` records the git commit, upstream commit, Claude CLI version, Python and package versions, the model *requested* and the model *served* (read from the stream; they can differ), effort, and deviations.
- **Raw before derived:** `events.jsonl` (the raw stream) is the primary record. `answer.md`, `scores.json`, `results.json` and the website are all derived from it and can be rebuilt (`wsp score`, `wsp site`). Never edit raw data by hand; if a reader had a bug, fix the reader and re-derive (upstream did exactly this for Exp 5, and documented it).
- **Hashes:** each run records the SHA-256 of the prompt it sent, so "same prompt" is checkable, not assumed.

## 7. Write predictions down first

Before a run, write in `NOTEBOOK.md` what you expect and why. Afterwards you can't fool yourself about what you "expected". This is a lightweight version of **pre-registration**. It also makes the notebook much more interesting to read later.

## 8. Contamination

Could the model have seen the answers in training? The paper appeared 2 Nov 2026, after Claude's training data, and the runs have no web access. The MinAtar source is in the prompt anyway. For future *new* test networks this question matters more: anything that has been public for a while might be in training data.

## 9. Deviations are reported, not hidden

No replication is identical. Ours: a different model, a different CLI, effort levels with the same names but no calibration between vendors, and Claude's thinking instead of Codex's reasoning summaries. These are listed in `wsp/experiments.py` and shown on every experiment page. A result is only as good as the reader's ability to see what was different.

## 10. Budget

Tokens are the cost. Exp 1: ~75K in / a few K out per case. Exp 2: ~100K in. Exp 5: ~10K in, 20-30K out (mostly thinking). All three experiments together cost a few dollars at API prices, or a small slice of a subscription week. Exps 6-8 (multi-turn, with forward passes) are ~300M tokens each; plan those deliberately.

---

## Repository map

```
upstream/            pinned, untouched copy of RikiyaT/lm_understand-logs (git submodule)
wsp/                 the lab's code
  runner.py          one tool-free `claude -p` turn, recorded and audited
  experiments.py     the experiment definitions: which upstream files, effort, deviations
  scoring.py         Exp 1/2 answer scorers (keyword mapping, as upstream)
  edits.py           Exp 5 reader: reply -> weights
  minatar_eval.py    Exp 5 scorer: 1,000 MinAtar episodes
  provenance.py      git state, versions, hashes, timestamps
  site.py            builds docs/data/results.json
  cli.py             the `wsp` command
runs/<exp>/<run>/    our raw records + scores, one folder per run (committed)
validation/          instrument check report
docs/                the website (GitHub Pages serves this folder)
guide/GUIDE.md       this file
NOTEBOOK.md          the lab notebook: dated entries, predictions, decisions
```

## The workflow

```
uv sync                      # build the exact environment from uv.lock
uv run wsp check             # is everything pinned, committed, installed?
uv run wsp validate          # do the instruments reproduce upstream? (once, or after changing a scorer)
uv run wsp smoke             # does Claude really see no tools and no extra context?
# write a prediction in NOTEBOOK.md, commit
uv run wsp run exp1          # ask + audit + score
uv run wsp site              # rebuild the website data
git add -A && git commit -m "exp1: first Claude run" && git push
```

## Glossary

- **PPO:** Proximal Policy Optimization, the standard RL algorithm used to train the baseline networks.
- **DDPM:** denoising diffusion model; learns to turn noise into images like its training set.
- **MinAtar:** small 10×10 versions of Atari games, built for fast RL research.
- **Sticky actions:** with probability 0.1 the game repeats the last action, so memorised action sequences don't work.
- **Effort:** how much the model is allowed to think before answering. Same names across vendors, different scales.
- **Submodule:** a git repo inside a git repo, pinned to one commit.
- **Lockfile (`uv.lock`):** the exact version of every Python package, so `uv sync` rebuilds the same environment anywhere.
