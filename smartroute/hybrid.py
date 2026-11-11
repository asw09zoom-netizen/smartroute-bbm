"""Hybrid Metaheuristic GA-SA-RL.

GA  : populasi N, inisialisasi 60% greedy (NN + perturbasi) / 40% acak, seleksi
      turnamen (k=5), Order Crossover (OX), mutasi inversi/swap/relocate dengan
      laju adaptif, elitisme.
SA  : penyempurnaan lokal solusi terbaik GA, P = exp(-dE/T), T = T0 * alpha^t.
RL  : Q-Learning memilih operator ketetanggaan SA secara adaptif
      Q(s,a) <- Q(s,a) + a_rl [R + gamma max Q(s',.) - Q(s,a)].
Varian untuk uji ablasi: "GA", "GA-SA" (operator acak seragam), "GA-SA-ALNS" (bobot adaptif
roda roulet, Ropke & Pisinger 2006) dan "GA-SA-RL" (Q-learning berkeadaan).
Operator SA: lima gerakan lokal acak, dua gerakan granular (k tetangga terdekat) dan dua
gerakan ruin-and-recreate (hapus klaster/acak lalu sisip ulang termurah).
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

OPERATORS = ["2opt", "relocate", "swap", "oropt", "seg_swap",
             "nn_relocate", "nn_2opt", "ruin_cluster", "ruin_random"]
SA_VARIANTS = ("GA-SA", "GA-SA-ALNS", "GA-SA-RL")
# skor imbalan gaya ALNS: solusi terbaik baru, perbaikan solusi kini, diterima walau memburuk, ditolak
SIGMA = (1.0, 0.4, 0.0, -0.02)


@dataclass
class HybridConfig:
    variant: str = "GA-SA-RL"     # "GA", "GA-SA", "GA-SA-RL"
    pop_size: int = 100
    generations: int = 50
    pc: float = 0.85
    pm: float = 0.10
    tournament: int = 5
    greedy_frac: float = 0.60
    elite: int = 2
    diversity_eps: float = 0.05
    sa_T0: float = 1000.0
    sa_alpha: float = 0.0                # 0 = otomatis: T turun dari T0 ke Tmin tepat di akhir iterasi
    sa_iters: int = 20000
    sa_Tmin: float = 0.01
    rl_alpha: float = 0.10
    rl_gamma: float = 0.50
    rl_eps: float = 0.15
    alns_r: float = 0.10                 # laju reaksi bobot ALNS
    alns_seg: int = 100                  # panjang segmen pembaruan bobot ALNS
    knn: int = 8                         # ukuran daftar tetangga granular
    ruin_max: float = 0.15               # porsi maksimum SPBU yang dihapus pada ruin
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
def _reinsert(p: List[int], removed: List[int], D: np.ndarray, rng: random.Random) -> List[int]:
    """Sisip ulang termurah (jarak) ke tur raksasa; depot di kedua ujung."""
    rng.shuffle(removed)
    for c in removed:
        best_j, best_d = 0, float("inf")
        prev = 0
        for j in range(len(p) + 1):
            nxt = p[j] if j < len(p) else 0
            d = D[prev, c] + D[c, nxt] - D[prev, nxt]
            if d < best_d:
                best_j, best_d = j, d
            prev = nxt
        p.insert(best_j, c)
    return p


def op_apply(perm: List[int], op: str, rng: random.Random, ctx=None) -> List[int]:
    n = len(perm)
    if n < 3:
        return perm[:]
    p = perm[:]
    if op in ("nn_relocate", "nn_2opt", "ruin_cluster", "ruin_random") and ctx is None:
        op = "relocate"
    if op == "nn_relocate":  # pindahkan c ke sebelah salah satu tetangga terdekatnya
        D, knn = ctx
        c = rng.choice(p)
        m = rng.choice(knn[c])
        p.remove(c)
        j = p.index(m) + (1 if rng.random() < 0.5 else 0)
        p.insert(j, c)
        return p
    if op == "nn_2opt":  # balik segmen agar c bersebelahan dengan tetangga terdekatnya
        D, knn = ctx
        c = rng.choice(p)
        m = rng.choice(knn[c])
        i, j = p.index(c), p.index(m)
        if i < j:
            p[i + 1:j + 1] = p[i + 1:j + 1][::-1]
        else:
            p[j:i] = p[j:i][::-1]
        return p
    if op in ("ruin_cluster", "ruin_random"):
        D, knn = ctx
        frac = getattr(rng, "ruin_max", 0.15)
        r = rng.randint(2, max(3, int(round(frac * n))))
        if op == "ruin_cluster":
            seed = rng.choice(p)
            order = np.argsort(D[seed, 1:]) + 1
            removed = [int(x) for x in order[:r]]
        else:
            removed = rng.sample(p, r)
        rem = set(removed)
        p = [x for x in p if x not in rem]
        return _reinsert(p, removed, D, rng)
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
        D = ev.D
        k = max(1, min(cfg.knn, ev.n - 1))
        knn = {c: [int(x) for x in np.argsort(D[c, 1:] + D[1:, c])[:k + 1] + 1 if int(x) != c][:k]
               for c in self.customers}
        self.ctx = (D, knn)
        self.rng.ruin_max = cfg.ruin_max

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
    def run_sa(self, start: List[int], start_f: float, mode: str, t_start: float,
               history: List[float], phase: List[str], op_counts, op_succ):
        """mode: "uniform" (GA-SA), "alns" (roda roulet adaptif), "rl" (Q-learning berkeadaan)."""
        cfg = self.cfg
        cur, cur_f = start[:], start_f
        best, best_f = start[:], start_f
        scale = cfg.sa_scale / max(abs(start_f), 1e-12)   # energi ternormalisasi E = sa_scale * F / F_GA
        T = cfg.sa_T0
        alpha = cfg.sa_alpha or (cfg.sa_Tmin / cfg.sa_T0) ** (1.0 / max(1, cfg.sa_iters))
        nA = len(OPERATORS)
        nS = 9
        Q = np.zeros((nS, nA))
        w = np.ones(nA); sc = np.zeros(nA); used = np.zeros(nA)   # ALNS
        stagn = 0
        tag = {"uniform": "SA", "alns": "SA-ALNS", "rl": "SA-RL"}[mode]

        def state(it):
            b = 0 if stagn < 50 else (1 if stagn < 300 else 2)
            ph = min(2, 3 * it // max(1, cfg.sa_iters))
            return 3 * b + ph

        s = state(0)
        for it in range(cfg.sa_iters):
            if T < cfg.sa_Tmin:
                T = cfg.sa_Tmin
            if cfg.time_limit and time.time() - t_start > cfg.time_limit:
                break
            if mode == "rl":
                eps = cfg.rl_eps
                a = self.rng.randrange(nA) if self.rng.random() < eps else int(np.argmax(Q[s]))
            elif mode == "alns":
                a = self.rng.choices(range(nA), weights=w)[0]
            else:
                a = self.rng.randrange(nA)
            op = OPERATORS[a]
            op_counts[op] = op_counts.get(op, 0) + 1
            cand = op_apply(cur, op, self.rng, self.ctx)
            f = self.fit(cand)
            dE = (f - cur_f) * scale
            reward = SIGMA[3]
            if dE < 0 or self.rng.random() < math.exp(-dE / T):
                if f < cur_f - 1e-12:
                    reward = SIGMA[1]
                    op_succ[op] = op_succ.get(op, 0) + 1
                elif f > cur_f + 1e-12:
                    reward = SIGMA[2]
                cur, cur_f = cand, f
            if cur_f < best_f - 1e-12:
                best, best_f = cur[:], cur_f
                reward = SIGMA[0]
                stagn = 0
            else:
                stagn += 1
                if cfg.sa_restart and stagn % cfg.sa_restart == 0:
                    cur, cur_f = best[:], best_f
            s2 = state(it + 1)
            if mode == "rl":
                Q[s, a] += cfg.rl_alpha * (reward + cfg.rl_gamma * Q[s2].max() - Q[s, a])
            elif mode == "alns":
                sc[a] += reward; used[a] += 1
                if (it + 1) % cfg.alns_seg == 0:
                    m = used > 0
                    w[m] = (1 - cfg.alns_r) * w[m] + cfg.alns_r * sc[m] / used[m]
                    w = np.maximum(w, 0.01)
                    sc[:] = 0; used[:] = 0
            s = s2
            T *= alpha
            if it % 50 == 0 or it == cfg.sa_iters - 1:
                history.append(best_f); phase.append(tag)
            if self.progress and it % 250 == 0:
                self.progress(tag, it, cfg.sa_iters, best_f)
        return best, best_f, (Q if mode == "rl" else w)

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
        if cfg.variant in SA_VARIANTS:
            mode = {"GA-SA": "uniform", "GA-SA-ALNS": "alns", "GA-SA-RL": "rl"}[cfg.variant]
            best, best_f, Q = self.run_sa(best, best_f, mode, t0, history, phase, op_counts, op_succ)
        sol = self.ev.evaluate(best)
        return RunResult(sol, history, phase, time.time() - t0, self.ev.n_evals, op_counts, op_succ,
                         Q if cfg.variant == "GA-SA-RL" else None, ga_best)


def solve(ev: Evaluator, cfg: Optional[HybridConfig] = None, **kw) -> RunResult:
    cfg = cfg or HybridConfig(**kw)
    return HybridGASARL(ev, cfg).run()
