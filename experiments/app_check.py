"""Uji konsistensi aplikasi vs skrip: menjalankan GA-SA-RL dengan pengaturan bawaan aplikasi
(jalan OSM legal-truk, multi-produk, armada eksisting, bobot 0,5/0,3/0,2, seed 1) lalu menyimpan KPI.
Nilai yang tampil di aplikasi (dicatat dari tangkapan layar menu Optimasi) disimpan berdampingan.

Jalankan: python -m experiments.app_check
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from smartroute.data import BASELINE_ROUTES, build_instance, load_tables  # noqa: E402
from smartroute.hybrid import HybridConfig, HybridGASARL  # noqa: E402
from smartroute.model import Evaluator, evaluate_routes  # noqa: E402

# KPI yang ditampilkan aplikasi (menu Optimasi, pengaturan bawaan, 11 Nov 2026)
APP = dict(fitness=0.4701, dist_km=283.2, cost_rp=3.43e6, co2_kg=268.4, trucks=2, trips=5, late=0, overtime=0,
           runtime_s=9.7)

if __name__ == "__main__":
    t = load_tables()
    inst = build_instance(t, multiproduct=True, road="osm")
    ev = Evaluator(inst)
    r = HybridGASARL(ev, HybridConfig(variant="GA-SA-RL", seed=1)).run()
    s = r.best.summary()
    b = evaluate_routes(Evaluator(inst), BASELINE_ROUTES).summary()
    out = dict(app=APP, script=s, script_runtime_s=r.runtime, baseline=b)
    json.dump(out, open(os.path.join(ROOT, "results", "APP_check.json"), "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))
