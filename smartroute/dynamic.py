"""Perutean ulang dinamis (dynamic re-routing) saat gangguan operasional.

Kebijakan yang dibandingkan:
  - "tanpa re-routing" : rencana awal dipertahankan; pelanggan truk yang rusak
                          dikirim ulang dari FT oleh truk lain setelah jadwalnya.
  - "RL re-optimization": residual problem diselesaikan ulang oleh GA-SA-RL
                          (operator SA dipilih Q-Learning) dengan warm-start dari
                          sisa rencana awal dan waktu siap tiap truk.
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from .hybrid import HybridConfig, HybridGASARL
from .model import Evaluator, Instance, Solution, evaluate_routes


def subinstance(inst: Instance, customers: List[int]) -> Tuple[Instance, List[int]]:
    idx = [0] + list(customers)
    sub = replace(inst,
                  D=inst.D[np.ix_(idx, idx)], demand=inst.demand[idx],
                  labels=[inst.labels[i] for i in idx],
                  coords=None if inst.coords is None else inst.coords[idx],
                  tw=None if inst.tw is None else inst.tw[idx],
                  priority=None if inst.priority is None else inst.priority[idx],
                  access=None if inst.access is None else inst.access[idx],
                  quota=None if inst.quota is None else inst.quota[idx])
    return sub, idx


def _state_at(inst: Instance, sol: Solution, t_event: float, broken: int):
    """Tentukan SPBU yang sudah dilayani, sisa pelanggan, dan waktu siap truk."""
    served, residual, residual_trips = [], [], []
    avail: Dict[int, float] = {}
    unit_type: Dict[int, int] = {}
    stranded = []
    for tr in sol.trips:
        if tr.truck < 0:
            residual += tr.seq; residual_trips.append((tr.seq, tr.vtype))
            continue
        unit_type[tr.truck] = tr.vtype
        if tr.start >= t_event:
            residual += tr.seq; residual_trips.append((tr.seq, tr.vtype))
            continue
        if tr.truck == broken and tr.end > t_event:
            for i, a in zip(tr.seq, tr.arrivals):
                (served if a <= t_event else stranded).append(i)
            continue
        served += tr.seq                    # ritase berjalan/selesai pada truk sehat
        avail[tr.truck] = max(avail.get(tr.truck, 0.0), tr.end)
    for u, k in unit_type.items():
        if u != broken:
            avail.setdefault(u, t_event)
            avail[u] = max(avail[u], t_event)
    return served, residual, stranded, avail, unit_type, residual_trips


def breakdown_event(inst: Instance, sol: Solution, broken_unit: int, t_event: float,
                    cfg: Optional[HybridConfig] = None, seed: int = 0) -> Dict:
    ev_full = Evaluator(inst)
    served, residual, stranded, avail, unit_type, residual_trips = _state_at(inst, sol, t_event, broken_unit)
    todo = stranded + residual
    # semua unit (termasuk yang belum terpakai) selain yang rusak
    all_units = [(k, 0.0) for k, vt in enumerate(inst.vtypes) for _ in range(vt.count)]
    truck_avail = []
    for u, (k, _) in enumerate(all_units):
        if u == broken_unit:
            continue
        truck_avail.append((k, avail.get(u, t_event)))
    if not todo:
        return dict(n_affected=0)
    sub, idx = subinstance(inst, todo)
    ev = Evaluator(sub)
    ev.ref = ev_full.ref            # normalisasi sama dengan rencana awal
    pos = {c: j for j, c in enumerate(idx)}
    # Kebijakan 0: tanpa re-routing -> struktur ritase semula dipertahankan; SPBU yang
    # tertahan di truk rusak menjadi satu ritase baru dari FT.
    naive_routes = ([[pos[c] for c in stranded]] if stranded else []) + \
                   [[pos[c] for c in seq] for seq, _ in residual_trips]
    naive_perm = [c for r in naive_routes for c in r]
    naive = evaluate_routes(ev, naive_routes, truck_avail=truck_avail)
    # Kebijakan 1: re-optimasi GA-SA-RL (warm start)
    cfg = cfg or HybridConfig(variant="GA-SA-RL", pop_size=40, generations=60, sa_iters=1500, seed=seed)
    t0 = time.time()
    ev.default_avail = truck_avail
    res = HybridGASARL(ev, cfg, init_perms=[naive_perm]).run()
    t_comp = time.time() - t0
    reopt = res.best
    out = dict(n_affected=len(todo), n_stranded=len(stranded), t_event=t_event,
               naive=_kpi(naive), reopt=_kpi(reopt), compute_s=t_comp,
               naive_sol=naive, reopt_sol=reopt, idx=idx)
    return out


def _kpi(s: Solution) -> Dict:
    makespan = max((t.end for t in s.trips), default=0.0)
    return dict(fitness=s.fitness, dist_km=s.dist, co2_kg=s.Z2, cost_rp=s.Z1, late_min=s.late_min,
                overtime_min=s.overtime_min, unassigned=s.unassigned, makespan_min=makespan,
                trips=len(s.trips))


def congestion_shock(inst: Instance, sol: Solution, t_event: float, cf: float = 0.3, hours: int = 3,
                     cfg: Optional[HybridConfig] = None, seed: int = 0) -> Dict:
    """Kemacetan mendadak mulai t_event selama `hours` jam (CF turun ke `cf`)."""
    prof = list(inst.params.congestion)
    h0 = int((inst.params.shift_start_h * 60 + t_event) // 60)
    for h in range(h0, h0 + hours):
        prof[h % 24] = cf
    shocked = inst.with_params(congestion=tuple(prof))
    # tidak ada truk rusak -> broken_unit = -1
    return breakdown_event(shocked, Evaluator(shocked).evaluate(sol.perm), -1, t_event, cfg, seed)
