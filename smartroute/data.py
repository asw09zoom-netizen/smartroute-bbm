"""Pemuatan data studi kasus FT Gelumbang (data Capstone Design 2026 PEM Akamigas).

Sumber data primer (tidak diubah):
  - data/spbu.csv      : 13 SPBU, kode, koordinat, permintaan harian (KL/hari)
  - data/jarak_km.csv  : matriks jarak jalan 14x14 (FT + 13 SPBU) dari Saving_Matrix_Fixx.xlsx
Parameter yang merupakan ASUMSI model (dapat diubah pengguna, juga lewat Google Sheets):
  - data/armada.csv    : tipe truk, kompartemen, konsumsi BBM, biaya tetap, jumlah unit
  - data/produk.csv    : proporsi produk per SPBU (data capstone hanya memuat total)
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional

import numpy as np

from .fuzzy import priorities
from .model import Instance, Params, VehicleType

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _read_csv(name: str, data_dir: Optional[str] = None) -> List[Dict[str, str]]:
    with open(os.path.join(data_dir or DATA_DIR, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_tables(data_dir: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    t = {}
    for name in ["spbu", "armada", "produk"]:
        t[name] = _read_csv(f"{name}.csv", data_dir)
    with open(os.path.join(data_dir or DATA_DIR, "jarak_km.csv"), newline="") as f:
        rows = list(csv.reader(f))
    t["jarak"] = rows
    return t


def matrix_from_rows(rows: List[List[str]]) -> np.ndarray:
    return np.array([[float(x) for x in r[1:]] for r in rows[1:]], dtype=float)


def build_instance(tables: Optional[Dict] = None, *, multiproduct: bool = False,
                   fleet: Optional[Dict[str, int]] = None, params: Optional[Params] = None,
                   tte_hours: Optional[np.ndarray] = None, demand_cv: Optional[np.ndarray] = None,
                   demand_scale: Optional[np.ndarray] = None, name: str = "FT Gelumbang") -> Instance:
    t = tables or load_tables()
    spbu = t["spbu"]
    D = matrix_from_rows(t["jarak"])
    n = len(spbu) - 1
    labels = [r["id"] for r in spbu]
    coords = np.array([[float(r["lat"]), float(r["lon"])] for r in spbu])
    tot = np.array([float(r["demand_kl"]) for r in spbu])
    if demand_scale is not None:
        tot = tot * demand_scale
    if multiproduct:
        prod_rows = t["produk"]
        products = [r["produk"] for r in prod_rows]
        share = np.array([float(r["proporsi"]) for r in prod_rows])
        share = share / share.sum()
        demand = np.outer(tot, share)
    else:
        products = ["BBM"]
        demand = tot.reshape(-1, 1)
    vtypes = []
    for r in t["armada"]:
        cnt = int(float(r["jumlah_unit"]))
        if fleet is not None:
            cnt = int(fleet.get(r["tipe"], 0))
        comps = tuple(float(x) for x in r["kompartemen_kl"].split("+"))
        vtypes.append(VehicleType(r["tipe"], float(r["kapasitas_kl"]), comps, cnt, float(r["fc0_l_per_km"]),
                                  float(r["biaya_tetap_rp"]), tuple(r["produk_kompatibel"].split("|")),
                                  float(r["lebar_jalan_min_m"])))
    p = params or Params()
    tw = np.zeros((n + 1, 2)); tw[:, 1] = p.shift_len
    if tte_hours is None:
        tte_hours = np.full(n + 1, 24.0)
    if demand_cv is None:
        demand_cv = np.full(n + 1, 0.10)
    prio = priorities(tte_hours, D[0], demand_cv)
    return Instance(name, D, demand, products, vtypes, labels, coords, tw, prio, None, None, p)


# Baseline Saving Matrix capstone (Laporan Kemajuan Tabel 2.6), indeks SPBU 1..13
BASELINE_ROUTES = [[1], [2, 3, 4, 5], [6, 7], [8, 9, 10], [11, 12, 13]]
BASELINE_DIST_KM = 279.4
DIRECT_DIST_KM = 728.2
