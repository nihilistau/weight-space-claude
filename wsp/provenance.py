"""Provenance: record exactly what produced a result, so anyone can tell what they are looking at."""
from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
UPSTREAM_PIN = "4d09ba6d6a7e891dd8063974dfe81b3d78e3494f"


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _git(*args, cwd=ROOT) -> str:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


def git_state() -> dict:
    dirty = _git("status", "--porcelain", "--untracked-files=no", "--", ".", ":!runs", ":!docs/data")
    return {"commit": _git("rev-parse", "HEAD"), "dirty": bool(dirty), "dirty_files": dirty.splitlines()[:20]}


def upstream_state() -> dict:
    head = _git("rev-parse", "HEAD", cwd=UPSTREAM)
    dirty = _git("status", "--porcelain", cwd=UPSTREAM)
    return {"commit": head, "pinned": UPSTREAM_PIN, "matches_pin": head == UPSTREAM_PIN, "dirty": bool(dirty)}


def claude_version(exe: str) -> str:
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"unknown ({e})"


def find_claude() -> str:
    return shutil.which("claude") or "claude"


def environment() -> dict:
    import numpy
    try:
        from importlib.metadata import version
        minatar = version("minatar")
    except Exception:
        minatar = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.node(),
            "numpy": numpy.__version__, "minatar": minatar}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
