"""Scores a 600-32-32-6 tanh policy on MinAtar 1.0.15, the way Experiment 5 describes it.

Protocol (exp5 README / prompt): mean score over 1,000 episodes, actions sampled from the softmax
of the logits, sticky actions 0.1, episodes cut at 10,000 steps. The 6 input channels are built
from the game's own channels by the mapping written in each prompt; we parse that mapping out of
the prompt text so the prompt stays the single source of truth.

Upstream did not publish this script either. `wsp validate` checks it by re-scoring Astra's
published networks and comparing with the published means.
"""
from __future__ import annotations

import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np

MAPPING_LINE = re.compile(r"How the 6 channels are built.*?:(.*?)A cell is 1", re.S)
GAMES = {"breakout": "breakout", "seaquest": "seaquest", "asterix": "asterix"}


def parse_mapping(prompt: str) -> list[list[str]]:
    """'channel 0 (player) <- sub_front, sub_back; ...' -> [[sub_front, sub_back], ...]"""
    body = MAPPING_LINE.search(prompt).group(1)
    out = [[] for _ in range(6)]
    for part in body.split(";"):
        m = re.search(r"channel (\d) \([^)]*\) <- (.+)", part.strip().rstrip("."))
        if m:
            srcs = [s.strip() for s in m.group(2).split(",")]
            out[int(m.group(1))] = [s for s in srcs if s != "nothing"]
    return out


def _forward(t, x):
    h1 = np.tanh(x @ t["W1"] + t["b1"])
    h2 = np.tanh(h1 @ t["W2"] + t["b2"])
    return h2 @ t["W3"] + t["b3"]


def _worker(args):
    game, tensors, mapping, n_episodes, seed, max_steps, n_par = args
    from minatar import Environment

    rng = np.random.default_rng(seed)
    t = {k: v.astype(np.float64) for k, v in tensors.items()}
    scores, lengths = [], []
    started = 0

    def new_env():
        nonlocal started
        started += 1
        e = Environment(GAMES[game], sticky_action_prob=0.1)
        e.random = np.random.RandomState(int(rng.integers(2**31)))  # sticky-action RNG
        e.env.random = np.random.RandomState(int(rng.integers(2**31)))  # game RNG
        e.reset()
        return e

    chans = None
    live = []
    for _ in range(min(n_par, n_episodes)):
        live.append([new_env(), 0.0, 0])
    while live:
        if chans is None:
            names = live[0][0].env.channels
            chans = [[names[s] for s in srcs] for srcs in mapping]
        obs = np.zeros((len(live), 10, 10, 6))
        for i, (e, _, _) in enumerate(live):
            s = e.state()
            for c, idx in enumerate(chans):
                if idx:
                    obs[i, :, :, c] = s[:, :, idx].any(axis=2)
        logits = _forward(t, obs.reshape(len(live), 600))
        logits -= logits.max(axis=1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(axis=1, keepdims=True)
        u = rng.random((len(live), 1))
        acts = (p.cumsum(axis=1) < u).sum(axis=1).clip(0, 5)
        nxt = []
        for (e, score, steps), a in zip(live, acts):
            r, done = e.act(int(a))
            score += r
            steps += 1
            if done or steps >= max_steps:
                scores.append(score)
                lengths.append(steps)
                if started < n_episodes:
                    nxt.append([new_env(), 0.0, 0])
            else:
                nxt.append([e, score, steps])
        live = nxt
    return scores, lengths


def evaluate(game, tensors, mapping, episodes=1000, seed=0, max_steps=10_000, workers=8, n_par=32):
    per = [episodes // workers + (1 if i < episodes % workers else 0) for i in range(workers)]
    jobs = [(game, tensors, mapping, n, seed * 1000 + i, max_steps, n_par) for i, n in enumerate(per) if n]
    scores, lengths = [], []
    with ProcessPoolExecutor(len(jobs)) as ex:
        for s, l in ex.map(_worker, jobs):
            scores += s
            lengths += l
    s = np.array(scores)
    return {"mean": float(s.mean()), "se": float(s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 1 else 0.0,
            "episodes": len(s), "max": float(s.max()), "mean_length": float(np.mean(lengths)),
            "seed": seed, "max_steps": max_steps, "sticky_action_prob": 0.1}
