"""Simulasi mikro pergerakan truk tangki untuk rencana distribusi (replay rinci).

Rencana dari optimasi (ritase, urutan SPBU, unit truk, jam berangkat) dijalankan ulang
secara rinci di sepanjang lintasan jalan legal-truk:

* kecepatan per segmen  v = min(v_jalan(jenis ruas), v_maks_truk) x CF(jam) x (1 - gamma x muatan/kapasitas)
  x eps_lalin, dengan v_jalan dari data/osm_jalan.csv (batas kecepatan, asumsi mengacu PM 111/2015),
  v_maks_truk dari data/armada.csv (asumsi), CF(jam) profil kemacetan model, gamma pengaruh muatan,
  dan eps_lalin variasi acak lognormal per ruas jenis-sama (opsional);
* waktu muat di FT  = antrean rack + muatan x menit/KL (sama dengan model);
* waktu bongkar di SPBU = waktu tetap (administrasi, grounding, cek dip) + volume / laju bongkar tipe truk
  x eps_bongkar (variasi acak opsional);
* ritase berikutnya suatu unit dimulai paling cepat pada jam rencana dan setelah unit kembali ke FT.

Keluaran dipakai animasi peta (keyframe per unit) dan tabel rencana vs simulasi.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import roadnet
from .model import Instance, Solution, cf_at

DEFAULT_ROAD_SPEED = 30.0


@dataclass
class SimConfig:
    v_truck: Dict[str, float] = field(default_factory=dict)        # km/jam per tipe
    unload_rate: Dict[str, float] = field(default_factory=dict)    # L/menit per tipe
    road_speed: Dict[str, float] = field(default_factory=dict)     # km/jam per jenis ruas OSM
    unload_fixed: Optional[float] = None    # menit; None = pakai Params.unload_fixed
    load_gamma: float = 0.15                # penurunan kecepatan saat muatan penuh (15%)
    traffic_cv: float = 0.0                 # variasi kecepatan antar-ruas (koefisien variasi)
    unload_cv: float = 0.0                  # variasi waktu bongkar
    seed: int = 0
    use_congestion: bool = True


def default_config(data_dir: Optional[str] = None) -> SimConfig:
    import csv
    import os
    dd = data_dir or roadnet.DATA_DIR
    vt, ur, rs = {}, {}, {}
    with open(os.path.join(dd, "armada.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vt[r["tipe"]] = float(r.get("v_maks_kmh") or 60)
            ur[r["tipe"]] = float(r.get("laju_bongkar_l_per_menit") or 400)
    with open(os.path.join(dd, "osm_jalan.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rs[r["highway"]] = float(r.get("kecepatan_maks_kmh") or DEFAULT_ROAD_SPEED)
    rs.setdefault("akses", 15.0)
    return SimConfig(v_truck=vt, unload_rate=ur, road_speed=rs)


def _legs(inst: Instance, vname: str, k: int, seq_labels: List[str], geom: Dict):
    """Daftar ruas (a,b) dengan titik & kode jalan; panjang diskalakan ke jarak model."""
    out = []
    D = inst.Dk[k] if inst.Dk is not None else inst.D
    pos = {l: i for i, l in enumerate(inst.labels)}
    for a, b in zip(seq_labels[:-1], seq_labels[1:]):
        g = roadnet.leg_geometry(geom, vname, a, b) if geom else None
        dkm = float(D[pos[a], pos[b]])
        if g is None or not np.isfinite(dkm):
            pa, pb = inst.coords[pos[a]], inst.coords[pos[b]]
            g = {"p": [list(pa), list(pb)], "h": [-1]}  # garis lurus (mode matriks capstone)
            if not np.isfinite(dkm):
                dkm = float(roadnet.haversine(pa[0], pa[1], pb[0], pb[1])) * 1.3
        P = np.array(g["p"], dtype=float)
        seg = roadnet.haversine(P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1])
        tot = float(seg.sum())
        if tot > 0:
            seg = seg * (dkm / tot)
        out.append(dict(a=a, b=b, P=P, seg=seg, h=list(g["h"]), km=dkm))
    return out


def simulate(inst: Instance, sol: Solution, cfg: Optional[SimConfig] = None, geom: Optional[Dict] = None) -> Dict:
    cfg = cfg or default_config()
    p = inst.params
    if geom is None:
        geom = roadnet.load_geometry() if inst.Dk is not None else {}
    rng = np.random.default_rng(cfg.seed)
    unload_fixed = p.unload_fixed if cfg.unload_fixed is None else cfg.unload_fixed
    qtot = inst.demand.sum(axis=1)
    trips = [t for t in sol.trips]
    units: Dict[str, List] = {}
    nx = 0
    for t in trips:
        if t.truck >= 0:
            key = f"{inst.vtypes[t.vtype].name}-{t.truck}"
        else:  # ritase tanpa unit truk (armada kurang): ditampilkan sebagai truk tambahan
            nx += 1
            key = f"{inst.vtypes[t.vtype].name}-tambahan{nx}"
        units.setdefault(key, []).append(t)
    out_units, stops, events = [], [], []
    for u, (key, ts) in enumerate(sorted(units.items())):
        ts.sort(key=lambda t: (t.start, t.trip_no))
        vt = inst.vtypes[ts[0].vtype]
        vname = vt.name
        vmax_truck = cfg.v_truck.get(vname, 60.0)
        rate = cfg.unload_rate.get(vname, 400.0)
        frames = []        # [t_menit, lat, lon, kode_status, kecepatan, sisa_muatan_KL, km_kumulatif]
        cum = 0.0
        status_spans = []  # (t0, t1, teks)
        clock = 0.0
        assigned = ts[0].truck >= 0
        stats = dict(km=0.0, drive_min=0.0, unload_min=0.0, load_min=0.0, wait_min=0.0)
        depot = list(inst.coords[0])
        for t in ts:
            seq = [inst.labels[i] for i in t.seq]
            start = max(t.start, clock) if assigned else t.start
            if start > clock:
                stats["wait_min"] += start - clock
                status_spans.append((clock, start, "Siaga di FT"))
            clock = start
            load = float(sum(qtot[i] for i in t.seq))
            tl = p.rack_wait + load * p.load_min_per_kl
            frames.append([clock, depot[0], depot[1], 0, 0.0, 0.0, cum])
            status_spans.append((clock, clock + tl, f"Muat {load:.1f} KL di FT (ritase {t.trip_no})"))
            events.append(dict(unit=key, t=clock, ev=f"mulai muat {load:.1f} KL", tempat="FT"))
            clock += tl
            stats["load_min"] += tl
            frames.append([clock, depot[0], depot[1], 0, 0.0, load, cum])
            legs = _legs(inst, vname, t.vtype, ["FT"] + seq + ["FT"], geom)
            L = load
            for li, leg in enumerate(legs):
                to_depot = leg["b"] == "FT"
                status_spans.append((clock, None, ("Kembali ke FT" if to_depot else f"Menuju {leg['b']}")))
                t_leg0 = clock
                run_eps = 1.0
                last_code = None
                for j in range(len(leg["seg"])):
                    code = leg["h"][j] if j < len(leg["h"]) else -1
                    if code != last_code:
                        run_eps = float(rng.lognormal(-0.5 * cfg.traffic_cv ** 2, cfg.traffic_cv)) if cfg.traffic_cv > 0 else 1.0
                        last_code = code
                    if code >= 0:
                        vr = cfg.road_speed.get(roadnet.HW_CODES[code], DEFAULT_ROAD_SPEED)
                    else:
                        vr = p.vmax  # mode capstone: kecepatan rata-rata model
                    v = min(vr, vmax_truck)
                    if cfg.use_congestion:
                        v *= cf_at(p, clock)
                    v *= (1.0 - cfg.load_gamma * min(1.0, L / vt.capacity))
                    v = max(5.0, v * run_eps)
                    dt = leg["seg"][j] / v * 60.0
                    clock += dt
                    cum += float(leg["seg"][j])
                    frames.append([clock, float(leg["P"][j + 1][0]), float(leg["P"][j + 1][1]), 1 if not to_depot else 3,
                                   round(v, 1), round(L, 2), cum])
                stats["km"] += leg["km"]
                stats["drive_min"] += clock - t_leg0
                status_spans[-1] = (t_leg0, clock, status_spans[-1][2])
                if not to_depot:
                    i = inst.labels.index(leg["b"])
                    vol = float(qtot[i])
                    eps = float(rng.lognormal(-0.5 * cfg.unload_cv ** 2, cfg.unload_cv)) if cfg.unload_cv > 0 else 1.0
                    tu = (unload_fixed + vol * 1000.0 / rate) * eps
                    planned = t.arrivals[li] if li < len(t.arrivals) else float("nan")
                    tw_b = inst.tw[i, 1] if inst.tw is not None else float("inf")
                    stops.append(dict(unit=key, tipe=vname, ritase=t.trip_no, spbu=leg["b"], volume_kl=round(vol, 2),
                                      tiba_rencana=planned, tiba_simulasi=clock, bongkar_menit=tu,
                                      terlambat_menit=max(0.0, clock - tw_b)))
                    events.append(dict(unit=key, t=clock, ev=f"tiba, bongkar {vol:.2f} KL ({tu:.0f} mnt)", tempat=leg["b"]))
                    status_spans.append((clock, clock + tu, f"Bongkar {vol:.2f} KL di {leg['b']}"))
                    P1 = leg["P"][-1]
                    frames.append([clock, float(P1[0]), float(P1[1]), 2, 0.0, round(L, 2), cum])
                    clock += tu
                    stats["unload_min"] += tu
                    L = max(0.0, L - vol)
                    frames.append([clock, float(P1[0]), float(P1[1]), 2, 0.0, round(L, 2), cum])
                else:
                    events.append(dict(unit=key, t=clock, ev=f"kembali ke FT (ritase {t.trip_no} selesai)", tempat="FT"))
            frames.append([clock, depot[0], depot[1], 0, 0.0, 0.0, cum])
        out_units.append(dict(unit=key, tipe=vname, kapasitas=vt.capacity, assigned=assigned,
                              frames=[[round(f[0], 2), round(f[1], 6), round(f[2], 6), f[3], f[4], f[5], round(f[6], 3)] for f in frames],
                              spans=[[round(a, 2), round(b, 2), s] for a, b, s in status_spans],
                              selesai=clock, **{k: round(v, 1) for k, v in stats.items()}))
    events.sort(key=lambda e: e["t"])
    t_end = max((u["selesai"] for u in out_units), default=0.0)
    return dict(units=out_units, stops=stops, events=events, t_end=t_end,
                shift_start_h=p.shift_start_h, shift_len=p.shift_len)
