"""Model eksak CVRP (two-index, MTZ load-based) dengan solver HiGHS (scipy.optimize.milp).
Dipakai untuk memverifikasi optimalitas pada kasus kecil (13 SPBU)."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def solve_cvrp_exact(D: np.ndarray, q: np.ndarray, Q: float, max_vehicles: Optional[int] = None,
                     time_limit: float = 600.0) -> Tuple[float, List[List[int]], dict]:
    n = D.shape[0] - 1
    N = n + 1
    arcs = [(i, j) for i in range(N) for j in range(N) if i != j]
    A = len(arcs)
    nv = A + N  # x_ij + u_i (muatan kumulatif)
    c = np.zeros(nv)
    for k, (i, j) in enumerate(arcs):
        c[k] = D[i, j]
    idx = {a: k for k, a in enumerate(arcs)}
    rows, lb, ub = [], [], []
    M = lil_matrix((2 * n + 2 + n * n, nv))
    r = 0
    for i in range(1, N):  # keluar tepat satu
        for j in range(N):
            if i != j: M[r, idx[(i, j)]] = 1
        lb.append(1); ub.append(1); r += 1
    for j in range(1, N):  # masuk tepat satu
        for i in range(N):
            if i != j: M[r, idx[(i, j)]] = 1
        lb.append(1); ub.append(1); r += 1
    for j in range(1, N):  # depot out = depot in
        M[r, idx[(0, j)]] = 1; M[r, idx[(j, 0)]] = -1
    lb.append(0); ub.append(0); r += 1
    for j in range(1, N):
        M[r, idx[(0, j)]] = 1
    lb.append(int(np.ceil(q[1:].sum() / Q))); ub.append(max_vehicles or n); r += 1
    # MTZ: u_j >= u_i + q_j - Q(1 - x_ij)  ->  u_i - u_j + Q x_ij <= Q - q_j
    for i in range(1, N):
        for j in range(1, N):
            if i == j: continue
            M[r, A + i] = 1; M[r, A + j] = -1; M[r, idx[(i, j)]] = Q
            lb.append(-np.inf); ub.append(Q - q[j]); r += 1
    M = M[:r]
    lo = np.zeros(nv); hi = np.ones(nv)
    for i in range(1, N):
        lo[A + i] = q[i]; hi[A + i] = Q
    lo[A] = 0; hi[A] = 0
    integ = np.zeros(nv); integ[:A] = 1
    res = milp(c, constraints=LinearConstraint(M.tocsr(), lb, ub), integrality=integ,
               bounds=Bounds(lo, hi), options=dict(time_limit=time_limit, disp=False, mip_rel_gap=0))
    if res.x is None:
        return float("nan"), [], dict(status=res.status, message=res.message)
    x = res.x[:A]
    succ = {i: j for k, (i, j) in enumerate(arcs) if x[k] > 0.5}
    starts = [j for k, (i, j) in enumerate(arcs) if i == 0 and x[k] > 0.5]
    routes = []
    for s in starts:
        r_ = [s]; cur = s
        while succ[cur] != 0:
            cur = succ[cur]; r_.append(cur)
        routes.append(r_)
    return float(res.fun), routes, dict(status=res.status, message=res.message,
                                         mip_gap=getattr(res, "mip_gap", None))
