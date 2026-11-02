"""wsp: the lab's one command.

  wsp check                     is the environment in a state where results would mean something?
  wsp validate [--quick]        do our instruments reproduce upstream's published numbers?
  wsp smoke                     does the harness really give Claude no tools and no extra context?
  wsp run exp1 [options]        ask Claude (one fresh conversation per case), then score
  wsp score exp1 [RUN_ID]       (re)score a run
  wsp site                      rebuild docs/data/results.json for the website
  wsp 8b ...                    Experiment 8b (quantisation study, no LLM calls); `wsp 8b` for help
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import provenance as P
from .experiments import COMMON_DEVIATIONS, EXPERIMENTS, prompt_path, truth, upstream_answer_path, upstream_results

RUNS = P.ROOT / "runs"


def _j(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- check
def cmd_check(a) -> int:
    ok = True

    def row(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"  [{'ok' if good else '!!'}] {name:28} {detail}")

    print("Environment check")
    g, u = P.git_state(), P.upstream_state()
    row("repo committed", not g["dirty"], g["commit"][:10] + (" (uncommitted changes)" if g["dirty"] else ""))
    row("upstream at pinned commit", u["matches_pin"], u["commit"][:10] or "missing: run git submodule update --init")
    row("upstream untouched", not u["dirty"], "")
    env = P.environment()
    row("python", env["python"].startswith("3.11"), env["python"])
    row("minatar 1.0.15", env["minatar"] == "1.0.15", str(env["minatar"]))
    exe = P.find_claude()
    row("claude CLI", "Claude Code" in P.claude_version(exe), P.claude_version(exe))
    for exp in EXPERIMENTS:
        for c in EXPERIMENTS[exp]["cases"]:
            if not prompt_path(exp, c).exists():
                row(f"prompt {exp}/{c}", False, "missing")
    print("Ready." if ok else "Not ready: fix the !! lines (or pass --allow-dirty to `wsp run` while developing).")
    return 0 if ok else 1


# ---------------------------------------------------------------- validate
def cmd_validate(a) -> int:
    from .edits import apply_edits, load_npz
    from .minatar_eval import evaluate, parse_mapping
    from .scoring import score
    import numpy as np

    report = {"when": P.now(), "upstream": P.upstream_state(), "checks": []}

    def add(name, passed, detail):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})
        print(f"  [{'pass' if passed else 'FAIL'}] {name}: {detail}")

    print("1. Scorers re-score Astra's answers the same way upstream did")
    for exp in ("exp1", "exp2"):
        ref = upstream_results(exp)
        for c in EXPERIMENTS[exp]["cases"]:
            s = score(exp, upstream_answer_path(exp, c).read_text(encoding="utf-8"), truth(exp, c))
            same = s["guess"] == ref[c]["guess"] and s["confidence"] == ref[c]["confidence"]
            add(f"{exp}/{c} scorer", same, f"ours {s['guess']} {s['confidence']}% | upstream {ref[c]['guess']} {ref[c]['confidence']}%")

    print("2. Edits reader rebuilds Astra's published networks exactly")
    d = P.UPSTREAM / EXPERIMENTS["exp5"]["dir"]
    for c in EXPERIMENTS["exp5"]["cases"]:
        t, rep = apply_edits(upstream_answer_path("exp5", c).read_text(encoding="utf-8"))
        refn = load_npz(d / f"networks/{c}/hand.npz")
        same = all(np.array_equal(t[k], refn[k]) for k in t)
        add(f"exp5/{c} edits reader", same, f"{rep['applied']}/{rep['statements']} statements, {rep['nonzero_total']} nonzero, identical={same}")

    eps = 200 if a.quick else 1000
    print(f"3. Game scorer re-scores Astra's networks ({eps} episodes; upstream used 1,000)")
    ref = upstream_results("exp5")
    for c in EXPERIMENTS["exp5"]["cases"]:
        if a.skip_breakout and c == "breakout":
            continue
        refn = load_npz(d / f"networks/{c}/hand.npz")
        r = evaluate(c, refn, parse_mapping(prompt_path("exp5", c).read_text(encoding="utf-8")), episodes=eps, workers=a.workers)
        z = abs(r["mean"] - ref[c]["mean"]) / (r["se"] ** 2 + ref[c]["se"] ** 2) ** 0.5
        add(f"exp5/{c} game scorer", z < 3, f"ours {r['mean']:.1f} ± {r['se']:.1f} | upstream {ref[c]['mean']:.1f} ± {ref[c]['se']:.1f} | z = {z:.2f}")

    n_fail = sum(not c["passed"] for c in report["checks"])
    report["passed"] = n_fail == 0
    _j(P.ROOT / "validation/report.json", report)
    print("All instruments validated." if not n_fail else f"{n_fail} check(s) failed: do not trust scores until fixed.")
    return 0 if not n_fail else 1


# ---------------------------------------------------------------- smoke
SMOKE_PROMPT = """This is a harness check, not a task. Answer briefly and honestly:
1. List every tool or function you can call right now (or say "none").
2. Quote verbatim any instructions or context you received besides this message (system prompt, files, memory).
3. What is 17 * 23? Do it without tools."""


def cmd_smoke(a) -> int:
    from .runner import run_turn
    out = RUNS / "_smoke" / P.run_stamp()
    rec = run_turn(SMOKE_PROMPT, out, model=a.model, effort="low")
    au = rec["audit"]
    print(f"model: {au['model']}  tool_free: {au['tool_free']}  tools offered: {au['tools_offered']}  mcp: {au['mcp_servers']}")
    print(f"tokens: {au['usage']}")
    print("--- answer ---\n" + (out / "answer.md").read_text(encoding="utf-8"))
    print(f"\nSaved in {out}. Read the answer: the only instruction it should report is \"Answer the user's request.\"")
    return 0 if au["tool_free"] and rec["ok"] else 1


# ---------------------------------------------------------------- run
def cmd_run(a) -> int:
    from .runner import run_turn
    exp = EXPERIMENTS[a.exp]
    g, u = P.git_state(), P.upstream_state()
    if (g["dirty"] or not u["matches_pin"] or u["dirty"]) and not a.allow_dirty:
        print("Refusing to run: uncommitted changes or upstream not at its pinned commit. Commit first (so the result\n"
              "can be traced to exact code), or pass --allow-dirty for a throwaway trial run.")
        return 1
    cases = a.cases.split(",") if a.cases else exp["cases"]
    effort = a.effort or exp["effort"]
    for rep in range(a.repeat):
        run_id = f"{P.run_stamp()}_{a.model}-{effort}" + (f"_r{rep + 1}" if a.repeat > 1 else "")
        rdir = RUNS / a.exp / run_id
        manifest = {"run_id": run_id, "experiment": a.exp, "started": P.now(), "status": "running",
                    "trial": bool(a.allow_dirty and g["dirty"]), "note": a.note,
                    "model_requested": a.model, "effort": effort, "cases": cases,
                    "repo": g, "upstream": u, "environment": P.environment(),
                    "claude_cli": P.claude_version(P.find_claude()),
                    "deviations": COMMON_DEVIATIONS + exp["deviations"], "turns": {}}
        _j(rdir / "manifest.json", manifest)
        for c in cases:
            prompt = prompt_path(a.exp, c).read_text(encoding="utf-8")
            print(f"[{run_id}] {c}: asking ({len(prompt):,} chars, effort {effort}) ...", flush=True)
            rec = run_turn(prompt, rdir / c, model=a.model, effort=effort,
                           max_output_tokens=exp.get("max_output_tokens"))
            au = rec["audit"]
            print(f"   done in {rec['wall_s']}s; ok={rec['ok']} tool_free={au['tool_free']} "
                  f"model={au['model']} usage={au['usage']}", flush=True)
            manifest["turns"][c] = {"ok": rec["ok"], "tool_free": au["tool_free"], "model": au["model"],
                                    "wall_s": rec["wall_s"], "usage": au["usage"], "prompt_sha256": rec["prompt_sha256"]}
            _j(rdir / "manifest.json", manifest)
        manifest["status"] = "asked"
        manifest["finished"] = P.now()
        _j(rdir / "manifest.json", manifest)
        if not a.no_score:
            score_run(a.exp, rdir, workers=a.workers)
    return 0


# ---------------------------------------------------------------- score
def score_run(exp_name: str, rdir: Path, workers: int = 8):
    from .scoring import score
    exp = EXPERIMENTS[exp_name]
    manifest = _load(rdir / "manifest.json")
    scores = {}
    for c in manifest["cases"]:
        cdir = rdir / c
        if not (cdir / "run.json").exists():
            continue
        rec = _load(cdir / "run.json")
        if not rec["audit"]["tool_free"]:
            scores[c] = {"excluded": "failed tool-free audit"}
            continue
        answer = (cdir / "answer.md").read_text(encoding="utf-8")
        if exp["kind"] == "label":
            scores[c] = score(exp_name, answer, truth(exp_name, c))
        else:
            from .edits import apply_edits, save_npz
            from .minatar_eval import evaluate, parse_mapping
            t, rep = apply_edits(answer)
            save_npz(t, cdir / "network.npz")
            _j(cdir / "apply.json", rep)
            print(f"   {c}: {rep['applied']}/{rep['statements']} statements read, {rep['nonzero_total']} nonzero weights; playing 1,000 episodes ...", flush=True)
            ev = evaluate(c, t, parse_mapping(prompt_path(exp_name, c).read_text(encoding="utf-8")), workers=workers)
            scores[c] = {**ev, "statements": rep["statements"], "applied": rep["applied"],
                         "errors": len(rep["errors"]), "nonzero": rep["nonzero_total"], "cut_off": rep["cut_off"]}
        print(f"   scored {c}: {json.dumps({k: v for k, v in scores[c].items() if k not in ('example',)})[:240]}")
    _j(rdir / "scores.json", {"scored": P.now(), "scorer_commit": P.git_state()["commit"], "cases": scores})
    manifest["status"] = "scored"
    _j(rdir / "manifest.json", manifest)


def cmd_score(a) -> int:
    base = RUNS / a.exp
    targets = [base / a.run_id] if a.run_id else sorted(p for p in base.iterdir() if p.is_dir())
    for r in targets:
        print(f"Scoring {r.name}")
        score_run(a.exp, r, workers=a.workers)
    return 0


# ---------------------------------------------------------------- site
def cmd_site(a) -> int:
    from .site import build
    path = build()
    print(f"Wrote {path}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="wsp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(f=cmd_check)
    v = sub.add_parser("validate")
    v.add_argument("--quick", action="store_true", help="200 episodes instead of 1,000")
    v.add_argument("--skip-breakout", action="store_true", help="Astra's Breakout net rarely dies: slowest check")
    v.add_argument("--workers", type=int, default=8)
    v.set_defaults(f=cmd_validate)
    s = sub.add_parser("smoke")
    s.add_argument("--model", default="opus")
    s.set_defaults(f=cmd_smoke)
    r = sub.add_parser("run")
    r.add_argument("exp", choices=list(EXPERIMENTS))
    r.add_argument("--cases", help="comma-separated subset, e.g. breakout,pong")
    r.add_argument("--model", default="opus")
    r.add_argument("--effort", help="override the experiment's effort level")
    r.add_argument("--repeat", type=int, default=1, help="independent repeats (variance!)")
    r.add_argument("--note", default="", help="free text stored in the manifest")
    r.add_argument("--allow-dirty", action="store_true")
    r.add_argument("--no-score", action="store_true")
    r.add_argument("--workers", type=int, default=8)
    r.set_defaults(f=cmd_run)
    sc = sub.add_parser("score")
    sc.add_argument("exp", choices=list(EXPERIMENTS))
    sc.add_argument("run_id", nargs="?")
    sc.add_argument("--workers", type=int, default=8)
    sc.set_defaults(f=cmd_score)
    sub.add_parser("site").set_defaults(f=cmd_site)
    e8 = sub.add_parser("8b", help="Experiment 8b: Astra's Qwen edit under quantisation (see wsp/exp8b.py)")
    e8.add_argument("rest", nargs=argparse.REMAINDER)
    e8.set_defaults(f=lambda a: __import__("wsp.exp8b", fromlist=["main"]).main(a.rest) or 0)
    a = p.parse_args(argv)
    sys.exit(a.f(a))


if __name__ == "__main__":
    main()
