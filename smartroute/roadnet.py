"""Jaringan jalan nyata (OpenStreetMap) dengan filter legalitas truk tangki.

Alur
----
1. ``tools/fetch_osm.py`` mengunduh ruas jalan OSM (Overpass API) di sekitar FT
   Gelumbang dan 13 SPBU ke ``data/osm/roads.json.gz``.
2. :func:`build_matrices` menyaring ruas yang boleh dilalui tiap tipe truk,
   menghitung lintasan terpendek (Dijkstra) antar FT/SPBU, lalu menyimpan
   ``data/jarak_jalan_osm.csv`` (jarak per tipe truk) dan
   ``data/rute_osm_geom.json.gz`` (geometri lintasan untuk peta).

Aturan legalitas ruas untuk truk tipe k (lihat data/aturan_kelas_jalan.csv dan
data/osm_jalan.csv):
  a. jenis ruas (tag ``highway``) termasuk jalan umum yang dapat dilalui truk;
  b. tidak ada larangan akses (``access``/``motor_vehicle``/``hgv`` = no/private);
  c. kelas jalan (UU 22/2009 Pasal 19; PP 79/2013) mengizinkan dimensi dan MST
     truk: kelas ruas >= kelas minimum yang dibutuhkan truk;
  d. rambu batas eksplisit di OSM bila ada (maxwidth, maxlength, maxheight,
     maxweight, maxaxleload) tidak dilanggar;
  e. lebar badan jalan (tag ``width``, atau ``lanes`` x lebar lajur, atau nilai
     bawaan per jenis ruas) >= lebar jalan minimum operasional truk
     (kolom ``lebar_jalan_min_m`` pada data/armada.csv, untuk jalan dua arah);
     pada jalur satu arah cukup lebar truk + 1,0 m ruang bebas;
  f. arah satu jalur (``oneway``) dipatuhi.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OSM_RAW = os.path.join(DATA_DIR, "osm", "roads.json.gz")
MATRIX_CSV = os.path.join(DATA_DIR, "jarak_jalan_osm.csv")
GEOM_JSON = os.path.join(DATA_DIR, "rute_osm_geom.json.gz")
EDGE_SUMMARY_CSV = os.path.join(DATA_DIR, "osm", "ringkasan_ruas.csv")

KELAS_RANK = {"III": 1, "II": 2, "I": 3, "KHUSUS": 4}
ONEWAY_CLEARANCE_M = 1.0   # ruang bebas samping (0,5 m kiri + 0,5 m kanan) pada jalur satu arah
SNAP_MAX_KM = 0.25  # jarak maksimum titik FT/SPBU ke ruas legal terdekat (km)


# ---------------------------------------------------------------------------
# Tabel aturan
# ---------------------------------------------------------------------------
def _read(name: str, data_dir: Optional[str] = None) -> List[Dict[str, str]]:
    with open(os.path.join(data_dir or DATA_DIR, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_rules(data_dir: Optional[str] = None):
    kelas = {r["kelas"].upper(): r for r in _read("aturan_kelas_jalan.csv", data_dir)}
    jalan = {r["highway"]: r for r in _read("osm_jalan.csv", data_dir)}
    return kelas, jalan


def truck_class_required(truck: Dict[str, str], kelas: Dict[str, Dict[str, str]]) -> str:
    """Kelas jalan paling rendah yang mengizinkan dimensi & MST truk."""
    w, l, h, mst = (float(truck[c]) for c in ("lebar_kendaraan_m", "panjang_kendaraan_m",
                                               "tinggi_kendaraan_m", "mst_ton"))
    for name in sorted(kelas, key=lambda k: KELAS_RANK[k]):
        r = kelas[name]
        if (w <= float(r["lebar_maks_m"]) + 1e-9 and l <= float(r["panjang_maks_m"]) + 1e-9
                and h <= float(r["tinggi_maks_m"]) + 1e-9 and mst <= float(r["mst_maks_ton"]) + 1e-9):
            return name
    return "KHUSUS"


# ---------------------------------------------------------------------------
# Parsing tag OSM
# ---------------------------------------------------------------------------
_num = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def _tag_num(v: Optional[str]) -> Optional[float]:
    """'2.5', '2,5 m', '10 t', '3.8m' -> float; nilai non-numerik -> None."""
    if not v:
        return None
    m = _num.search(v)
    if not m:
        return None
    x = float(m.group(0).replace(",", "."))
    if "'" in v or "ft" in v:  # satuan kaki (jarang di Indonesia)
        x *= 0.3048
    return x


def road_width(tags: Dict[str, str], jalan: Dict[str, Dict[str, str]]) -> Tuple[float, str]:
    """Lebar badan jalan (m) dan sumbernya: 'width', 'lanes', atau 'bawaan'."""
    w = _tag_num(tags.get("width")) or _tag_num(tags.get("est_width"))
    if w and 2.0 <= w <= 60:
        return w, "width"
    lanes = _tag_num(tags.get("lanes"))
    hw = tags.get("highway", "")
    rule = jalan.get(hw)
    if lanes and rule:
        return lanes * float(rule["lebar_lajur_m"]), "lanes"
    return (float(rule["lebar_bawaan_m"]) if rule else 0.0), "bawaan"


def edge_allowed(tags: Dict[str, str], truck: Dict[str, str], truck_kelas: str,
                 jalan: Dict[str, Dict[str, str]]) -> Tuple[bool, str]:
    hw = tags.get("highway", "")
    rule = jalan.get(hw)
    if rule is None or rule["boleh_truk"].strip().lower() not in ("ya", "yes", "1", "true"):
        return False, "jenis_ruas"
    for key in ("access", "motor_vehicle", "hgv", "goods"):
        if tags.get(key, "").lower() in ("no", "private", "agricultural", "forestry", "delivery_no"):
            return False, "larangan_akses"
    if tags.get("area") == "yes":
        return False, "jenis_ruas"
    road_kelas = rule["kelas_asumsi"].upper()
    if KELAS_RANK.get(road_kelas, 0) < KELAS_RANK[truck_kelas]:
        return False, "kelas_jalan"
    lim = {"maxwidth": "lebar_kendaraan_m", "maxlength": "panjang_kendaraan_m",
           "maxheight": "tinggi_kendaraan_m", "maxweight": "gvw_ton", "maxaxleload": "mst_ton"}
    for tag, col in lim.items():
        x = _tag_num(tags.get(tag)) or _tag_num(tags.get(tag + ":physical"))
        if x is not None and x > 0 and float(truck[col]) > x + 1e-9:
            return False, "rambu_" + tag
    w, _ = road_width(tags, jalan)
    need = float(truck["lebar_jalan_min_m"])        # jalan dua arah: truk harus dapat berpapasan
    if _oneway(tags) != 0:                          # jalur satu arah (mis. jalan raya terpisah median)
        need = min(need, float(truck["lebar_kendaraan_m"]) + ONEWAY_CLEARANCE_M)
    if w + 1e-9 < need:
        return False, "lebar_jalan"
    return True, "ok"


def _oneway(tags: Dict[str, str]) -> int:
    v = tags.get("oneway", "").lower()
    if v in ("yes", "1", "true"):
        return 1
    if v == "-1":
        return -1
    if tags.get("junction") in ("roundabout", "circular") and v != "no":
        return 1
    if tags.get("highway") == "motorway" and v != "no":
        return 1
    return 0


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# Graf
# ---------------------------------------------------------------------------
def load_osm(path: str = OSM_RAW) -> Dict:
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def parse_osm(osm: Dict):
    nodes = {}
    ways = []
    for el in osm["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way" and "nodes" in el:
            ways.append((el["id"], el["nodes"], el.get("tags", {})))
    ids = np.array(sorted(nodes), dtype=np.int64)
    index = {nid: i for i, nid in enumerate(ids)}
    latlon = np.array([nodes[i] for i in ids], dtype=float)
    return index, latlon, ways


def build_graph(index, latlon, ways, allow_fn):
    """Graf berarah ruas legal. allow_fn(tags)->(bool, alasan)."""
    rows, cols, w = [], [], []
    reasons: Dict[str, float] = {}
    for _, nds, tags in ways:
        seq = [index[n] for n in nds if n in index]
        if len(seq) < 2:
            continue
        a = np.array(seq[:-1]); b = np.array(seq[1:])
        d = haversine(latlon[a, 0], latlon[a, 1], latlon[b, 0], latlon[b, 1])
        ok, why = allow_fn(tags)
        reasons[why] = reasons.get(why, 0.0) + float(d.sum())
        if not ok:
            continue
        ow = _oneway(tags)
        if ow >= 0:
            rows += a.tolist(); cols += b.tolist(); w += d.tolist()
        if ow <= 0:
            rows += b.tolist(); cols += a.tolist(); w += d.tolist()
    N = len(latlon)
    w = np.maximum(np.array(w, dtype=float), 1e-6)
    G = csr_matrix((w, (rows, cols)), shape=(N, N))
    # sisakan sisi terpendek bila ada duplikat (csr menjumlahkan duplikat -> tangani)
    if len(rows):
        key = np.array(rows, dtype=np.int64) * N + np.array(cols, dtype=np.int64)
        order = np.lexsort((w, key))
        key, w2 = key[order], w[order]
        first = np.r_[True, key[1:] != key[:-1]]
        r = (key[first] // N).astype(np.int64); c = (key[first] % N).astype(np.int64)
        G = csr_matrix((w2[first], (r, c)), shape=(N, N))
    return G, reasons


def snap(points: np.ndarray, latlon: np.ndarray, G) -> Tuple[np.ndarray, np.ndarray]:
    """Node graf terdekat (pada komponen terhubung kuat terbesar) untuk tiap titik."""
    ncomp, lab = connected_components(G, directed=True, connection="strong")
    deg = np.asarray((G != 0).sum(axis=1)).ravel()
    sizes = np.bincount(lab[deg > 0], minlength=ncomp) if (deg > 0).any() else np.zeros(ncomp)
    main = int(np.argmax(sizes)) if len(sizes) else 0
    cand = np.where((lab == main) & (deg > 0))[0]
    out_n = np.full(len(points), -1); out_d = np.full(len(points), np.inf)
    if len(cand) == 0:
        return out_n, out_d
    for i, (la, lo) in enumerate(points):
        d = haversine(la, lo, latlon[cand, 0], latlon[cand, 1])
        j = int(np.argmin(d))
        out_n[i], out_d[i] = cand[j], d[j]
    return out_n, out_d


def _path(pred_row: np.ndarray, src: int, dst: int) -> List[int]:
    p = [dst]
    while p[-1] != src:
        q = pred_row[p[-1]]
        if q < 0:
            return []
        p.append(int(q))
    return p[::-1]


def _simplify(coords: List[Tuple[float, float]], tol_deg: float = 0.00008) -> List[Tuple[float, float]]:
    """Douglas-Peucker sederhana untuk memperkecil berkas geometri (~9 m)."""
    if len(coords) < 3:
        return coords
    pts = np.array(coords)
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue
        a, b = pts[s], pts[e]
        ab = b - a
        L = float(np.hypot(*ab))
        seg = pts[s + 1:e]
        if L == 0:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > tol_deg:
            m = s + 1 + k
            keep[m] = True
            stack += [(s, m), (m, e)]
    return [tuple(map(float, x)) for x in pts[keep]]


def build_matrices(osm_path: str = OSM_RAW, data_dir: Optional[str] = None, write: bool = True,
                   snap_max_km: float = SNAP_MAX_KM) -> Dict:
    data_dir = data_dir or DATA_DIR
    kelas, jalan = load_rules(data_dir)
    armada = _read("armada.csv", data_dir)
    spbu = _read("spbu.csv", data_dir)
    labels = [r["id"] for r in spbu]
    pts = np.array([[float(r["lat"]), float(r["lon"])] for r in spbu])
    index, latlon, ways = parse_osm(load_osm(osm_path))
    n = len(pts)
    out = {"labels": labels, "types": {}, "geom": {}, "summary": []}
    for tr in armada:
        t = tr["tipe"]
        tk = truck_class_required(tr, kelas)
        G, reasons = build_graph(index, latlon, ways, lambda tags: edge_allowed(tags, tr, tk, jalan))
        node, sd = snap(pts, latlon, G)
        ok = (node >= 0) & (sd <= snap_max_km)
        Dm = np.full((n, n), np.nan)
        geoms = {}
        srcs = node[ok]
        if len(srcs):
            dist, pred = dijkstra(G, directed=True, indices=srcs, return_predecessors=True)
            okidx = np.where(ok)[0]
            for a_pos, a in enumerate(okidx):
                for b in okidx:
                    if a == b:
                        Dm[a, b] = 0.0
                        continue
                    d = dist[a_pos, node[b]]
                    if not np.isfinite(d):
                        continue
                    Dm[a, b] = d + sd[a] + sd[b]
                    path = _path(pred[a_pos], node[a], node[b])
                    c = [tuple(pts[a])] + [tuple(latlon[p]) for p in path] + [tuple(pts[b])]
                    geoms[f"{labels[a]}>{labels[b]}"] = [[round(x, 6), round(y, 6)] for x, y in _simplify(c)]
        out["types"][t] = {"kelas_min": tk, "D": Dm, "snap_km": sd, "reasons": reasons}
        out["geom"][t] = geoms
        tot = sum(reasons.values())
        out["summary"].append(dict(tipe=t, kelas_jalan_min=tk,
                                   km_ruas_total=round(tot, 1),
                                   km_ruas_legal=round(reasons.get("ok", 0.0), 1),
                                   **{f"km_ditolak_{k}": round(v, 1) for k, v in sorted(reasons.items()) if k != "ok"},
                                   simpul_tak_terjangkau=";".join(labels[i] for i in range(n) if not ok[i]),
                                   snap_maks_m=round(float(np.nanmax(np.where(ok, sd, np.nan))) * 1000, 0)
                                   if ok.any() else None))
    if write:
        save(out, data_dir)
    return out


def save(out: Dict, data_dir: str = DATA_DIR):
    labels = out["labels"]
    with open(os.path.join(data_dir, os.path.basename(MATRIX_CSV)), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["tipe", "dari", "ke", "jarak_km"])
        for t, v in out["types"].items():
            D = v["D"]
            for i, a in enumerate(labels):
                for j, b in enumerate(labels):
                    wr.writerow([t, a, b, "" if not np.isfinite(D[i, j]) else f"{D[i, j]:.3f}"])
    raw = json.dumps(out["geom"], separators=(",", ":"), sort_keys=True).encode("utf-8")
    with open(os.path.join(data_dir, os.path.basename(GEOM_JSON)), "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as f:  # deterministik
            f.write(raw)
    os.makedirs(os.path.join(data_dir, "osm"), exist_ok=True)
    keys = []
    for s in out["summary"]:
        keys += [k for k in s if k not in keys]
    with open(os.path.join(data_dir, "osm", os.path.basename(EDGE_SUMMARY_CSV)), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for s in out["summary"]:
            wr.writerow(s)


# ---------------------------------------------------------------------------
# Pemakaian oleh model & aplikasi
# ---------------------------------------------------------------------------
def available(data_dir: Optional[str] = None) -> bool:
    return os.path.exists(os.path.join(data_dir or DATA_DIR, os.path.basename(MATRIX_CSV)))


def load_type_matrices(labels: List[str], types: List[str], data_dir: Optional[str] = None) -> np.ndarray:
    """-> array (|K|, n+1, n+1) km; NaN = tidak ada lintasan legal."""
    pos = {l: i for i, l in enumerate(labels)}
    tpos = {t: k for k, t in enumerate(types)}
    n = len(labels)
    Dk = np.full((len(types), n, n), np.nan)
    with open(os.path.join(data_dir or DATA_DIR, os.path.basename(MATRIX_CSV)), newline="") as f:
        for r in csv.DictReader(f):
            if r["tipe"] in tpos and r["dari"] in pos and r["ke"] in pos and r["jarak_km"] != "":
                Dk[tpos[r["tipe"]], pos[r["dari"]], pos[r["ke"]]] = float(r["jarak_km"])
    return Dk


_GEOM_CACHE: Dict[str, Dict] = {}


def load_geometry(data_dir: Optional[str] = None) -> Dict[str, Dict[str, List[List[float]]]]:
    p = os.path.join(data_dir or DATA_DIR, os.path.basename(GEOM_JSON))
    if p not in _GEOM_CACHE:
        if not os.path.exists(p):
            return {}
        with gzip.open(p, "rt", encoding="utf-8") as f:
            _GEOM_CACHE[p] = json.load(f)
    return _GEOM_CACHE[p]


def route_polyline(geom: Dict, vtype: str, seq_labels: List[str]) -> Optional[List[List[float]]]:
    """Gabungkan geometri ruas a>b untuk satu ritase (label berurutan, termasuk depot)."""
    g = geom.get(vtype, {})
    pts: List[List[float]] = []
    for a, b in zip(seq_labels[:-1], seq_labels[1:]):
        seg = g.get(f"{a}>{b}")
        if seg is None:
            return None
        pts += seg if not pts else seg[1:]
    return pts


if __name__ == "__main__":
    import sys
    res = build_matrices(sys.argv[1] if len(sys.argv) > 1 else OSM_RAW)
    for s in res["summary"]:
        print(s)
