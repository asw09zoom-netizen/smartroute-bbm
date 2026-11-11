"""
Model MC-MP-MT-VRP (Multi-Compartment, Multi-Product, Multi-Trip VRP) SMARTROUTE-BBM.

Struktur solusi
---------------
Kromosom   : permutasi SPBU (giant tour).
Decoder    : prosedur Split (Prins, 2004) yang dimodifikasi untuk armada heterogen
             multi-kompartemen -> himpunan ritase (trip) beserta tipe truknya.
Scheduler  : penugasan ritase ke unit truk (multi-trip) dengan batas shift dan
             batas jumlah ritase, waktu tempuh time-dependent, time window SPBU,
             dan antrian loading rack FT.
Evaluasi   : Z1 biaya, Z2 emisi CO2 (IPCC Tier 2 + koreksi beban & kecepatan),
             Z3 waktu, ditambah fungsi penalti Pi(x).

Satuan: jarak km, volume KL, waktu menit (t=0 = awal shift), biaya Rupiah,
emisi kg CO2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

PRODUCTS_ALL = ["Pertalite", "Pertamax", "Pertamax Turbo", "Biosolar", "Pertamina Dex"]


# ---------------------------------------------------------------------------
# Struktur data
# ---------------------------------------------------------------------------
@dataclass
class VehicleType:
    name: str                      # "A", "B", "C", "D"
    capacity: float                # KL
    compartments: Tuple[float, ...]  # kapasitas tiap kompartemen (KL)
    count: int                     # jumlah unit tersedia
    fc0: float                     # konsumsi BBM truk kosong (L/km)
    fixed_cost: float              # biaya tetap per unit per hari (Rp)
    allowed_products: Tuple[str, ...] = tuple(PRODUCTS_ALL)
    min_road_width: float = 0.0    # m (informasi restriksi jalan)


@dataclass
class Params:
    # Bobot fungsi objektif (w1 biaya, w2 emisi, w3 waktu)
    w: Tuple[float, float, float] = (0.50, 0.30, 0.20)
    # Biaya
    fuel_price: float = 12_000.0     # Rp/L solar industri (asumsi, dapat diubah)
    maint_per_km: float = 1_500.0    # Rp/km (asumsi)
    # Emisi (IPCC 2006 Tier 2)
    ef: float = 2.68                 # kg CO2 / L solar
    beta: float = 0.30               # koefisien beban
    alpha1: float = 0.0001           # koefisien koreksi kecepatan
    v0: float = 65.0                 # kecepatan optimal (km/jam)
    # Waktu
    vmax: float = 40.0               # kecepatan rata-rata arus bebas truk tangki (km/jam)
    congestion: Tuple[float, ...] = tuple([1.0] * 24)  # CF(t) per jam, 0.2..1.0
    shift_start_h: float = 6.0       # jam mulai shift
    shift_len: float = 12 * 60.0     # menit
    max_trips: int = 3               # batas ritase per truk per shift
    load_min_per_kl: float = 5.0     # loading FT: 80 menit / 16 KL
    unload_fixed: float = 15.0       # menit per SPBU (bongkar, administrasi)
    unload_per_kl: float = 2.5       # menit per KL
    rack_wait: float = 0.0           # rerata antrian loading rack (menit, Erlang-C)
    # Penalti
    pen_late: float = 0.02           # per menit keterlambatan x prioritas/100
    pen_overtime: float = 0.02       # per menit lewat shift
    pen_fleet: float = 5.0           # per ritase tanpa truk tersedia
    pen_quota: float = 1.0           # per KL kelebihan kuota
    # Mode
    single_trip: bool = False        # True = tiap truk hanya 1 ritase (setara baseline)
    distance_only: bool = False      # True = objektif murni jarak (CVRP klasik/benchmark)
    cap_safety: float = 1.0
    split_fixed_amort: bool = True   # Split memperhitungkan biaya tetap truk yang diamortisasi per ritase          # faktor pengaman kapasitas (<=1)


@dataclass
class Instance:
    name: str
    D: np.ndarray                    # (n+1)x(n+1) km, 0 = depot
    demand: np.ndarray               # (n+1) x |P| KL
    products: List[str]
    vtypes: List[VehicleType]
    labels: List[str]
    coords: Optional[np.ndarray] = None   # (n+1)x2 lat,lon
    tw: Optional[np.ndarray] = None       # (n+1)x2 menit [a,b]
    priority: Optional[np.ndarray] = None  # (n+1) skor 0..100
    access: Optional[np.ndarray] = None    # (n+1) x |K| bool, akses tipe truk
    quota: Optional[np.ndarray] = None     # (n+1) x |P| KL (nan = tanpa kuota)
    params: Params = field(default_factory=Params)
    Dk: Optional[np.ndarray] = None        # |K| x (n+1) x (n+1) km jalan legal per tipe truk (NaN = tak ada lintasan)

    @property
    def n(self) -> int:
        return self.D.shape[0] - 1

    def total_demand(self) -> np.ndarray:
        return self.demand.sum(axis=1)

    def with_params(self, **kw) -> "Instance":
        return replace(self, params=replace(self.params, **kw))


# ---------------------------------------------------------------------------
# Kelayakan kompartemen
# ---------------------------------------------------------------------------
@lru_cache(maxsize=200_000)
def _comp_assign(comps: Tuple[float, ...], vols: Tuple[float, ...]) -> Optional[Tuple[int, ...]]:
    """Cari penugasan kompartemen->produk sehingga tiap produk p dengan volume
    vols[p] > 0 mendapat himpunan kompartemen (tidak tercampur) dengan total
    kapasitas >= vols[p]. Mengembalikan tuple indeks produk per kompartemen
    (-1 = kosong) atau None bila tidak layak. Pencarian eksak (<=5 kompartemen)."""
    m = len(comps)
    need = [(v, p) for p, v in enumerate(vols) if v > 1e-9]
    need.sort(reverse=True)
    if sum(v for v, _ in need) > sum(comps) + 1e-9:
        return None
    if len(need) > m:
        return None
    assign = [-1] * m
    full = (1 << m) - 1

    masks_by_cap = []
    for mask in range(1, full + 1):
        cap = sum(comps[i] for i in range(m) if mask >> i & 1)
        masks_by_cap.append((cap, bin(mask).count("1"), mask))
    masks_by_cap.sort()

    def rec(k: int, free: int) -> bool:
        if k == len(need):
            return True
        v, p = need[k]
        for cap, _, mask in masks_by_cap:
            if mask & ~free:
                continue
            if cap + 1e-9 < v:
                continue
            for i in range(m):
                if mask >> i & 1:
                    assign[i] = p
            if rec(k + 1, free & ~mask):
                return True
            for i in range(m):
                if mask >> i & 1:
                    assign[i] = -1
        return False

    if rec(0, full):
        return tuple(assign)
    return None


def compartment_feasible(vt: VehicleType, vols: Sequence[float], products: List[str],
                         safety: float = 1.0) -> Optional[Tuple[int, ...]]:
    for p, v in enumerate(vols):
        if v > 1e-9 and products[p] not in vt.allowed_products and products[p] != "BBM":
            return None
    comps = tuple(round(c * safety, 4) for c in vt.compartments)
    return _comp_assign(comps, tuple(round(float(v), 4) for v in vols))


# ---------------------------------------------------------------------------
# Fungsi emisi & bahan bakar
# ---------------------------------------------------------------------------
def speed_factor(v: float, p: Params) -> float:
    return 1.0 + p.alpha1 * (v - p.v0) ** 2


def cf_at(p: Params, t_min: float) -> float:
    h = int(((p.shift_start_h * 60 + t_min) // 60) % 24)
    return max(0.2, min(1.0, p.congestion[h]))


# ---------------------------------------------------------------------------
# Hasil
# ---------------------------------------------------------------------------
@dataclass
class Trip:
    seq: List[int]
    vtype: int
    load: float
    vols: np.ndarray
    comp_assign: Tuple[int, ...]
    dist: float
    truck: int = -1           # indeks unit truk global
    trip_no: int = 0          # ritase ke-
    start: float = 0.0        # menit
    end: float = 0.0
    arrivals: List[float] = field(default_factory=list)
    fuel: float = 0.0
    co2: float = 0.0
    cost: float = 0.0


@dataclass
class Solution:
    perm: List[int]
    trips: List[Trip]
    fitness: float
    Z1: float
    Z2: float
    Z3: float
    dist: float
    penalty: float
    trucks_used: int
    late_min: float
    overtime_min: float
    unassigned: int
    info: Dict = field(default_factory=dict)

    def summary(self) -> Dict:
        return dict(fitness=self.fitness, dist_km=self.dist, cost_rp=self.Z1, co2_kg=self.Z2,
                    time_min=self.Z3, trips=len(self.trips), trucks=self.trucks_used,
                    late_min=self.late_min, overtime_min=self.overtime_min,
                    unassigned=self.unassigned, penalty=self.penalty)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------
class Evaluator:
    """Menyimpan cache dan referensi normalisasi untuk satu instance."""

    def __init__(self, inst: Instance):
        self.inst = inst
        self.p = inst.params
        self.n = inst.n
        self.D = inst.D
        self.q = inst.demand
        self.qtot = inst.demand.sum(axis=1)
        self.nP = inst.demand.shape[1]
        self.K = len(inst.vtypes)
        self.prio = inst.priority if inst.priority is not None else np.full(self.n + 1, 50.0)
        self.access = inst.access if inst.access is not None else np.ones((self.n + 1, self.K), bool)
        self.Dk = None
        if inst.Dk is not None:
            # jarak jalan legal per tipe truk; SPBU tanpa lintasan legal -> tidak boleh dilayani tipe itu
            Dk = np.asarray(inst.Dk, dtype=float)
            reach = np.isfinite(Dk[:, 0, :]) & np.isfinite(Dk[:, :, 0])  # K x (n+1)
            self.access = self.access & reach.T
            self.Dk = np.where(np.isfinite(Dk), Dk, 1e6)
        self.n_evals = 0
        self.default_avail = None   # waktu siap truk default (dipakai pada re-routing dinamis)
        # batas panjang segmen pada split (kapasitas terbesar)
        self.maxcap = max(v.capacity for v in inst.vtypes) * self.p.cap_safety
        # referensi normalisasi: pengiriman langsung (direct delivery)
        self.ref = (1.0, 1.0, 1.0)
        if not self.p.distance_only:
            self.ref = self._direct_reference()

    # -- trip-level (tanpa jadwal) ------------------------------------------
    def _trip_static(self, seq: Sequence[int], k: int) -> Tuple[float, float, float, float]:
        """dist, fuel(L), duration(min, kecepatan arus bebas), cost var (Rp)."""
        p = self.p
        vt = self.inst.vtypes[k]
        D = self.D if self.Dk is None else self.Dk[k]
        load = float(sum(self.qtot[i] for i in seq))
        dist = 0.0
        fuel = 0.0
        prev = 0
        L = load
        g = speed_factor(p.vmax, p)
        for i in seq:
            d = D[prev, i]
            dist += d
            fuel += vt.fc0 * (1 + p.beta * L / vt.capacity) * g * d
            L -= self.qtot[i]
            prev = i
        d = D[prev, 0]
        dist += d
        fuel += vt.fc0 * g * d
        dur = (load * p.load_min_per_kl + dist / p.vmax * 60
               + len(seq) * p.unload_fixed + load * p.unload_per_kl)
        cost = fuel * p.fuel_price + dist * p.maint_per_km
        return dist, fuel, dur, cost

    def best_type(self, seq: Sequence[int]) -> Optional[Tuple[int, Tuple[int, ...], float]]:
        """Tipe truk dengan biaya terbobot terendah yang layak untuk segmen."""
        vols = self.q[list(seq)].sum(axis=0)
        load = vols.sum()
        best = None
        for k, vt in enumerate(self.inst.vtypes):
            if vt.count <= 0 or load > vt.capacity * self.p.cap_safety + 1e-9:
                continue
            if not all(self.access[i, k] for i in seq):
                continue
            ca = compartment_feasible(vt, vols, self.inst.products, self.p.cap_safety)
            if ca is None:
                continue
            c = self.trip_weighted(seq, k)
            if self.p.split_fixed_amort and not self.p.distance_only:
                mt = 1 if self.p.single_trip else self.p.max_trips
                c += self.p.w[0] * vt.fixed_cost / (mt * self.ref[0])
            if best is None or c < best[2]:
                best = (k, ca, c)
        return best

    def trip_weighted(self, seq: Sequence[int], k: int) -> float:
        dist, fuel, dur, cost = self._trip_static(seq, k)
        if self.p.distance_only:
            return dist
        w1, w2, w3 = self.p.w
        r1, r2, r3 = self.ref
        return w1 * cost / r1 + w2 * fuel * self.p.ef / r2 + w3 * dur / r3

    def _direct_reference(self) -> Tuple[float, float, float]:
        c = e = t = 0.0
        p = self.p
        for i in range(1, self.n + 1):
            best = None
            for k, vt in enumerate(self.inst.vtypes):
                if vt.count <= 0 or self.qtot[i] > vt.capacity * p.cap_safety or not self.access[i, k]:
                    continue
                dist, fuel, dur, cost = self._trip_static([i], k)
                if best is None or cost < best[0]:
                    best = (cost, fuel * p.ef, dur)
            if best is None:  # permintaan > truk terbesar: pakai tipe terbesar
                k = int(np.argmax([v.capacity for v in self.inst.vtypes]))
                dist, fuel, dur, cost = self._trip_static([i], k)
                best = (cost, fuel * p.ef, dur)
            c += best[0]; e += best[1]; t += best[2]
        fixed = max(v.fixed_cost for v in self.inst.vtypes)
        return (c + fixed * max(1, self.n // 3), e, t)

    # -- Split (Prins 2004), armada heterogen ---------------------------------
    def split(self, perm: Sequence[int]) -> List[Tuple[List[int], int, Tuple[int, ...]]]:
        n = len(perm)
        INF = float("inf")
        V = [INF] * (n + 1)
        pred = [-1] * (n + 1)
        choice: List[Optional[Tuple[int, Tuple[int, ...]]]] = [None] * (n + 1)
        V[0] = 0.0
        qtot = self.qtot
        for i in range(n):
            if V[i] == INF:
                continue
            load = 0.0
            seg: List[int] = []
            for j in range(i, n):
                c = perm[j]
                load += qtot[c]
                if load > self.maxcap + 1e-9:
                    break
                seg.append(c)
                bt = self.best_type(seg)
                if bt is None:
                    if len(seg) == 1:  # permintaan tunggal tidak muat / tak terjangkau -> tetap paksa
                        caps = [v.capacity if self.access[c, kk] else -1.0
                                for kk, v in enumerate(self.inst.vtypes)]
                        if max(caps) < 0:  # tak ada tipe yang punya lintasan legal
                            caps = [v.capacity for v in self.inst.vtypes]
                        k = int(np.argmax(caps))
                        cost = self.trip_weighted(seg, k) + self.p.pen_fleet
                        bt = (k, tuple(), cost)
                    else:
                        continue
                k, ca, cost = bt
                if V[i] + cost < V[j + 1] - 1e-12:
                    V[j + 1] = V[i] + cost
                    pred[j + 1] = i
                    choice[j + 1] = (k, ca)
        trips = []
        j = n
        while j > 0:
            i = pred[j]
            k, ca = choice[j]
            trips.append((list(perm[i:j]), k, ca))
            j = i
        trips.reverse()
        return trips

    # -- Penjadwalan multi-trip ---------------------------------------------
    def _simulate_trip(self, seq: List[int], k: int, t0: float) -> Tuple[float, List[float], float, float, float]:
        """Simulasi time-dependent satu ritase mulai t0. -> end, arrivals, dist, fuel, late."""
        p = self.p
        vt = self.inst.vtypes[k]
        D = self.D if self.Dk is None else self.Dk[k]
        load = float(sum(self.qtot[i] for i in seq))
        t = t0 + p.rack_wait + load * p.load_min_per_kl
        prev = 0
        L = load
        dist = fuel = late = 0.0
        arr = []
        tw = self.inst.tw
        for i in seq:
            d = D[prev, i]
            v = p.vmax * cf_at(p, t)
            t += d / v * 60
            fuel += vt.fc0 * (1 + p.beta * L / vt.capacity) * speed_factor(v, p) * d
            dist += d
            if tw is not None:
                if t < tw[i, 0]:
                    t = tw[i, 0]
                if t > tw[i, 1]:
                    late += (t - tw[i, 1]) * self.prio[i] / 100.0
            arr.append(t)
            t += p.unload_fixed + self.qtot[i] * p.unload_per_kl
            L -= self.qtot[i]
            prev = i
        d = D[prev, 0]
        v = p.vmax * cf_at(p, t)
        t += d / v * 60
        fuel += vt.fc0 * speed_factor(v, p) * d
        dist += d
        return t, arr, dist, fuel, late

    def schedule(self, raw_trips, truck_avail: Optional[List[Tuple[int, float]]] = None,
                 fixed_units: Optional[List[int]] = None) -> Tuple[List[Trip], Dict]:
        """Tugaskan ritase ke unit truk. truck_avail: daftar (tipe, waktu siap)
        per unit; default seluruh armada siap di t=0."""
        p = self.p
        if truck_avail is None:
            truck_avail = self.default_avail
        if truck_avail is None:
            truck_avail = [(k, 0.0) for k, vt in enumerate(self.inst.vtypes) for _ in range(vt.count)]
        units = [{"k": k, "t": t, "n": 0, "used": False} for k, t in truck_avail]
        # urutan ritase: prioritas fuzzy tertinggi lebih dulu, lalu durasi terpanjang (LPT)
        order = []
        for idx, (seq, k, ca) in enumerate(raw_trips):
            pr = max(self.prio[i] for i in seq)
            dur = self._trip_static(seq, k)[2]
            order.append((-pr, -dur, idx))
        order.sort()
        if fixed_units is not None:   # penugasan unit dan urutan ritase ditetapkan pemanggil
            order = [(0, 0, idx) for idx in range(len(raw_trips))]
        trips: List[Trip] = []
        unassigned = 0
        late_tot = over_tot = 0.0
        for _, _, idx in order:
            seq, k, ca = raw_trips[idx]
            maxtrips = 1 if p.single_trip else p.max_trips
            # kandidat unit: tipe sama dulu, lalu tipe lain yang layak
            cands = []
            for u_i, u in enumerate(units):
                if fixed_units is not None and u_i != fixed_units[idx]:
                    continue
                if u["n"] >= maxtrips:
                    continue
                kk = u["k"]
                if not all(self.access[i, kk] for i in seq):
                    continue
                if kk != k or not ca:  # tipe lain, atau ritase paksaan (kompartemen belum terbukti layak)
                    vols = self.q[seq].sum(axis=0)
                    if vols.sum() > self.inst.vtypes[kk].capacity * p.cap_safety + 1e-9:
                        continue
                    if compartment_feasible(self.inst.vtypes[kk], vols, self.inst.products, p.cap_safety) is None:
                        continue
                end, arr, dist, fuel, late = self._simulate_trip(seq, kk, u["t"])
                over = max(0.0, end - p.shift_len)
                score = (kk != k, over > 0, late + over, (not u["used"]), end)
                cands.append((score, u_i, kk, end, arr, dist, fuel, late, over))
            if not cands:
                unassigned += 1
                end, arr, dist, fuel, late = self._simulate_trip(seq, k, 0.0)
                tr = Trip(seq, k, float(self.qtot[seq].sum()), self.q[seq].sum(axis=0), ca, dist,
                          truck=-1, trip_no=0, start=0.0, end=end, arrivals=arr, fuel=fuel)
                trips.append(tr)
                continue
            cands.sort(key=lambda c: c[0])
            _, u_i, kk, end, arr, dist, fuel, late, over = cands[0]
            u = units[u_i]
            start = u["t"]
            u["t"] = end
            u["n"] += 1
            u["used"] = True
            vols = self.q[seq].sum(axis=0)
            if kk != k:
                ca = compartment_feasible(self.inst.vtypes[kk], vols, self.inst.products, p.cap_safety) or tuple()
            tr = Trip(seq, kk, float(vols.sum()), vols, ca, dist, truck=u_i, trip_no=u["n"],
                      start=start, end=end, arrivals=arr, fuel=fuel)
            late_tot += late
            over_tot += over
            trips.append(tr)
        used = sum(1 for u in units if u["used"])
        used_by_type = {}
        for u in units:
            if u["used"]:
                used_by_type[u["k"]] = used_by_type.get(u["k"], 0) + 1
        return trips, dict(unassigned=unassigned, late=late_tot, over=over_tot, used=used,
                           used_by_type=used_by_type)

    # -- Evaluasi lengkap ------------------------------------------------------
    def evaluate(self, perm: Sequence[int], truck_avail=None) -> Solution:
        self.n_evals += 1
        p = self.p
        raw = None if (p.distance_only and self.K == 1 and self.nP == 1) else self.split(perm)
        if p.distance_only and self.K == 1 and self.nP == 1:
            dist, routes = split_cvrp(perm, self.D, self.qtot, self.maxcap)
            trips = [Trip(r, 0, float(self.qtot[r].sum()), self.q[r].sum(axis=0), tuple(), 0.0) for r in routes]
            return Solution(list(perm), trips, dist, dist, dist, 0.0, dist, 0.0, len(routes), 0, 0, 0)
        if p.distance_only:
            dist = sum(self._trip_static(s, k)[0] for s, k, _ in raw)
            trips = [Trip(s, k, float(self.qtot[s].sum()), self.q[s].sum(axis=0), ca,
                          self._trip_static(s, k)[0]) for s, k, ca in raw]
            return Solution(list(perm), trips, dist, dist, dist, 0.0, dist, 0.0, len(raw), 0, 0, 0)
        trips, info = self.schedule(raw, truck_avail)
        dist = sum(t.dist for t in trips)
        fuel = sum(t.fuel for t in trips)
        Z2 = fuel * p.ef
        fixed = sum(self.inst.vtypes[k].fixed_cost * c for k, c in info["used_by_type"].items())
        var_cost = fuel * p.fuel_price + dist * p.maint_per_km
        Z1 = var_cost + fixed
        Z3 = sum(t.end - t.start for t in trips) + info["late"]
        for t in trips:
            t.co2 = t.fuel * p.ef
            t.cost = t.fuel * p.fuel_price + t.dist * p.maint_per_km
        # kuota BPH Migas
        quota_ex = 0.0
        if self.inst.quota is not None:
            qq = np.nan_to_num(self.inst.quota, nan=np.inf)
            quota_ex = float(np.clip(self.q - qq, 0, None).sum())
        w1, w2, w3 = p.w
        r1, r2, r3 = self.ref
        pen = (p.pen_late * info["late"] + p.pen_overtime * info["over"]
               + p.pen_fleet * info["unassigned"] + p.pen_quota * quota_ex)
        fit = w1 * Z1 / r1 + w2 * Z2 / r2 + w3 * Z3 / r3 + pen
        return Solution(list(perm), trips, fit, Z1, Z2, Z3, dist, pen, info["used"],
                        info["late"], info["over"], info["unassigned"],
                        info=dict(fixed_cost=fixed, var_cost=var_cost, fuel_l=fuel,
                                  quota_excess=quota_ex, used_by_type=info["used_by_type"]))

    def fitness(self, perm: Sequence[int]) -> float:
        return self.evaluate(perm).fitness


def evaluate_routes(ev: Evaluator, routes: List[List[int]], vtypes: Optional[List[int]] = None,
                    truck_avail=None, fixed_units: Optional[List[int]] = None) -> Solution:
    """Evaluasi solusi rute yang diberikan langsung (mis. baseline Saving Matrix)
    tanpa melalui split, agar dibandingkan dengan fungsi objektif yang sama."""
    raw = []
    for r_i, r in enumerate(routes):
        if vtypes is not None:
            k = vtypes[r_i]
            vols = ev.q[r].sum(axis=0)
            ca = compartment_feasible(ev.inst.vtypes[k], vols, ev.inst.products, ev.p.cap_safety) or tuple()
        else:
            bt = ev.best_type(r)
            if bt is None:  # tidak ada tipe tersedia yang layak -> paksa tipe terbesar yang punya lintasan legal
                caps = [v.capacity if all(ev.access[i, kk] for i in r) else -1.0
                        for kk, v in enumerate(ev.inst.vtypes)]
                if max(caps) < 0:
                    caps = [v.capacity for v in ev.inst.vtypes]
                k = int(np.argmax(caps)); ca = tuple()
            else:
                k, ca, _ = bt
        raw.append((list(r), k, ca))
    perm = [i for r in routes for i in r]
    p = ev.p
    if p.distance_only:
        trips = [Trip(s, k, float(ev.qtot[s].sum()), ev.q[s].sum(axis=0), ca, ev._trip_static(s, k)[0])
                 for s, k, ca in raw]
        dist = sum(t.dist for t in trips)
        return Solution(perm, trips, dist, dist, dist, 0, dist, 0, len(trips), 0, 0, 0)
    trips, info = ev.schedule(raw, truck_avail, fixed_units)
    dist = sum(t.dist for t in trips)
    fuel = sum(t.fuel for t in trips)
    for t in trips:
        t.co2 = t.fuel * p.ef
        t.cost = t.fuel * p.fuel_price + t.dist * p.maint_per_km
    fixed = sum(ev.inst.vtypes[k].fixed_cost * c for k, c in info["used_by_type"].items())
    Z1 = fuel * p.fuel_price + dist * p.maint_per_km + fixed
    Z2 = fuel * p.ef
    Z3 = sum(t.end - t.start for t in trips) + info["late"]
    w1, w2, w3 = p.w
    r1, r2, r3 = ev.ref
    pen = p.pen_late * info["late"] + p.pen_overtime * info["over"] + p.pen_fleet * info["unassigned"]
    fit = w1 * Z1 / r1 + w2 * Z2 / r2 + w3 * Z3 / r3 + pen
    return Solution(perm, trips, fit, Z1, Z2, Z3, dist, pen, info["used"], info["late"], info["over"],
                    info["unassigned"], info=dict(fixed_cost=fixed, fuel_l=fuel, used_by_type=info["used_by_type"]))


def split_cvrp(perm: Sequence[int], D: np.ndarray, q: np.ndarray, Q: float) -> Tuple[float, List[List[int]]]:
    """Split O(n*L) untuk CVRP homogen murni jarak (dipakai pada benchmark CVRPLIB)."""
    n = len(perm)
    INF = float("inf")
    V = [INF] * (n + 1)
    pred = [0] * (n + 1)
    V[0] = 0.0
    Dl = D
    for i in range(n):
        vi = V[i]
        if vi == INF:
            continue
        load = 0.0
        cost = 0.0
        first = perm[i]
        prev = first
        for j in range(i, n):
            c = perm[j]
            load += q[c]
            if load > Q + 1e-9:
                break
            if j == i:
                cost = Dl[0, c]
            else:
                cost += Dl[prev, c]
            tot = vi + cost + Dl[c, 0]
            if tot < V[j + 1]:
                V[j + 1] = tot
                pred[j + 1] = i
            prev = c
    routes = []
    j = n
    while j > 0:
        i = pred[j]
        routes.append(list(perm[i:j]))
        j = i
    routes.reverse()
    return V[n], routes
