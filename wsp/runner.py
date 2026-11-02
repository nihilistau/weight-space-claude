"""Runs ONE tool-free turn of Claude through the Claude Code CLI and records it the way upstream did.

Upstream: `codex exec` with every tool switched off, a one-line system prompt, prompt on stdin,
raw event stream saved, every turn audited for tool use. Ours is the same idea with `claude -p`:

  --tools ""              no built-in tools (no shell, no files, no web)
  --strict-mcp-config     no MCP servers (none are passed)
  --safe-mode             no CLAUDE.md, skills, plugins, hooks, memory or other customizations
  --system-prompt TEXT    replaces Claude Code's own system prompt with upstream's one line
  --output-format stream-json --verbose   the raw event stream, saved as events.jsonl
  --no-session-persistence                nothing is kept between turns: every case is a fresh conversation

The audit then checks the stream itself: the tool list the session started with must be empty and
no message may contain a tool call. A run that fails the audit is kept but marked, never scored.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from . import provenance as P

SYSTEM_PROMPT = "Answer the user's request."  # upstream harness/instructions.md, verbatim


def build_cmd(exe: str, model: str, effort: str) -> list[str]:
    return [exe, "-p",
            "--model", model,
            "--effort", effort,
            "--tools", "",
            "--strict-mcp-config",
            "--safe-mode",
            "--system-prompt", SYSTEM_PROMPT,
            "--output-format", "stream-json", "--verbose",
            "--no-session-persistence",
            "--disable-slash-commands"]


def audit(events: list[dict]) -> dict:
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    tool_calls, block_types = [], {}
    for e in events:
        if e.get("type") in ("assistant", "user"):
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict):
                    block_types[b.get("type")] = block_types.get(b.get("type"), 0) + 1
                    if b.get("type") in ("tool_use", "server_tool_use", "tool_result"):
                        tool_calls.append(b.get("name") or b.get("type"))
    tools_offered = init.get("tools") or []
    mcp = init.get("mcp_servers") or []
    return {
        "tool_free": not tool_calls and not tools_offered and not mcp,
        "tools_offered": tools_offered, "mcp_servers": mcp, "tool_calls": tool_calls,
        "block_types": block_types,
        "model": init.get("model"), "session_id": init.get("session_id"),
        "usage": result.get("usage") or {}, "cost_usd": result.get("total_cost_usd"),
        "num_turns": result.get("num_turns"), "is_error": result.get("is_error"),
        "stop_reason": result.get("stop_reason") or result.get("subtype"),
        "duration_api_ms": result.get("duration_api_ms"),
    }


def extract(events: list[dict]) -> tuple[str, str]:
    """(final answer text, thinking text) from the event stream."""
    texts, thinking = [], []
    for e in events:
        if e.get("type") == "assistant":
            for b in (e.get("message") or {}).get("content") or []:
                if b.get("type") == "text":
                    texts.append(b.get("text", ""))
                elif b.get("type") == "thinking":
                    thinking.append(b.get("thinking", ""))
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    answer = result.get("result") or "\n".join(texts)
    return answer, "\n\n---\n\n".join(t for t in thinking if t)


def run_turn(prompt: str, out_dir: Path, *, model: str, effort: str, max_output_tokens: int | None = None,
             timeout_s: int = 3600, exe: str | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = exe or P.find_claude()
    cmd = build_cmd(exe, model, effort)
    env = dict(os.environ)
    if max_output_tokens:
        env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_output_tokens)
    # run from an empty folder so nothing in the repo can be picked up as context
    with tempfile.TemporaryDirectory(prefix="wsp-") as cwd:
        t0 = time.time()
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=cwd, env=env, timeout=timeout_s)
        wall = time.time() - t0
    (out_dir / "events.jsonl").write_text(proc.stdout, encoding="utf-8")
    (out_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    answer, thinking = extract(events)
    (out_dir / "answer.md").write_text(answer, encoding="utf-8")
    if thinking:
        (out_dir / "thinking.md").write_text(thinking, encoding="utf-8")
    record = {
        "ok": proc.returncode == 0 and bool(answer.strip()),
        "rc": proc.returncode, "wall_s": round(wall, 1), "end": P.now(),
        "requested": {"model": model, "effort": effort, "max_output_tokens": max_output_tokens},
        "prompt_sha256": P.sha256(prompt), "prompt_chars": len(prompt),
        "system_prompt": SYSTEM_PROMPT,
        "cmd": [Path(cmd[0]).name, *cmd[1:]],
        "audit": audit(events),
    }
    (out_dir / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record
