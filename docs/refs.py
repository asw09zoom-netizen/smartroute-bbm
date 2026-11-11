"""Daftar pustaka (gaya IEEE), penomoran mengikuti urutan sitasi pertama.

Setiap entri jurnal/konferensi diverifikasi keberadaannya lewat basis data Consensus
(Semantic Scholar/OpenAlex) pada 11 November 2026; tautan Consensus dicantumkan sebagai
alamat berkas. Entri klasik memakai DOI penerbit.
"""

REFS = {
    'ropke2006': 'S. Ropke and D. Pisinger, "An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows," _Transportation Science_, vol. 40, no. 4, pp. 455–472, 2006. [Online]. Available: https://consensus.app/papers/details/07cd08e30ccf581187c9d77918d90552/',
    'schrimpf2000': 'G. Schrimpf, J. Schneider, H. Stamm-Wilbrandt, and G. Dueck, "Record breaking optimization results using the ruin and recreate principle," _Journal of Computational Physics_, vol. 159, no. 2, pp. 139–171, 2000, doi: 10.1006/jcph.1999.6413.',
    'toth2003': 'P. Toth and D. Vigo, "The granular tabu search and its application to the vehicle-routing problem," _INFORMS Journal on Computing_, vol. 15, no. 4, pp. 333–346, 2003, doi: 10.1287/ijoc.15.4.333.24890.',
    'ortools': 'L. Perron and V. Furnon, _OR-Tools_, ver. 9.15. Google, 2025. [Online]. Available: https://developers.google.com/optimization/',
    'dantzig1959': 'G. B. Dantzig and J. H. Ramser, "The truck dispatching problem," _Management Science_, vol. 6, no. 1, pp. 80–91, 1959, doi: 10.1287/mnsc.6.1.80.',
    'clarke1964': 'G. Clarke and J. W. Wright, "Scheduling of vehicles from a central depot to a number of delivery points," _Operations Research_, vol. 12, no. 4, pp. 568–581, 1964, doi: 10.1287/opre.12.4.568.',
    'rios2021': 'B. H. O. Rios, E. C. Xavier, F. K. Miyazawa, P. Amorim, E. Curcio, and M. J. Santos, "Recent dynamic vehicle routing problems: A survey," _Computers & Industrial Engineering_, vol. 160, p. 107604, 2021, doi: 10.1016/j.cie.2021.107604.',
    'sze2024': 'J. F. Sze, S. Salhi, and N. Wassan, "An adaptive variable neighbourhood search approach for the dynamic vehicle routing problem," _Computers & Operations Research_, vol. 164, p. 106531, 2024, doi: 10.1016/j.cor.2024.106531.',
    'cornillier2008': 'F. Cornillier, F. F. Boctor, G. Laporte, and J. Renaud, "A heuristic for the multi-period petrol station replenishment problem," _European Journal of Operational Research_, vol. 191, no. 2, pp. 295–305, 2008.',
    'wang2020': 'L. Wang, J. Kinable, and T. van Woensel, "The fuel replenishment problem: A split-delivery multi-compartment vehicle routing problem with multiple trips," _Computers & Operations Research_, vol. 118, p. 104904, 2020.',
    'coelho2015': 'L. C. Coelho and G. Laporte, "Classification, models and exact algorithms for multi-compartment delivery problems," _European Journal of Operational Research_, vol. 242, no. 3, pp. 854–864, 2015.',
    'ostermeier2021': 'M. Ostermeier, T. Henke, A. Hübner, and G. Wäscher, "Multi-compartment vehicle routing problems: State-of-the-art, modeling framework and future directions," _European Journal of Operational Research_, vol. 292, no. 3, pp. 799–817, 2021.',
    'cattaruzza2016': 'D. Cattaruzza, N. Absi, and D. Feillet, "Vehicle routing problems with multiple trips," _4OR_, vol. 14, no. 3, pp. 223–259, 2016.',
    'azi2014': 'N. Azi, M. Gendreau, and J.-Y. Potvin, "An adaptive large neighborhood search for a vehicle routing problem with multiple routes," _Computers & Operations Research_, vol. 41, pp. 167–173, 2014.',
    'prins2004': 'C. Prins, "A simple and effective evolutionary algorithm for the vehicle routing problem," _Computers & Operations Research_, vol. 31, no. 12, pp. 1985–2002, 2004.',
    'holland1975': 'J. H. Holland, _Adaptation in Natural and Artificial Systems_. Ann Arbor, MI, USA: Univ. of Michigan Press, 1975.',
    'kirkpatrick1983': 'S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi, "Optimization by simulated annealing," _Science_, vol. 220, no. 4598, pp. 671–680, 1983, doi: 10.1126/science.220.4598.671.',
    'sutton2018': 'R. S. Sutton and A. G. Barto, _Reinforcement Learning: An Introduction_, 2nd ed. Cambridge, MA, USA: MIT Press, 2018.',
    'watkins1992': 'C. J. C. H. Watkins and P. Dayan, "Q-learning," _Machine Learning_, vol. 8, no. 3–4, pp. 279–292, 1992.',
    'dekker2012': 'R. Dekker, J. Bloemhof, and I. Mallidis, "Operations Research for green logistics – An overview of aspects, issues, contributions and challenges," _European Journal of Operational Research_, vol. 219, no. 3, pp. 671–679, 2012, doi: 10.1016/j.ejor.2011.11.010.',
    'bektas2011': 'T. Bektaş and G. Laporte, "The pollution-routing problem," _Transportation Research Part B: Methodological_, vol. 45, no. 8, pp. 1232–1250, 2011.',
    'ipcc2006': 'IPCC, _2006 IPCC Guidelines for National Greenhouse Gas Inventories_, vol. 2 (Energy), ch. 3 (Mobile Combustion). Hayama, Japan: IGES, 2006.',
    'mamdani1975': 'E. H. Mamdani and S. Assilian, "An experiment in linguistic synthesis with a fuzzy logic controller," _International Journal of Man-Machine Studies_, vol. 7, no. 1, pp. 1–13, 1975.',
    'mtz1960': 'C. E. Miller, A. W. Tucker, and R. A. Zemlin, "Integer programming formulation of traveling salesman problems," _Journal of the ACM_, vol. 7, no. 4, pp. 326–329, 1960.',
    'uu22_2009': 'Republik Indonesia, _Undang-Undang Nomor 22 Tahun 2009 tentang Lalu Lintas dan Angkutan Jalan_, Lembaran Negara RI Tahun 2009 Nomor 96, 2009.',
    'pp79_2013': 'Republik Indonesia, _Peraturan Pemerintah Nomor 79 Tahun 2013 tentang Jaringan Lalu Lintas dan Angkutan Jalan_, Lembaran Negara RI Tahun 2013 Nomor 193, 2013.',
    'haklay2008': 'M. Haklay and P. Weber, "OpenStreetMap: User-generated street maps," _IEEE Pervasive Computing_, vol. 7, no. 4, pp. 12–18, 2008, doi: 10.1109/MPRV.2008.80.',
    'dijkstra1959': 'E. W. Dijkstra, "A note on two problems in connexion with graphs," _Numerische Mathematik_, vol. 1, pp. 269–271, 1959, doi: 10.1007/BF01386390.',
    'huangfu2018': 'Q. Huangfu and J. A. J. Hall, "Parallelizing the dual revised simplex method," _Mathematical Programming Computation_, vol. 10, no. 1, pp. 119–142, 2018.',
    'uchoa2017': 'E. Uchoa, D. Pecin, A. Pessoa, M. Poggi, T. Vidal, and A. Subramanian, "New benchmark instances for the capacitated vehicle routing problem," _European Journal of Operational Research_, vol. 257, no. 3, pp. 845–858, 2017.',
    'vidal2022': 'T. Vidal, "Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood," _Computers & Operations Research_, vol. 140, p. 105643, 2022.',
    'gross2008': 'D. Gross, J. F. Shortle, J. M. Thompson, and C. M. Harris, _Fundamentals of Queueing Theory_, 4th ed. Hoboken, NJ, USA: Wiley, 2008.',
    'derrac2011': 'J. Derrac, S. García, D. Molina, and F. Herrera, "A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms," _Swarm and Evolutionary Computation_, vol. 1, no. 1, pp. 3–18, 2011.',
    'burke2013': 'E. K. Burke _et al._, "Hyper-heuristics: a survey of the state of the art," _Journal of the Operational Research Society_, vol. 64, no. 12, pp. 1695–1724, 2013.',
    'wu2024': 'W.-T. Wu et al., “The multi-compartment truck and trailer petrol station replenishment problem with domino hazard risks,” _Transportation Research Part B: Methodological_, 2024. [Online]. Available: https://consensus.app/papers/details/93c2ca1ba4ef5871b44f5fcca7607efd/',
    'febriandini2020': 'I. F. Febriandini et al., “Multi-compartment vehicle routing problem to find the alternative distribution route of petroleum product delivery,” _IOP Conference Series: Materials Science and Engineering_, 2020. [Online]. Available: https://consensus.app/papers/details/39163bc045405f879fbe2361ba927598/',
    'che2023': 'A. Che et al., “Tabu-based adaptive large neighborhood search for multi-depot petrol station replenishment with open inter-depot routes,” _IEEE Transactions on Intelligent Transportation Systems_, 2023. [Online]. Available: https://consensus.app/papers/details/0841fe16992457d69b91946d30684915/',
    'haseltalab2024': 'S. Haseltalab et al., “Enhancing efficiency in delivering petroleum products: optimizing the deteriorating inventory-routing problem with heterogeneous multi-compartment vehicles,” _International Journal of Management Science and Engineering Management_, 2024. [Online]. Available: https://consensus.app/papers/details/141eab9ba863535eac40eecf23077e7e/',
    'liu2025': 'Z.-S. Liu et al., “A hybrid variable neighborhood search for a real-world petrol station replenishment problem with multi-compartment vehicles,” _RAIRO – Operations Research_, 2025. [Online]. Available: https://consensus.app/papers/details/c03758e257785676955d62c478579dcd/',
    'benantar2016': 'A. Benantar et al., “A petrol station replenishment problem: new variant and formulation,” _Logistics Research_, 2016. [Online]. Available: https://consensus.app/papers/details/7c21d5eef0d955a986fa5182c10f8986/',
    'cornillier2008b': 'F. Cornillier et al., “An exact algorithm for the petrol station replenishment problem,” _Journal of the Operational Research Society_, 2008. [Online]. Available: https://consensus.app/papers/details/e728664bb42a5b79b5e72553a3995316/',
    'cornillier2009': 'F. Cornillier et al., “The petrol station replenishment problem with time windows,” _Computers & Operations Research_, 2009. [Online]. Available: https://consensus.app/papers/details/a9b3a806184857ebbc3d81abbb5b14f4/',
    'bani2023': 'A. Bani et al., “Solving a real-world multi-depot multi-period petrol replenishment problem with complex loading constraints,” _European Journal of Operational Research_, 2023. [Online]. Available: https://consensus.app/papers/details/1b055e24a30855549bfb7cfe542640fd/',
    'baptista2024': 'G. Baptista et al., “An exact approach to the multi-compartment vehicle routing problem: The case of a fuel distribution company,” _Mathematics_, 2024. [Online]. Available: https://consensus.app/papers/details/4752c3664a745051bfa0f827e33cf39f/',
    'yahyaoui2018': 'H. Yahyaoui et al., “Two metaheuristic approaches for solving the multi-compartment vehicle routing problem,” _Operational Research_, 2018. [Online]. Available: https://consensus.app/papers/details/731d19e9aaca56f6a6850efc334e62a2/',
    'efthymiadis2023': 'S. Efthymiadis et al., “Solving a heterogeneous fleet multi-compartment vehicle routing problem: a case study,” _International Journal of Systems Science: Operations & Logistics_, 2023. [Online]. Available: https://consensus.app/papers/details/4a2445f11be3581aa9b46d8b517b605c/',
    'hajba2023': 'T. Hajba et al., “A MILP approach combined with clustering to solve a special petrol station replenishment problem,” _Central European Journal of Operations Research_, 2023. [Online]. Available: https://consensus.app/papers/details/570857c4cc03586a8aa1e324a539e24d/',
    'xu2021': 'X. Xu et al., “Multi-objective robust optimisation model for MDVRPLS in refined oil distribution,” _International Journal of Production Research_, 2021. [Online]. Available: https://consensus.app/papers/details/06740e4aa72d5504b6c0d751f7696435/',
    'wang2019': 'B.-H. Wang et al., “A metaheuristic method for the multireturn-to-depot petrol truck routing problem with time windows,” _Petroleum Science_, 2019. [Online]. Available: https://consensus.app/papers/details/af03b0b434f855a5ad4bc0d4bbab00e2/',
    'surjandari2011': 'I. Surjandari et al., “Oil fuel delivery optimization for multi product and multi depot: the case of petrol station replenishment problem (PSRP),” _Proc. Int. Conf. (indexed record)_, 2011. [Online]. Available: https://consensus.app/papers/details/a99d0231213c58089783ade7aff0e49f/',
    'ramadhani2021': 'D. S. Ramadhani et al., “Model of vehicle routing problem with split delivery, multi trips, multi products and compartments for determining fuel distribution routes,” _ASEAN Journal of Systems Engineering_, 2021. [Online]. Available: https://consensus.app/papers/details/30b16b8722035dd4b378e0664ec67bda/',
    'zhao2025': 'W. Zhao et al., “A Q-learning-assisted evolutionary optimization method for solving the capacitated vehicle routing problem,” _Applied Sciences_, 2025. [Online]. Available: https://consensus.app/papers/details/d3ea93218f29576aa64e83db61b27bcd/',
    'qi2022': 'R. Qi et al., “QMOEA: A Q-learning-based multiobjective evolutionary algorithm for solving time-dependent green vehicle routing problems with time windows,” _Information Sciences_, 2022. [Online]. Available: https://consensus.app/papers/details/5e6b1b01e1fa525f9696e3c0cf3b7030/',
    'koc2026': 'A. Koç et al., “A novel reinforcement learning–assisted genetic algorithm for the multi-objective capacitated vehicle routing problem with time windows,” _International Journal of Industrial Engineering Computations_, 2026. [Online]. Available: https://consensus.app/papers/details/8a689c9798615639aadb14ddf0a2a520/',
    'yi2023': 'W. Yi et al., “Automated design of metaheuristics using reinforcement learning within a novel general search framework,” _IEEE Transactions on Evolutionary Computation_, 2023. [Online]. Available: https://consensus.app/papers/details/bfdd1a44a315580ea81f3e6f79aa81bd/',
    'lin2025': 'J. Lin et al., “A Q-learning-based hyper-heuristic for capacitated electric vehicle routing problem,” _IEEE Transactions on Intelligent Transportation Systems_, 2025. [Online]. Available: https://consensus.app/papers/details/762b7b88b91457e8bf9c043684fac0b2/',
    'kalatzantonakis2022': 'P. Kalatzantonakis et al., “A reinforcement learning-variable neighborhood search method for the capacitated vehicle routing problem,” _Expert Systems with Applications_, 2022. [Online]. Available: https://consensus.app/papers/details/25c803b0414e53318c70a5b87bf04cc5/',
    'qin2021': 'W. Qin et al., “A novel reinforcement learning-based hyper-heuristic for heterogeneous vehicle routing problem,” _Computers & Industrial Engineering_, 2021. [Online]. Available: https://consensus.app/papers/details/68abaf42d7e85bd6bdfdae1bfc282c7b/',
    'mohammadi2022': 'M. Karimi-Mamaghan et al., “Learning to select operators in meta-heuristics: An integration of Q-learning into the iterated greedy algorithm for the permutation flowshop scheduling problem,” _European Journal of Operational Research_, 2022. [Online]. Available: https://consensus.app/papers/details/3ac40c4d9036563e865f2c3b67c91670/',
    'voigt2024': 'S. Voigt, “A review and ranking of operators in adaptive large neighborhood search for vehicle routing problems,” _European Journal of Operational Research_, 2024. [Online]. Available: https://consensus.app/papers/details/50d140bde97e5a399619f0d1fa2d768e/',
    'tian2023': 'Y. Tian et al., “Deep reinforcement learning based adaptive operator selection for evolutionary multi-objective optimization,” _IEEE Transactions on Emerging Topics in Computational Intelligence_, 2023. [Online]. Available: https://consensus.app/papers/details/5cd4cecb0d99520c8007657bfbb3e6a5/',
    'jaouhari2026': 'M. E. L. Jaouhari et al., “Metaheuristic and reinforcement learning techniques for solving the vehicle routing problem: A literature review,” _Journal of Traffic and Transportation Engineering (English Edition)_, 2026. [Online]. Available: https://consensus.app/papers/details/3188230afed35d399e354ee777f7b9ae/',
    'zhaoj2024': 'J.-Y. Zhao et al., “A hybrid genetic search and dynamic programming-based split algorithm for the multi-trip time-dependent vehicle routing problem,” _European Journal of Operational Research_, 2024. [Online]. Available: https://consensus.app/papers/details/0d7e183e7358563fbada7bc4876cdf8f/',
    'cattaruzza2014': 'D. Cattaruzza et al., “A memetic algorithm for the multi trip vehicle routing problem,” _European Journal of Operational Research_, 2014. [Online]. Available: https://consensus.app/papers/details/9d934a9269e2524eb1b1d32d793cc613/',
    'prins2009': 'C. Prins, “Two memetic algorithms for heterogeneous fleet vehicle routing problems,” _Engineering Applications of Artificial Intelligence_, 2009. [Online]. Available: https://consensus.app/papers/details/a902cd6b24a15b4a9bef421e1c7f567b/',
    'vidal2012': 'T. Vidal et al., “A hybrid genetic algorithm for multidepot and periodic vehicle routing problems,” _Operations Research_, 2012. [Online]. Available: https://consensus.app/papers/details/fee7f1935e745f588e25af8a0ac6f80b/',
    'subramanian2012': 'A. Subramanian et al., “A hybrid algorithm for the heterogeneous fleet vehicle routing problem,” _European Journal of Operational Research_, 2012. [Online]. Available: https://consensus.app/papers/details/90fa898cc98759c1bc3e6598d199d607/',
    'ariyani2018': 'A. Ariyani et al., “Hybrid genetic algorithms and simulated annealing for multi-trip vehicle routing problem with time windows,” _International Journal of Electrical and Computer Engineering (IJECE)_, 2018. [Online]. Available: https://consensus.app/papers/details/77111e214127545186589332958d4eb9/',
    'sahin2022': 'M. K. Sahin et al., “A branch and price algorithm for the heterogeneous fleet multi-depot multi-trip vehicle routing problem with time windows,” _Transportation Science_, 2022. [Online]. Available: https://consensus.app/papers/details/d018433344205480b8b08785db454e52/',
    'xiao2012': 'Y. Xiao et al., “Development of a fuel consumption optimization model for the capacitated vehicle routing problem,” _Computers & Operations Research_, 2012. [Online]. Available: https://consensus.app/papers/details/c0b7fe014cbf50528730397f33fd1de2/',
    'kopfer2014': 'H. W. Kopfer et al., “Reducing greenhouse gas emissions of a heterogeneous vehicle fleet,” _Flexible Services and Manufacturing Journal_, 2014. [Online]. Available: https://consensus.app/papers/details/3418129944f057c69b0cc92e1cf9d729/',
    'ehmke2016': 'J. F. Ehmke et al., “Vehicle routing to minimize time-dependent emissions in urban areas,” _European Journal of Operational Research_, 2016. [Online]. Available: https://consensus.app/papers/details/70e6675c1d075268814a347058ccc5bc/',
    'turkensteen2017': 'M. Turkensteen, “The accuracy of carbon emission and fuel consumption computations in green vehicle routing,” _European Journal of Operational Research_, 2017. [Online]. Available: https://consensus.app/papers/details/66896fc1de1354c4af1a591aa027fdac/',
    'santos2011': 'L. Santos et al., “A web spatial decision support system for vehicle routing using Google Maps,” _Decision Support Systems_, 2011. [Online]. Available: https://consensus.app/papers/details/b579c21de06f56d5adf86debb597277a/',
    'cavecchia2024': 'M. Cavecchia et al., “An optimization-based decision support system for multi-trip vehicle routing problems,” _SN Computer Science_, 2024. [Online]. Available: https://consensus.app/papers/details/02fc6922cc5d55a5bd018e5f3049432d/',
    'ray2007': 'J. J. Ray, “A web-based spatial decision support system optimizes routes for oversize/overweight vehicles in Delaware,” _Decision Support Systems_, 2007. [Online]. Available: https://consensus.app/papers/details/aa71bf579f7f52c2b84f38e440895f58/',
    'sahin2024': 'M. K. Sahin et al., “The vehicle routing problem with access restrictions,” _Transportation Science_, 2024. [Online]. Available: https://consensus.app/papers/details/0b34e035aee65a9f81ccd1ab2978002a/',
    'peng2020': 'L. Peng et al., “VeRoViz: A vehicle routing visualization toolkit,” _INFORMS Journal on Computing_, 2020. [Online]. Available: https://consensus.app/papers/details/d76e4db70adf53d895a2276aa349b030/',
    'andersson2008': 'G. Andersson et al., “RuttOpt – A decision support system for routing of logging trucks,” _Canadian Journal of Forest Research_, 2008. [Online]. Available: https://consensus.app/papers/details/4abf1b63b0ff5980b16adf0540ba207b/',
    'tas2012': 'D. Taş et al., “Vehicle routing problem with stochastic travel times including soft time windows and service costs,” _Computers & Operations Research_, 2012. [Online]. Available: https://consensus.app/papers/details/e246a15a64ab5dfbaf16513d415cd210/',
    'hu2018': 'C. Hu et al., “Robust vehicle routing problem with hard time windows under demand and travel time uncertainty,” _Computers & Operations Research_, 2018. [Online]. Available: https://consensus.app/papers/details/a7f506a682bd554c8dda5213fbada986/',
    'munari2019': 'P. Munari et al., “The robust vehicle routing problem with time windows: Compact formulation and branch-price-and-cut method,” _Transportation Science_, 2019. [Online]. Available: https://consensus.app/papers/details/b3f5c72f0054573c85a48152c76e577a/',
    'zhang2021': 'Y. Zhang et al., “Robust data-driven vehicle routing with time windows,” _Operations Research_, 2021. [Online]. Available: https://consensus.app/papers/details/41fc0a48e66c57e8baa9529fde76fcf4/',
    'abdullahi2025': 'H. Abdullahi et al., “A reliability-extended simheuristic for the sustainable vehicle routing problem with stochastic travel times and demands,” _Journal of Heuristics_, 2025. [Online]. Available: https://consensus.app/papers/details/d8d5d786e0ae53dfb4d69bb214a894ba/',
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
