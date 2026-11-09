"""Sepuluh kategori skenario simulasi What-If (Proposal Tabel 3.4).

Setiap fungsi `apply_*` mengembalikan salinan Instance yang telah dimodifikasi.
Nilai default skenario adalah ASUMSI pengujian (bukan data lapangan) dan dapat
diubah melalui antarmuka aplikasi.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

import numpy as np

from .fuzzy import priorities
from .model import Evaluator, Instance, Solution, compartment_feasible

SCENARIOS = [
    "1. Kemacetan dinamis",
    "2. Kelas & restriksi jalan",
    "3. Variabilitas permintaan stokastik",
    "4. Kerusakan armada (breakdown)",
    "5. Time window SPBU",
    "6. Emisi truk realistis",
    "7. Tank management SPBU",
    "8. Antrian loading rack FT",
    "9. Panic buying / surge demand",
    "10. Kuota BPH Migas",
]


# 1 ---------------------------------------------------------------------------
def congestion_profile(peak_cf: float = 0.5, offpeak_cf: float = 0.9,
                       peaks: Sequence[int] = (7, 8, 16, 17)) -> tuple:
    prof = [1.0] * 24
    for h in range(24):
        if 6 <= h <= 20:
            prof[h] = offpeak_cf
    for h in peaks:
        prof[h] = peak_cf
    return tuple(prof)


def apply_congestion(inst: Instance, peak_cf=0.5, offpeak_cf=0.9, peaks=(7, 8, 16, 17)) -> Instance:
    return inst.with_params(congestion=congestion_profile(peak_cf, offpeak_cf, peaks))


# 2 ---------------------------------------------------------------------------
def apply_road_restriction(inst: Instance, road_width: Dict[int, float]) -> Instance:
    """road_width: {indeks SPBU: lebar jalan akses (m)}. Truk dengan lebar jalan
    minimum > lebar jalan akses tidak boleh melayani SPBU tsb."""
    K = len(inst.vtypes)
    acc = np.ones((inst.n + 1, K), bool)
    for i, w in road_width.items():
        for k, vt in enumerate(inst.vtypes):
            acc[i, k] = vt.min_road_width <= w + 1e-9
    return replace(inst, access=acc)


# 3 ---------------------------------------------------------------------------
def monte_carlo_service(inst: Instance, sol: Solution, cv: float = 0.15, iters: int = 1000,
                        seed: int = 0, dist: str = "normal") -> Dict:
    """Uji ketahanan rencana terhadap permintaan stokastik. Truk diisi penuh pada
    kompartemen yang dialokasikan untuk tiap produk; SPBU dilayani berurutan.
    Kekurangan terjadi bila permintaan aktual melebihi isi kompartemen."""
    rng = np.random.default_rng(seed)
    n, P = inst.n, inst.demand.shape[1]
    mu = inst.demand
    unmet_tot = 0.0
    dem_tot = 0.0
    stockout_spbu = np.zeros(n + 1)
    fails = 0
    for _ in range(iters):
        if dist == "poisson":
            real = rng.poisson(mu * 10) / 10.0
        else:
            real = np.clip(rng.normal(mu, cv * mu), 0, None)
        any_fail = False
        for tr in sol.trips:
            vt = inst.vtypes[tr.vtype]
            cap = np.zeros(P)
            if tr.comp_assign:
                for c_i, p_i in enumerate(tr.comp_assign):
                    if p_i >= 0:
                        cap[p_i] += vt.compartments[c_i]
            else:
                cap[:] = tr.vols
            for i in tr.seq:
                give = np.minimum(real[i], cap)
                short = real[i] - give
                cap -= give
                if short.sum() > 1e-9:
                    stockout_spbu[i] += 1
                    any_fail = True
                unmet_tot += short.sum()
                dem_tot += real[i].sum()
        fails += any_fail
    return dict(service_level=1 - unmet_tot / dem_tot, unmet_kl_per_day=unmet_tot / iters,
                p_any_shortfall=fails / iters, stockout_prob=stockout_spbu[1:] / iters)


# 5 ---------------------------------------------------------------------------
def apply_time_windows(inst: Instance, windows: Dict[int, tuple]) -> Instance:
    """windows: {SPBU: (jam_awal, jam_akhir)} dalam jam dinding (mis. (6,10))."""
    tw = inst.tw.copy()
    s = inst.params.shift_start_h
    for i, (a, b) in windows.items():
        tw[i] = [(a - s) * 60, (b - s) * 60]
    return replace(inst, tw=tw)


def on_time_rate(inst: Instance, sol: Solution) -> float:
    ok = tot = 0
    for tr in sol.trips:
        for i, t in zip(tr.seq, tr.arrivals):
            tot += 1
            ok += t <= inst.tw[i, 1] + 1e-6
    return ok / max(tot, 1)


# 7 ---------------------------------------------------------------------------
def apply_tank_management(inst: Instance, stock_frac: np.ndarray, tank_days: float = 2.0,
                          safety_h: float = 1.0, demand_cv: Optional[np.ndarray] = None) -> Instance:
    """stock_frac: fraksi stok saat awal shift relatif kapasitas tangki (tank_days x
    permintaan harian). TTE_i = stok / laju jual (asumsi jual merata 24 jam).
    Prioritas fuzzy dihitung dari TTE; batas akhir kedatangan = TTE - safety."""
    tot = inst.demand.sum(axis=1)
    rate = tot / 24.0
    stock = stock_frac * tank_days * tot
    tte = np.where(rate > 0, stock / np.maximum(rate, 1e-9), 99.0)
    cv = demand_cv if demand_cv is not None else np.full(inst.n + 1, 0.1)
    prio = priorities(tte, inst.D[0], cv)
    tw = inst.tw.copy()
    for i in range(1, inst.n + 1):
        tw[i, 1] = min(tw[i, 1], max(0.0, (tte[i] - safety_h) * 60))
    out = replace(inst, priority=prio, tw=tw)
    out.__dict__["tte_hours"] = tte
    return out


def stockouts(inst: Instance, sol: Solution) -> int:
    tte = inst.__dict__.get("tte_hours")
    if tte is None:
        return 0
    cnt = 0
    for tr in sol.trips:
        for i, t in zip(tr.seq, tr.arrivals):
            cnt += t > tte[i] * 60
    return cnt


# 8 ---------------------------------------------------------------------------
def erlang_c_wait(lam_per_h: float, mu_per_h: float, c: int) -> float:
    """Rerata waktu tunggu antrian M/M/c (menit)."""
    rho = lam_per_h / (c * mu_per_h)
    if rho >= 1:
        return float("inf")
    a = lam_per_h / mu_per_h
    s = sum(a ** k / math.factorial(k) for k in range(c))
    pc = (a ** c / math.factorial(c)) / (1 - rho)
    P_wait = pc / (s + pc)
    Wq_h = P_wait / (c * mu_per_h - lam_per_h)
    return Wq_h * 60


def apply_loading_rack(inst: Instance, n_racks: int = 4, other_trucks_per_h: float = 4.0,
                       mean_load_min: float = 80.0) -> Instance:
    """FT juga melayani truk lain (rute lain); laju kedatangan total
    lambda = other_trucks_per_h + ritase studi kasus/jam."""
    lam = other_trucks_per_h + inst.n / 12.0 * 0.5
    mu = 60.0 / mean_load_min
    w = erlang_c_wait(lam, mu, n_racks)
    out = inst.with_params(rack_wait=w if math.isfinite(w) else 240.0)
    return out


# 9 ---------------------------------------------------------------------------
def apply_surge(inst: Instance, factor: float = 2.0, spbu: Optional[List[int]] = None) -> Instance:
    dem = inst.demand.copy()
    idx = spbu or list(range(1, inst.n + 1))
    dem[idx] *= factor
    return replace(inst, demand=dem)


def detect_anomaly(hist: np.ndarray, today: float) -> bool:
    mu, sd = float(np.mean(hist)), float(np.std(hist))
    return abs(today - mu) > 2 * sd


# 10 --------------------------------------------------------------------------
def apply_bph_quota(inst: Instance, quota_frac: float = 0.95, product: str = "Biosolar") -> Instance:
    """Kuota harian solar subsidi = quota_frac x permintaan. Volume yang dikirim
    dibatasi kuota (audit trail mencatat selisih)."""
    if product not in inst.products:
        return inst
    p = inst.products.index(product)
    quota = np.full(inst.demand.shape, np.nan)
    quota[:, p] = inst.demand[:, p] * quota_frac
    dem = inst.demand.copy()
    dem[:, p] = np.minimum(dem[:, p], quota[:, p])
    out = replace(inst, demand=dem, quota=quota)
    out.__dict__["quota_cut_kl"] = float((inst.demand[:, p] - dem[:, p]).sum())
    return out
