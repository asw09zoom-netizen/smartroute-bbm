"""Hybrid Metaheuristic GA-SA-RL.

GA  : populasi N, inisialisasi 60% greedy (NN + perturbasi) / 40% acak, seleksi
      turnamen (k=5), Order Crossover (OX), mutasi inversi/swap/relocate dengan
      laju adaptif, elitisme.
SA  : penyempurnaan lokal solusi terbaik GA, P = exp(-dE/T), T = T0 * alpha^t.
RL  : Q-Learning memilih operator ketetanggaan SA secara adaptif
      Q(s,a) <- Q(s,a) + a_rl [R + gamma max Q(s',.) - Q(s,a)].
Varian untuk uji ablasi: "GA", "GA-SA", "GA-SA-RL".
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from .heuristics import nearest_neighbor_perm
from .model import Evaluator, Solution

OPERATORS = ["2opt", "relocate", "swap", "oropt", "seg_swap"]


@dataclass
class HybridConfig:
    variant: str = "GA-SA-RL"     # "GA", "GA-SA", "GA-SA-RL"
    pop_size: int = 100
    generations: int = 200
    pc: float = 0.85
    pm: float = 0.10
    tournament: int = 5
    greedy_frac: float = 0.60
    elite: int = 2
    diversity_eps: float = 0.05
    sa_T0: float = 1000.0
    sa_alpha: float = 0.995
    sa_iters: int = 5000
    sa_Tmin: float = 0.01
    rl_alpha: float = 0.10
    rl_gamma: float = 0.90
    rl_eps: float = 0.10
    seed: Optional[int] = None
    time_limit: Optional[float] = None   # detik (opsional)
    sa_scale: float = 1.0e6              # E = sa_scale * F / F_GA; memburuk 0,1% diterima p=e^-1 pada T0=1000
    sa_restart: int = 0                  # kembali ke solusi terbaik bila stagnasi >= nilai ini (0 = nonaktif)
    equal_budget: bool = True            # varian GA mendapat generasi tambahan setara iterasi SA


@dataclass
class RunResult:
    best: Solution
    history: List[float]          # fitness terbaik per generasi/iterasi
    phase: List[str]
    runtime: float
    evals: int
    op_counts: Dict[str, int] = field(default_factory=dict)
    op_success: Dict[str, int] = field(default_factory=dict)
    q_table: Optional[np.ndarray] = None
    ga_best: float = float("nan")


# ---------------------------------------------------------------------------
# Operator permutasi
# ---------------------------------------------------------------------------
def op_apply(perm: List[int], op: str, rng: random.Random) -> List[int]:
    n = len(perm)
    if n < 3:
        return perm[:]
    p = perm[:]
    if op == "2opt":
        i, j = sorted(rng.sample(range(n), 2))
        p[i:j + 1] = p[i:j + 1][::-1]
    elif op == "relocate":
        i, j = rng.sample(range(n), 2)
        c = p.pop(i); p.insert(j, c)
    elif op == "swap":
        i, j = rng.sample(range(n), 2)
        p[i], p[j] = p[j], p[i]
    elif op == "oropt":
        L = rng.randint(2, min(3, n - 1))
        i = rng.randrange(0, n - L + 1)
        seg = p[i:i + L]; del p[i:i + L]
        j = rng.randrange(0, len(p) + 1)
        if rng.random() < 0.5:
            seg = seg[::-1]
        p[j:j] = seg
    elif op == "seg_swap":  # pertukaran dua segmen (gerakan tipe 3-opt)
        a, b, c, d = sorted(rng.sample(range(n + 1), 4)) if n >= 4 else (0, 1, 1, 2)
        p = p[:a] + p[c:d] + p[b:c] + p[a:b] + p[d:]
    return p


def ox_crossover(p1: List[int], p2: List[int], rng: random.Random) -> List[int]:
    n = len(p1)
    a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n
    child[a:b + 1] = p1[a:b + 1]
    used = set(p1[a:b + 1])
    fill = [g for g in p2[b + 1:] + p2[:b + 1] if g not in used]
    idx = 0
    for k in list(range(b + 1, n)) + list(range(0, a)):
        child[k] = fill[idx]; idx += 1
    return child


# ---------------------------------------------------------------------------
class HybridGASARL:
    def __init__(self, ev: Evaluator, cfg: HybridConfig, init_perms: Optional[List[List[int]]] = None,
                 progress: Optional[Callable[[str, int, int, float], None]] = None):
        self.ev = ev
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.np_rng = np.random.default_rng(cfg.seed)
        self.cache: Dict[tuple, float] = {}
        self.init_perms = init_perms or []
        self.progress = progress
        self.customers = list(range(1, ev.n + 1))

    def fit(self, perm: Sequence[int]) -> float:
        key = tuple(perm)
        f = self.cache.get(key)
        if f is None:
            f = self.ev.fitness(perm)
            if len(self.cache) < 500_000:
                self.cache[key] = f
        return f

    # -- GA -------------------------------------------------------------------
    def _init_population(self) -> List[List[int]]:
        N = self.cfg.pop_size
        pop = [list(p) for p in self.init_perms][:N]
        n_greedy = int(N * self.cfg.greedy_frac)
        D = self.ev.D
        while len(pop) < n_greedy:
            start = self.rng.choice(self.customers)
            p = nearest_neighbor_perm(D, start=start)
            for _ in range(self.rng.randint(0, 2)):
                p = op_apply(p, self.rng.choice(["swap", "2opt"]), self.rng)
            pop.append(p)
        while len(pop) < N:
            p = self.customers[:]
            self.rng.shuffle(p)
            pop.append(p)
        return pop

    def _tournament(self, pop, fits):
        idx = self.rng.sample(range(len(pop)), min(self.cfg.tournament, len(pop)))
        return pop[min(idx, key=lambda i: fits[i])]

    def run_ga(self, generations: int, t_start: float, history: List[float], phase: List[str]):
        cfg = self.cfg
        pop = self._init_population()
        fits = [self.fit(p) for p in pop]
        best_i = int(np.argmin(fits))
        best, best_f = pop[best_i][:], fits[best_i]
        for g in range(generations):
            if cfg.time_limit and time.time() - t_start > cfg.time_limit * 0.7:
                break
            # laju mutasi adaptif berdasarkan keragaman populasi
            fa = np.array(fits)
            div = float(fa.std() / (abs(fa.mean()) + 1e-12))
            pm = min(0.5, cfg.pm * 3) if div < cfg.diversity_eps else cfg.pm
            order = np.argsort(fits)
            new_pop = [pop[i][:] for i in order[:cfg.elite]]
            while len(new_pop) < cfg.pop_size:
                p1 = self._tournament(pop, fits)
                p2 = self._tournament(pop, fits)
                if self.rng.random() < cfg.pc:
                    c = ox_crossover(p1, p2, self.rng)
                else:
                    c = p1[:]
                if self.rng.random() < pm:
                    c = op_apply(c, self.rng.choice(["2opt", "swap", "relocate"]), self.rng)
                new_pop.append(c)
            pop = new_pop
            fits = [self.fit(p) for p in pop]
            bi = int(np.argmin(fits))
            if fits[bi] < best_f:
                best, best_f = pop[bi][:], fits[bi]
            history.append(best_f); phase.append("GA")
            if self.progress and (g % 5 == 0 or g == generations - 1):
                self.progress("GA", g + 1, generations, best_f)
        return best, best_f

    # -- SA (+RL) -------------------------------------------------------------
    def run_sa(self, start: List[int], start_f: float, use_rl: bool, t_start: float,
               history: List[float], phase: List[str], op_counts, op_succ):
        cfg = self.cfg
        cur, cur_f = start[:], start_f
        best, best_f = start[:], start_f
        scale = cfg.sa_scale / max(abs(start_f), 1e-12)   # energi ternormalisasi E = sa_scale * F / F_GA
        T = cfg.sa_T0
        nA = len(OPERATORS)
        Q = np.zeros((3 * nA, nA))
        last_a = 0
        stagn = 0

        def state():
            b = 0 if stagn < 50 else (1 if stagn < 200 else 2)
            return b * nA + last_a

        s = state()
        for it in range(cfg.sa_iters):
            if T < cfg.sa_Tmin:
                T = cfg.sa_Tmin
            if cfg.time_limit and time.time() - t_start > cfg.time_limit:
                break
            if use_rl:
                eps = max(0.02, cfg.rl_eps * (1 - it / cfg.sa_iters))
                a = self.rng.randrange(nA) if self.rng.random() < eps else int(np.argmax(Q[s]))
            else:
                a = self.rng.randrange(nA)
            op = OPERATORS[a]
            op_counts[op] = op_counts.get(op, 0) + 1
            cand = op_apply(cur, op, self.rng)
            f = self.fit(cand)
            dE = (f - cur_f) * scale
            reward = -0.05
            if dE < 0 or self.rng.random() < math.exp(-dE / T):
                if f < cur_f - 1e-12:
                    reward = (cur_f - f) * scale  # perbaikan relatif
                    op_succ[op] = op_succ.get(op, 0) + 1
                else:
                    reward = 0.0
                cur, cur_f = cand, f
            if cur_f < best_f - 1e-12:
                best, best_f = cur[:], cur_f
                reward += 1.0
                stagn = 0
            else:
                stagn += 1
                if cfg.sa_restart and stagn % cfg.sa_restart == 0:
                    cur, cur_f = best[:], best_f
            last_a = a
            s2 = state()
            if use_rl:
                Q[s, a] += cfg.rl_alpha * (reward + cfg.rl_gamma * Q[s2].max() - Q[s, a])
            s = s2
            T *= cfg.sa_alpha
            if it % 50 == 0 or it == cfg.sa_iters - 1:
                history.append(best_f); phase.append("SA-RL" if use_rl else "SA")
            if self.progress and it % 250 == 0:
                self.progress("SA-RL" if use_rl else "SA", it, cfg.sa_iters, best_f)
        return best, best_f, Q

    # -- main -------------------------------------------------------------------
    def run(self) -> RunResult:
        cfg = self.cfg
        t0 = time.time()
        self.ev.n_evals = 0
        history: List[float] = []
        phase: List[str] = []
        op_counts: Dict[str, int] = {}
        op_succ: Dict[str, int] = {}
        gens = cfg.generations
        if cfg.variant == "GA" and cfg.equal_budget:
            gens += int(math.ceil(cfg.sa_iters / max(1, cfg.pop_size - cfg.elite)))
        best, best_f = self.run_ga(gens, t0, history, phase)
        ga_best = best_f
        Q = None
        if cfg.variant in ("GA-SA", "GA-SA-RL"):
            best, best_f, Q = self.run_sa(best, best_f, cfg.variant == "GA-SA-RL", t0, history, phase,
                                          op_counts, op_succ)
        sol = self.ev.evaluate(best)
        return RunResult(sol, history, phase, time.time() - t0, self.ev.n_evals, op_counts, op_succ,
                         Q if cfg.variant == "GA-SA-RL" else None, ga_best)


def solve(ev: Evaluator, cfg: Optional[HybridConfig] = None, **kw) -> RunResult:
    cfg = cfg or HybridConfig(**kw)
    return HybridGASARL(ev, cfg).run()
