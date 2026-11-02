"""The experiments, defined by pointing at upstream's files. Prompts are used verbatim from the
pinned upstream copy; nothing here rewrites them. Any deliberate change to the protocol must be
listed under `deviations`, so the website can show it next to the result."""
from __future__ import annotations

import json

from .provenance import UPSTREAM

EXPERIMENTS = {
    "exp1": {
        "dir": "exp1_which_game",
        "title": "Which game was this network trained on?",
        "question": "From the raw weights of a small PPO policy (17,253 weights, as text), name the game it plays. "
                    "Open answer: no list of games is given. No tools.",
        "kind": "label",
        "effort": "high",
        "cases": ["breakout", "pong", "pacman", "freeway"],
        "prompt": "runs/{case}/prompt.txt",
        "upstream_answer": "runs/{case}/answer.md",
        "truth_key": "game",
        "deviations": [],
    },
    "exp2": {
        "dir": "exp2_diffusion",
        "title": "What does this diffusion model generate?",
        "question": "From the weights of a small DDPM (23,824 weights, as text), describe the images it generates "
                    "and draw one. No tools, and no forward-pass calculation allowed.",
        "kind": "label",
        "effort": "high",
        "cases": ["circle", "square", "triangle"],
        "prompt": "runs/{case}/prompt.txt",
        "upstream_answer": "runs/{case}/answer.md",
        "truth_key": "shape",
        "deviations": [],
    },
    "exp5": {
        "dir": "exp5_write_from_scratch",
        "title": "Write a game-playing network from scratch",
        "question": "Every weight of a 600-32-32-6 policy starts at 0. Given the MinAtar game's rules and source, write "
                    "the weights in one reply, no tools, no feedback. Scored over 1,000 episodes against PPO.",
        "kind": "minatar",
        "effort": "xhigh",
        "max_output_tokens": 64000,
        "cases": ["breakout", "seaquest", "asterix"],
        "prompt": "runs/{case}/message.txt",
        "upstream_answer": "runs/{case}/reply/answer.md",
        "deviations": [],
    },
}

COMMON_DEVIATIONS = [
    "Model: Claude Opus 5.5 (`claude-opus-5-5`, via Claude Code `claude -p`) instead of gpt-6-astra (via Codex `codex exec`).",
    "Reasoning effort uses Claude's level of the same name (high / xhigh); the two scales are not calibrated to each other.",
    "Claude Code returns its own thinking (or a summary of it) instead of Codex's reasoning summaries.",
    "Claude Code in -p mode adds an identity line and a short environment block (temp working folder, OS, date, model name) "
    "to the one-line system prompt; it also claims a shell tool exists. Found by `wsp smoke` (runs/_smoke/). No tool is actually "
    "offered or callable (audited per turn). Removing the block needs the raw API instead of the subscription.",
]


def exp_dir(exp: str):
    return UPSTREAM / EXPERIMENTS[exp]["dir"]


def prompt_path(exp: str, case: str):
    return exp_dir(exp) / EXPERIMENTS[exp]["prompt"].format(case=case)


def upstream_answer_path(exp: str, case: str):
    return exp_dir(exp) / EXPERIMENTS[exp]["upstream_answer"].format(case=case)


def truth(exp: str, case: str) -> str:
    """The answer key. Read only by scorers, never by the runner."""
    e = EXPERIMENTS[exp]
    if e["kind"] != "label":
        return case
    key = json.loads((exp_dir(exp) / "eval/answer_key.json").read_text())
    vals = {v[e["truth_key"]] for v in key.values()}
    assert case in vals, f"{case} not in answer key"
    return case


def upstream_results(exp: str) -> dict:
    """Astra's published numbers, per case, for side-by-side display."""
    e, d = EXPERIMENTS[exp], exp_dir(exp)
    out = {}
    if e["kind"] == "label":
        key = json.loads((d / "eval/answer_key.json").read_text())
        for s in json.loads((d / "eval/scores.json").read_text()):
            case = key[s["id"]][e["truth_key"]]
            out[case] = {"guess": s["guess"], "correct": s["correct"], "confidence": s["confidence"],
                         "answer_line": s["answer_line"], "usage": s["usage"], "wall_s": s["wall_s"]}
    else:
        ev = json.loads((d / "eval/minatar_eval.json").read_text())
        for case in e["cases"]:
            g = ev[case]
            ppo100 = max((v for k, v in g.items() if k.startswith("ppo100")), key=lambda v: v["mean"])
            ppo500 = max((v for k, v in g.items() if k.startswith("ppo500")), key=lambda v: v["mean"])
            run = json.loads((d / f"runs/{case}/reply/run.json").read_text())
            out[case] = {"mean": g["hand"]["mean"], "se": g["hand"]["se"], "ppo100": ppo100["mean"],
                         "ppo500": ppo500["mean"], "usage": run["audit"]["usage"], "wall_s": run["wall_s"]}
    return out
