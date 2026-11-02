"""Scorers for the open-answer experiments (1 and 2).

Upstream maps the answer's `Game:` / `Images:` line to a label by keywords; the answer key is read
only here, never by the runner. `wsp validate` re-scores Astra's answers with these functions and
checks they agree with upstream's eval/scores.json.
"""
from __future__ import annotations

import re

KEYWORDS = {
    "exp1": {
        "breakout": ["breakout", "brick"],
        "pong": ["pong"],
        "pacman": ["pac-man", "pacman", "pac man"],
        "freeway": ["freeway", "frogger", "road-crossing", "road crossing", "traffic-crossing", "traffic crossing"],
    },
    "exp2": {
        "circle": ["circle", "disc", "disk", "round", "oval", "ring"],
        "square": ["square", "rectangle", "rectangular", "box"],
        "triangle": ["triangle", "triangular", "pyramid", "wedge"],
    },
}
FIELD = {"exp1": "Game", "exp2": "Images"}
_NAMES = r"(Observations|Reasoning|Game|Description|Images|Example|Confidence)"
HEADERS = [
    re.compile(r"^\s*#+\s*\**" + _NAMES + r"\**\s*:?\s*(.*)$", re.I),          # ## Game
    re.compile(r"^\s*\*\*" + _NAMES + r"\s*:?\s*\*\*\s*:?\s*(.*)$", re.I),      # **Game:** / **Game**:
    re.compile(r"^\s*\*\*" + _NAMES + r"\s*:\s*(.*?)\**\s*$", re.I),           # **Confidence: 77%**
    re.compile(r"^\s*" + _NAMES + r"\s*:\s*(.*)$", re.I),                      # Game:
]


def fields(answer: str) -> dict[str, str]:
    """Split a reply into its 'Name: value' sections (handles '## Game', '**Game:**', 'Game:')."""
    out, cur = {}, None
    for line in answer.splitlines():
        m = next((h.match(line) for h in HEADERS if h.match(line)), None)
        if m:
            cur = m.group(1).capitalize()
            out[cur] = m.group(2).strip()
        elif cur:
            out[cur] = (out[cur] + "\n" + line).strip()
    return out


def map_label(exp: str, text: str) -> str | None:
    t = text.lower()
    best = None
    for label, kws in KEYWORDS[exp].items():
        for kw in kws:
            i = t.find(kw)
            if i >= 0 and (best is None or i < best[0]):
                best = (i, label)
    return best[1] if best else None


def confidence(f: dict) -> int | None:
    m = re.search(r"(\d{1,3})\s*%", f.get("Confidence", ""))
    return int(m.group(1)) if m else None


def example_grid(f: dict) -> list[str] | None:
    """Exp2: the 12x12 '#'/'.' drawing, if present."""
    rows = [r.strip().strip("`") for r in f.get("Example", "").splitlines()]
    rows = [r for r in rows if r and set(r) <= {"#", "."}]
    return rows[:12] if len(rows) >= 8 else None


def fill_ratio(grid: list[str] | None) -> float | None:
    """Share of cells that are '#' between the first and last '#' of each row.
    ~1.0 = filled shape, low = outline. Upstream's notable finding: Astra drew outlines,
    the models generate filled shapes."""
    if not grid:
        return None
    inside = marked = 0
    for r in grid:
        if "#" in r:
            a, b = r.index("#"), r.rindex("#")
            seg = r[a:b + 1]
            inside += len(seg)
            marked += seg.count("#")
    return round(marked / inside, 3) if inside else None


def score(exp: str, answer: str, truth: str) -> dict:
    f = fields(answer)
    line = f.get(FIELD[exp], "")
    guess = map_label(exp, line.split("\n\n")[0])
    out = {"true": truth, "guess": guess, "correct": guess == truth,
           "answer_line": line.split("\n")[0][:300], "confidence": confidence(f)}
    if exp == "exp2":
        g = example_grid(f)
        out["example"] = g
        out["fill_ratio"] = fill_ratio(g)
    return out
