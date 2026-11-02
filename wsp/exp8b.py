"""Experiment 8b: does Astra's weight edit to Qwen3.5-0.8B survive quantisation, and does quantisation bring the
looping back?

No LLM is asked anything here. We take Astra's published edit (upstream exp8_math, run p50c: the loop direction
removed from 64 MLP output columns in layers 15 and 19), rebuild the edited model bit-for-bit with upstream's own
apply_edit code, convert base and edited to GGUF, quantise both to the same levels, and run the same math problems
through llama.cpp with upstream's evaluation sampling.

  wsp 8b fetch-data          MATH-500 + the fixed problem subset
  wsp 8b build               edited checkpoint (hash-checked) -> GGUF F16 -> quants, for base and edited
  wsp 8b check-grader        our grading of upstream's own sample texts must match upstream's grades
  wsp 8b eval COND [COND..]  e.g. base-F16 p50c-Q4_K_M ; or 'all'
  wsp 8b report              paired comparison table -> runs/exp8b/summary.json

Work files (models, GGUF, llama.cpp) live in work/ (git-ignored, rebuildable). Results live in runs/exp8b/.
"""
from __future__ import annotations

import concurrent.futures as cf
import gzip
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

from . import provenance as P

UP8 = P.UPSTREAM / "exp8_math"
WORK = P.ROOT / "work"
BASE_DIR = WORK / "models" / "Qwen3.5-0.8B"
BASE_REV = "2fc06364715b967f1860aea9cf38778875588b17"
LLAMA_TAG = "b12060"
LLAMA_BIN = WORK / "tools" / "llama"
LLAMA_SRC = WORK / "tools" / "llama.cpp-src"
GGUF = WORK / "gguf"
OUT = P.ROOT / "runs" / "exp8b"

EDITS = ["p50c"]                                  # upstream runs whose edit we test
QUANTS = ["F16", "Q8_0", "Q4_K_M", "Q3_K_M", "Q2_K"]
N_PROBLEMS = 100
SUBSET_SEED = 8
# upstream protocol think35 (exp8 README / code/evaluate.py SAMPLING_THINK35), plus llama.cpp's own defaults switched
# off so the sampler matches vLLM's (min_p 0.05 and repeat_penalty are llama.cpp defaults vLLM doesn't apply)
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "presence_penalty": 1.5, "min_p": 0.0,
            "repeat_penalty": 1.0, "typical_p": 1.0, "n_predict": 32768}
PARALLEL = 12
CTX_PER_SLOT = 32768 + 1024
PORT = 8091


# ------------------------------------------------------------------------------------------------ helpers
def _j(p: Path, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=1, ensure_ascii=False), encoding="utf-8")


def _upstream_code():
    """Import upstream's exp8 code (apply_edit, st_numpy, mathqa) unchanged. mathqa imports a module upstream did not
    publish (mcqa, used only for a loop signal we don't call): a stub stands in for it."""
    code = str(UP8 / "code")
    if code not in sys.path:
        sys.path.insert(0, code)
    if "mcqa" not in sys.modules:
        stub = types.ModuleType("mcqa")
        stub.loop_signals = lambda text: {"repetitive_end": None}
        sys.modules["mcqa"] = stub
    old, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # never write __pycache__ into the pinned upstream
    try:
        import apply_edit, mathqa, st_numpy  # noqa: E401
    finally:
        sys.dont_write_bytecode = old
    if os.name == "nt":   # math-verify's timeouts use signal.alarm, which Windows lacks; upstream already runs without
        mathqa._timeouts = lambda: None   # them off the main thread, so this matches one of upstream's own modes
    return apply_edit, mathqa, st_numpy


def _run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def subset_ids():
    p = OUT / "subset.json"
    if p.exists():
        return json.loads(p.read_text())["ids"]
    rows = [json.loads(l) for l in (WORK / "data" / "math500.jsonl").read_text(encoding="utf-8").splitlines()]
    ids = sorted(random.Random(SUBSET_SEED).sample([r["id"] for r in rows], N_PROBLEMS))
    _j(p, {"seed": SUBSET_SEED, "n": N_PROBLEMS, "source": "HuggingFaceH4/MATH-500 test", "ids": ids})
    return ids


def seed_of(pid: str) -> int:
    """Fixed per problem, identical for every model: base and edited answers are paired, as in upstream."""
    return int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16)


