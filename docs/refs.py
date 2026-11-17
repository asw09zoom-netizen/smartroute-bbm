"""Daftar pustaka (gaya IEEE sampai volume dan halaman), penomoran mengikuti urutan sitasi pertama.

Setiap artikel jurnal/prosiding diverifikasi keberadaannya lewat Consensus/SciSpace (November 2026).
DOI dan tautan Consensus dipakai untuk berkas .ris; di naskah laporan hanya sampai volume dan halaman.
Bidang yang kosong (volume, nomor, halaman) belum terverifikasi dan dilengkapi lewat DOI di reference manager.
"""

# key: (penulis, judul, terbitan, tahun, volume, nomor, halaman, doi, url)
META = {
    'dantzig1959': ('G. B. Dantzig and J. H. Ramser', 'The truck dispatching problem', 'Management Science', 1959, '6', '1', '80–91', '10.1287/mnsc.6.1.80', None),
    'clarke1964': ('G. Clarke and J. W. Wright', 'Scheduling of vehicles from a central depot to a number of delivery points', 'Operations Research', 1964, '12', '4', '568–581', '10.1287/opre.12.4.568', None),
    'prins2004': ('C. Prins', 'A simple and effective evolutionary algorithm for the vehicle routing problem', 'Computers & Operations Research', 2004, '31', '12', '1985–2002', '10.1016/S0305-0548(03)00158-8', None),
    'kirkpatrick1983': ('S. Kirkpatrick, C. D. Gelatt, Jr., and M. P. Vecchi', 'Optimization by simulated annealing', 'Science', 1983, '220', '4598', '671–680', '10.1126/science.220.4598.671', None),
    'watkins1992': ('C. J. C. H. Watkins and P. Dayan', 'Q-learning', 'Machine Learning', 1992, '8', '3–4', '279–292', '10.1007/BF00992698', None),
    'mtz1960': ('C. E. Miller, A. W. Tucker, and R. A. Zemlin', 'Integer programming formulation of traveling salesman problems', 'Journal of the ACM', 1960, '7', '4', '326–329', '10.1145/321043.321046', None),
    'dijkstra1959': ('E. W. Dijkstra', 'A note on two problems in connexion with graphs', 'Numerische Mathematik', 1959, '1', '1', '269–271', '10.1007/BF01386390', None),
    'mamdani1975': ('E. H. Mamdani and S. Assilian', 'An experiment in linguistic synthesis with a fuzzy logic controller', 'International Journal of Man-Machine Studies', 1975, '7', '1', '1–13', '10.1016/S0020-7373(75)80002-2', None),
    'huangfu2018': ('Q. Huangfu and J. A. J. Hall', 'Parallelizing the dual revised simplex method', 'Mathematical Programming Computation', 2018, '10', '1', '119–142', '10.1007/s12532-017-0130-5', None),
    'bektas2011': ('T. Bektaş and G. Laporte', 'The pollution-routing problem', 'Transportation Research Part B: Methodological', 2011, '45', '8', '1232–1250', '10.1016/j.trb.2011.02.004', None),
    'uchoa2017': ('E. Uchoa, D. Pecin, A. Pessoa, M. Poggi, T. Vidal, and A. Subramanian', 'New benchmark instances for the capacitated vehicle routing problem', 'European Journal of Operational Research', 2017, '257', '3', '845–858', '10.1016/j.ejor.2016.08.012', None),
    'vidal2022': ('T. Vidal', 'Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood', 'Computers & Operations Research', 2022, '140', '', 'Art. no. 105643', '10.1016/j.cor.2021.105643', None),
    'derrac2011': ('J. Derrac, S. García, D. Molina, and F. Herrera', 'A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms', 'Swarm and Evolutionary Computation', 2011, '1', '1', '3–18', '10.1016/j.swevo.2011.02.002', None),
    'ropke2006': ('S. Ropke and D. Pisinger', 'An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows', 'Transportation Science', 2006, '40', '4', '455–472', '10.1287/trsc.1050.0135', 'https://consensus.app/papers/details/07cd08e30ccf581187c9d77918d90552/'),
    'schrimpf2000': ('G. Schrimpf, J. Schneider, H. Stamm-Wilbrandt, and G. Dueck', 'Record breaking optimization results using the ruin and recreate principle', 'Journal of Computational Physics', 2000, '159', '2', '139–171', '10.1006/jcph.1999.6413', None),
    'toth2003': ('P. Toth and D. Vigo', 'The granular tabu search and its application to the vehicle-routing problem', 'INFORMS Journal on Computing', 2003, '15', '4', '333–346', '10.1287/ijoc.15.4.333.24890', None),
    'voigt2024': ('S. Voigt', 'A review and ranking of operators in adaptive large neighborhood search for vehicle routing problems', 'European Journal of Operational Research', 2024, '', '', '', '10.1016/j.ejor.2024.05.033', 'https://consensus.app/papers/details/50d140bde97e5a399619f0d1fa2d768e/'),
    'cornillier2008': ('F. Cornillier, F. F. Boctor, G. Laporte, and J. Renaud', 'A heuristic for the multi-period petrol station replenishment problem', 'European Journal of Operational Research', 2008, '191', '2', '295–305', '10.1016/j.ejor.2007.08.030', None),
    'cornillier2009': ('F. Cornillier, G. Laporte, F. F. Boctor, and J. Renaud', 'The petrol station replenishment problem with time windows', 'Computers & Operations Research', 2009, '36', '3', '919–935', '10.1016/j.cor.2007.11.003', 'https://consensus.app/papers/details/a9b3a806184857ebbc3d81abbb5b14f4/'),
    'coelho2015': ('L. C. Coelho and G. Laporte', 'Classification, models and exact algorithms for multi-compartment delivery problems', 'European Journal of Operational Research', 2015, '242', '3', '854–864', '10.1016/j.ejor.2014.10.059', None),
    'ostermeier2021': ('M. Ostermeier, T. Henke, A. Hübner, and G. Wäscher', 'Multi-compartment vehicle routing problems: State-of-the-art, modeling framework and future directions', 'European Journal of Operational Research', 2021, '292', '3', '799–817', '10.1016/j.ejor.2020.11.009', None),
    'wang2020': ('L. Wang, J. Kinable, and T. van Woensel', 'The fuel replenishment problem: A split-delivery multi-compartment vehicle routing problem with multiple trips', 'Computers & Operations Research', 2020, '118', '', 'Art. no. 104904', '10.1016/j.cor.2020.104904', None),
    'wu2024': ('W.-T. Wu et al.', 'The multi-compartment truck and trailer petrol station replenishment problem with domino hazard risks', 'Transportation Research Part B: Methodological', 2024, '', '', '', '', 'https://consensus.app/papers/details/93c2ca1ba4ef5871b44f5fcca7607efd/'),
    'bani2023': ('A. Bani et al.', 'Solving a real-world multi-depot multi-period petrol replenishment problem with complex loading constraints', 'European Journal of Operational Research', 2023, '', '', '', '', 'https://consensus.app/papers/details/1b055e24a30855549bfb7cfe542640fd/'),
    'che2023': ('A. Che, W. Wang, and X. Mu', 'Tabu-based adaptive large neighborhood search for multi-depot petrol station replenishment with open inter-depot routes', 'IEEE Transactions on Intelligent Transportation Systems', 2023, '', '', '', '10.1109/TITS.2022.3215084', 'https://consensus.app/papers/details/0841fe16992457d69b91946d30684915/'),
    'liu2025': ('Z. Liu, Y. M. Cheng, F. Tian, and W. Zhou', 'A hybrid variable neighborhood search for a real-world petrol station replenishment problem with multi-compartment vehicles', 'RAIRO – Operations Research', 2025, '', '', '', '10.1051/ro/2025004', 'https://consensus.app/papers/details/c03758e257785676955d62c478579dcd/'),
    'baptista2024': ('G. Baptista, M. Vieira, and T. Pinto', 'An exact approach to the multi-compartment vehicle routing problem: The case of a fuel distribution company', 'Mathematics', 2024, '12', '4', 'Art. no. 527', '10.3390/math12040527', 'https://consensus.app/papers/details/4752c3664a745051bfa0f827e33cf39f/'),
    'cattaruzza2016': ('D. Cattaruzza, N. Absi, and D. Feillet', 'Vehicle routing problems with multiple trips', '4OR', 2016, '14', '3', '223–259', '10.1007/s10288-016-0306-2', None),
    'azi2014': ('N. Azi, M. Gendreau, and J.-Y. Potvin', 'An adaptive large neighborhood search for a vehicle routing problem with multiple routes', 'Computers & Operations Research', 2014, '41', '', '167–173', '10.1016/j.cor.2013.08.016', None),
    'zhaoj2024': ('J.-Y. Zhao et al.', 'A hybrid genetic search and dynamic programming-based split algorithm for the multi-trip time-dependent vehicle routing problem', 'European Journal of Operational Research', 2024, '', '', '', '', 'https://consensus.app/papers/details/0d7e183e7358563fbada7bc4876cdf8f/'),
    'sahin2022': ('M. K. Şahin and H. Yaman', 'A branch and price algorithm for the heterogeneous fleet multi-depot multi-trip vehicle routing problem with time windows', 'Transportation Science', 2022, '', '', '', '10.1287/trsc.2022.1146', 'https://consensus.app/papers/details/d018433344205480b8b08785db454e52/'),
    'subramanian2012': ('A. Subramanian, P. H. V. Penna, E. Uchoa, and L. S. Ochi', 'A hybrid algorithm for the heterogeneous fleet vehicle routing problem', 'European Journal of Operational Research', 2012, '221', '2', '285–295', '10.1016/j.ejor.2012.03.016', 'https://consensus.app/papers/details/90fa898cc98759c1bc3e6598d199d607/'),
    'qi2022': ('R. Qi et al.', 'QMOEA: A Q-learning-based multiobjective evolutionary algorithm for solving time-dependent green vehicle routing problems with time windows', 'Information Sciences', 2022, '', '', '', '', 'https://consensus.app/papers/details/5e6b1b01e1fa525f9696e3c0cf3b7030/'),
    'koc2026': ('A. Koç, D. Tezcaner Öztürk, and C. Tuncer Şakar', 'A novel reinforcement learning–assisted genetic algorithm for the multi-objective capacitated vehicle routing problem with time windows', 'International Journal of Industrial Engineering Computations', 2026, '', '', '', '10.5267/j.ijiec.2026.5.004', 'https://consensus.app/papers/details/8a689c9798615639aadb14ddf0a2a520/'),
    'mohammadi2022': ('M. Karimi-Mamaghan, M. Mohammadi, B. Pasdeloup, and P. Meyer', 'Learning to select operators in meta-heuristics: An integration of Q-learning into the iterated greedy algorithm for the permutation flowshop scheduling problem', 'European Journal of Operational Research', 2023, '304', '3', '1296–1330', '10.1016/j.ejor.2022.03.054', 'https://consensus.app/papers/details/3ac40c4d9036563e865f2c3b67c91670/'),
    'jaouhari2026': ('M. El Jaouhari et al.', 'Metaheuristic and reinforcement learning techniques for solving the vehicle routing problem: A literature review', 'Journal of Traffic and Transportation Engineering (English Edition)', 2026, '', '', '', '10.1016/j.jtte.2025.06.005', 'https://consensus.app/papers/details/3188230afed35d399e354ee777f7b9ae/'),
    'xiao2012': ('Y. Xiao, Q. Zhao, I. Kaku, and Y. Xu', 'Development of a fuel consumption optimization model for the capacitated vehicle routing problem', 'Computers & Operations Research', 2012, '39', '7', '1419–1431', '10.1016/j.cor.2011.08.013', 'https://consensus.app/papers/details/c0b7fe014cbf50528730397f33fd1de2/'),
    'turkensteen2017': ('M. Turkensteen', 'The accuracy of carbon emission and fuel consumption computations in green vehicle routing', 'European Journal of Operational Research', 2017, '262', '2', '647–659', '10.1016/j.ejor.2017.03.054', 'https://consensus.app/papers/details/66896fc1de1354c4af1a591aa027fdac/'),
    'santos2011': ('L. Santos, J. Coutinho-Rodrigues, and C. H. Antunes', 'A web spatial decision support system for vehicle routing using Google Maps', 'Decision Support Systems', 2011, '51', '1', '1–16', '10.1016/j.dss.2010.11.001', 'https://consensus.app/papers/details/b579c21de06f56d5adf86debb597277a/'),
    'cavecchia2024': ('M. Cavecchia et al.', 'An optimization-based decision support system for multi-trip vehicle routing problems', 'SN Computer Science', 2024, '', '', '', '', 'https://consensus.app/papers/details/02fc6922cc5d55a5bd018e5f3049432d/'),
    'sahin2024': ('M. K. Şahin and H. Yaman', 'The vehicle routing problem with access restrictions', 'Transportation Science', 2024, '', '', '', '10.1287/trsc.2023.0261', 'https://consensus.app/papers/details/0b34e035aee65a9f81ccd1ab2978002a/'),
    'haklay2008': ('M. Haklay and P. Weber', 'OpenStreetMap: User-generated street maps', 'IEEE Pervasive Computing', 2008, '7', '4', '12–18', '10.1109/MPRV.2008.80', None),
    'tas2012': ('D. Taş, N. Dellaert, T. van Woensel, and T. de Kok', 'Vehicle routing problem with stochastic travel times including soft time windows and service costs', 'Computers & Operations Research', 2013, '40', '1', '214–224', '10.1016/j.cor.2012.06.008', 'https://consensus.app/papers/details/e246a15a64ab5dfbaf16513d415cd210/'),
    'abdullahi2025': ('H. Abdullahi et al.', 'A reliability-extended simheuristic for the sustainable vehicle routing problem with stochastic travel times and demands', 'Journal of Heuristics', 2025, '', '', '', '', 'https://consensus.app/papers/details/d8d5d786e0ae53dfb4d69bb214a894ba/'),
    'rios2021': ('B. H. O. Rios, E. C. Xavier, F. K. Miyazawa, P. Amorim, E. Curcio, and M. J. Santos', 'Recent dynamic vehicle routing problems: A survey', 'Computers & Industrial Engineering', 2021, '160', '', 'Art. no. 107604', '10.1016/j.cie.2021.107604', None),
    'ramadhani2021': ('D. S. Ramadhani et al.', 'Model of vehicle routing problem with split delivery, multi trips, multi products and compartments for determining fuel distribution routes', 'ASEAN Journal of Systems Engineering', 2021, '', '', '', '', 'https://consensus.app/papers/details/30b16b8722035dd4b378e0664ec67bda/'),
}

