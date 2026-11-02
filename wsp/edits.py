"""Reader for the `edits` mini-language used in Experiment 5.

The language is defined in the upstream prompt (exp5 message.txt, "HOW TO WRITE THE WEIGHTS").
Upstream did not publish their reader, so this is a re-implementation. It is validated by
`wsp validate`: reading Astra's published replies must give exactly the published hand.npz.

Rules (from the prompt):
- only the LAST ```edits block of the reply is read
- one statement per line, '#' starts a comment, a long list may continue over the next lines
- tensors W1 b1 W2 b2 W3 b3; ops  =  *=  +=  -=
- indices: ints, a:b (half-open), a:b:s, ':'; values: number or (nested) list, |v| <= 1e6
- statements apply in order; a statement that cannot be read is skipped, the rest still apply
- every weight starts at 0
"""
from __future__ import annotations

import ast
import re

import numpy as np

SHAPES = {"W1": (600, 32), "b1": (32,), "W2": (32, 32), "b2": (32,), "W3": (32, 6), "b3": (6,)}
NPZ_KEYS = {
    "W1": "actor/dense1/kernel", "b1": "actor/dense1/bias",
    "W2": "actor/dense2/kernel", "b2": "actor/dense2/bias",
    "W3": "actor/logits/kernel", "b3": "actor/logits/bias",
}
STMT = re.compile(r"^\s*(W1|b1|W2|b2|W3|b3)\s*\[([^\]]*)\]\s*(=|\*=|\+=|-=)\s*(.+?)\s*$", re.S)
BLOCK = re.compile(r"```edits[ \t]*\n(.*?)```", re.S)


def last_block(reply: str) -> str | None:
    blocks = BLOCK.findall(reply)
    if blocks:
        return blocks[-1]
    # a reply cut off by the output limit has an opening fence but no closing one
    i = reply.rfind("```edits")
    return reply[i + len("```edits"):] if i >= 0 else None


def _statements(block: str):
    """Yield (line_no, text) with comments stripped and continuation lines joined."""
    buf, start, depth = [], None, 0
    for n, raw in enumerate(block.splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() and depth == 0:
            continue
        if start is None:
            start = n
        buf.append(line.strip())
        # depth counts only list brackets on the value side; the index brackets close on one line
        depth += line.count("[") - line.count("]")
        if depth <= 0:
            yield start, " ".join(buf)
            buf, start, depth = [], None, 0
    if buf:
        yield start, " ".join(buf)


def _index(spec: str, shape):
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) != len(shape):
        raise ValueError(f"{len(parts)} indices for a {len(shape)}-D tensor")
    out = []
    for p, dim in zip(parts, shape):
        if ":" in p:
            nums = [int(x) if x.strip() else None for x in p.split(":")]
            if len(nums) > 3:
                raise ValueError(f"bad slice {p!r}")
            out.append(slice(*nums))
        else:
            i = int(p)
            if not -dim <= i < dim:
                raise ValueError(f"index {i} out of range {dim}")
            out.append(i)
    return tuple(out)


def apply_edits(reply: str):
    """Return (tensors, report). tensors maps W1..b3 to float32 arrays."""
    t = {k: np.zeros(s, dtype=np.float32) for k, s in SHAPES.items()}
    block = last_block(reply)
    report = {"block": block is not None, "cut_off": block is not None and not BLOCK.findall(reply),
              "statements": 0, "applied": 0, "entries_written": 0, "errors": [], "tensors_touched": []}
    if block is None:
        return t, report
    touched = set()
    for line_no, text in _statements(block):
        report["statements"] += 1
        try:
            m = STMT.match(text)
            if not m:
                raise ValueError("not a statement")
            name, idx, op, val = m.groups()
            idx = _index(idx, SHAPES[name])
            target = t[name][idx]
            v = np.asarray(ast.literal_eval(val), dtype=np.float64)
            if np.any(np.abs(v) > 1e6):
                raise ValueError("value above 1e6")
            if v.ndim and v.shape != np.shape(target):
                raise ValueError(f"value shape {v.shape} != target shape {np.shape(target)}")
            if op == "=":
                t[name][idx] = v
            elif op == "*=":
                t[name][idx] *= v
            elif op == "+=":
                t[name][idx] += v
            else:
                t[name][idx] -= v
            report["applied"] += 1
            report["entries_written"] += int(np.size(target))
            touched.add(name)
        except Exception as e:  # skip unreadable statements, as the prompt promises
            report["errors"].append({"line": line_no, "text": text[:200], "error": str(e)})
    report["tensors_touched"] = sorted(touched)
    report["nonzero"] = {k: int(np.count_nonzero(v)) for k, v in t.items()}
    report["nonzero_total"] = sum(report["nonzero"].values())
    report["parameters"] = sum(int(np.prod(s)) for s in SHAPES.values())
    report["max_abs"] = {k: float(np.abs(v).max()) for k, v in t.items()}
    return t, report


def save_npz(tensors, path):
    np.savez(path, **{NPZ_KEYS[k]: v for k, v in tensors.items()})


def load_npz(path):
    d = np.load(path)
    return {k: d[NPZ_KEYS[k]].astype(np.float32) for k in SHAPES}
