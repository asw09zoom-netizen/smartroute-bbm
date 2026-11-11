"""E11: uji pembanding pada instance sulit (armada padat, jendela waktu, antrean loading rack,
larangan jalan per tipe truk) berukuran 50, 100 dan 200 SPBU di jaringan jalan OSM legal-truk.

Metode: Clarke-Wright (kapasitas efektif kompartemen), OR-Tools GLS (waktu = median waktu
GA-SA-RL pada ukuran yang sama), GA, GA-SA, GA-SA-ALNS, GA-SA-RL (10 seed, anggaran evaluasi sama).

Jalankan:  python -m experiments.run_e11 [run|ortools|summary] [ukuran ...]
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RES = os.path.join(ROOT, "results")
OUTCSV = os.path.join(RES, "E11_runs.csv")
VARIANTS = ["GA", "GA-SA", "GA-SA-ALNS", "GA-SA-RL"]
SEEDS = 10
KIND = "ketat"


def _inst(n):
    from smartroute.instances import synthetic
    return synthetic(n, 2000 + n, KIND)


def _row(sol, **kw):
    d = sol.summary()
    d = {k: (float(v) if hasattr(v, "item") else v) for k, v in d.items()}
    d.update(kw)
    return d


def _task(args):
    n, variant, seed = args
    from smartroute.hybrid import HybridConfig, HybridGASARL
    from smartroute.model import Evaluator
    ev = Evaluator(_inst(n))
    r = HybridGASARL(ev, HybridConfig(variant=variant, seed=seed)).run()
    row = _row(r.best, n=n, variant=variant, seed=seed, runtime=r.runtime, evals=r.evals)
    print("E11", n, variant, seed, round(row["fitness"], 4), round(r.runtime), flush=True)
    return row


def _append(rows):
    df = pd.DataFrame(rows)
    if os.path.exists(OUTCSV):
        df = pd.concat([pd.read_csv(OUTCSV), df])
    df.to_csv(OUTCSV, index=False)


def run(sizes):
    done = set()
    if os.path.exists(OUTCSV):
        d0 = pd.read_csv(OUTCSV)
        done = set(zip(d0.n, d0.variant, d0.seed))
    tasks = [(n, v, s) for n in sorted(sizes, reverse=True) for s in range(SEEDS) for v in VARIANTS
             if (n, v, s) not in done]
    with Pool(4) as pool:
        buf = []
        for row in pool.imap_unordered(_task, tasks):
            buf.append(row)
            if len(buf) >= 4:
                _append(buf); buf = []
        if buf:
            _append(buf)


def _base_task(n):
    from smartroute.heuristics import clarke_wright
    from smartroute.model import Evaluator, evaluate_routes
    from smartroute.ortools_solver import effective_capacity, solve_ortools
    ev = Evaluator(_inst(n))
    d0 = pd.read_csv(OUTCSV)
    tl = float(d0[(d0.n == n) & (d0.variant == "GA-SA-RL")].runtime.median())
    rows = []
    k = max(range(len(ev.inst.vtypes)), key=lambda k: ev.inst.vtypes[k].count)
    t0 = time.time()
    cw = evaluate_routes(ev, clarke_wright(ev.D, ev.qtot, effective_capacity(ev, k)))
    rows.append(_row(cw, n=n, variant="Clarke-Wright", seed=-1, runtime=time.time() - t0, evals=1))
    t0 = time.time()
    s = solve_ortools(ev, time_limit=tl)
    rows.append(_row(s, n=n, variant="OR-Tools", seed=-1, runtime=time.time() - t0, evals=0))
    print("E11 base", n, [round(r["fitness"], 4) for r in rows], flush=True)
    return rows


def ortools(sizes):
    with Pool(min(4, len(sizes))) as pool:
        rows = [r for rr in pool.map(_base_task, sizes) for r in rr]
    df = pd.read_csv(OUTCSV)
    df = df[~df.variant.isin(["Clarke-Wright", "OR-Tools"]) | ~df.n.isin(sizes)]
    pd.concat([df, pd.DataFrame(rows)]).to_csv(OUTCSV, index=False)


def summary():
    from scipy import stats
    df = pd.read_csv(OUTCSV)
    out = dict(kind=KIND, instances=[], tests=[], table=[])
    for n in sorted(df.n.unique()):
        inst = _inst(n)
        out["instances"].append(dict(n=int(n), total_kl=float(inst.demand.sum()),
                                     units={v.name: v.count for v in inst.vtypes if v.count},
                                     tw_frac=float(np.mean(inst.tw[1:, 1] < inst.params.shift_len)),
                                     rack_wait=inst.params.rack_wait))
        g = df[df.n == n]
        for v, gv in g.groupby("variant"):
            out["table"].append(dict(n=int(n), variant=v, fit_mean=gv.fitness.mean(), fit_sd=gv.fitness.std(ddof=1) if len(gv) > 1 else 0.0,
                                     fit_best=gv.fitness.min(), dist=gv.dist_km.mean(), cost=gv.cost_rp.mean(),
                                     co2=gv.co2_kg.mean(), late=gv.late_min.mean(), over=gv.overtime_min.mean(),
                                     unassigned=gv.unassigned.mean(), trucks=gv.trucks.mean(), runtime=gv.runtime.mean()))
        rl = g[g.variant == "GA-SA-RL"].fitness.values
        res = dict(n=int(n))
        for o in ["GA", "GA-SA", "GA-SA-ALNS"]:
            b = g[g.variant == o].fitness.values
            res[f"p_vs_{o}"] = float(stats.mannwhitneyu(rl, b, alternative="less").pvalue)
            res[f"delta_vs_{o}"] = float(np.mean([np.sign(y - x) for x in rl for y in b]))
        for o in ["Clarke-Wright", "OR-Tools"]:
            b = g[g.variant == o].fitness.values
            if len(b):
                res[f"p_vs_{o}"] = float(stats.wilcoxon(rl - b[0], alternative="less").pvalue)
                res[f"impr_vs_{o}"] = float((b[0] - rl.mean()) / b[0] * 100)
        sa = [g[g.variant == v].fitness.values for v in ["GA-SA", "GA-SA-ALNS", "GA-SA-RL"]]
        res["kruskal_sa"] = float(stats.kruskal(*sa).pvalue)
        out["tests"].append(res)
    with open(os.path.join(RES, "E11_summary.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps(out["tests"], indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    sizes = [int(a) for a in sys.argv[2:]] or [50, 100, 200]
    if cmd == "run":
        run(sizes)
    elif cmd == "ortools":
        ortools(sizes)
    else:
        summary()