# ------------------------------------------------------------------------------------------------ fetch-data
def fetch_data():
    from huggingface_hub import hf_hub_download
    d = WORK / "data"
    d.mkdir(parents=True, exist_ok=True)
    src = hf_hub_download("HuggingFaceH4/MATH-500", "test.jsonl", repo_type="dataset")
    rows = [json.loads(l) for l in Path(src).read_text(encoding="utf-8").splitlines() if l.strip()]
    with open(d / "math500.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"id": r["unique_id"], "problem": r["problem"], "answer": r["answer"],
                                "level": r.get("level"), "subject": r.get("subject")}, ensure_ascii=False) + "\n")
    print(f"{len(rows)} MATH-500 problems; subset of {len(subset_ids())} in {OUT / 'subset.json'}")


# ------------------------------------------------------------------------------------------------ build
def build_edited(run: str) -> Path:
    apply_edit, _, S = _upstream_code()
    import numpy as np
    out = WORK / "models" / f"Qwen3.5-0.8B-{run}"
    done = out / "edit_applied.json"
    if done.exists():
        return out
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(BASE_DIR, out, ignore=shutil.ignore_patterns(".cache"))
    edit_dir = UP8 / "runs" / run / "edit"
    man = json.loads((edit_dir / "manifest.json").read_text())
    z = np.load(edit_dir / "edit.npz")
    idx = json.loads((BASE_DIR / "model.safetensors.index.json").read_text())["weight_map"]
    by_shard = {}
    for i, t in enumerate(man["tensors"]):
        by_shard.setdefault(idx[t["name"]], []).append((i, t))
    report = []
    for shard, items in by_shard.items():
        tensors = S.load(str(BASE_DIR / shard))
        for i, t in items:
            dt, b = tensors[t["name"]]
            assert dt == "BF16" and list(b.shape) == t["shape"]
            assert hashlib.sha256(np.ascontiguousarray(b).tobytes()).hexdigest() == t["base_sha256"], \
                f"{t['name']}: base differs from the one the edit was made on"
            e = apply_edit.rebuild(b, t, z, i)
            assert hashlib.sha256(np.ascontiguousarray(e).tobytes()).hexdigest() == t["edited_sha256"], \
                f"{t['name']}: rebuilt tensor does not match upstream's evaluated checkpoint"
            tensors[t["name"]] = ("BF16", e)
            report.append({"tensor": t["name"], "changed_entries": t["changed_entries"], "hash_ok": True})
            print(f"  {t['name']}: rebuilt, hash matches upstream's evaluated checkpoint")
        head, _ = S.read_header(str(BASE_DIR / shard))
        S.save(str(out / shard), tensors, head.get("__metadata__"))
    _j(done, {"upstream_run": run, "base_revision": BASE_REV, "tensors": report})
    return out


def gguf_path(model: str, quant: str) -> Path:
    return GGUF / f"qwen3.5-0.8b-{model}-{quant}.gguf"


def build():
    if not (BASE_DIR / "config.json").exists():
        raise SystemExit("base model missing: see README (work/ setup)")
    dirs = {"base": BASE_DIR, **{r: build_edited(r) for r in EDITS}}
    GGUF.mkdir(parents=True, exist_ok=True)
    quantize = LLAMA_BIN / ("llama-quantize.exe" if os.name == "nt" else "llama-quantize")
    for name, d in dirs.items():
        f16 = gguf_path(name, "F16")
        if not f16.exists():
            _run([sys.executable, LLAMA_SRC / "convert_hf_to_gguf.py", d, "--outtype", "f16", "--outfile", f16])
        for q in QUANTS[1:]:
            out = gguf_path(name, q)
            if not out.exists():
                _run([quantize, f16, out, q], stdout=subprocess.DEVNULL)
    sizes = {p.name: p.stat().st_size for p in sorted(GGUF.glob("*.gguf"))}
    _j(OUT / "build.json", {"llama_cpp": LLAMA_TAG, "base_revision": BASE_REV, "edits": EDITS, "quants": QUANTS,
                            "gguf_bytes": sizes, "built": P.now()})
    print(json.dumps(sizes, indent=1))


