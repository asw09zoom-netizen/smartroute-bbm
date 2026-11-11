"""Rangkaian eksperimen penelitian SMARTROUTE-BBM.

Jalankan:  python -m experiments.run_all [E0 E1 E2 ...]
Hasil disimpan di results/*.csv dan results/*.json (angka apa adanya, tanpa
penyesuaian manual).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import asdict

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from smartroute import scenarios as sc  # noqa: E402
from smartroute.cvrplib import read_vrp  # noqa: E402
from smartroute.data import (BASELINE_DIST_KM, BASELINE_ROUTES, DIRECT_DIST_KM,  # noqa: E402
                             build_instance, load_tables)
from smartroute.dynamic import breakdown_event, congestion_shock  # noqa: E402
from smartroute.exact import solve_cvrp_exact  # noqa: E402
from smartroute.heuristics import (clarke_wright, direct_routes, nearest_neighbor_routes,  # noqa: E402
                                   routes_distance)
from smartroute.hybrid import HybridConfig, HybridGASARL  # noqa: E402
from smartroute.model import Evaluator, Params, evaluate_routes  # noqa: E402

RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)
VARIANTS = ["GA", "GA-SA", "GA-SA-RL"]
NREP = int(os.environ.get("NREP", 30))


def save_json(name, obj):
    with open(os.path.join(RES, name), "w") as f:
        json.dump(obj, f, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def lbl(inst, seq):
    return "-".join(inst.labels[i] for i in seq)


def sol_rows(inst, sol):
    rows = []
    for t in sol.trips:
        rows.append(dict(rute=lbl(inst, t.seq), tipe=inst.vtypes[t.vtype].name, unit=t.truck, ritase=t.trip_no,
                         muatan_kl=round(t.load, 2), jarak_km=round(t.dist, 2), co2_kg=round(t.co2, 2),
                         mulai_menit=round(t.start, 1), selesai_menit=round(t.end, 1),
                         kompartemen=str([inst.products[p] if p >= 0 else "-" for p in t.comp_assign])))
    return rows


# ---------------------------------------------------------------------------
def E0():
    """Audit data capstone."""
    t = load_tables()
    inst = build_instance()
    D, C = inst.D, inst.coords

    def hav(a, b):
        la1, lo1, la2, lo2 = map(math.radians, [*a, *b])
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(h))
    rows = []
    for i in range(inst.n + 1):
        for j in range(i + 1, inst.n + 1):
            h = hav(C[i], C[j])
            rows.append(dict(i=inst.labels[i], j=inst.labels[j], jalan_km=D[i, j], garis_lurus_km=round(h, 2),
                             faktor_sirkuitas=round(D[i, j] / h, 3) if h > 0.05 else np.nan))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E0_sirkuitas.csv"), index=False)
    viol = [(i, j, k) for i in range(inst.n + 1) for j in range(inst.n + 1) for k in range(inst.n + 1)
            if len({i, j, k}) == 3 and D[i, j] > D[i, k] + D[k, j] + 1e-9]
    worst = max(((D[i, j] - D[i, k] - D[k, j]), inst.labels[i], inst.labels[j], inst.labels[k]) for i, j, k in viol)
    dep = df[df.i == "FT"]
    out = dict(total_demand_kl=float(inst.total_demand().sum()), dot_trend_projection_kl=58.39,
               circuity_mean=float(df.faktor_sirkuitas.mean()), circuity_sd=float(df.faktor_sirkuitas.std()),
               circuity_min=float(df.faktor_sirkuitas.min()), circuity_max=float(df.faktor_sirkuitas.max()),
               circuity_depot_mean=float(dep.faktor_sirkuitas.mean()),
               triangle_violations_ordered=len(viol), triangle_worst=worst,
               max_depot_dist_km=float(D[0].max()), spbu_beyond_30km=int((D[0, 1:] > 30).sum()))
    save_json("E0_audit.json", out)
    print(out)


# ---------------------------------------------------------------------------
def E1():
    """Validasi pada setting capstone: CVRP homogen 16 KL, satu ritase, objektif jarak."""
    inst = build_instance(params=Params(distance_only=True, single_trip=True), fleet={"C": 13})
    D, q = inst.D, inst.total_demand()
    ev = Evaluator(inst)
    res = dict(direct=routes_distance(D, direct_routes(inst.n)), baseline_capstone=routes_distance(D, BASELINE_ROUTES))
    cw = clarke_wright(D, q, 16.0)
    nn = nearest_neighbor_routes(D, q, 16.0)
    res.update(cw_reimpl=routes_distance(D, cw), cw_routes=[lbl(inst, r) for r in cw],
               nn=routes_distance(D, nn), nn_routes=[lbl(inst, r) for r in nn])
    t0 = time.time()
    opt, routes, info = solve_cvrp_exact(D, q, 16.0, time_limit=1200)
    res.update(milp_opt=opt, milp_routes=[lbl(inst, r) for r in routes], milp_time_s=time.time() - t0,
               milp_status=str(info.get("message")))
    print(res)
    rows, hist = [], {}
    for v in VARIANTS:
        for s in range(NREP):
            r = HybridGASARL(ev, HybridConfig(variant=v, seed=s)).run()
            rows.append(dict(variant=v, seed=s, dist=r.best.dist, runtime=r.runtime, evals=r.evals,
                             routes=" | ".join(lbl(inst, t.seq) for t in r.best.trips), n_routes=len(r.best.trips)))
            if s == 0:
                hist[v] = r.history
        print(v, "done")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E1_runs.csv"), index=False)
    res["stats"] = stats_block(df, "dist", BASELINE_DIST_KM, opt)
    res["history_seed0"] = hist
    save_json("E1_summary.json", res)


def stats_block(df, col, baseline, optimum=None):
    out = {}
    for v, g in df.groupby("variant"):
        x = g[col].values
        d = dict(n=len(x), mean=float(x.mean()), sd=float(x.std(ddof=1)), min=float(x.min()), max=float(x.max()),
                 median=float(np.median(x)), runtime_mean=float(g.runtime.mean()))
        d["improve_vs_baseline_pct"] = float((baseline - x.mean()) / baseline * 100)
        if x.std() > 1e-12:
            t, p = stats.ttest_1samp(x, baseline, alternative="less")
            d.update(t_one_sample=float(t), p_one_sample=float(p))
            try:
                w, pw = stats.wilcoxon(x - baseline, alternative="less")
                d.update(wilcoxon=float(w), p_wilcoxon=float(pw))
            except ValueError:
                pass
        else:
            d.update(t_one_sample=None, p_one_sample=None, note="varian nol (semua replikasi identik)")
        if optimum is not None:
            d["gap_to_opt_mean_pct"] = float((x.mean() - optimum) / optimum * 100)
            d["hit_rate_opt"] = float(np.mean(np.abs(x - optimum) < 1e-6))
        out[v] = d
    groups = [g[col].values for _, g in df.groupby("variant")]
    if all(np.std(g) > 0 for g in groups) or len(set(np.concatenate(groups))) > 1:
        F, p = stats.f_oneway(*groups)
        out["anova"] = dict(F=float(F), p=float(p))
        kw, pk = stats.kruskal(*groups)
        out["kruskal"] = dict(H=float(kw), p=float(pk))
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            tk = pairwise_tukeyhsd(df[col].values, df["variant"].values)
            out["tukey"] = str(tk.summary())
        except Exception as e:  # pragma: no cover
            out["tukey"] = f"n/a: {e}"
    else:
        out["anova"] = "tidak dapat dihitung: seluruh replikasi bernilai identik"
    return out


# ---------------------------------------------------------------------------
def E2():
    """Model lengkap MC-MP-MT-VRP (multi-produk asumsi, armada eksisting 4C+1B, multi-ritase)."""
    out = {}
    for mp in [False, True]:
        key = "multiproduk" if mp else "agregat"
        inst = build_instance(multiproduct=mp)
        ev = Evaluator(inst)
        base = evaluate_routes(ev, BASELINE_ROUTES)
        bsum = base.summary()
        out[key] = dict(baseline=bsum, baseline_trips=sol_rows(inst, base), ref=list(ev.ref))
        rows, best = [], None
        for v in VARIANTS:
            for s in range(NREP):
                r = HybridGASARL(ev, HybridConfig(variant=v, seed=s)).run()
                d = r.best.summary(); d.update(variant=v, seed=s, runtime=r.runtime)
                rows.append(d)
                if v == "GA-SA-RL" and (best is None or r.best.fitness < best.fitness):
                    best = r.best
            print(key, v, "done")
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(RES, f"E2_runs_{key}.csv"), index=False)
        out[key]["stats_fitness"] = stats_block(df, "fitness", bsum["fitness"])
        out[key]["means"] = df.groupby("variant")[["fitness", "dist_km", "cost_rp", "co2_kg", "time_min", "trucks",
                                                   "trips", "late_min", "overtime_min", "unassigned"]].mean().to_dict()
        out[key]["best_ga_sa_rl"] = best.summary()
        out[key]["best_trips"] = sol_rows(inst, best)
        out[key]["best_perm"] = best.perm
    save_json("E2_summary.json", out)


# ---------------------------------------------------------------------------
def E3b():
    """Seperti E3 tetapi dengan opsi armada diperluas (A, B, C, D tersedia) -> trade-off pemilihan armada."""
    E3(fleet=FLEET_OPT, suffix="b", sens=False)


FLEET_OPT = dict(A=2, B=2, C=4, D=1)


def E3c():
    """Seperti E3b (armada diperluas) tetapi pada jaringan jalan OSM legal-truk."""
    E3(fleet=FLEET_OPT, suffix="c", sens=False, road="osm")


def E3(fleet=None, suffix="", sens=True, road="capstone"):
    """Analisis trade-off multi-objektif: sapuan bobot -> Pareto front."""
    inst0 = build_instance(multiproduct=True, fleet=fleet, road=road)
    rows = []
    for w1 in np.arange(0, 1.01, 0.1):
        for w2 in np.arange(0, 1.01 - w1, 0.1):
            w3 = max(0.0, 1 - w1 - w2)
            inst = inst0.with_params(w=(float(w1), float(w2), float(w3)))
            ev = Evaluator(inst)
            for s in range(2):
                r = HybridGASARL(ev, HybridConfig(seed=s, generations=150, sa_iters=3000)).run()
                d = r.best.summary(); d.update(w1=round(w1, 2), w2=round(w2, 2), w3=round(w3, 2), seed=s,
                                               trip_types="".join(sorted(inst.vtypes[t.vtype].name for t in r.best.trips)))
                rows.append(d)
        print("w1", round(w1, 1))
    df = pd.DataFrame(rows)
    pts = df[["cost_rp", "co2_kg", "time_min"]].values
    feas = (df.unassigned == 0).values
    nd = []
    for i in range(len(pts)):
        dom = feas[i] and not any(feas[j] and np.all(pts[j] <= pts[i]) and np.any(pts[j] < pts[i])
                                  for j in range(len(pts)) if j != i)
        nd.append(dom)
    df["pareto"] = nd
    nd2 = []
    for i in range(len(pts)):
        dom = feas[i] and not any(feas[j] and np.all(pts[j, :2] <= pts[i, :2]) and np.any(pts[j, :2] < pts[i, :2])
                                  for j in range(len(pts)) if j != i)
        nd2.append(dom)
    df["pareto_cost_co2"] = nd2
    df.to_csv(os.path.join(RES, f"E3{suffix}_pareto.csv"), index=False)
    if not sens:
        return
    # sensitivitas biaya tetap truk
    rows = []
    for fc_mult in [0.0, 0.5, 1.0, 1.5, 2.0]:
        inst = build_instance(multiproduct=True)
        for vt in inst.vtypes:
            vt.fixed_cost *= fc_mult
        ev = Evaluator(inst)
        for s in range(3):
            r = HybridGASARL(ev, HybridConfig(seed=s, generations=150, sa_iters=3000)).run()
            d = r.best.summary(); d.update(fixed_cost_mult=fc_mult, seed=s); rows.append(d)
    pd.DataFrame(rows).to_csv(os.path.join(RES, "E3_sens_fixedcost.csv"), index=False)


# ---------------------------------------------------------------------------
def _hyb(inst, seeds=5, **kw):
    ev = Evaluator(inst)
    best, runs = None, []
    for s in range(seeds):
        r = HybridGASARL(ev, HybridConfig(seed=s, **kw)).run()
        runs.append(r.best.fitness)
        if best is None or r.best.fitness < best.fitness:
            best = r.best
    return ev, best, runs


def E4():
    """Sepuluh kategori skenario (asumsi parameter dicatat pada results/E4_scenarios.json)."""
    base = build_instance(multiproduct=True)
    out = {}

    def record(name, inst, assumption, extra=None, base_eval=True):
        ev, best, runs = _hyb(inst)
        d = dict(assumption=assumption, hybrid=best.summary(), hybrid_trips=sol_rows(inst, best),
                 fitness_runs=runs)
        if base_eval:
            b = evaluate_routes(ev, BASELINE_ROUTES)
            d["baseline"] = b.summary()
            d["_bsol"] = b
        d["_sol"] = best
        if extra:
            d.update(extra(inst, best, d))
        out[name] = d
        print(name, {k: round(float(v), 2) for k, v in best.summary().items()})

    record("0. Kondisi normal", base, "Parameter dasar")
    # 1 kemacetan
    record("1. Kemacetan dinamis", sc.apply_congestion(base, 0.5, 0.85),
           "CF=0,5 pada jam 07-09 & 16-18; CF=0,85 jam lain 06-20")
    # 2 restriksi jalan
    rw = {2: 5.0, 3: 5.0, 4: 5.0, 5: 5.0}
    record("2. Kelas & restriksi jalan", sc.apply_road_restriction(base, rw),
           "Asumsi akses SPBU Ogan Ilir (S2-S5) lebar jalan 5 m -> tipe C/D (min 6 m) dilarang", base_eval=True)
    # 3 stokastik -> dievaluasi di E6
    out["3. Variabilitas permintaan stokastik"] = dict(assumption="Lihat E6 (Monte Carlo 1000 iterasi)")
    # 4 breakdown -> E5
    out["4. Kerusakan armada (breakdown)"] = dict(assumption="Lihat E5 (re-routing dinamis)")
    # 5 time window
    tw = {i: (6, 11) for i in [7, 8, 9, 11, 12, 13]}
    inst5 = sc.apply_time_windows(base, tw)
    record("5. Time window SPBU", inst5, "Asumsi SPBU Kota Prabumulih hanya menerima 06.00-11.00",
           extra=lambda i, s, d: dict(on_time_hybrid=sc.on_time_rate(i, s), on_time_baseline=sc.on_time_rate(i, d["_bsol"])))
    # 6 emisi: bobot emisi dominan & armada D tersedia
    inst6 = base.with_params(w=(0.1, 0.8, 0.1))
    record("6. Emisi truk realistis", inst6, "Bobot (0,1; 0,8; 0,1) memprioritaskan emisi CO2")
    # 7 tank management
    rng = np.random.default_rng(7)
    frac = np.concatenate([[1.0], rng.uniform(0.15, 0.6, base.n)])
    inst7 = sc.apply_tank_management(base, frac)
    record("7. Tank management SPBU", inst7,
           "Asumsi stok awal 15-60% kapasitas tangki (2 hari penjualan), seed 7; batas kedatangan = TTE - 1 jam",
           extra=lambda i, s, d: dict(tte_hours=list(np.round(i.__dict__['tte_hours'], 2)),
                                     priority=list(np.round(i.priority, 1)),
                                     stockouts_hybrid=sc.stockouts(i, s), stockouts_baseline=sc.stockouts(i, d["_bsol"])))
    # 8 loading rack
    inst8 = sc.apply_loading_rack(base, n_racks=4, other_trucks_per_h=2.5)
    record("8. Antrian loading rack FT", inst8,
           f"M/M/4, kedatangan truk lain 2,5/jam, layanan 80 menit; Wq = {inst8.params.rack_wait:.1f} menit/ritase")
    # 9 panic buying
    inst9 = sc.apply_surge(base, 1.5)
    record("9. Panic buying / surge demand", inst9, "Seluruh permintaan x1,5 (SF=1,5)", base_eval=False)
    inst9b = sc.apply_surge(base, 3.0, [1, 6, 10])
    record("9b. Panic buying lokal", inst9b, "SPBU Muara Enim (S1, S6, S10) x3,0", base_eval=False)
    # 10 kuota
    inst10 = sc.apply_bph_quota(base, 0.95)
    record("10. Kuota BPH Migas", inst10, "Kuota Biosolar = 95% permintaan; volume dibatasi kuota",
           extra=lambda i, s, d: dict(quota_cut_kl=i.__dict__["quota_cut_kl"], quota_excess=s.info.get("quota_excess", 0)))
    for v in out.values():
        v.pop("_sol", None); v.pop("_bsol", None)
    save_json("E4_scenarios.json", out)


def E4b():
    """Tindak lanjut E4: skenario yang tidak layak dengan armada eksisting diuji ulang dengan
    penambahan armada minimum (fungsi DSS untuk perencanaan armada)."""
    out = {}
    cases = [
        ("2R. Restriksi jalan + 1 unit tipe B", dict(B=2, C=4), lambda b: sc.apply_road_restriction(b, {2: 5.0, 3: 5.0, 4: 5.0, 5: 5.0}),
         "Seperti skenario 2, armada 4C + 2B"),
        ("9bR. Panic buying lokal + 1 unit tipe D", dict(B=1, C=4, D=1), lambda b: sc.apply_surge(b, 3.0, [1, 6, 10]),
         "Seperti skenario 9b, armada 4C + 1B + 1D (32 KL)"),
        ("9R. Panic buying x1,5 (armada eksisting)", None, lambda b: sc.apply_surge(b, 1.5), "Kontrol: armada 4C + 1B"),
    ]
    for name, fleet, fn, note in cases:
        inst = fn(build_instance(multiproduct=True, fleet=fleet))
        ev, best, runs = _hyb(inst)
        out[name] = dict(assumption=note, hybrid=best.summary(), hybrid_trips=sol_rows(inst, best), fitness_runs=runs)
        print(name, {k: round(float(v), 2) for k, v in best.summary().items()})
    save_json("E4b_fleet_remedy.json", out)


# ---------------------------------------------------------------------------
def E5():
    """Re-routing dinamis: breakdown & kemacetan mendadak."""
    inst = build_instance(multiproduct=True)
    ev, best, _ = _hyb(inst)
    used = sorted({t.truck for t in best.trips if t.truck >= 0})
    rows = []
    for u in used:
        for tb in [60, 120, 180, 240, 300]:
            for s in range(3):
                o = breakdown_event(inst, best, u, tb, seed=s)
                if o.get("n_affected", 0) == 0:
                    continue
                rows.append(dict(event="breakdown", unit=u, t_event=tb, seed=s, n_affected=o["n_affected"],
                                 n_stranded=o["n_stranded"], compute_s=o["compute_s"],
                                 **{f"naive_{k}": v for k, v in o["naive"].items()},
                                 **{f"reopt_{k}": v for k, v in o["reopt"].items()}))
    for tb in [60, 120, 180, 240]:
        for s in range(3):
            o = congestion_shock(inst, best, tb, cf=0.3, hours=3, seed=s)
            if o.get("n_affected", 0) == 0:
                continue
            rows.append(dict(event="kemacetan", unit=-1, t_event=tb, seed=s, n_affected=o["n_affected"],
                             n_stranded=0, compute_s=o["compute_s"],
                             **{f"naive_{k}": v for k, v in o["naive"].items()},
                             **{f"reopt_{k}": v for k, v in o["reopt"].items()}))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E5_dynamic.csv"), index=False)
    summ = {}
    for ev_name, g in df.groupby("event"):
        d = dict(n=len(g))
        for k in ["fitness", "dist_km", "co2_kg", "cost_rp", "late_min", "overtime_min", "makespan_min", "unassigned"]:
            a, b = g[f"naive_{k}"].values.astype(float), g[f"reopt_{k}"].values.astype(float)
            d[k] = dict(naive=float(a.mean()), reopt=float(b.mean()))
            if np.any(a != b):
                try:
                    w, p = stats.wilcoxon(b, a, alternative="less")
                    d[k]["p_wilcoxon"] = float(p)
                except ValueError:
                    pass
        d["compute_s_mean"] = float(g.compute_s.mean())
        d["share_improved_fitness"] = float(np.mean(g.reopt_fitness < g.naive_fitness - 1e-9))
        summ[ev_name] = d
    save_json("E5_summary.json", dict(plan=best.summary(), used_units=used, summary=summ))
    print(summ)


def E5b():
    """Re-routing dinamis pada kondisi ketat: tenggat stok SPBU (tank management, skenario 7)."""
    base = build_instance(multiproduct=True)
    rows = []
    for st_seed in range(5):
        rng = np.random.default_rng(100 + st_seed)
        inst = sc.apply_tank_management(base, np.concatenate([[1.0], rng.uniform(0.15, 0.6, base.n)]))
        ev, best, _ = _hyb(inst, seeds=3)
        used = sorted({t.truck for t in best.trips if t.truck >= 0})
        for u in used:
            for tb in [60, 120, 180]:
                o = breakdown_event(inst, best, u, tb, seed=0)
                if o.get("n_affected", 0) == 0:
                    continue
                rows.append(dict(event="breakdown", stock_seed=st_seed, unit=u, t_event=tb,
                                 n_affected=o["n_affected"], compute_s=o["compute_s"],
                                 **{f"naive_{k}": v for k, v in o["naive"].items()},
                                 **{f"reopt_{k}": v for k, v in o["reopt"].items()}))
        for tb in [60, 120]:
            o = congestion_shock(inst, best, tb, cf=0.3, hours=3, seed=0)
            if o.get("n_affected", 0):
                rows.append(dict(event="kemacetan", stock_seed=st_seed, unit=-1, t_event=tb,
                                 n_affected=o["n_affected"], compute_s=o["compute_s"],
                                 **{f"naive_{k}": v for k, v in o["naive"].items()},
                                 **{f"reopt_{k}": v for k, v in o["reopt"].items()}))
        print("stock seed", st_seed)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E5b_dynamic_tight.csv"), index=False)
    summ = {}
    for ev_name, g in df.groupby("event"):
        d = dict(n=len(g), compute_s_mean=float(g.compute_s.mean()),
                 share_improved_fitness=float(np.mean(g.reopt_fitness < g.naive_fitness - 1e-9)))
        for k in ["fitness", "late_min", "overtime_min", "dist_km", "co2_kg", "makespan_min"]:
            a, b = g[f"naive_{k}"].values.astype(float), g[f"reopt_{k}"].values.astype(float)
            d[k] = dict(naive=float(a.mean()), reopt=float(b.mean()))
            if np.any(a != b):
                try:
                    d[k]["p_wilcoxon"] = float(stats.wilcoxon(b, a, alternative="less")[1])
                except ValueError:
                    pass
        summ[ev_name] = d
    save_json("E5b_summary.json", summ)
    print(summ)


# ---------------------------------------------------------------------------
def E6():
    """Monte Carlo permintaan stokastik (1000 iterasi)."""
    rows = []
    for mp in [False, True]:
        inst = build_instance(multiproduct=mp)
        ev = Evaluator(inst)
        base = evaluate_routes(ev, BASELINE_ROUTES)
        _, hyb, _ = _hyb(inst)
        _, rob, _ = _hyb(inst.with_params(cap_safety=0.90))
        for cv in [0.05, 0.10, 0.15, 0.20]:
            for name, s in [("Saving Matrix", base), ("GA-SA-RL", hyb), ("GA-SA-RL robust (90%)", rob)]:
                m = sc.monte_carlo_service(inst, s, cv=cv, iters=1000, seed=1)
                rows.append(dict(produk="multiproduk" if mp else "agregat", cv=cv, plan=name,
                                 service_level=m["service_level"], unmet_kl=m["unmet_kl_per_day"],
                                 p_shortfall=m["p_any_shortfall"], dist_km=s.dist, trucks=s.trucks_used,
                                 unassigned=s.unassigned))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E6_montecarlo.csv"), index=False)
    print(df.to_string())


# ---------------------------------------------------------------------------
def E7():
    """Validasi algoritma pada instance CVRPLIB set X (Uchoa et al., 2017)."""
    d = os.path.join(ROOT, "data", "cvrplib")
    files = sorted(f for f in os.listdir(d) if f.endswith(".vrp"))
    part = os.environ.get("E7_PART")  # "0" / "1": bagi instance ke dua proses paralel
    first5 = files[:5]
    if part is not None:
        files = files[int(part)::2]
    rows = []
    nrep = int(os.environ.get("NREP_BENCH", 10))
    for f in files:
        inst, bks = read_vrp(os.path.join(d, f))
        ev = Evaluator(inst)
        cw = routes_distance(inst.D, clarke_wright(inst.D, inst.total_demand(), inst.vtypes[0].capacity))
        variants = VARIANTS if f in first5 else ["GA-SA-RL"]
        for v in variants:
            for s in range(nrep):
                r = HybridGASARL(ev, HybridConfig(variant=v, seed=s, generations=1000)).run()
                rows.append(dict(instance=inst.name, n=inst.n, bks=bks, cw=cw, variant=v, seed=s, cost=r.best.dist,
                                 gap_pct=(r.best.dist - bks) / bks * 100, cw_gap_pct=(cw - bks) / bks * 100,
                                 runtime=r.runtime))
            print(f, v, np.mean([x["gap_pct"] for x in rows if x["instance"] == inst.name and x["variant"] == v]))
        pd.DataFrame(rows).to_csv(os.path.join(RES, f"E7_cvrplib{'_part' + part if part is not None else ''}.csv"), index=False)


# ---------------------------------------------------------------------------
def E8():
    """Jaringan jalan nyata OSM dengan filter legalitas truk vs matriks capstone."""
    from smartroute import roadnet
    out = {}
    cap = build_instance()
    osm = build_instance(road="osm")
    names = [v.name for v in osm.vtypes]
    iu = np.triu_indices(cap.n + 1, 1)
    comp = {}
    for k, t in enumerate(names):
        Dk = osm.Dk[k]
        m = np.isfinite(Dk[iu])
        a, b = cap.D[iu][m], Dk[iu][m]
        reach = [osm.labels[i] for i in range(1, osm.n + 1)
                 if np.isfinite(Dk[0, i]) and np.isfinite(Dk[i, 0])]
        comp[t] = dict(pasangan=int(m.sum()), spbu_terjangkau=len(reach),
                       spbu_tak_terjangkau=[l for l in osm.labels[1:] if l not in reach],
                       rerata_selisih_km=float(np.mean(b - a)) if m.any() else None,
                       rerata_selisih_abs_pct=float(np.mean(np.abs(b - a) / np.maximum(a, 1e-9)) * 100) if m.any() else None,
                       korelasi=float(np.corrcoef(a, b)[0, 1]) if m.sum() > 2 else None)
    out["matriks"] = comp
    rs = os.path.join(ROOT, "data", "osm", "ringkasan_ruas.csv")
    if os.path.exists(rs):
        out["ringkasan_ruas"] = pd.read_csv(rs).to_dict(orient="records")
    rows = []
    for fleet_name, fleet in [("eksisting", None), ("diperluas", FLEET_OPT)]:
        for mp in [False, True]:
            key = f"{fleet_name}_{'multiproduk' if mp else 'agregat'}"
            res = {}
            for road in ["capstone", "osm"]:
                inst = build_instance(multiproduct=mp, fleet=fleet, road=road)
                ev = Evaluator(inst)
                base = evaluate_routes(ev, BASELINE_ROUTES).summary()
                best = None
                for s in range(NREP):
                    r = HybridGASARL(ev, HybridConfig(seed=s)).run()
                    d = r.best.summary(); d.update(case=key, road=road, seed=s, runtime=r.runtime)
                    rows.append(d)
                    if best is None or r.best.fitness < best.fitness:
                        best = r.best
                res[road] = dict(baseline=base, best=best.summary(), best_trips=sol_rows(inst, best))
            out[key] = res
            print("E8", key, "done")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E8_runs_osm.csv"), index=False)
    out["means"] = df.groupby(["case", "road"])[["fitness", "dist_km", "cost_rp", "co2_kg", "time_min", "trucks",
                                                 "trips", "unassigned"]].mean().reset_index().to_dict(orient="records")
    save_json("E8_summary.json", out)


if __name__ == "__main__":
    todo = sys.argv[1:] or ["E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7"]
    for e in todo:
        t = time.time()
        print("=====", e)
        globals()[e]()
        print(f"===== {e} selesai {time.time() - t:.0f}s")
