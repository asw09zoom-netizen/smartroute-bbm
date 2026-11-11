"""Pembanding OR-Tools (Google, routing solver + Guided Local Search).

OR-Tools tidak memiliki kendala kompartemen-produk dan multi-ritase bawaan, sehingga dipakai
relaksasi yang lazim: setiap unit truk digandakan sebanyak batas ritase (satu kendaraan virtual
per ritase), kapasitas agregat per kendaraan, jarak jalan legal per tipe truk, larangan simpul
per tipe, biaya tetap teramortisasi per ritase, serta dimensi waktu dengan jendela waktu lunak.
Rute yang dihasilkan kemudian dinilai ulang oleh Evaluator yang sama (kompartemen, penjadwalan
multi-ritase per unit, penalti), sehingga semua metode dibandingkan dengan fungsi objektif sama.
"""
from __future__ import annotations

import time
from typing import List, Optional

import numpy as np

from .model import Evaluator, Solution, evaluate_routes


def effective_capacity(ev: Evaluator, k: int) -> float:
    """Muatan agregat terbesar yang masih layak kompartemen untuk bauran produk rata-rata instance.
    Pada instance dengan proporsi produk seragam per SPBU, batas ini setara kendala kompartemen."""
    from .model import compartment_feasible
    vt = ev.inst.vtypes[k]
    mix = ev.q[1:].sum(axis=0)
    mix = mix / max(mix.sum(), 1e-12)
    L = vt.capacity * ev.p.cap_safety
    while L > 0 and compartment_feasible(vt, mix * L, ev.inst.products, ev.p.cap_safety) is None:
        L -= 0.05
    return max(L, 0.0)


