"""Daftar pustaka (gaya IEEE). Penomoran mengikuti urutan sitasi pertama.

Catatan: entri bertanda VERIFY belum dilengkapi volume/halaman/DOI; periksa ulang
sebelum submit ke jurnal.
"""

REFS = {
    "dantzig1959": 'G. B. Dantzig and J. H. Ramser, "The truck dispatching problem," _Management Science_, vol. 6, no. 1, pp. 80–91, 1959, doi: 10.1287/mnsc.6.1.80.',
    "clarke1964": 'G. Clarke and J. W. Wright, "Scheduling of vehicles from a central depot to a number of delivery points," _Operations Research_, vol. 12, no. 4, pp. 568–581, 1964, doi: 10.1287/opre.12.4.568.',
    "rios2021": 'B. H. O. Rios, E. C. Xavier, F. K. Miyazawa, P. Amorim, E. Curcio, and M. J. Santos, "Recent dynamic vehicle routing problems: A survey," _Computers & Industrial Engineering_, vol. 160, p. 107604, 2021, doi: 10.1016/j.cie.2021.107604.',
    "sze2024": 'J. F. Sze, S. Salhi, and N. Wassan, "An adaptive variable neighbourhood search approach for the dynamic vehicle routing problem," _Computers & Operations Research_, vol. 164, p. 106531, 2024, doi: 10.1016/j.cor.2024.106531.',
    "melani2025": 'T. Melani, S. Abusini, and M. Marjono, "Optimization of Pertamax fuel distribution using Clarke-Wright Savings, Nearest Neighbour, and Goal Programming (case study: Malang City)," _CAUCHY: Jurnal Matematika Murni dan Aplikasi_, vol. 10, no. 1, 2025, doi: 10.18860/cauchy.v10i1.31529.',
    "hidayat2025": 'D. W. Hidayat and N. B. Mulyono, "Optimizing fuel distribution costs through vehicle routing problem modeling in Jakarta-Tanjung Gerem terminals," _Jurnal Ilmiah Manajemen Kesatuan_, vol. 13, no. 5, 2025, doi: 10.37641/jimkes.v13i5.3547.',
    "nugroho2020": 'S. Nugroho, L. Nafisah, M. S. A. Khannan, H. Mastrisiswadi, and M. Ramdhani, "Vehicle routing problem with heterogeneous fleet, split delivery, multiple product, multiple trip, and time windows: A case study in fuel distribution," _IOP Conf. Ser.: Materials Science and Engineering_, vol. 847, 2020. [VERIFY]',
    "ramadhani2021": 'D. S. Ramadhani, N. A. Masruroh, and J. Waluyo, "Model of vehicle routing problem with split delivery, multi trips, multi products and compartments for determining fuel distribution routes," _ASEAN Journal of Systems Engineering_, vol. 5, no. 2, 2021, doi: 10.22146/ajse.v5i2.72461.',
    "surjandari2011": 'I. Surjandari _et al._, "Oil fuel delivery optimization for multi product and multi depot: the case of petrol station replenishment problem (PSRP)," 2011. [VERIFY]',
    "awaludin2025": 'A. Awaludin _et al._, "Fuel distribution route optimization model based on hybrid Cheapest Insertion–Tabu Search," _Jurnal Riset Ilmu Teknik_, 2025. [VERIFY]',
    "abdul2023": 'U. I. Abdul _et al._, "Optimasi rute pendistribusian BBM menggunakan algoritma Tabu Search dan Cheapest Insertion Heuristic," _Transformasi: Jurnal Pendidikan Matematika dan Matematika_, 2023. [VERIFY]',
    "aqidawati2021": 'E. F. Aqidawati _et al._, "Application of vehicle routing problem to determine optimal route in fuel distribution: A case study," in _Proc. Int. Conf. Industrial Engineering and Operations Management_, 2021. [VERIFY]',
    "febriandini2020": 'I. F. Febriandini _et al._, "Multi-compartment vehicle routing problem to find the alternative distribution route of petroleum product delivery," _IOP Conf. Ser.: Materials Science and Engineering_, 2020. [VERIFY]',
    "cornillier2008": 'F. Cornillier, F. F. Boctor, G. Laporte, and J. Renaud, "A heuristic for the multi-period petrol station replenishment problem," _European Journal of Operational Research_, vol. 191, no. 2, pp. 295–305, 2008.',
    "benantar2016": 'A. Benantar, R. Ouafi, and J. Boukachour, "A petrol station replenishment problem: new variant and formulation," _Logistics Research_, vol. 9, 2016. [VERIFY]',
    "wang2020": 'L. Wang, J. Kinable, and T. van Woensel, "The fuel replenishment problem: A split-delivery multi-compartment vehicle routing problem with multiple trips," _Computers & Operations Research_, vol. 118, p. 104904, 2020.',
    "wang2019": 'B.-H. Wang _et al._, "A metaheuristic method for the multireturn-to-depot petrol truck routing problem with time windows," _Petroleum Science_, 2019. [VERIFY]',
    "che2023": 'A. Che _et al._, "Tabu-based adaptive large neighborhood search for multi-depot petrol station replenishment with open inter-depot routes," _IEEE Transactions on Intelligent Transportation Systems_, 2023. [VERIFY]',
    "wu2024": 'W.-T. Wu _et al._, "The multi-compartment truck and trailer petrol station replenishment problem with domino hazard risks," _Transportation Research Part B: Methodological_, 2024. [VERIFY]',
    "baptista2024": 'G. Baptista _et al._, "An exact approach to the multi-compartment vehicle routing problem: The case of a fuel distribution company," _Mathematics_, 2024. [VERIFY]',
    "efthymiadis2023": 'S. Efthymiadis _et al._, "Solving a heterogeneous fleet multi-compartment vehicle routing problem: a case study," _International Journal of Systems Science: Operations & Logistics_, 2023. [VERIFY]',
    "yahyaoui2018": 'H. Yahyaoui _et al._, "Two metaheuristic approaches for solving the multi-compartment vehicle routing problem," _Operational Research_, 2018. [VERIFY]',
    "haseltalab2024": 'S. Haseltalab _et al._, "Enhancing efficiency in delivering petroleum products: optimizing the deteriorating inventory-routing problem with heterogeneous multi-compartment vehicles," _International Journal of Management Science and Engineering Management_, 2024. [VERIFY]',
    "liu2025": 'Z.-S. Liu _et al._, "A hybrid variable neighborhood search for a real-world petrol station replenishment problem with multi-compartment vehicles," _RAIRO – Operations Research_, 2025. [VERIFY]',
    "coelho2015": 'L. C. Coelho and G. Laporte, "Classification, models and exact algorithms for multi-compartment delivery problems," _European Journal of Operational Research_, vol. 242, no. 3, pp. 854–864, 2015.',
    "ostermeier2021": 'M. Ostermeier, T. Henke, A. Hübner, and G. Wäscher, "Multi-compartment vehicle routing problems: State-of-the-art, modeling framework and future directions," _European Journal of Operational Research_, vol. 292, no. 3, pp. 799–817, 2021.',
    "cattaruzza2016": 'D. Cattaruzza, N. Absi, and D. Feillet, "Vehicle routing problems with multiple trips," _4OR_, vol. 14, no. 3, pp. 223–259, 2016.',
    "azi2014": 'N. Azi, M. Gendreau, and J.-Y. Potvin, "An adaptive large neighborhood search for a vehicle routing problem with multiple routes," _Computers & Operations Research_, vol. 41, pp. 167–173, 2014.',
    "prins2004": 'C. Prins, "A simple and effective evolutionary algorithm for the vehicle routing problem," _Computers & Operations Research_, vol. 31, no. 12, pp. 1985–2002, 2004.',
    "holland1975": 'J. H. Holland, _Adaptation in Natural and Artificial Systems_. Ann Arbor, MI, USA: Univ. of Michigan Press, 1975.',
    "kirkpatrick1983": 'S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, "Optimization by simulated annealing," _Science_, vol. 220, no. 4598, pp. 671–680, 1983, doi: 10.1126/science.220.4598.671.',
    "sutton2018": 'R. S. Sutton and A. G. Barto, _Reinforcement Learning: An Introduction_, 2nd ed. Cambridge, MA, USA: MIT Press, 2018.',
    "watkins1992": 'C. J. C. H. Watkins and P. Dayan, "Q-learning," _Machine Learning_, vol. 8, no. 3–4, pp. 279–292, 1992.',
    "qi2022": 'R. Qi, J. Li, J. Wang, H. Jin, and Y. Han, "QMOEA: A Q-learning-based multiobjective evolutionary algorithm for solving time-dependent green vehicle routing problems with time windows," _Information Sciences_, 2022. [VERIFY]',
    "zhao2025": 'W. Zhao _et al._, "A Q-learning-assisted evolutionary optimization method for solving the capacitated vehicle routing problem," _Applied Sciences_, 2025. [VERIFY]',
    "lin2025": 'J. Lin _et al._, "A Q-learning-based hyper-heuristic for capacitated electric vehicle routing problem," _IEEE Transactions on Intelligent Transportation Systems_, 2025. [VERIFY]',
    "koc2026": 'A. Koç _et al._, "A novel reinforcement learning–assisted genetic algorithm for the multi-objective capacitated vehicle routing problem with time windows," _International Journal of Industrial Engineering Computations_, 2026. [VERIFY]',
    "zhaoy2024": 'Y. Zhao _et al._, "Energy-efficient dynamic vehicle routing for waste collection by Q-learning-based hyperheuristic particle swarm optimization," _IEEE Access_, 2024. [VERIFY]',
    "yi2023": 'W. Yi, R. Qu, L. Jiao, and B. Niu, "Automated design of metaheuristics using reinforcement learning within a novel general search framework," _IEEE Transactions on Evolutionary Computation_, 2023. [VERIFY]',
    "dekker2012": 'R. Dekker, J. Bloemhof, and I. Mallidis, "Operations Research for green logistics – An overview of aspects, issues, contributions and challenges," _European Journal of Operational Research_, vol. 219, no. 3, pp. 671–679, 2012, doi: 10.1016/j.ejor.2011.11.010.',
    "bektas2011": 'T. Bektaş and G. Laporte, "The pollution-routing problem," _Transportation Research Part B: Methodological_, vol. 45, no. 8, pp. 1232–1250, 2011.',
    "ipcc2006": 'IPCC, _2006 IPCC Guidelines for National Greenhouse Gas Inventories_, vol. 2 (Energy), ch. 3 (Mobile Combustion). Hayama, Japan: IGES, 2006.',
    "mamdani1975": 'E. H. Mamdani and S. Assilian, "An experiment in linguistic synthesis with a fuzzy logic controller," _International Journal of Man-Machine Studies_, vol. 7, no. 1, pp. 1–13, 1975.',
    "mtz1960": 'C. E. Miller, A. W. Tucker, and R. A. Zemlin, "Integer programming formulation of traveling salesman problems," _Journal of the ACM_, vol. 7, no. 4, pp. 326–329, 1960.',
    "huangfu2018": 'Q. Huangfu and J. A. J. Hall, "Parallelizing the dual revised simplex method," _Mathematical Programming Computation_, vol. 10, no. 1, pp. 119–142, 2018.',
    "uchoa2017": 'E. Uchoa, D. Pecin, A. Pessoa, M. Poggi, T. Vidal, and A. Subramanian, "New benchmark instances for the capacitated vehicle routing problem," _European Journal of Operational Research_, vol. 257, no. 3, pp. 845–858, 2017.',
    "vidal2022": 'T. Vidal, "Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood," _Computers & Operations Research_, vol. 140, p. 105643, 2022.',
    "gross2008": 'D. Gross, J. F. Shortle, J. M. Thompson, and C. M. Harris, _Fundamentals of Queueing Theory_, 4th ed. Hoboken, NJ, USA: Wiley, 2008.',
    "derrac2011": 'J. Derrac, S. García, D. Molina, and F. Herrera, "A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms," _Swarm and Evolutionary Computation_, vol. 1, no. 1, pp. 3–18, 2011.',
    "burke2013": 'E. K. Burke _et al._, "Hyper-heuristics: a survey of the state of the art," _Journal of the Operational Research Society_, vol. 64, no. 12, pp. 1695–1724, 2013.',
}


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
