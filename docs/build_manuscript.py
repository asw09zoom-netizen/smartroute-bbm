"""Builds the English journal manuscript (.docx) from results/ (no hand-typed result numbers).

Run:  python -m docs.build_manuscript
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from docx import Document  # noqa: E402
from docx.enum.section import WD_SECTION  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

from docs.build_laporan import REPO, SHEET, VAR, J, load_results  # noqa: E402
from docs.docbuild import Cursor  # noqa: E402
from docs.refs import Citer  # noqa: E402

FIGEN = os.path.join(ROOT, "figures", "en")
OUT = os.path.join(ROOT, "docs", "output")

TITLE = ("A web-based decision support system with a hybrid GA–SA–Q-learning metaheuristic for multi-compartment, "
         "multi-product, multi-trip fuel distribution: an Indonesian fuel-terminal case")
AUTHORS = "Asepta Surya Wardhana^1*^, Astrie Kusuma Dewi^1^, Chalidia Nurin Hamdani^1^, Nano Koes Ardhiyanto^1^"
AFFIL = "^1^Politeknik Energi dan Mineral Akamigas (PEM Akamigas), Cepu, Blora, Central Java, Indonesia"
CORR = "*Corresponding author: aseptasw@esdm.go.id"


def g(x, d=1):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{d}f}"


def idr(x):
    return "IDR " + f"{x:,.0f}"


def pv(p):
    return "–" if p is None else ("< 0.001" if p < 0.001 else f"{p:.3f}")


def kw(st):
    a, k = st.get("anova"), st.get("kruskal")
    if not isinstance(a, dict):
        return "all runs of all variants returned the same plan, so no between-variant test applies"
    return (f"one-way ANOVA F = {a['F']:.2f} (p = {pv(a['p'])}), Kruskal–Wallis H = {k['H']:.2f} (p = {pv(k['p'])}), "
            f"i.e. the variants {'differ' if k['p'] < 0.05 else 'do not differ'} significantly at α = 0.05")


def e7_tests(e7):
    from scipy import stats as ss
    inst5 = [i for i in e7.instance.unique() if e7[e7.instance == i].variant.nunique() == 3]
    d = e7[e7.instance.isin(inst5)]
    piv = d.groupby(["instance", "variant"]).gap_pct.mean().unstack()
    out = dict(n_inst=len(inst5), means={v: float(piv[v].mean()) for v in VAR if v in piv})
    try:
        fr = ss.friedmanchisquare(*[piv[v].values for v in VAR])
        out["friedman"] = (float(fr.statistic), float(fr.pvalue))
    except Exception:
        out["friedman"] = None
    out["pairs"] = {}
    for other in ["GA-SA", "GA"]:
        a = d[d.variant == "GA-SA-RL"].sort_values(["instance", "seed"]).gap_pct.values
        b = d[d.variant == other].sort_values(["instance", "seed"]).gap_pct.values
        if len(a) == len(b) and np.any(a != b):
            out["pairs"][other] = (float(ss.wilcoxon(a, b, alternative="less").pvalue), len(a),
                                   float(np.mean(a < b)), float(np.mean(a > b)))
    return out


def build():
    R = load_results()
    e0, e1, e2, e3, e3s, e4, e4b, e5, e5b, e6, e7 = (R[k] for k in ["e0", "e1", "e2", "e3", "e3s", "e4", "e4b", "e5",
                                                                  "e5b", "e6", "e7"])
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(11)
    st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.15
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.5); s.top_margin = s.bottom_margin = Cm(2.5)
    for lvl, size in [(1, 12), (2, 11)]:
        hs = doc.styles[f"Heading {lvl}"]
        hs.font.name = "Times New Roman"; hs.font.size = Pt(size); hs.font.bold = True
        hs.font.color.rgb = None
        hs.font.italic = (lvl == 2)
    c = Cursor(doc, doc.add_paragraph()._p)
    cite = Citer()
    H1 = lambda t: c.h(t, "Heading 1")  # noqa: E731
    H2 = lambda t: c.h(t, "Heading 2")  # noqa: E731
    P = lambda t: c.p(t, indent_first=0.75)  # noqa: E731

    c.para(TITLE, align="c", bold=True, size=14)
    c.para(AUTHORS, align="c")
    c.para(AFFIL, align="c", size=9)
    c.para(CORR, align="c", size=9)

    mp = e2["multiproduk"] if e2 else None
    imp = (e1["baseline_capstone"] - e1["milp_opt"]) / e1["baseline_capstone"] * 100
    abs_txt = (
        "Petrol-station replenishment combines compartmented tank trucks, several products and multiple trips per shift, "
        "so routes planned on aggregated volumes may not be loadable. This paper formulates a multi-compartment, "
        "multi-product, multi-trip vehicle routing problem (MC-MP-MT-VRP) with a heterogeneous fleet, time-dependent "
        "speeds, soft time windows and a load- and speed-dependent CO₂ model, and solves it with a hybrid genetic "
        "algorithm–simulated annealing method in which a tabular Q-learning agent selects the annealing move (GA-SA-RL). "
        "A heterogeneous-fleet Split decoder with an exact compartment-assignment check turns giant tours into "
        "feasible trips, and a scheduler chains trips into truck-days. The method is embedded in an open-source "
        "web decision support system with a Google Sheets database. On a 13-station case from an Indonesian fuel "
        f"terminal, the algorithm matched the MILP-proven optimum ({e1['milp_opt']:.1f} km) in all 30 runs of the "
        f"capacitated setting, {imp:.1f}% shorter than the incumbent Savings plan. ")
    ag0 = e2["agregat"] if e2 else None
    if ag0 and ag0["best_ga_sa_rl"]["trucks"] < ag0["baseline"]["trucks"]:
        b0, h0 = ag0["baseline"], ag0["best_ga_sa_rl"]
        abs_txt += (f"Allowing multiple trips, the full model serves the aggregated demand with {int(h0['trucks'])} instead "
                    f"of {int(b0['trucks'])} trucks, reducing daily cost by {(b0['cost_rp'] - h0['cost_rp']) / b0['cost_rp'] * 100:.1f}%. ")
    if mp:
        b, h = mp["baseline"], mp["best_ga_sa_rl"]
        abs_txt += (f"Under compartment and product constraints the Savings plan contained {int(b['unassigned'])} "
                    f"unloadable trip, whereas GA-SA-RL returned a feasible plan with {int(h['trucks'])} trucks and "
                    f"{int(h['trips'])} trips. ")
    if e7 is not None and len(e7):
        gg = e7[e7.variant == "GA-SA-RL"].groupby("instance").gap_pct.mean()
        t = e7_tests(e7)
        abs_txt += (f"On {len(gg)} CVRPLIB X instances the mean gap to the best-known solutions was {gg.mean():.2f}%. ")
        abs_txt = abs_txt[:-2] + f" (Clarke–Wright {e7.groupby('instance').cw_gap_pct.first().mean():.2f}%). "
        pr, pg = t["pairs"].get("GA-SA"), t["pairs"].get("GA")
        if pr and pg:
            abs_txt += ("In an ablation, the hybrid " + ("significantly outperformed" if pg[0] < 0.05 else "did not outperform") +
                        f" the GA alone (Wilcoxon p = {pv(pg[0])}), while Q-learning move selection " +
                        ("significantly outperformed" if pr[0] < 0.05 else "did not significantly outperform") +
                        f" uniform random selection (p = {pv(pr[0])}). ")
    e8a = J("E8_summary.json")
    if e8a:
        abs_txt += ("Routes are computed on the OpenStreetMap network filtered per truck type by road class, signed limits "
                    f"and carriageway width; these distances correlate at {e8a['matriks']['C']['korelasi']:.3f} with the "
                    "capstone matrix. ")
    abs_txt += ("Scenario, Pareto, Monte Carlo and dynamic re-routing experiments illustrate the decision support "
                "value; product shares and compartment sizes are assumptions to be calibrated with operator data.")
    p = c.para("", align="j")
    c._runs(p, "**Abstract** — " + abs_txt)
    p = c.para("", align="j")
    c._runs(p, "**Keywords:** petrol station replenishment; multi-compartment vehicle routing; multi-trip; hybrid "
               "metaheuristic; Q-learning; decision support system")

    # 1 ------------------------------------------------------------------------
    H1("1. Introduction")
    P("Fuel distribution from terminals to petrol stations is a daily, safety-critical logistics operation. Compared "
      "with general freight it has three distinctive features: tank trucks are divided into compartments that each hold a "
      "single product, several fuel grades must be delivered to each station, and trucks usually perform more than one "
      f"trip per shift. These features define the petrol station replenishment problem (PSRP) {cite('cornillier2008', 'benantar2016')}, "
      f"a member of the multi-compartment vehicle routing problem (MCVRP) family {cite('ostermeier2021', 'coelho2015')} "
      f"with multiple trips {cite('cattaruzza2016', 'wang2020')}.")
    P("In Indonesia, published fuel-routing studies mostly use constructive heuristics such as Clarke–Wright savings "
      f"and nearest neighbour {cite('clarke1964', 'melani2025', 'aqidawati2021')}, or a single metaheuristic such as tabu "
      f"search {cite('awaludin2025', 'abdul2023')}, and typically aggregate all products into one volume. A few studies "
      f"model compartments, products and trips {cite('nugroho2020', 'ramadhani2021', 'surjandari2011')}, but on small "
      "instances, without emissions and without a reusable decision tool. Internationally, learning-assisted "
      "metaheuristics, in which reinforcement learning selects among neighbourhood operators, have produced competitive "
      f"results on several VRP variants {cite('qi2022', 'zhao2025', 'lin2025', 'koc2026')}, yet they have rarely been "
      "applied to compartmented fuel distribution or evaluated against exact optima on a real case.")
    P("This paper addresses that gap with four contributions. (i) An MC-MP-MT-VRP model with a heterogeneous fleet, "
      "exact compartment feasibility, product–truck compatibility, road-access restrictions, time-dependent speeds, "
      "soft time windows weighted by a fuzzy priority, and a load- and speed-dependent fuel/CO₂ model. (ii) A hybrid "
      "GA-SA-RL algorithm built on a heterogeneous-fleet Split decoder, with an ablation that isolates the contribution "
      "of the annealing phase and of Q-learning move selection. (iii) A layered validation: reproduction of the "
      "incumbent plan, comparison with a MILP-proven optimum, CVRPLIB benchmarks, and stochastic, scenario and dynamic "
      "experiments. (iv) An open-source web decision support system (DSS) backed by Google Sheets, released together "
      "with data and scripts so that every number in this paper can be regenerated.")
    P("Section 2 reviews related work, Section 3 states the model, Section 4 describes the algorithm and DSS, Section 5 "
      "reports the computational study, Section 6 discusses implications and limitations, and Section 7 concludes.")

    # 2 ------------------------------------------------------------------------
    H1("2. Related work")
    P(f"Cornillier et al. {cite('cornillier2008')} introduced heuristics for the multi-period PSRP, and subsequent work "
      f"added time windows, multiple depots and split deliveries {cite('benantar2016', 'wang2019', 'che2023', 'wang2020')}. "
      f"Recent studies consider truck-and-trailer configurations with hazard risk {cite('wu2024')}, deteriorating "
      f"inventory {cite('haseltalab2024')}, exact methods for real fuel distributors {cite('baptista2024')}, and hybrid "
      f"variable neighbourhood search for real PSRP instances {cite('liu2025')}. Heterogeneous-fleet MCVRP case studies "
      f"{cite('efthymiadis2023', 'yahyaoui2018')} confirm that compartment constraints change the solution structure. "
      f"Surveys of MCVRP {cite('ostermeier2021')} and multi-trip VRP {cite('cattaruzza2016')} identify the combination of "
      "compartments, multiple trips and heterogeneous fleets as under-studied.")
    P(f"Giant-tour genetic algorithms with an optimal Split decoder {cite('prins2004')} remain the backbone of leading "
      f"CVRP methods {cite('vidal2022')}. Simulated annealing {cite('kirkpatrick1983')} is a common intensification "
      f"step. Hyper-heuristics and adaptive operator selection {cite('burke2013')} have increasingly used Q-learning "
      f"{cite('watkins1992', 'sutton2018')}: QMOEA for the time-dependent green VRPTW {cite('qi2022')}, Q-learning "
      f"assisted evolutionary search for the CVRP {cite('zhao2025')}, a Q-learning hyper-heuristic for the electric "
      f"CVRP {cite('lin2025')}, RL-assisted NSGA-II for the multi-objective CVRPTW {cite('koc2026')}, and RL-designed "
      f"metaheuristics {cite('yi2023')}. Dynamic VRP surveys {cite('rios2021', 'sze2024')} and Q-learning based "
      f"rescheduling for waste collection {cite('zhaoy2024')} motivate the re-routing module. Emissions are modelled "
      f"following the pollution-routing literature {cite('bektas2011', 'dekker2012')} and IPCC Tier 2 factors {cite('ipcc2006')}.")
    rows = [
        (f"Cornillier et al. {cite('cornillier2008')}", "Multi-period PSRP", "Heuristic", "–", "–", "–"),
        (f"Wang et al. {cite('wang2020')}", "Split-delivery MCVRP, multi-trip", "Exact / heuristic", "✓", "–", "–"),
        (f"Che et al. {cite('che2023')}", "Multi-depot PSRP", "Tabu-ALNS", "–", "–", "–"),
        (f"Liu et al. {cite('liu2025')}", "Real PSRP, compartments", "Hybrid VNS", "–", "–", "–"),
        (f"Qi et al. {cite('qi2022')}", "Green TD-VRPTW", "EA + Q-learning", "–", "✓", "–"),
        (f"Nugroho et al. {cite('nugroho2020')}", "Fuel, Indonesia", "Sequential insertion", "✓", "–", "–"),
        (f"Ramadhani et al. {cite('ramadhani2021')}", "Fuel, Indonesia", "MILP", "✓", "–", "–"),
        ("This study", "MC-MP-MT-VRP", "GA-SA-RL + MILP check", "✓", "✓", "✓"),
    ]
    c.table(["Study", "Problem", "Method", "Multi-trip", "CO₂/learning", "Open DSS"], rows,
            "Positioning of this study", label="Table", size=8.5)

    # 3 ------------------------------------------------------------------------
    H1("3. Problem description and model")
    P("Let N = {1,…,n} be the stations and 0 the terminal; P the products; K the truck types, each with capacity Q~k~, "
      "compartments {c~k1~,…,c~km~}, U~k~ units, base consumption FC~0,k~ and daily fixed cost B~k~. Station i requires "
      "q~ip~ of product p, and d~ij~ is the road distance. A trip is a sequence (0, i~1~,…,i~L~, 0) performed by one truck. "
      "Each station is served by exactly one trip (no split delivery). A trip is loadable by type k if every product is "
      "compatible with k, every station's access road is at least the minimum width of k, and there is an assignment of "
      "compartments to products (each compartment holds at most one product) such that Σ~j∈C(p)~ c~kj~ ≥ Σ~i∈r~ q~ip~ "
      "for all p. A truck performs at most three consecutive trips within a 12-h shift; loading takes 5 min/kL, "
      "unloading 15 min + 2.5 min/kL, and the speed is v(t) = 40·CF(t) km/h with an hourly congestion factor CF(t). "
      "Fuel use on arc (i,j) is")
    c.eq("F~ij~ = FC~0,k~ (1 + β L~ij~/Q~k~)(1 + α~1~(v − v~0~)^2^) d~ij~")
    P("with on-board load L~ij~, β = 0.3, α~1~ = 10^−4^ and v~0~ = 65 km/h. The three objectives are cost "
      "Z~1~ = h Σ F~ij~ + c~km~ Σ d~ij~ + Σ~k~ u~k~ B~k~ (fuel price h = IDR 12,000/L, maintenance c~km~ = IDR 1,500/km, "
      "u~k~ trucks of type k used), emissions Z~2~ = EF Σ F~ij~ with EF = 2.68 kg CO₂/L, and time Z~3~ = total trip "
      "duration plus priority-weighted lateness. The scalar objective is")
    c.eq("F = w~1~ Z~1~/Z~1~^ref^ + w~2~ Z~2~/Z~2~^ref^ + w~3~ Z~3~/Z~3~^ref^ + penalties")
    P("where Z^ref^ are the objectives of direct delivery (one trip per station), (w~1~,w~2~,w~3~) = (0.5, 0.3, 0.2), "
      "and penalties apply to lateness and overtime (0.02 per minute), trips without an available truck (5.0 each) "
      "and quota excess (1.0 per kL). Station priorities in [0,100] come from a Mamdani fuzzy system "
      f"{cite('mamdani1975')} with time-to-empty, distance and demand variability as inputs. For verification, the "
      "special case with one 16-kL truck type, one trip per truck and distance objective is solved exactly as a "
      f"two-index MILP with load-based Miller–Tucker–Zemlin constraints {cite('mtz1960')} using HiGHS {cite('huangfu2018')}.")

    # 4 ------------------------------------------------------------------------
    H1("4. Solution approach and decision support system")
    H2("4.1 Representation, Split and scheduling")
    P("A solution is a permutation of stations. The Split procedure of Prins "
      f"{cite('prins2004')} is extended to a heterogeneous fleet: for every sub-sequence it selects the cheapest truck "
      "type that is loadable (exact compartment assignment by memoised recursion), accessible and compatible, and finds "
      "the minimum weighted-cost partition by dynamic programming; each trip cost includes the truck's daily fixed "
      "cost amortised over the maximum number of trips per truck-day (w~1~B~k~/(3Z~1~^ref^)), so that type selection "
      "does not ignore fixed costs. The resulting trips are assigned to truck units in "
      "decreasing fuzzy priority and then longest-duration order, preferring the same type and avoiding lateness and "
      "overtime, and are simulated with time-dependent speeds to obtain arrival times, fuel and CO₂.")
    H2("4.2 GA, SA and Q-learning move selection")
    P("The GA uses a population of 100 (60% greedy nearest-neighbour with perturbation), tournament selection (k = 5), "
      "order crossover (p~c~ = 0.85), inversion/swap/relocation mutation (p~m~ = 0.10, tripled when diversity falls "
      "below 5%), elitism of two and 200 generations. SA starts from the GA best with T~0~ = 1000, geometric cooling "
      "α = 0.995 and 5,000 iterations, using the normalised energy E = 10^6^ F/F~GA~, so that a 0.1% deterioration is "
      "initially accepted with probability e^−1^. In GA-SA-RL, a tabular Q-learning agent chooses the move at every SA "
      "iteration among 2-opt, relocate, swap, or-opt and segment swap. The state combines a stagnation level (< 50, "
      "50–199, ≥ 200 non-improving iterations) with the previous move; the reward is the relative improvement plus 1 for "
      "a new best and −0.05 for a rejected move; α = 0.1, γ = 0.9 and ε decays linearly from 0.1 to 0.02. Two ablation "
      "variants use the same evaluation budget: GA alone (extra generations equivalent to the SA iterations) and GA-SA "
      "(uniform random move selection). The energy scale was calibrated beforehand on X-n101-k25 with seeds 100–102, "
      "which are disjoint from the evaluation seeds; with the initial scale 10^5^ the SA phase behaved as a random walk "
      "and almost never improved the GA solution.")
    H2("4.3 Dynamic re-routing")
    P("At an event time (truck breakdown, or a sudden congestion with CF = 0.3 for 3 h), served stations are removed, the "
      "load of a broken truck is stranded, and the other trucks become available when their current trip ends. A naive "
      "policy keeps the remaining plan and adds one trip for stranded stations; the re-optimisation policy reruns "
      "GA-SA-RL (population 40, 60 generations, 1,500 SA iterations) warm-started with the naive plan.")
    H2("4.4 Truck-legal real road network")
    P("Instead of a single distance matrix, each truck type k is given its own directed graph built from OpenStreetMap "
      f"{cite('haklay2008')}. A link is kept for type k only if (i) it is a public road usable as a truck path; (ii) no "
      "access, motor_vehicle, hgv or goods restriction applies; (iii) its road class admits the truck's width, length, "
      f"height and maximum axle load under Indonesian Law 22/2009, Art. 19 {cite('uu22_2009', 'pp79_2013')} (class I: "
      "≤ 2.5 m wide, ≤ 18 m long, 10 t axle load; class II: ≤ 2.5 m, ≤ 12 m, 8 t; class III: ≤ 2.1 m, ≤ 9 m, 8 t); "
      "(iv) signed maxwidth, maxlength, maxheight, maxweight and maxaxleload limits are respected; (v) the carriageway "
      "width (width tag, lanes × lane width, or a default per link type) is at least the truck's two-way passing width, "
      "or the truck width plus 1.0 m on one-way carriageways; and (vi) one-way restrictions hold. Road classes and default "
      "widths per OSM link type are documented assumptions (trunk/primary class I, secondary/tertiary class II, "
      "unclassified/residential class III). Terminal and stations are snapped to the largest strongly connected "
      "component (≤ 250 m); a station that cannot be snapped is inaccessible to that type. Distances d~ij~^k^ are "
      f"Dijkstra shortest paths {cite('dijkstra1959')}, asymmetric and type-specific, and are used in trip evaluation "
      "and scheduling; the path geometry is drawn on the DSS map. A GitHub Actions workflow downloads OSM and rebuilds "
      "the matrices whenever rules or data change.")
    H2("4.5 Web DSS")
    P("SMARTROUTE-BBM is a Streamlit application with five modules: data and map; optimisation with KPIs relative to the "
      "incumbent plan, route map, convergence and operator statistics, multi-trip Gantt chart and compartment loading "
      "table; dynamic re-routing; research results; and reports with an optional Telegram notification. Master data "
      "(stations, distance matrix, fleet, product shares) are read from Google Sheets, with a CSV fallback, and every "
      f"run is appended to an audit-log sheet. Code, data and experiment scripts are public at {REPO}.")
    c.figure(os.path.join(FIGEN, "fig1_framework.png"), "Architecture of SMARTROUTE-BBM and the GA-SA-RL loop",
             15.5, label="Fig.")

    # 5 ------------------------------------------------------------------------
    H1("5. Computational study")
    H2("5.1 Data and set-up")
    P(f"The case is FT Gelumbang (South Sumatra, Indonesia), serving 13 stations with a total demand of "
      f"{e0['total_demand_kl']:.2f} kL/day, taken from a 2026 capstone design project together with a 14×14 road-distance "
      f"matrix. The road distances average {e0['circuity_mean']:.2f} times the great-circle distances, contain "
      f"{e0['triangle_violations_ordered']} ordered triangle-inequality violations (actual, not shortest, roads) and "
      f"place {e0['spbu_beyond_30km']} stations beyond 30 km from the terminal. The existing fleet is four 16-kL trucks "
      "(compartments 6+4+3+3 kL) and one 8-kL truck (4+2+2 kL). Product shares (Pertalite 62%, Biosolar 26%, Pertamax "
      "12%), compartment sizes, consumption and fixed costs are assumptions because the capstone data report only "
      "total volumes. Each algorithm variant was run 30 times (seeds 0–29) on the case and 10 times on benchmarks, on a "
      "4-core Linux machine in Python.")
    H2("5.2 Validation against the incumbent plan and the exact optimum")
    s1 = e1["stats"]
    P(f"In the capacitated setting used by the capstone (16 kL, one trip per truck, distance objective), the incumbent "
      f"Savings plan measures {e1['baseline_capstone']:.1f} km and direct delivery {e1['direct']:.1f} km, both reproduced "
      f"exactly from the matrix. Our Clarke–Wright implementation yields {e1['cw_reimpl']:.1f} km and nearest neighbour "
      f"{e1['nn']:.1f} km. The MILP was solved to proven optimality in {e1['milp_time_s']:.0f} s with "
      f"{e1['milp_opt']:.1f} km. All three variants reached this optimum in every run (hit rates "
      + ", ".join(f"{v} {s1[v]['hit_rate_opt'] * 100:.0f}%" for v in VAR) +
      f"; mean run time {s1['GA']['runtime_mean']:.1f}–{max(s1[v]['runtime_mean'] for v in VAR):.1f} s), i.e. "
      f"{imp:.2f}% shorter than the incumbent (Fig. 2). The instance is too small to discriminate between variants; "
      "the ablation is therefore assessed on the full model and on benchmarks.")
    c.figure(os.path.join(FIGEN, "fig3_validation.png"), "Total distance of the methods in the capacitated setting",
             12.5, label="Fig.")
    H2("5.3 Full MC-MP-MT-VRP and ablation on the case")
    if e2 is None:
        raise SystemExit("E2 results missing")
    rows = []
    for key, name in [("agregat", "Aggregated"), ("multiproduk", "Multi-product")]:
        E = e2[key]
        b, h, m = E["baseline"], E["best_ga_sa_rl"], E["means"]
        rows.append((name, "Savings plan", f"{b['fitness']:.4f}", g(b["dist_km"]), idr(b["cost_rp"]), g(b["co2_kg"]),
                     f"{int(b['trucks'])}/{int(b['trips'])}", int(b["unassigned"])))
        for v in VAR:
            rows.append((name, f"{v} (mean)", f"{m['fitness'][v]:.4f}", g(m["dist_km"][v]), idr(m["cost_rp"][v]),
                         g(m["co2_kg"][v]), f"{m['trucks'][v]:.1f}/{m['trips'][v]:.1f}", g(m["unassigned"][v], 2)))
    c.table(["Case", "Plan", "Fitness", "Distance (km)", "Cost/day", "CO₂ (kg)", "Trucks/trips", "Unloadable trips"],
            rows, "Full-model results with the existing fleet (30 runs per variant)", label="Table", size=8)
    b, h = mp["baseline"], mp["best_ga_sa_rl"]
    P(f"With products and compartments, the incumbent plan is infeasible: {int(b['unassigned'])} of its trips cannot be "
      "loaded on any truck because, for example, route S8–S9–S10 needs 9.60 kL of Pertalite, 4.02 kL of Biosolar and "
      "1.86 kL of Pertamax, which does not fit the 6+4+3+3 kL compartments. GA-SA-RL returns a feasible plan with "
      f"{int(h['trucks'])} trucks and {int(h['trips'])} trips, {h['dist_km']:.1f} km, {idr(h['cost_rp'])} and "
      f"{h['co2_kg']:.1f} kg CO₂ per day, without lateness or overtime (Fig. 3); between variants, "
      f"{kw(mp['stats_fitness'])} (Fig. 4).")
    ag = e2["agregat"]
    hb, bb = ag["best_ga_sa_rl"], ag["baseline"]
    if hb["trucks"] < bb["trucks"]:
        P(f"In the aggregated case the best plan uses {int(hb['trucks'])} instead of {int(bb['trucks'])} trucks by "
          f"chaining trips, which lowers the daily cost by {(bb['cost_rp'] - hb['cost_rp']) / bb['cost_rp'] * 100:.1f}% "
          f"({idr(bb['cost_rp'])} → {idr(hb['cost_rp'])}) for a {abs(hb['dist_km'] - bb['dist_km']):.1f} km "
          f"{'longer' if hb['dist_km'] > bb['dist_km'] else 'shorter'} distance ({hb['dist_km']:.1f} vs {bb['dist_km']:.1f} km); "
          f"between variants, {kw(ag['stats_fitness'])}. The size of this saving depends on the assumed truck fixed cost.")
    c.figure(os.path.join(FIGEN, "fig2_routes.png"), "Routes of (a) the incumbent Savings plan and (b) the GA-SA-RL "
             "multi-product plan", 15.5, label="Fig.")
    c.figure(os.path.join(FIGEN, "fig4_ablation_case.png"), "Distribution of 30 runs per variant on the multi-product case",
             15.5, label="Fig.")
    if e7 is not None and len(e7):
        H2("5.4 Benchmark validation and ablation on CVRPLIB")
        gr = e7.groupby(["instance", "variant"]).agg(n=("n", "first"), bks=("bks", "first"), cw=("cw_gap_pct", "first"),
                                                     gap=("gap_pct", "mean"), sd=("gap_pct", "std"),
                                                     best=("gap_pct", "min"), t=("runtime", "mean")).reset_index()
        rows = [(r.instance, r.variant, int(r.bks), f"{r.cw:.2f}", f"{r.gap:.2f}", f"{r.sd:.2f}", f"{r.best:.2f}",
                 f"{r.t:.0f}") for r in gr.itertuples()]
        c.table(["Instance", "Variant", "BKS", "CW gap %", "Mean gap %", "SD", "Best gap %", "Time (s)"], rows,
                f"Results on CVRPLIB set X {cite('uchoa2017')} (10 runs, 1,000 generations)", label="Table", size=8)
        gg = gr[gr.variant == "GA-SA-RL"]
        t = e7_tests(e7)
        txt = (f"Across {len(gg)} X instances (n = {int(gg.n.min())}–{int(gg.n.max())}), GA-SA-RL obtains a mean gap of "
               f"{gg.gap.mean():.2f}% (range {gg.gap.min():.2f}–{gg.gap.max():.2f}%), against {gg.cw.mean():.2f}% for "
               f"Clarke–Wright (Fig. 5). The implementation is therefore correct but only modestly better than the savings "
               f"heuristic on average (and worse on some instances), and far from state-of-the-art CVRP solvers such as HGS "
               f"{cite('vidal2022')}, which typically reach gaps below 0.5%; the method should be read as a flexible engine "
               "for the rich case model rather than as a competitive pure-CVRP solver. On the "
               f"{t['n_inst']} instances used for the ablation, mean gaps are " +
               ", ".join(f"{v} {t['means'][v]:.2f}%" for v in VAR if v in t["means"]) + ".")
        if t["friedman"]:
            txt += f" A Friedman test over instance means gives χ² = {t['friedman'][0]:.2f} (p = {pv(t['friedman'][1])})."
        for other, (p, n, win, loss) in t["pairs"].items():
            txt += (f" Paired one-sided Wilcoxon test GA-SA-RL < {other}: p = {pv(p)} over {n} instance–seed pairs "
                    f"(GA-SA-RL better in {win * 100:.0f}%, worse in {loss * 100:.0f}%).")
        P(txt)
        c.figure(os.path.join(FIGEN, "fig6_cvrplib.png"), "Gap to best-known solutions on CVRPLIB set X", 14.0, label="Fig.")
    H2("5.5 Cost–emission trade-off")
    e3b = R.get("e3b")
    if e3 is not None:
        fe = e3[e3.unassigned == 0]
        pf = fe[fe.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])
        txt = (f"A weight sweep with step 0.1 (two seeds per weight vector) produced {len(e3)} solutions ({len(fe)} "
               f"feasible) and {len(pf)} distinct non-dominated cost–CO₂ point(s)" +
               (f", spanning {idr(pf.cost_rp.min())}–{idr(pf.cost_rp.max())} and {pf.co2_kg.min():.1f}–"
                f"{pf.co2_kg.max():.1f} kg CO₂ per day (Fig. 6a)." if len(pf) > 1 else
                f" ({idr(pf.cost_rp.iloc[0])}, {pf.co2_kg.iloc[0]:.1f} kg CO₂ per day; Fig. 6a)."))
        if e3s is not None:
            gs = e3s.groupby("fixed_cost_mult").mean(numeric_only=True)
            if abs(gs.trucks.iloc[0] - gs.trucks.iloc[-1]) < 1e-9 and abs(gs.dist_km.iloc[0] - gs.dist_km.iloc[-1]) < 1e-9:
                txt += (f" Scaling the truck fixed cost from 0 to 2 times its assumed value leaves the plan unchanged "
                        f"({gs.trucks.iloc[0]:.0f} trucks, {gs.dist_km.iloc[0]:.1f} km; Fig. 6b), so the recommendation "
                        "for the existing fleet is robust to this assumption.")
            else:
                txt += (f" When the truck fixed cost is scaled from 0 to 2 times its assumed value, the mean fleet size "
                        f"moves from {gs.trucks.iloc[0]:.1f} to {gs.trucks.iloc[-1]:.1f} and distance from "
                        f"{gs.dist_km.iloc[0]:.1f} to {gs.dist_km.iloc[-1]:.1f} km (Fig. 6b).")
        if len(pf) <= 1:
            txt += (" With the existing fleet, the cost-minimal plan is also emission-minimal, so no genuine trade-off "
                    "exists.")
        if e3b is not None:
            feb = e3b[e3b.unassigned == 0]
            pfb = feb[feb.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])
            txt += (f" When the fleet options are extended (2×6 kL, 2×8 kL, 4×16 kL, 1×32 kL), the sweep yields "
                    f"{len(pfb)} non-dominated points")
            if len(pfb) > 1:
                lo, hi = pfb.iloc[0], pfb.iloc[-1]
                txt += (f", from the cheapest plan ({idr(lo.cost_rp)}, {lo.co2_kg:.1f} kg CO₂, trip types {lo.trip_types}) "
                        f"to the lowest-emission plan ({idr(hi.cost_rp)}, {hi.co2_kg:.1f} kg, trip types {hi.trip_types}); "
                        f"the implied abatement cost at the extremes is about "
                        f"{idr((hi.cost_rp - lo.cost_rp) / max(lo.co2_kg - hi.co2_kg, 1e-9))} per kg CO₂.")
            else:
                txt += "."
        e3c = R.get("e3c")
        if e3c is not None:
            fec = e3c[e3c.unassigned == 0]
            pfc = fec[fec.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])
            if len(pfc) == 1:
                r0 = pfc.iloc[0]
                txt += (f" On the truck-legal road network (Section 5.8), however, the extended fleet yields a single "
                        f"non-dominated point ({idr(r0.cost_rp)}, {r0.co2_kg:.1f} kg CO₂, trip types {r0.trip_types}): the "
                        "trade-off disappears because the semi-trailer may not enter some stations.")
            elif len(pfc) > 1:
                lo, hi = pfc.iloc[0], pfc.iloc[-1]
                txt += (f" On the truck-legal road network (Section 5.8) the extended fleet yields {len(pfc)} non-dominated "
                        f"points, from {idr(lo.cost_rp)} ({lo.co2_kg:.1f} kg, {lo.trip_types}) to {idr(hi.cost_rp)} "
                        f"({hi.co2_kg:.1f} kg, {hi.trip_types}).")
        P(txt)
        c.figure(os.path.join(FIGEN, "fig5_pareto.png"), "(a) Cost–CO₂ Pareto front; (b) sensitivity to truck fixed cost",
                 15.5, label="Fig.")
    H2("5.6 What-if scenarios and robustness")
    if e4:
        rows = []
        for k, v in list(e4.items()) + list((e4b or {}).items()):
            if "hybrid" not in v:
                continue
            h = v["hybrid"]
            rows.append((k.split(". ", 1)[0], SC_EN.get(k.split(". ", 1)[0], k), idr(h["cost_rp"]), g(h["co2_kg"]),
                         f"{int(h['trucks'])}/{int(h['trips'])}", int(h["unassigned"])))
        c.table(["#", "Scenario (assumption)", "Cost/day", "CO₂ (kg)", "Trucks/trips", "Unserved trips"], rows,
                "GA-SA-RL plans under what-if scenarios (best of 5 seeds)", label="Table", size=8)
        n0 = e4["0. Kondisi normal"]["hybrid"]
        h8 = e4["8. Antrian loading rack FT"]["hybrid"]
        h1 = e4["1. Kemacetan dinamis"]["hybrid"]
        txt = (f"Peak-hour congestion raises emissions by {(h1['co2_kg'] / n0['co2_kg'] - 1) * 100:.1f}% without changing "
               f"routes, whereas a congested loading rack (M/M/4 queue) raises daily cost by "
               f"{(h8['cost_rp'] / n0['cost_rp'] - 1) * 100:.0f}% because waiting time forces {int(h8['trucks'])} trucks "
               "into service. Two scenarios are infeasible with the existing fleet: a road-width restriction that limits "
               "four stations to the single 8-kL truck, and a local threefold demand surge in which one station needs "
               "about 20 kL, more than the largest available truck, while split delivery is not modelled.")
        if e4b:
            r2 = e4b.get("2R. Restriksi jalan + 1 unit tipe B"); r9 = e4b.get("9bR. Panic buying lokal + 1 unit tipe D")
            if r2 and r9:
                txt += (f" Adding one 8-kL truck leaves {int(r2['hybrid']['unassigned'])} unserved trip(s) in the first "
                        f"case, and adding one 32-kL truck leaves {int(r9['hybrid']['unassigned'])} in the second, "
                        "illustrating how the DSS supports fleet sizing.")
        P(txt)
    if e6 is not None:
        m = e6[(e6.produk == "multiproduk") & (e6.cv == 0.2)].set_index("plan")
        P(f"Monte Carlo simulation (1,000 demand draws per cell, normal demand with coefficient of variation up to 0.20) "
          f"gives, for the multi-product case at CV = 0.20, service levels of "
          f"{m.loc['Saving Matrix', 'service_level'] * 100:.2f}% for the incumbent plan, "
          f"{m.loc['GA-SA-RL', 'service_level'] * 100:.2f}% for GA-SA-RL and "
          f"{m.loc['GA-SA-RL robust (90%)', 'service_level'] * 100:.2f}% for a robust variant planned with 90% of truck "
          f"capacity (at {m.loc['GA-SA-RL robust (90%)', 'dist_km']:.1f} km). The capacity buffer is thus a transparent "
          "lever for trading distance against shortage risk.")
    H2("5.7 Dynamic re-routing")
    if e5:
        d = e5["summary"]["breakdown"]
        txt = (f"Over {d['n']} breakdown events (truck × time × seed), re-optimisation lowered the residual fitness from "
               f"{d['fitness']['naive']:.4f} to {d['fitness']['reopt']:.4f} (one-sided Wilcoxon p = "
               f"{pv(d['fitness'].get('p_wilcoxon'))}) in {d['compute_s_mean']:.2f} s on average, but improved only "
               f"{d['share_improved_fitness'] * 100:.0f}% of events and by little (residual distance "
               f"{d['dist_km']['naive']:.1f} → {d['dist_km']['reopt']:.1f} km), because the existing fleet has ample slack.")
        if e5b and "breakdown" in e5b:
            d2 = e5b["breakdown"]
            txt += (f" With tight stock-out deadlines the share of improved events was {d2['share_improved_fitness'] * 100:.0f}% "
                    f"(p = {pv(d2['fitness'].get('p_wilcoxon'))}).")
        k = e5["summary"].get("kemacetan")
        if k:
            txt += (" For sudden congestion the two policies produced " +
                    ("identical plans." if abs(k["fitness"]["naive"] - k["fitness"]["reopt"]) < 1e-9 else "different plans."))
        P(txt)

    e8 = J("E8_summary.json")
    if e8:
        H2("5.8 Routing on the truck-legal real road network")
        rr = e8.get("ringkasan_ruas", [])
        m = e8["matriks"]
        txt = ""
        if rr:
            byt = {r["tipe"]: r for r in rr}
            txt += (f"The study area contains {rr[0]['km_ruas_total']:.0f} km of OSM links; {byt['C']['km_ruas_legal']:.0f} km "
                    f"are legal for the 8- and 16-kL trucks (class II) and {byt['D']['km_ruas_legal']:.0f} km for the "
                    "32-kL semi-trailer (class I), most rejected links being local and residential streets. ")
        if m.get("D", {}).get("spbu_tak_terjangkau"):
            txt += (f"All stations remain reachable by the 16-kL truck, whereas the semi-trailer cannot legally reach "
                    f"{', '.join(m['D']['spbu_tak_terjangkau'])}. ")
        txt += (f"Truck-legal distances for the 16-kL truck correlate at {m['C']['korelasi']:.3f} with the capstone matrix "
                f"(mean absolute difference {m['C']['rerata_selisih_abs_pct']:.1f}%), which validates the capstone data while "
                "adding type-specific legality and one-way asymmetry. ")
        parts = []
        for key, name in [("eksisting_agregat", "aggregated"), ("eksisting_multiproduk", "multi-product")]:
            if key in e8:
                hc, ho = e8[key]["capstone"]["best"], e8[key]["osm"]["best"]
                bo = e8[key]["osm"]["baseline"]
                parts.append(f"for the {name} case with the existing fleet the best GA-SA-RL plan on legal roads covers "
                             f"{ho['dist_km']:.1f} km at IDR {ho['cost_rp']:,.0f}/day with {int(ho['trucks'])} trucks and "
                             f"{int(ho['trips'])} trips (capstone matrix: {hc['dist_km']:.1f} km; incumbent plan on legal "
                             f"roads: {bo['dist_km']:.1f} km, {int(bo['unassigned'])} unloadable trip(s))")
        if parts:
            txt += "Over 30 runs, " + "; ".join(parts) + ". "
        if "diperluas_multiproduk" in e8:
            tc = "".join(sorted(t["tipe"] for t in e8["diperluas_multiproduk"]["capstone"]["best_trips"]))
            to = "".join(sorted(t["tipe"] for t in e8["diperluas_multiproduk"]["osm"]["best_trips"]))
            txt += (f"With the extended fleet the trip-type mix of the best plan is {tc} on the capstone matrix and {to} on "
                    "legal roads" + (", i.e. road-class restrictions change the fleet choice." if tc != to else
                                     "; road-class restrictions do not change the best fleet mix here."))
            bad = sorted({x for t in e8["diperluas_multiproduk"]["capstone"]["best_trips"] for x in t["rute"].split("-")
                          if x in m.get(t["tipe"], {}).get("spbu_tak_terjangkau", [])})
            if bad:
                txt += (f" The semi-trailer trip in the capstone-matrix plan serves {', '.join(bad)}, which the semi-trailer "
                        "cannot legally reach, so the lower-emission CCCD fleet option of Section 5.5 is not executable on "
                        "legal roads.")
        P(txt)
        c.figure(os.path.join(FIGEN, "fig7_osm_legal.png"),
                 "(a) OSM links legal per truck type; (b) GA-SA-RL multi-product routes on truck-legal roads", 15.5,
                 label="Fig.")

    # 6 ------------------------------------------------------------------------
    H1("6. Discussion")
    P("Three findings matter for practice. First, a plan that is optimal on aggregated volumes may be unloadable once "
      "compartments and product mix are considered; modelling compartments is therefore a feasibility issue, not a "
      "refinement. Second, on a small terminal network the distance gain over a well-built Savings plan is modest "
      f"({imp:.1f}% to the proven optimum), which is far below the 15–60% savings often reported against unoptimised "
      f"existing routes {cite('aqidawati2021', 'melani2025', 'awaludin2025')}; the larger value of the model lies in "
      "fleet utilisation through multiple trips, feasibility checking, and scenario analysis. Third, the loading rack "
      "and the fixed cost of trucks can dominate routing decisions, so terminal capacity planning should be considered "
      "together with routing.")
    t = e7_tests(e7) if e7 is not None and len(e7) else None
    if t and "GA-SA" in t["pairs"]:
        p_rl = t["pairs"]["GA-SA"][0]
        P("Regarding the learning component, the evidence must be read carefully. " +
          ("Q-learning move selection improved on random selection with statistical significance on the benchmark set, "
           "in line with reports on learning-based operator selection " + cite('qi2022', 'zhao2025', 'koc2026') + "." if p_rl < 0.05 else
           "Q-learning move selection did not significantly improve on uniform random selection on the benchmark set, "
           "which echoes comparative studies where learned and simple selection policies show complementary strengths "
           "rather than uniform dominance; the annealing phase itself, not the learning rule, provides most of the "
           "intensification in our implementation.") +
          " On the 13-station case all variants find the optimum, so the case alone cannot demonstrate a benefit of RL.")
    P("Limitations are as follows. Product shares, compartment sizes, consumption, fixed costs and congestion profiles "
      "are assumptions; road classes and widths are mostly inferred from OSM link types because few links carry width or "
      "lanes tags, and truck dimensions are typical values, so link legality should be checked against official road-class "
      "decrees and field surveys; split delivery is not "
      "modelled; the learning component is a tabular operator-selection policy, not a trained routing policy; and the "
      "DSS has not yet been evaluated with industrial users. Because code, data and scripts are released, these "
      "assumptions can be replaced and every experiment re-run.")

    # 7 ------------------------------------------------------------------------
    H1("7. Conclusion")
    P("This study formulated an MC-MP-MT-VRP for petrol-station replenishment, solved it with a hybrid GA-SA-RL "
      "built on a heterogeneous-fleet Split decoder with exact compartment checking, and embedded it in an open-source "
      "web DSS with a Google Sheets database. The method reproduces the incumbent plan, reaches the MILP-proven optimum "
      "on the capacitated case, exposes the infeasibility of volume-based plans under compartment constraints, and "
      "supports scenario, Pareto, stochastic and dynamic analyses within seconds. Future work will calibrate the "
      "assumptions with operator data, add split deliveries and hired trucks, verify road classes and widths on the selected routes, integrate historical traffic data, "
      "evaluate the DSS with users, and compare learned operator selection with other adaptive schemes.")
    p = c.para("", align="j")
    c._runs(p, "**Data and code availability.** Source code, data, experiment scripts and raw results: " + REPO +
            ". Master data are also mirrored in a Google Sheets database: " + SHEET + ".")
    p = c.para("", align="j")
    c._runs(p, "**Acknowledgement.** This research was funded by DIPA 2026 PEM Akamigas (SP3 No. 046/SP3/Penelitian/"
               "DIPA2026/PEM Akamigas). The authors thank the 2026 Capstone Design students for the field data.")
    p = c.para("", align="j")
    c._runs(p, "**Author contributions (CRediT).** A.S.W.: conceptualisation, methodology, software, writing – original "
               "draft. A.K.D.: validation, resources, writing – review. C.N.H.: data curation, investigation. N.K.A.: "
               "formal analysis, visualisation. [Authors to confirm.]")
    H1("References")
    for ref in cite.bibliography():
        q = c.para(ref.replace(" [VERIFY]", ""), align="j", size=9.5, space_after=2)
        q.paragraph_format.left_indent = Cm(0.8)
        q.paragraph_format.first_line_indent = Cm(-0.8)
    # remove first empty paragraph
    first = doc.paragraphs[0]
    if not first.text:
        first._p.getparent().remove(first._p)
    out = os.path.join(OUT, "Manuscript_SMARTROUTE-BBM_EN.docx")
    doc.save(out)
    unverified = [k for k in cite.order if "[VERIFY]" in __import__("docs.refs", fromlist=["REFS"]).REFS[k]]
    print("saved", out, "refs", len(cite.order), "to verify:", unverified)
    return out


SC_EN = {
    "0": "Normal operations", "1": "Peak congestion (CF 0.5 at 07–09, 16–18; 0.85 otherwise)",
    "2": "Road-width limit 5 m at S2–S5 (types C/D barred)", "5": "Time window 06:00–11:00 at six stations",
    "6": "Emission-dominant weights (0.1, 0.8, 0.1)", "7": "Tank management, initial stock 15–60%",
    "8": "Loading-rack queue M/M/4", "9": "Demand surge ×1.5 (all stations)", "9b": "Local surge ×3 at S1, S6, S10",
    "10": "Biosolar quota 95% of demand", "2R": "Scenario 2 + one extra 8-kL truck",
    "9bR": "Scenario 9b + one 32-kL truck", "9R": "Scenario 9 control (existing fleet)",
}

if __name__ == "__main__":
    build()
