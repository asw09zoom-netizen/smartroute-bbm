"""Generator instance sintetis di atas jaringan jalan OSM legal-truk wilayah studi.

Dua kelas instance:
- "longgar": armada lapang, tanpa jendela waktu (dipakai E10 versi awal).
- "ketat"  : armada dekat batas minimum, 40% SPBU berjendela waktu 3 jam, antrean loading
             rack 15 menit, armada heterogen B/C/D dengan larangan jalan per tipe.
Permintaan total per SPBU di-bootstrap dari data capstone; proporsi produk dari produk.csv.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict, Tuple

import numpy as np

from . import roadnet
from .data import load_tables
from .fuzzy import priorities
from .model import Instance, Params, VehicleType


@lru_cache(maxsize=1)
def _graphs():
    tables = load_tables()
    kelas, jalan = roadnet.load_rules()
    index, latlon, ways = roadnet.parse_osm(roadnet.load_osm())
    G_by_type: Dict[str, Tuple] = {}
    for tr in tables["armada"]:
        tk = roadnet.truck_class_required(tr, kelas)
        G, _ = roadnet.build_graph(index, latlon, ways,
                                   lambda tags, tr=tr, tk=tk: roadnet.edge_allowed(tags, tr, tk, jalan))[:2]
        G_by_type[tr["tipe"]] = (G, latlon)
    from scipy.sparse.csgraph import connected_components
    Gc = G_by_type["C"][0]
    _, lab = connected_components(Gc, directed=True, connection="strong")
    big = np.argmax(np.bincount(lab))
    nodes_ll = latlon[np.where(lab == big)[0]]
    return tables, G_by_type, nodes_ll


def synthetic(n: int, seed: int, kind: str = "longgar") -> Instance:
    tables, G_by_type, nodes_ll = _graphs()
    rng = np.random.default_rng(seed)
    spbu = tables["spbu"]
    depot = np.array([[float(spbu[0]["lat"]), float(spbu[0]["lon"])]])
    dem0 = np.array([float(r["demand_kl"]) for r in spbu[1:]])
    pick = []
    for c in rng.permutation(len(nodes_ll)):
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
    p = Params()
    if kind == "ketat":
        p = Params(rack_wait=15.0)
        # armada: kapasitas efektif per unit C dalam satu shift ~ 3 ritase x 16 KL x 0,75 isi
        need_c = math.ceil(tot.sum() / (16.0 * p.max_trips * 0.75))
        counts = {"B": max(1, math.ceil(n / 25)), "C": max(2, need_c - math.ceil(n / 50)),
                  "D": max(1, math.ceil(n / 50))}
    else:
        scale = n / 13.0
        counts = {"B": math.ceil(scale), "C": math.ceil(4 * scale)}
    vt = []
    for r in tables["armada"]:
        comps = tuple(float(x) for x in r["kompartemen_kl"].split("+"))
        vt.append(VehicleType(r["tipe"], float(r["kapasitas_kl"]), comps, counts.get(r["tipe"], 0),
                              float(r["fc0_l_per_km"]), float(r["biaya_tetap_rp"]),
                              tuple(r["produk_kompatibel"].split("|")), float(r["lebar_jalan_min_m"])))
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
    tw = np.zeros((n + 1, 2)); tw[:, 1] = p.shift_len
    if kind == "ketat":
        sel = rng.choice(np.arange(1, n + 1), size=int(round(0.4 * n)), replace=False)
        for i in sel:
            a = float(rng.uniform(60, p.shift_len - 240))
            tw[i] = (a, a + 180.0)
    prio = priorities(np.full(n + 1, 24.0), D[0], np.full(n + 1, 0.10))
    return Instance(f"Sintetis-{kind}-{n}", D, demand, products, vt, labels, pts, tw, prio, None, None, p, Dk)