# ------------------------------------------------------------------------------------------------ check-grader
def check_grader():
    """Re-grade upstream's own saved first samples (MATH-500, unedited and p50c) with our import of their grader."""
    _, Q, _ = _upstream_code()
    res = {}
    for run in ("unedited", "p50c"):
        agree = total = 0
        for part in sorted((UP8 / "eval" / run / "parts").glob("math500_*")):
            per = {r["id"]: r["correct"][0] for r in json.loads((part / "math500_per_problem.json").read_text())}
            gold = {json.loads(l)["id"]: json.loads(l)["answer"]
                    for l in (WORK / "data" / "math500.jsonl").read_text(encoding="utf-8").splitlines()}
            with gzip.open(part / "math500_first_samples.jsonl.gz", "rt", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    ours = Q.is_correct(Q.extract(r["text"])[0], gold[r["id"]])
                    agree += int(ours) == per[r["id"]]
                    total += 1
        res[run] = {"agree": agree, "total": total}
        print(f"  {run}: our grade == upstream's on {agree}/{total} saved sample texts")
    res["passed"] = all(v["agree"] == v["total"] for v in res.values() if isinstance(v, dict))
    _j(OUT / "grader_check.json", {**res, "when": P.now()})
    return res["passed"]


# ------------------------------------------------------------------------------------------------ eval
def _server(gguf: Path):
    exe = LLAMA_BIN / ("llama-server.exe" if os.name == "nt" else "llama-server")
    cmd = [str(exe), "-m", str(gguf), "-ngl", "99", "-c", str(PARALLEL * CTX_PER_SLOT), "-np", str(PARALLEL),
           "--port", str(PORT), "--no-webui", "-fa", "on", "--seed", "0"]
    log = open(OUT / "server.log", "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    import requests
    for _ in range(300):
        try:
            if requests.get(f"http://127.0.0.1:{PORT}/health", timeout=2).status_code == 200:
                return proc, cmd
        except Exception:
            pass
        if proc.poll() is not None:
            raise RuntimeError("llama-server exited; see runs/exp8b/server.log")
        time.sleep(1)
    proc.kill()
    raise RuntimeError("llama-server did not become ready")


def gen_file(cond: str) -> Path:
    """Full generations (large, plain) live in work/; a gzipped copy is kept in runs/ as the record."""
    return WORK / "exp8b" / cond / "generations.jsonl"


def tail_dup8(text: str, window: int = 1000) -> float:
    """Share of word 8-grams in the last `window` words that already occurred earlier in that window (loop signal)."""
    w = text.split()[-window:]
    seen, dup, n = set(), 0, 0
    for i in range(len(w) - 7):
        g = tuple(w[i:i + 8])
        dup += g in seen
        seen.add(g)
        n += 1
    return round(dup / n, 3) if n else 0.0


def eval_condition(cond: str, limit: int | None = None):
    import requests
    from transformers import AutoTokenizer
    _, Q, _ = _upstream_code()
    model, quant = cond.split("-", 1)
    gguf = gguf_path(model, quant)
    assert gguf.exists(), f"{gguf} missing: run `wsp 8b build`"
    tok = AutoTokenizer.from_pretrained(str(BASE_DIR))
    template = (UP8 / "base_model" / "Qwen3.5-0.8B-text" / "chat_template.jinja").read_text(encoding="utf-8")  # the one upstream used
    rows = {json.loads(l)["id"]: json.loads(l) for l in (WORK / "data" / "math500.jsonl").read_text(encoding="utf-8").splitlines()}
    ids = subset_ids()[:limit] if limit else subset_ids()
    odir = OUT / cond
    odir.mkdir(parents=True, exist_ok=True)
    gen_path = gen_file(cond)
    gen_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if gen_path.exists():
        for l in gen_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            done[r["id"]] = r
    todo = [i for i in ids if i not in done]
    print(f"[{cond}] {len(todo)} of {len(ids)} problems to generate", flush=True)
    if todo:
        proc, cmd = _server(gguf)
        t0 = time.time()

        def one(pid):
            r = rows[pid]
            prompt = tok.apply_chat_template([{"role": "user", "content": Q.build_prompt(r["problem"])}], tokenize=False,
                                             add_generation_prompt=True, enable_thinking=True,
                                             chat_template=template)
            body = {"prompt": prompt, **SAMPLING, "seed": seed_of(pid), "cache_prompt": False}
            js = requests.post(f"http://127.0.0.1:{PORT}/completion", json=body, timeout=7200).json()
            text = js["content"]
            pred = Q.extract(text)[0]
            return {"id": pid, "answer": r["answer"], "pred": pred, "correct": bool(Q.is_correct(pred, r["answer"])),
                    "tokens": js.get("tokens_predicted"), "stop_type": js.get("stop_type"),
                    "cut": js.get("stop_type") == "limit", "tail_dup8": tail_dup8(text),
                    "closed_thinking": "</think>" in text, "text": text}

        try:
            with cf.ThreadPoolExecutor(PARALLEL) as ex, open(gen_path, "a", encoding="utf-8") as f:
                for k, res in enumerate(ex.map(one, todo), 1):
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
                    f.flush()
                    if k % 10 == 0 or k == len(todo):
                        print(f"  {k}/{len(todo)} done, {time.time() - t0:.0f}s", flush=True)
        finally:
            proc.terminate()
            proc.wait(timeout=60)
        _j(odir / "engine.json", {"llama_cpp": LLAMA_TAG, "cmd": [Path(cmd[0]).name, *cmd[1:]], "sampling": SAMPLING,
                                  "parallel": PARALLEL, "seconds": round(time.time() - t0), "gguf": gguf.name,
                                  "gguf_sha256_head": hashlib.sha256(gguf.read_bytes()[:1 << 24]).hexdigest()})
    summarize(cond)


def summarize(cond: str):
    rs = [json.loads(l) for l in gen_file(cond).read_text(encoding="utf-8").splitlines()]
    ids = set(subset_ids())
    rs = [r for r in rs if r["id"] in ids]
    n = len(rs)
    s = {"condition": cond, "n": n, "acc": sum(r["correct"] for r in rs) / n, "cut_share": sum(r["cut"] for r in rs) / n,
         "mean_tokens": sum(r["tokens"] or 0 for r in rs) / n,
         "closed_thinking": sum(r["closed_thinking"] for r in rs) / n,
         "loop_tail_dup8_cut": (sum(r["tail_dup8"] for r in rs if r["cut"]) / max(1, sum(r["cut"] for r in rs)))}
    _j(OUT / cond / "summary.json", s)
    # the texts are the raw evidence but large: keep them gzipped in git, the plain file only in work/
    with gzip.open(OUT / cond / "generations.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(gen_file(cond).read_text(encoding="utf-8"))
    print(f"  [{cond}] acc {s['acc']:.1%}  cut {s['cut_share']:.1%}  mean tokens {s['mean_tokens']:.0f}", flush=True)
    return s


# ------------------------------------------------------------------------------------------------ report
def upstream_on_subset():
    """Upstream's vLLM results (4 samples per problem) restricted to our subset: the reference our F16 rows check."""
    ids = set(subset_ids())
    out = {}
    for run in ("unedited", "p50c"):
        acc = []
        for part in (UP8 / "eval" / run / "parts").glob("math500_*"):
            for r in json.loads((part / "math500_per_problem.json").read_text()):
                if r["id"] in ids:
                    acc.append(sum(r["correct"]) / len(r["correct"]))
        merged = json.loads((UP8 / "eval" / run / "merged.json").read_text())["math500"]
        out[run] = {"acc_subset": sum(acc) / len(acc), "n": len(acc), "acc_all500": merged["acc"],
                    "cut_share_all500": merged["cut_share"]}
    return out


def report():
    import math
    rows = []
    for q in QUANTS:
        b, e = gen_file(f"base-{q}"), gen_file(f"p50c-{q}")
        if not (b.exists() and e.exists()):
            continue
        rb = {json.loads(l)["id"]: json.loads(l) for l in b.read_text(encoding="utf-8").splitlines()}
        re_ = {json.loads(l)["id"]: json.loads(l) for l in e.read_text(encoding="utf-8").splitlines()}
        ids = [i for i in subset_ids() if i in rb and i in re_]
        d = [int(re_[i]["correct"]) - int(rb[i]["correct"]) for i in ids]
        n = len(d)
        mean = sum(d) / n
        se = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1) / n) if n > 1 else 0
        rows.append({"quant": q, "n": n,
                     "base": summarize(f"base-{q}"), "edited": summarize(f"p50c-{q}"),
                     "paired_gain": mean, "paired_se": se,
                     "rescues": sum(x == 1 for x in d), "losses": sum(x == -1 for x in d)})
    build = json.loads((OUT / "build.json").read_text()) if (OUT / "build.json").exists() else {}
    _j(OUT / "summary.json", {"built": P.now(), "subset": json.loads((OUT / "subset.json").read_text()),
                              "sampling": SAMPLING, "llama_cpp": LLAMA_TAG, "upstream_vllm": upstream_on_subset(),
                              "gguf_bytes": build.get("gguf_bytes"), "rows": rows,
                              "grader_check": json.loads((OUT / "grader_check.json").read_text())
                              if (OUT / "grader_check.json").exists() else None})
    for r in rows:
        print(f"  {r['quant']:7} base {r['base']['acc']:.0%} (cut {r['base']['cut_share']:.0%})  "
              f"edited {r['edited']['acc']:.0%} (cut {r['edited']['cut_share']:.0%})  "
              f"gain {r['paired_gain']:+.0%} ± {r['paired_se']:.0%}")


def main(args):
    cmd = args[0] if args else "help"
    if cmd == "fetch-data":
        fetch_data()
    elif cmd == "build":
        build()
    elif cmd == "check-grader":
        sys.exit(0 if check_grader() else 1)
    elif cmd == "eval":
        conds = [f"{m}-{q}" for q in QUANTS for m in ("base", *EDITS)] if args[1:] == ["all"] else \
            [a for a in args[1:] if not a.startswith("--")]
        limit = next((int(a.split("=")[1]) for a in args if a.startswith("--limit=")), None)
        for c in conds:
            eval_condition(c, limit)
    elif cmd == "report":
        report()
    else:
        print(__doc__)