def solve_ortools(ev: Evaluator, time_limit: float = 60.0, seed: int = 0) -> Optional[Solution]:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    inst, p = ev.inst, ev.p
    n = ev.n
    SCALE = 100  # bilangan bulat OR-Tools
    veh_type: List[int] = []
    chain = []   # pasangan (ritase sebelumnya, ritase berikutnya) pada unit truk yang sama
    mt = 1 if p.single_trip else p.max_trips
    for k, vt in enumerate(inst.vtypes):
        for _ in range(vt.count):
            for j in range(mt):
                if j:
                    chain.append((len(veh_type) - 1, len(veh_type)))
                veh_type.append(k)
    V = len(veh_type)
    if V == 0:
        return None
    mgr = pywrapcp.RoutingIndexManager(n + 1, V, 0)
    routing = pywrapcp.RoutingModel(mgr)
    Dk = ev.Dk if ev.Dk is not None else np.repeat(ev.D[None], len(inst.vtypes), axis=0)
    w1, w2, w3 = p.w
    r1, r2, r3 = ev.ref
    # biaya terbobot per km (beban rata-rata setengah kapasitas) dan per menit
    cb = []
    for k, vt in enumerate(inst.vtypes):
        fuel_km = vt.fc0 * (1 + p.beta * 0.5)
        c_km = w1 * (fuel_km * p.fuel_price + p.maint_per_km) / r1 + w2 * fuel_km * p.ef / r2 \
            + w3 * (60.0 / p.vmax) / r3
        M = np.rint(Dk[k] * c_km * 1e6).astype(np.int64)

        def cost_cb(i, j, M=M):
            return int(M[mgr.IndexToNode(i), mgr.IndexToNode(j)])
        cb.append(routing.RegisterTransitCallback(cost_cb))
    for v in range(V):
        k = veh_type[v]
        routing.SetArcCostEvaluatorOfVehicle(cb[k], v)
        mt = 1 if p.single_trip else p.max_trips
        routing.SetFixedCostOfVehicle(int(round(w1 * inst.vtypes[k].fixed_cost / (mt * r1) * 1e6)), v)
    # kapasitas agregat
    q = np.rint(ev.qtot * SCALE).astype(np.int64)
    dcb = routing.RegisterUnaryTransitCallback(lambda i: int(q[mgr.IndexToNode(i)]))
    caps = [int(round(effective_capacity(ev, k) * SCALE)) for k in veh_type]
    routing.AddDimensionWithVehicleCapacity(dcb, 0, caps, True, "load")
    # waktu: layanan di simpul asal (bongkar + muat yang dibebankan per SPBU) + tempuh
    svc = np.array([0.0] + [p.unload_fixed + ev.qtot[i] * (p.unload_per_kl + p.load_min_per_kl)
                            for i in range(1, n + 1)])
    tcb = []
    for k in range(len(inst.vtypes)):
        T = Dk[k] / p.vmax * 60 + svc[:, None]
        T[0, :] += p.rack_wait          # antrean loading rack sebelum tiap ritase
        T = np.rint(T).astype(np.int64)
        T = np.minimum(T, 10 ** 7)

        def time_cb(i, j, T=T):
            return int(T[mgr.IndexToNode(i), mgr.IndexToNode(j)])
        tcb.append(routing.RegisterTransitCallback(time_cb))
    H = int(p.shift_len)
    routing.AddDimensionWithVehicleTransits([tcb[k] for k in veh_type], H, 2 * H, False, "time")
    tdim = routing.GetDimensionOrDie("time")
    tw = inst.tw
    if tw is not None:
        for i in range(1, n + 1):
            idx = mgr.NodeToIndex(i)
            if tw[i, 0] > 0:
                tdim.CumulVar(idx).SetMin(int(np.ceil(tw[i, 0])))   # tiba lebih awal = menunggu
            if tw[i, 1] < p.shift_len:
                tdim.SetCumulVarSoftUpperBound(idx, int(tw[i, 1]), int(p.pen_late * 1e6 * ev.prio[i] / 100))
    for v in range(V):
        tdim.SetCumulVarSoftUpperBound(routing.End(v), H, int(p.pen_overtime * 1e6))
    # multi-ritase: ritase ke-j sebuah unit baru boleh berangkat setelah ritase ke-(j-1) kembali
    slv = routing.solver()
    for a, b in chain:
        slv.Add(tdim.CumulVar(routing.Start(b)) >= tdim.CumulVar(routing.End(a)))
    # larangan simpul per tipe truk
    for i in range(1, n + 1):
        banned = [int(v) for v in range(V) if not bool(ev.access[i, veh_type[v]])]
        if banned and len(banned) < V:
            routing.VehicleVar(mgr.NodeToIndex(i)).RemoveValues(banned)
        # simpul boleh dilewati dengan penalti besar (agar model selalu layak)
        routing.AddDisjunction([mgr.NodeToIndex(i)], int(p.pen_fleet * 1e6))
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromMilliseconds(int(time_limit * 1000))
    t0 = time.time()
    sol = routing.SolveWithParameters(prm)
    if sol is None:
        return None
    routes, types, dropped, units = [], [], [], []
    for v in range(V):
        idx = routing.Start(v)
        r = []
        while not routing.IsEnd(idx):
            node = mgr.IndexToNode(idx)
            if node:
                r.append(node)
            idx = sol.Value(routing.NextVar(idx))
        if r:
            routes.append(r); types.append(veh_type[v]); units.append(v // mt)
    seen = {c for r in routes for c in r}
    for i in range(1, n + 1):
        if i not in seen:   # SPBU yang dilewati: ritase tunggal (akan terhitung tak terlayani bila tak ada unit)
            routes.append([i]); types.append(None); units.append(-1)
            dropped.append(i)
    vt_list = [t if t is not None else int(np.argmax([v.capacity if ev.access[r[0], kk] else -1
                                                     for kk, v in enumerate(inst.vtypes)]))
               for t, r in zip(types, routes)]
    s = evaluate_routes(ev, routes, vt_list, fixed_units=units)
    s.info = dict(s.info or {}, runtime=time.time() - t0, dropped=len(dropped))
    return s
