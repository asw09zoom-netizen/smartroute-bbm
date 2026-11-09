"""Fuzzy Priority Scoring (Mamdani, defuzzifikasi centroid) untuk ranking SPBU.

Masukan:
  - time-to-empty TTE (jam)  = stok tersedia / laju penjualan
  - jarak dari FT (km)
  - variabilitas permintaan (koefisien variasi, CV)
Keluaran: skor prioritas 0..100.
"""
from __future__ import annotations

import numpy as np

_Y = np.linspace(0, 100, 201)


def trimf(x, a, b, c):
    x = np.asarray(x, float)
    left = np.where(b > a, (x - a) / (b - a + 1e-12), 1.0)
    right = np.where(c > b, (c - x) / (c - b + 1e-12), 1.0)
    return np.clip(np.minimum(left, right), 0, 1)


def trapmf(x, a, b, c, d):
    x = np.asarray(x, float)
    up = np.where(b > a, (x - a) / (b - a + 1e-12), 1.0)
    down = np.where(d > c, (d - x) / (d - c + 1e-12), 1.0)
    return np.clip(np.minimum(np.minimum(up, 1.0), down), 0, 1)


# Himpunan fuzzy masukan
def mf_tte(t):
    return {
        "kritis": trapmf(t, -1, 0, 4, 8),
        "rendah": trimf(t, 4, 10, 16),
        "sedang": trimf(t, 12, 20, 28),
        "aman": trapmf(t, 24, 36, 1e6, 1e6 + 1),
    }


def mf_jarak(d):
    return {
        "dekat": trapmf(d, -1, 0, 10, 20),
        "sedang": trimf(d, 12, 22, 32),
        "jauh": trapmf(d, 26, 34, 1e6, 1e6 + 1),
    }


def mf_cv(c):
    return {
        "stabil": trapmf(c, -1, 0, 0.08, 0.15),
        "fluktuatif": trapmf(c, 0.10, 0.20, 10, 11),
    }


OUT = {
    "rendah": trimf(_Y, 0, 0, 35),
    "normal": trimf(_Y, 20, 45, 70),
    "tinggi": trimf(_Y, 55, 75, 95),
    "kritis": trimf(_Y, 80, 100, 100),
}

# Basis aturan (TTE, jarak, CV) -> prioritas
RULES = [
    ("kritis", None, None, "kritis"),
    ("rendah", "jauh", None, "kritis"),
    ("rendah", "sedang", None, "tinggi"),
    ("rendah", "dekat", None, "tinggi"),
    ("rendah", None, "fluktuatif", "kritis"),
    ("sedang", "jauh", None, "tinggi"),
    ("sedang", "sedang", None, "normal"),
    ("sedang", "dekat", None, "normal"),
    ("sedang", None, "fluktuatif", "tinggi"),
    ("aman", None, None, "rendah"),
    ("aman", "jauh", "fluktuatif", "normal"),
]


def priority(tte_h: float, dist_km: float, cv: float = 0.1) -> float:
    a, b, c = mf_tte(tte_h), mf_jarak(dist_km), mf_cv(cv)
    agg = np.zeros_like(_Y)
    for t, d, v, out in RULES:
        s = float(a[t])
        if d is not None:
            s = min(s, float(b[d]))
        if v is not None:
            s = min(s, float(c[v]))
        if s > 0:
            agg = np.maximum(agg, np.minimum(s, OUT[out]))
    if agg.sum() < 1e-12:
        return 50.0
    return float((agg * _Y).sum() / agg.sum())


def priorities(tte: np.ndarray, dist: np.ndarray, cv: np.ndarray) -> np.ndarray:
    out = np.zeros(len(tte))
    for i in range(1, len(tte)):
        out[i] = priority(tte[i], dist[i], cv[i])
    return out