OTHER = {
    'ipcc2006': 'IPCC, _2006 IPCC Guidelines for National Greenhouse Gas Inventories_, vol. 2 (Energy), ch. 3 (Mobile Combustion). Hayama, Japan: IGES, 2006.',
    'uu22_2009': 'Republik Indonesia, _Undang-Undang Nomor 22 Tahun 2009 tentang Lalu Lintas dan Angkutan Jalan_, Lembaran Negara RI Tahun 2009 Nomor 96, 2009.',
    'pp79_2013': 'Republik Indonesia, _Peraturan Pemerintah Nomor 79 Tahun 2013 tentang Jaringan Lalu Lintas dan Angkutan Jalan_, Lembaran Negara RI Tahun 2013 Nomor 193, 2013.',
    'ortools': 'L. Perron and V. Furnon, _OR-Tools_, ver. 9.15. Mountain View, CA, USA: Google, 2025.',
}



def _fmt(k, m):
    a, t, v, y, vol, no, pp, doi, url = m
    s = f"{a}, “{t},” _{v}_"
    if vol:
        s += f", vol. {vol}"
    if no:
        s += f", no. {no}"
    if pp:
        s += f", {'' if pp.startswith('Art.') else 'pp. '}{pp}"
    return s + f", {y}."


REFS = {k: _fmt(k, m) for k, m in META.items()}
REFS.update(OTHER)

