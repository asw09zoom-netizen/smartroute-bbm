import numpy as np

from smartroute.data import BASELINE_ROUTES, build_instance
from smartroute.heuristics import clarke_wright, direct_routes, routes_distance
from smartroute.hybrid import HybridConfig, HybridGASARL
from smartroute.model import Evaluator, Params, VehicleType, compartment_feasible


def test_baseline_reproduced():
    inst = build_instance()
    assert abs(routes_distance(inst.D, BASELINE_ROUTES) - 279.4) < 1e-6
    assert abs(routes_distance(inst.D, direct_routes(inst.n)) - 728.2) < 1e-6
    cw = clarke_wright(inst.D, inst.total_demand(), 16.0)
    assert routes_distance(inst.D, cw) <= 279.4 + 1e-6


def test_compartment():
    vt = VehicleType("C", 16, (6, 4, 3, 3), 1, 0.3, 0, ("Pertalite", "Biosolar", "Pertamax"))
    prods = ["Pertalite", "Biosolar", "Pertamax"]
    assert compartment_feasible(vt, [8.58, 3.6, 1.66], prods) is not None
    assert compartment_feasible(vt, [9.6, 4.02, 1.86], prods) is None   # R4 baseline tidak layak


def test_hybrid_finds_optimum_small():
    inst = build_instance(params=Params(distance_only=True, single_trip=True), fleet={"C": 13})
    r = HybridGASARL(Evaluator(inst), HybridConfig(seed=0, generations=100, sa_iters=1000)).run()
    assert r.best.dist <= 279.4
    served = sorted(i for t in r.best.trips for i in t.seq)
    assert served == list(range(1, 14))
    for t in r.best.trips:
        assert inst.total_demand()[t.seq].sum() <= 16 + 1e-9
