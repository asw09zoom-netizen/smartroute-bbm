import sys,itertools,json;import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from smartroute.cvrplib import read_vrp
from smartroute.model import Evaluator
from smartroute.data import build_instance
from smartroute.hybrid import HybridGASARL,HybridConfig
which=sys.argv[1]
if which=='x':
    inst,_=read_vrp(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','cvrplib','X-n101-k25.vrp')); key='dist'
else:
    inst=build_instance(multiproduct=True); key='fitness'
ev=Evaluator(inst)
for sc,rs in itertools.product([1e5,1e6,1e7],[0,200]):
    for v in ['GA-SA','GA-SA-RL']:
        imp=[]
        for seed in [100,101,102]:
            r=HybridGASARL(ev,HybridConfig(variant=v,seed=seed,sa_scale=sc,sa_restart=rs)).run()
            fb=getattr(r.best,key) if key=='dist' else r.best.fitness
            imp.append((r.ga_best-fb)/r.ga_best*100)
        print(which, f"scale={sc:.0e} restart={rs} {v}: SA improvement % over GA = {np.round(imp,3)} mean {np.mean(imp):.3f}", flush=True)
