"""Pembaca instance CVRPLIB (format VRPLIB) untuk validasi algoritma."""
from __future__ import annotations

import math
import os
import re
from typing import Tuple

import numpy as np

from .model import Instance, Params, VehicleType


def read_vrp(path: str) -> Tuple[Instance, float]:
    txt = open(path).read().splitlines()
    meta, coords, dem, sec = {}, [], [], None
    for line in txt:
        s = line.strip()
        if not s:
            continue
        if ":" in s and sec is None or s.split(":")[0].strip().isupper() and ":" in s:
            k, v = [x.strip() for x in s.split(":", 1)]
            meta[k] = v
            continue
        if s.endswith("SECTION"):
            sec = s; continue
        if s == "EOF":
            break
        parts = s.split()
        if sec == "NODE_COORD_SECTION":
            coords.append((float(parts[1]), float(parts[2])))
        elif sec == "DEMAND_SECTION":
            dem.append(float(parts[1]))
        elif sec == "DEPOT_SECTION":
            pass
    Q = float(meta["CAPACITY"])
    X = np.array(coords)
    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    if meta.get("EDGE_WEIGHT_TYPE", "EUC_2D") == "EUC_2D":
        D = np.floor(D + 0.5)  # pembulatan nint standar CVRPLIB
    q = np.array(dem).reshape(-1, 1)
    vt = VehicleType("CVRP", Q, (Q,), len(dem), 0.0, 0.0, ("BBM",))
    name = os.path.splitext(os.path.basename(path))[0]
    inst = Instance(name, D, q, ["BBM"], [vt], [str(i) for i in range(len(dem))],
                    params=Params(distance_only=True, single_trip=True))
    bks = float("nan")
    sol = path[:-4] + ".sol"
    if os.path.exists(sol):
        m = re.search(r"Cost\s+([\d.]+)", open(sol).read())
        if m:
            bks = float(m.group(1))
    return inst, bks