class Citer:
    def __init__(self):
        self.order = []

    def __call__(self, *keys):
        nums = []
        for k in keys:
            if k not in REFS:
                raise KeyError(k)
            if k not in self.order:
                self.order.append(k)
            nums.append(self.order.index(k) + 1)
        nums = sorted(set(nums))
        # rentang berurutan -> [3]–[5]
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            out.append(f"[{nums[i]}]" if j - i < 2 else f"[{nums[i]}]–[{nums[j]}]")
            if 0 < j - i < 2:
                out[-1] = ", ".join(f"[{n}]" for n in nums[i:j + 1])
            i = j + 1
        return ", ".join(out)

    def bibliography(self):
        return [f"[{i}] {REFS[k]}" for i, k in enumerate(self.order, 1)]


def _ris_names(a):
    a = a.replace(", Jr.", " Jr.").replace(" et al.", "").replace(", and ", ", ").replace(" and ", ", ")
    out = []
    for n in [x.strip() for x in a.split(",") if x.strip()]:
        t = n.split()
        i = max((j for j, w in enumerate(t) if w.endswith(".")), default=-1)
        first, last = " ".join(t[:i + 1]), " ".join(t[i + 1:])
        out.append(f"{last}, {first}" if first and last else n)
    return out


def write_ris(order, path):
    """Berkas RIS (UTF-8) untuk reference manager, urut sesuai daftar pustaka."""
    L = []
    for k in order:
        if k in META:
            a, t, v, y, vol, no, pp, doi, url = META[k]
            L.append("TY  - JOUR")
            L += [f"AU  - {n}" for n in _ris_names(a)]
            L += [f"TI  - {t}", f"JO  - {v}", f"PY  - {y}"]
            if vol:
                L.append(f"VL  - {vol}")
            if no:
                L.append(f"IS  - {no}")
            if pp:
                nums = pp.replace("Art. no. ", "").split("–")
                L.append(f"SP  - {nums[0]}")
                if len(nums) > 1:
                    L.append(f"EP  - {nums[1]}")
            if doi:
                L.append(f"DO  - {doi}")
                L.append(f"UR  - https://doi.org/{doi}")
            elif url:
                L.append(f"UR  - {url}")
            if not (vol and pp) and k not in ("watkins1992",):
                L.append("N1  - Volume/halaman belum terverifikasi; lengkapi lewat DOI atau judul di reference manager.")
        else:
            ty = {"ipcc2006": "RPRT", "uu22_2009": "STAT", "pp79_2013": "STAT", "ortools": "COMP"}[k]
            L.append(f"TY  - {ty}")
            txt = REFS[k]
            L.append(f"TI  - {txt}")
        L.append("ER  - ")
        L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(L))
