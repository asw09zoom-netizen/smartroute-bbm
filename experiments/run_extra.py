"""Eksperimen tambahan laporan akhir.

E9  : ketahanan rencana terhadap simulasi mikro stokastik di jalan OSM legal-truk
      (modul yang sama dengan menu "Simulasi Pergerakan" pada aplikasi).
E10 : skalabilitas pada instance sintetis 25/50/100 SPBU yang lokasinya diambil dari
      simpul jalan OSM legal-truk di wilayah studi (jarak = lintasan legal per tipe truk).

Jalankan:  python -m experiments.run_extra E9 E10
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from smartroute import roadnet  # noqa: E402
from smartroute import simulate as simmod  # noqa: E402
from smartroute.data import BASELINE_ROUTES, build_instance, load_tables, priorities  # noqa: E402
from smartroute.heuristics import clarke_wright  # noqa: E402
from smartroute.hybrid import HybridConfig, HybridGASARL  # noqa: E402
from smartroute.model import Evaluator, Instance, Params, VehicleType, evaluate_routes  # noqa: E402

RES = os.path.join(ROOT, "results")


def save_json(name, obj):
    with open(os.path.join(RES, name), "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


# ---------------------------------------------------------------------------
def _sim_metrics(inst, sol, cfg):
    r = simmod.simulate(inst, sol, cfg)
    st = pd.DataFrame(r["stops"])
    dev = (st.tiba_simulasi - st.tiba_rencana).abs() if len(st) else pd.Series([0.0])
    drive = sum(u["drive_min"] for u in r["units"])
    km = sum(u["km"] for u in r["units"])
    return dict(t_end=r["t_end"], overtime=max(0.0, r["t_end"] - inst.params.shift_len),
                late_stops=int((st.terlambat_menit > 0).sum()) if len(st) else 0,
                late_min=float(st.terlambat_menit.sum()) if len(st) else 0.0,
                arr_dev_mean=float(dev.mean()), arr_dev_max=float(dev.max()),
                v_mean=km / max(drive, 1e-9) * 60.0,
                unload_min=sum(u["unload_min"] for u in r["units"]))


def E9(nrep=300):
    """Simulasi mikro stokastik (variasi lalu lintas per ruas dan waktu bongkar) atas rencana harian."""
    out, rows = {}, []
    cases = [("multiproduk", True, None, ""), ("multiproduk_tw", True, None, "tw")]
    for key, mp, fleet, mode in cases:
        inst = build_instance(multiproduct=mp, fleet=fleet, road="osm")
        if mode == "tw":  # jendela waktu skenario 5 aplikasi: SPBU Prabumulih (S7-S9, S11-S13) 06.00-11.00
            tw = inst.tw.copy()
            for i in [7, 8, 9, 11, 12, 13]:
                tw[i, 1] = 5 * 60
            from dataclasses import replace
            inst = replace(inst, tw=tw)
        ev = Evaluator(inst)
        base = evaluate_routes(ev, BASELINE_ROUTES)
        best = None
        for s in range(5):
            r = HybridGASARL(ev, HybridConfig(seed=s)).run()
            if best is None or r.best.fitness < best.fitness:
                best = r.best
        plans = {"Saving Matrix": base, "GA-SA-RL": best}
        det = {}
        for pname, sol in plans.items():
            cfg0 = simmod.default_config()
            cfg0.traffic_cv = 0.0; cfg0.unload_cv = 0.0
            m0 = _sim_metrics(inst, sol, cfg0)
            m0.update(model_end=float(max(t.end for t in sol.trips)), model_dist=float(sol.dist),
                      unassigned=int(sol.unassigned), trucks=int(sol.trucks_used), trips=len(sol.trips))
            det[pname] = m0
            for cv in [0.1, 0.2, 0.3]:
                for rep in range(nrep):
                    cfg = simmod.default_config()
                    cfg.traffic_cv = cv; cfg.unload_cv = 0.15; cfg.seed = 10_000 + rep
                    m = _sim_metrics(inst, sol, cfg)
                    m.update(case=key, plan=pname, cv=cv, rep=rep)
                    rows.append(m)
            print("E9", key, pname, "done")
        out[key] = dict(deterministic=det)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, "E9_microsim.csv"), index=False)
    summ = []
    for (case, plan, cv), g in df.groupby(["case", "plan", "cv"]):
        summ.append(dict(case=case, plan=plan, cv=cv, t_end_mean=g.t_end.mean(), t_end_p95=g.t_end.quantile(0.95),
                         p_overtime=(g.overtime > 0).mean(), late_stops_mean=g.late_stops.mean(),
                         p_any_late=(g.late_stops > 0).mean(), late_min_mean=g.late_min.mean(),
                         arr_dev_mean=g.arr_dev_mean.mean(), v_mean=g.v_mean.mean()))
    out["summary"] = summ
    tests = []
    for case in df.case.unique():
        for cv in sorted(df.cv.unique()):
            a = df[(df.case == case) & (df.cv == cv) & (df.plan == "GA-SA-RL")].sort_values("rep")
            b = df[(df.case == case) & (df.cv == cv) & (df.plan == "Saving Matrix")].sort_values("rep")
            for col in ["t_end", "late_min"]:
                d = a[col].values - b[col].values
                p = float(stats.wilcoxon(a[col].values, b[col].values).pvalue) if np.any(d != 0) else None
                tests.append(dict(case=case, cv=cv, metric=col, median_diff=float(np.median(d)), p_wilcoxon=p))
    out["tests"] = tests
    save_json("E9_summary.json", out)


# ---------------------------------------------------------------------------
def _synthetic(n, seed, nodes_ll, G_by_type, tables):
    """Instance sintetis: n SPBU pada simpul jalan legal-truk C, permintaan bootstrap dari data capstone."""
    rng = np.random.default_rng(seed)
    spbu = tables["spbu"]
    depot = np.array([[float(spbu[0]["lat"]), float(spbu[0]["lon"])]])
    dem0 = np.array([float(r["demand_kl"]) for r in spbu[1:]])
    # sebar titik: pilih simpul acak berjarak >= 1 km satu sama lain
    pick = []
    cand = rng.permutation(len(nodes_ll))
    for c in cand:
        p = nodes_ll[c]
        if pick and np.min(roadnet.haversine(p[0], p[1], nodes_ll[pick, 0], nodes_ll[pick, 1])) < 1.0:
            continue
        if roadnet.haversine(p[0], p[1], depot[0, 0], depot[0, 1]) < 1.0:
            continue
        pick.append(c)
        if len(pick) == n:
            break
    pts = np.vstack([depot, nodes_ll[pick]])
    labels = ["FT"] + [f"X{i}" for i in range(1, n + 1)]
    prod_rows = tables["produk"]
    products = [r["produk"] for r in prod_rows]
    share = np.array([float(r["proporsi"]) for r in prod_rows]); share /= share.sum()
    tot = np.concatenate([[0.0], rng.choice(dem0, size=n, replace=True)])
    demand = np.outer(tot, share)
    vt = []
    scale = n / 13.0
    for r in tables["armada"]:
        cnt = {"B": math.ceil(scale), "C": math.ceil(4 * scale)}.get(r["tipe"], 0)
        comps = tuple(float(x) for x in r["kompartemen_kl"].split("+"))
        vt.append(VehicleType(r["tipe"], float(r["kapasitas_kl"]), comps, cnt, float(r["fc0_l_per_km"]),
                              float(r["biaya_tetap_rp"]), tuple(r["produk_kompatibel"].split("|")),
                              float(r["lebar_jalan_min_m"])))
    from scipy.sparse.csgraph import dijkstra
    K = len(vt)
    Dk = np.full((K, n + 1, n + 1), np.nan)
    for k, v in enumerate(vt):
        G, latlon = G_by_type[v.name]
        node, sd = roadnet.snap(pts, latlon, G)
        ok = (node >= 0) & (sd <= roadnet.SNAP_MAX_KM)
        idx = np.where(ok)[0]
        if not len(idx):
            continue
        dist = dijkstra(G, directed=True, indices=node[idx])
        for a_pos, a in enumerate(idx):
            for b in idx:
                Dk[k, a, b] = 0.0 if a == b else dist[a_pos, node[b]] + sd[a] + sd[b]
    with np.errstate(all="ignore"):
        D = np.nanmin(Dk, axis=0)
    D = np.where(np.isfinite(D), D, 1e6)
    p = Params()
    tw = np.zeros((n + 1, 2)); tw[:, 1] = p.shift_len
    prio = priorities(np.full(n + 1, 24.0), D[0], np.full(n + 1, 0.10))
    return Instance(f"Sintetis-{n}", D, demand, products, vt, labels, pts, tw, prio, None, None, p, Dk)


def E10(sizes=(25, 50, 100), seeds=10):
    tables = load_tables()
    kelas, jalan = roadnet.load_rules()
    index, latlon, ways = roadnet.parse_osm(roadnet.load_osm())
    G_by_type = {}
    for tr in tables["armada"]:
        tk = roadnet.truck_class_required(tr, kelas)
        G, _ = roadnet.build_graph(index, latlon, ways, lambda tags, tr=tr, tk=tk: roadnet.edge_allowed(tags, tr, tk, jalan))[:2]
        G_by_type[tr["tipe"]] = (G, latlon)
    # kandidat lokasi: simpul berderajat > 0 pada graf truk C (kelas II), komponen terhubung kuat terbesar
    from scipy.sparse.csgraph import connected_components
    Gc = G_by_type["C"][0]
    ncomp, lab = connected_components(Gc, directed=True, connection="strong")
    big = np.argmax(np.bincount(lab))
    cand = np.where(lab == big)[0]
    nodes_ll = latlon[cand]
    rows, inst_info = [], []
    for n in sizes:
        inst = _synthetic(n, 1000 + n, nodes_ll, G_by_type, tables)
        ev = Evaluator(inst)
        Q = max(v.capacity for v in inst.vtypes if v.count > 0)
        cw = clarke_wright(inst.D, inst.demand.sum(axis=1), Q)
        t0 = time.time()
        base = evaluate_routes(ev, cw)
        bs = base.summary(); bs.update(n=n, variant="Clarke-Wright", seed=-1, runtime=time.time() - t0)
        rows.append(bs)
        inst_info.append(dict(n=n, total_kl=float(inst.demand.sum()),
                              units={v.name: v.count for v in inst.vtypes if v.count},
                              unreachable={v.name: int(np.sum(~np.isfinite(inst.Dk[k][0, 1:])))
                                           for k, v in enumerate(inst.vtypes)}))
        for v in ["GA", "GA-SA-RL"]:
            for s in range(seeds):
                r = HybridGASARL(ev, HybridConfig(variant=v, seed=s)).run()
                d = r.best.summary(); d.update(n=n, variant=v, seed=s, runtime=r.runtime)
                rows.append(d)
            print("E10", n, v, np.mean([x["fitness"] for x in rows if x["n"] == n and x["variant"] == v]), flush=True)
    df = pd.DataFrame(rows)
    tag = "_".join(str(n) for n in sizes)
    df.to_csv(os.path.join(RES, f"E10_part_{tag}.csv"), index=False)
    with open(os.path.join(RES, f"E10_part_{tag}.json"), "w") as f:
        json.dump(inst_info, f)


def E10m(sizes=(25, 50, 100)):
    """Gabungkan hasil E10 per ukuran dan hitung uji statistik."""
    import glob
    df = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(RES, "E10_part_*.csv")))])
    df = df.sort_values(["n", "variant", "seed"])
    df.to_csv(os.path.join(RES, "E10_scalability.csv"), index=False)
    inst_info = []
    for f in sorted(glob.glob(os.path.join(RES, "E10_part_*.json"))):
        inst_info += json.load(open(f))
    sizes = sorted(df.n.unique())
    out = dict(instances=sorted(inst_info, key=lambda d: d["n"]), tests=[])
    for n in sizes:
        a = df[(df.n == n) & (df.variant == "GA-SA-RL")].sort_values("seed").fitness.values
        b = df[(df.n == n) & (df.variant == "GA")].sort_values("seed").fitness.values
        cwf = float(df[(df.n == n) & (df.variant == "Clarke-Wright")].fitness.iloc[0])
        # replikasi GA dan GA-SA-RL saling bebas (seed tidak berpasangan) -> Mann-Whitney U satu sisi
        out["tests"].append(dict(n=n, p_vs_ga=float(stats.mannwhitneyu(a, b, alternative="less").pvalue),
                                 p_vs_cw=float(stats.wilcoxon(a - cwf, alternative="less").pvalue),
                                 cliffs_delta=float(np.mean([np.sign(y - x) for x in a for y in b]))))
    save_json("E10_summary.json", out)


if __name__ == "__main__":
    args = sys.argv[1:] or ["E9", "E10", "E10m"]
    if args[0] == "E10" and len(args) > 1:
        E10(sizes=tuple(int(a) for a in args[1:]))
        sys.exit()
    for e in args:
        t = time.time()
        print("=====", e, flush=True)
        globals()[e]()
        print(f"===== {e} selesai {time.time() - t:.0f}s", flush=True)
