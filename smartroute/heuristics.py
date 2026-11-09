"""Metode pembanding: Direct delivery, Nearest Neighbour, Clarke-Wright Savings."""
from __future__ import annotations

from typing import List

import numpy as np


def direct_routes(n: int) -> List[List[int]]:
    return [[i] for i in range(1, n + 1)]


def nearest_neighbor_perm(D: np.ndarray, start: int | None = None, rng=None) -> List[int]:
    n = D.shape[0] - 1
    unv = set(range(1, n + 1))
    cur = 0
    perm = []
    if start is not None:
        perm.append(start); unv.remove(start); cur = start
    while unv:
        nxt = min(unv, key=lambda j: D[cur, j])
        perm.append(nxt); unv.remove(nxt); cur = nxt
    return perm


def nearest_neighbor_routes(D: np.ndarray, q: np.ndarray, Q: float) -> List[List[int]]:
    """NN sekuensial: rute baru dibuka bila kapasitas habis."""
    n = D.shape[0] - 1
    unv = set(range(1, n + 1))
    routes = []
    while unv:
        r, load, cur = [], 0.0, 0
        while True:
            cand = [j for j in unv if load + q[j] <= Q + 1e-9]
            if not cand:
                break
            nxt = min(cand, key=lambda j: D[cur, j])
            r.append(nxt); unv.remove(nxt); load += q[nxt]; cur = nxt
        if not r:  # permintaan tunggal > Q
            j = unv.pop(); r = [j]
        routes.append(r)
    return routes


def clarke_wright(D: np.ndarray, q: np.ndarray, Q: float) -> List[List[int]]:
    """Clarke & Wright (1964) versi paralel."""
    n = D.shape[0] - 1
    route_of = {i: [i] for i in range(1, n + 1)}
    load = {i: q[i] for i in range(1, n + 1)}
    sav = []
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            sav.append((D[0, i] + D[0, j] - D[i, j], i, j))
    sav.sort(key=lambda x: -x[0])
    for s, i, j in sav:
        if s <= 0:
            break
        ri, rj = route_of[i], route_of[j]
        if ri is rj:
            continue
        if load[ri[0]] + load[rj[0]] > Q + 1e-9:
            continue
        # i dan j harus berada di ujung rute masing-masing
        if ri[-1] == i and rj[0] == j:
            new = ri + rj
        elif ri[0] == i and rj[-1] == j:
            new = rj + ri
        elif ri[0] == i and rj[0] == j:
            new = ri[::-1] + rj
        elif ri[-1] == i and rj[-1] == j:
            new = ri + rj[::-1]
        else:
            continue
        L = load[ri[0]] + load[rj[0]]
        for c in new:
            route_of[c] = new
        load[new[0]] = L
    seen, routes = set(), []
    for i in range(1, n + 1):
        r = route_of[i]
        if id(r) not in seen:
            seen.add(id(r)); routes.append(r)
    return routes


def routes_distance(D: np.ndarray, routes: List[List[int]]) -> float:
    tot = 0.0
    for r in routes:
        prev = 0
        for c in r:
            tot += D[prev, c]; prev = c
        tot += D[prev, 0]
    return float(tot)
