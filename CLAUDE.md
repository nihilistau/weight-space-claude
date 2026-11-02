# Agent rules for this repo

Read [README.md](README.md), then [guide/GUIDE.md](guide/GUIDE.md), then the latest entries of [NOTEBOOK.md](NOTEBOOK.md).

1. **Never edit `upstream/`.** It is the pinned original (submodule at `4d09ba6`). `wsp check` fails if it changes.
2. **Never edit files under `runs/` by hand.** Raw records (`events.jsonl`, `answer.md`, `run.json`) are the evidence. Fix a reader or scorer and re-derive with `wsp score` instead.
3. **Commit before `wsp run`.** Runs record the git commit; `--allow-dirty` runs are flagged as trials.
4. **Changed a scorer, reader or the harness? Run `wsp validate`** and commit `validation/report.json` with it.
5. **Any change to the protocol is a deviation.** Add it to `deviations` in `wsp/experiments.py` and to the notebook.
6. **Notebook:** append a dated entry for every decision and every run; never rewrite past entries. Predictions go in *before* a run.
7. After runs: `wsp site`, commit `runs/`, `docs/data/`, `NOTEBOOK.md`, push. The website is GitHub Pages from `docs/`.
