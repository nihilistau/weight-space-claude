"""Builds docs/data/results.json: everything the website shows, in one file.
The website (docs/index.html) is static and only reads this file, so the site can never show a
number that isn't traceable to a file in runs/ or upstream/."""
from __future__ import annotations

import json

from . import provenance as P
from .experiments import COMMON_DEVIATIONS, EXPERIMENTS, exp_dir, upstream_answer_path, upstream_results

REPO_URL = "https://github.com/nihilistau/weight-space-claude"
UPSTREAM_URL = f"https://github.com/RikiyaT/lm_understand-logs/tree/{P.UPSTREAM_PIN}"
MAX_THINKING = 60_000


def model_label(model_id: str | None) -> str:
    """claude-opus-5-5 -> Claude Opus 5.5 (falls back to the raw id)."""
    if not model_id:
        return "Claude (unknown model)"
    parts = model_id.split("-")
    if parts[0] == "claude" and len(parts) >= 3:
        fam = parts[1].capitalize()
        ver = ".".join(p for p in parts[2:] if p.isdigit() and len(p) < 4)
        return f"Claude {fam} {ver}".strip()
    return model_id


def _read(p, limit=None):
    if not p.exists():
        return None
    t = p.read_text(encoding="utf-8", errors="replace")
    return t if limit is None or len(t) <= limit else t[:limit] + f"\n\n[... {len(t) - limit:,} more characters in the file]"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def build():
    out = {"built": P.now(), "repo_url": REPO_URL, "upstream_url": UPSTREAM_URL, "upstream_pin": P.UPSTREAM_PIN,
           "common_deviations": COMMON_DEVIATIONS, "validation": _load(P.ROOT / "validation/report.json"),
           "guide": _read(P.ROOT / "guide/GUIDE.md"), "notebook": _read(P.ROOT / "NOTEBOOK.md"),
           "experiments": []}
    for name, e in EXPERIMENTS.items():
        ref = upstream_results(name)
        astra = {c: {**ref[c], "answer": _read(upstream_answer_path(name, c))} for c in e["cases"]}
        if name == "exp2":
            from .scoring import example_grid, fields, fill_ratio
            key = json.loads((exp_dir(name) / "eval/answer_key.json").read_text())
            for c in e["cases"]:
                mid = next(k for k, v in key.items() if v["shape"] == c)
                astra[c]["samples"] = _read(exp_dir(name) / f"eval/samples/{mid}.txt")
                g = example_grid(fields(astra[c]["answer"]))
                astra[c]["example"], astra[c]["fill_ratio"] = g, fill_ratio(g)
        runs = []
        rbase = P.ROOT / "runs" / name
        for rdir in sorted((p for p in rbase.iterdir() if p.is_dir()), reverse=True) if rbase.exists() else []:
            m = _load(rdir / "manifest.json")
            if not m:
                continue
            sc = (_load(rdir / "scores.json") or {}).get("cases", {})
            cases = {}
            for c in m["cases"]:
                cd = rdir / c
                rec = _load(cd / "run.json")
                if not rec:
                    continue
                cases[c] = {"score": sc.get(c), "audit": rec["audit"], "wall_s": rec["wall_s"], "ok": rec["ok"],
                            "cmd": rec["cmd"], "answer": _read(cd / "answer.md"),
                            "thinking": _read(cd / "thinking.md", MAX_THINKING),
                            "apply": _load(cd / "apply.json")}
            served = next((c["audit"].get("model") for c in cases.values() if c["audit"].get("model")), None)
            runs.append({"run_id": m["run_id"], "model_served": served, "model_label": model_label(served), "status": m["status"], "trial": m.get("trial"), "note": m.get("note"),
                         "started": m["started"], "model_requested": m["model_requested"], "effort": m["effort"],
                         "repo_commit": m["repo"]["commit"], "claude_cli": m.get("claude_cli"),
                         "environment": m.get("environment"), "deviations": m.get("deviations"), "cases": cases})
        out["experiments"].append({"id": name, "title": e["title"], "question": e["question"], "kind": e["kind"],
                                   "effort": e["effort"], "cases": e["cases"], "upstream_dir": e["dir"],
                                   "deviations": e["deviations"], "astra": astra, "runs": runs})
    out["models_used"] = sorted({r["model_label"] for e in out["experiments"] for r in e["runs"] if not r.get("trial")})
    out["model_ids"] = sorted({r["model_served"] for e in out["experiments"] for r in e["runs"] if r.get("model_served") and not r.get("trial")})
    path = P.ROOT / "docs/data/results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return path
