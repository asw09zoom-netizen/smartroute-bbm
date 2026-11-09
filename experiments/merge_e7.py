"""Gabungkan keluaran E7 paralel (E7_cvrplib_part*.csv) menjadi results/E7_cvrplib.csv."""
import glob
import os

import pandas as pd

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
parts = sorted(glob.glob(os.path.join(RES, "E7_cvrplib_part*.csv")))
if parts:
    df = pd.concat([pd.read_csv(p) for p in parts]).sort_values(["n", "instance", "variant", "seed"])
    df.to_csv(os.path.join(RES, "E7_cvrplib.csv"), index=False)
    print("merged", len(df), "rows,", df.instance.nunique(), "instances")
