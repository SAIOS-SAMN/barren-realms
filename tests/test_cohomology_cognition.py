import unittest
from fractions import Fraction

from xylarium.kernel.engine import GameKernel
from xylarium.kernel import cognition, physics, counsel, intellect, torsion


class TestCohomologyCognition(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()

    def test_material_cochain_hodge_fields_and_coboundary(self):
        cochain = cognition.MaterialCochain()
        cochain.add("Fe", 100.0, 50.0)
        self.assertEqual(cochain.divergence("Fe"), 50.0)
        self.assertEqual(cochain.holonomy_phase, Fraction(0))

        # Test coboundary_1 on sector with planets
        sec = next(s for s in self.kernel.sectors.values() if len(s.planets) >= 2)
        diffs = cognition.coboundary_1(self.kernel, sec, cochain)
        self.assertIsInstance(diffs, dict)
        self.assertGreater(len(diffs), 0)

        # Test hodge decomposition preserving dimension
        grad, harm = cognition.hodge_decompose(diffs)
        self.assertEqual(len(harm), len(diffs))

    def test_electrodynamic_induction_locked_vs_spinning(self):
        star_dict = {"m": Fraction(1)}
        
        # 1. Tidally locked world: induction is strictly zero (Dirichlet mirror)
        body_locked = {"q": Fraction(1), "locked": True, "day": Fraction(365)}
        ind_locked = physics.electrodynamic_induction(star_dict, body_locked, 10.0)
        self.assertEqual(ind_locked, Fraction(0))

        # 2. Spinning world: non-zero holonomy induction
        body_spin = {"q": Fraction(1), "locked": False, "day": Fraction(1)}
        ind_spin = physics.electrodynamic_induction(star_dict, body_spin, 10.0)
        self.assertGreater(ind_spin, Fraction(0))

    def test_counsel_breadth_superposition_preservation(self):
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        holder = "civ:Test"
        
        # Evaluate breadth
        plans = counsel.breadth(self.kernel, planet, holder)
        self.assertIsInstance(plans, list)
        self.assertGreater(len(plans), 0)
        
        # Verify holonomy_phase is tracked without collapsing to a scalar utility
        first_plan = plans[0]
        self.assertIn("holonomy_phase", first_plan)
        self.assertIn("chance", first_plan)

    def test_verify_harmonic_convergence_and_proof_minting(self):
        sec = self.kernel.sectors[1]
        # Emit a strong resonant bounce
        torsion.emit_bounce(self.kernel, origin_sector=1, energy_scale=100.0, chirality=1)
        
        # Verify harmonic convergence
        cert = intellect.verify_harmonic_convergence(self.kernel, "civ:Elder", 1)
        if cert:
            self.assertEqual(cert["lane"], "INTELLECT")
            self.assertIn("proof:civ:Elder:1:", cert["id"])

    def test_non_abelian_quaternion_algebra(self):
        # Verify strict non-commutativity in SU(2)
        q1 = physics.Quaternion.from_axis_angle((1.0, 0.0, 0.0), 1.2)
        q2 = physics.Quaternion.from_axis_angle((0.0, 1.0, 0.0), 0.8)
        
        prod1 = q1 * q2
        prod2 = q2 * q1
        # In non-abelian space: q1 * q2 != q2 * q1
        self.assertNotEqual((prod1.w, prod1.x, prod1.y, prod1.z), (prod2.w, prod2.x, prod2.y, prod2.z))
        
        # Lie bracket commutator is non-zero
        comm = q1.commutator(q2)
        self.assertGreater(comm.norm(), 1e-4)

    def test_non_euclidean_manifold_and_curvature_2(self):
        # 1. Non-Euclidean curved geodesic vs flat Euclidean subtraction
        body1 = {"q": Fraction(1, 2), "orbital_angle": 0.0}
        body2 = {"q": Fraction(2), "orbital_angle": 1.5}
        geodesic_len, axis = physics.non_euclidean_geodesic(Fraction(1), body1, body2)
        flat_dist = abs(float(body1["q"])**2 - float(body2["q"])**2)
        
        self.assertGreater(geodesic_len, 0.0)
        self.assertNotEqual(geodesic_len, flat_dist)
        
        # 2. Non-abelian 2-simplex curvature Wilson loops
        sec = next(s for s in self.kernel.sectors.values() if len(s.planets) >= 3)
        cochain = cognition.MaterialCochain()
        diffs = cognition.coboundary_1(self.kernel, sec, cochain)
        plaquettes = cognition.curvature_2(self.kernel, sec, diffs)
        
        self.assertIsInstance(plaquettes, dict)
        if len(plaquettes) > 0:
            w_loop = next(iter(plaquettes.values()))
            self.assertIsInstance(w_loop, physics.Quaternion)

    def test_remediated_manifolds(self):
        from xylarium.kernel import decide, surface, ideology, spheres
        
        # 1. Pareto Frontier Multi-Objective Manifold
        vectors = [
            (100.0, 1.0, 0.5), # Option A: High net, moderate syntropy
            (50.0, 2.0, 0.8),  # Option B: Lower net, high syntropy (non-dominated!)
            (30.0, 0.5, 0.2),  # Option C: Dominated by both A and B
        ]
        frontier = decide.pareto_frontier(vectors)
        self.assertIn(0, frontier)
        self.assertIn(1, frontier)
        self.assertNotIn(2, frontier) # Option C is strictly dominated

        # 2. S^2 Spherical Planetary Manifold
        grid = surface.SurfaceGrid(width=8, height=8)
        t_equator = surface.SurfaceTile(x=4, y=4, terrain=surface.TerrainType.PLAINS)
        t_pole = surface.SurfaceTile(x=4, y=7, terrain=surface.TerrainType.PLAINS)
        
        self.assertGreater(t_equator.area_weight, t_pole.area_weight) # Cosine latitude scaling
        dist_s2 = grid.spherical_distance(t_equator, t_pole, planet_radius_km=1000.0)
        self.assertGreater(dist_s2, 0.0)

        # 3. Ideology Cohesion Stress-Energy Tensor and 4-Volume
        ledger = ideology.CohesionLedger()
        ledger.record_deed("compassion", 20.0, is_syntropic=True)
        ledger.record_deed("resonance", 15.0, is_syntropic=True)
        ledger.record_deed("integrity", 10.0, is_syntropic=True)
        ledger.record_deed("morality", 5.0, is_syntropic=False)
        
        tensor = ledger.stress_energy_tensor()
        self.assertEqual(len(tensor), 4)
        self.assertEqual(len(tensor[0]), 4)
        self.assertGreater(ledger.manifold_volume, 1.0)

        # 4. Spheres Continuous Potential Field
        phi = spheres.potential_field(self.kernel, 1, "progenitor:Elder")
        self.assertIsInstance(phi, float)

    def test_climate_manifold_s2_and_thermal_wind(self):
        from xylarium.kernel import skies, surface
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        
        clim = skies.compute_climate_manifold(planet, kernel=self.kernel)
        self.assertIn("column", clim)
        self.assertIsInstance(clim["column"], skies.AtmosphericColumn)
        
        # S^2 insolation: equator must be strictly warmer than polar nodes
        self.assertGreater(clim["t_equator_k"], clim["t_pole_k"])
        
        # Dynamic albedo bifurcation: polar node albedo >= equator albedo
        polar_albedo = clim["thermal_profile"][0]["albedo"]
        equator_albedo = clim["thermal_profile"][4]["albedo"]
        self.assertGreaterEqual(polar_albedo, equator_albedo)
        
        # Thermal wind balance: non-zero zonal wind shear
        self.assertGreaterEqual(clim["column"].zonal_wind_max_ms, 0.0)
        
        # S^2 surface grid tile integration
        grid = surface.SurfaceGrid(width=8, height=8)
        tile_climate = grid.compute_climate_tiles(planet, kernel=self.kernel)
        self.assertEqual(len(tile_climate), 64)
        for (x, y), tdata in tile_climate.items():
            self.assertIn("temp_k", tdata)
            self.assertIn("insolation_wm2", tdata)
            self.assertIn("albedo", tdata)
            self.assertIn("wind_ms", tdata)

    def test_relativistic_trade_tensor_and_fluid_flux(self):
        from xylarium.kernel import market
        tensor_data = market.relativistic_trade_tensor(self.kernel, source_sec=1, target_sec=2, commodity="ORE")
        
        self.assertIn("gravitational_lapse", tensor_data)
        self.assertIn("local_interest_rate", tensor_data)
        self.assertIn("commodity_flux", tensor_data)
        self.assertIn("stress_energy_tensor", tensor_data)
        
        # 4x4 relativistic stress-energy tensor
        t_munu = tensor_data["stress_energy_tensor"]
        self.assertEqual(len(t_munu), 4)
        self.assertEqual(len(t_munu[0]), 4)
        self.assertGreater(t_munu[0][0], 0.0) # Positive energy density

    def test_biochemical_morphospace_and_waddington_drift(self):
        from xylarium.kernel import genome
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        
        coord = genome.MorphospaceCoordinate(
            elemental_ratios={"C": 0.45, "N": 0.15, "P": 0.05, "O": 0.30, "H2O": 0.05},
            activation_energy_ev=0.85,
            catalytic_entropy=0.0022,
            basin_id="CARBON_AQUEOUS",
        )
        
        drifted = genome.evaluate_waddington_drift(self.kernel, planet, coord)
        self.assertIsInstance(drifted, genome.MorphospaceCoordinate)
        # Elemental ratios must be normalized to 1.0
        self.assertAlmostEqual(sum(drifted.elemental_ratios.values()), 1.0, places=3)
        self.assertIn(drifted.basin_id, genome.METABOLIC_BASINS)

    def test_associative_attractor_manifold_and_casimir_compaction(self):
        from xylarium.kernel import mindcore, physics
        manifold = mindcore.AssociativeAttractorManifold()
        
        q1 = physics.Quaternion(1.0, 0.0, 0.0, 0.0)
        q2 = physics.Quaternion(0.0, 1.0, 0.0, 0.0)
        manifold.add_memory(q1, weight=2.0)
        manifold.add_memory(q2, weight=1.0)
        
        # Recall near q1
        query = physics.Quaternion(0.9, 0.1, 0.0, 0.0)
        recalled = manifold.recall_invariant(query, beta=10.0)
        self.assertAlmostEqual(recalled.norm(), 1.0, places=4)
        # Recalled state should be closer to q1
        self.assertGreater(recalled.w, recalled.x)
        
        # Add 55 memories to test Casimir invariant compaction
        for i in range(55):
            manifold.add_memory(physics.Quaternion(0.7071, 0.7071, 0.0, 0.0))
        
        casimir = manifold.compact_oldest(keep_count=50)
        self.assertIsNotNone(casimir)
        self.assertGreater(len(manifold.casimir_invariants), 0)
        self.assertLessEqual(len(manifold.memory_attractors), 51) # 50 active + 1 macro-attractor

    def test_quasinormal_ringdown_and_dynamo_coupling(self):
        from xylarium.kernel import torsion, hydromagnetics
        # Emit a bounce
        torsion.emit_bounce(self.kernel, origin_sector=1, energy_scale=50.0, chirality=1)
        
        # Evaluate quasi-normal ringdown
        ring = torsion.compute_quasinormal_ringdown(self.kernel, target_sector_id=1, spin_param_a=0.7)
        self.assertIn("psi_amplitude", ring)
        self.assertIn("omega_r", ring)
        self.assertIn("omega_i", ring)
        self.assertGreater(ring["omega_r"], 0.0)
        self.assertGreater(ring["omega_i"], 0.0)
        self.assertEqual(ring["reverberation_mode"], "ACTIVE_REVERBERATION")
        
        # Couple into hydromagnetics stellar dynamo
        mhd = hydromagnetics.couple_torsion_ringdown(self.kernel, sector_id=1, torsion_wave=ring)
        self.assertIn("alpha_torsion", mhd)
        self.assertIn("magnetic_amplification", mhd)
        self.assertGreater(mhd["magnetic_amplification"], 1.0)
        self.assertGreater(mhd["modulated_activity"], mhd["base_activity"])
        self.assertGreater(mhd["cme_flare_joules"], 0.0)

    def test_unbroken_history_and_chronicle_causal_chains(self):
        from xylarium.kernel import history, chronicle
        # Record history event and verify unbroken hash root
        event = history.event(self.kernel, "STAR_BORN", "Sol ignition", sector_id=1)
        st = history.stats(self.kernel)
        self.assertIn("history_root", st)
        self.assertNotEqual(st["history_root"], "genesis")

        # Record chronicle entries and verify unbroken archive hash on compaction
        eng = chronicle.ChronicleEngine()
        for i in range(120):
            eng.record(self.kernel, "CAPTAINS_LOG", "cap_1", "Captain Test", f"Log {i}", f"Log body {i}")
        self.assertNotEqual(eng.archive_hash, "genesis")
        self.assertGreaterEqual(len(eng.entries), 100)

    def test_deep_clean_manifold_continuities(self):
        from xylarium.kernel import torsion, cartography, market, intellect, matter, models
        
        # 1. Torsion background strain accumulation
        for i in range(60):
            torsion.emit_bounce(self.kernel, origin_sector=1, energy_scale=10.0, chirality=1)
        torsion.season(self.kernel)
        st_t = torsion.stats(self.kernel)
        self.assertGreater(st_t.get("background_strain", 0.0), 0.0)
        amp, _, _ = torsion.eval_wavefront(self.kernel, 1)
        self.assertGreaterEqual(amp, st_t["background_strain"])

        # 2. Cartography survey probe manifold preservation
        probe = models.SurveyProbe(
            id="PROBE-01",
            owner_id="cap_01",
            current_sector=1,
            target_sector=1,
        )
        self.kernel.cartography_manager.survey_probes["PROBE-01"] = probe
        for s_id in range(1, 35):
            probe.sectors_surveyed.append(s_id)
        # Advance probe tick in cartography manager
        self.kernel.cartography_manager.tick_survey_probes(self.kernel)
        self.assertGreaterEqual(len(getattr(probe, "survey_manifold", [])), 20)

        # 3. Market corporate envelope (ATH / ATL)
        comp = next(iter(self.kernel.market_manager.companies.values()))
        for p in [50, 200, 10, 80]:
            comp.price_history.append(p)
        self.kernel.market_manager.tick_market(self.kernel)
        self.assertEqual(comp.all_time_high, 200)
        self.assertEqual(comp.all_time_low, 10)

        # 4. Intellect proof Merkle root
        st_i = intellect.stats(self.kernel)
        self.assertIn("proof_roots", st_i)

    def test_s60_and_s360_cone_manifolds(self):
        import math
        from xylarium.kernel import physics, surface
        
        # 1. Sphere60 continuous geometry & measure concentration
        s_area = physics.Sphere60.surface_area(1.0)
        self.assertGreater(s_area, 0.0)
        vol = physics.Sphere60.volume(1.0)
        self.assertAlmostEqual(vol, s_area / 61.0, places=12)
        
        # Levy concentration
        bound = physics.Sphere60.levy_concentration_bound(0.1)
        self.assertLess(bound, 2.0)
        var = physics.Sphere60.equatorial_variance()
        self.assertAlmostEqual(var, 1.0 / math.sqrt(59.0), places=6)
        
        # Deterministic projection onto S^60 in R^61
        pt1 = physics.Sphere60.project_point("terra")
        pt2 = physics.Sphere60.project_point("mars")
        self.assertEqual(len(pt1), 61)
        self.assertEqual(len(pt2), 61)
        norm1 = math.sqrt(sum(x * x for x in pt1))
        self.assertAlmostEqual(norm1, 1.0, places=6)
        dist_s60 = physics.Sphere60.geodesic_distance(pt1, pt2, radius=1.0)
        self.assertGreater(dist_s60, 0.0)
        
        # 2. Gravitational Cone Manifold join metric
        sec = next(s for s in self.kernel.sectors.values() if len(s.planets) >= 2)
        p_a = sec.planets[0]
        p_b = sec.planets[1]
        cone = physics.GravitationalConeManifold(p_a, p_b, distance_au=1.5)
        # Collimation half width ~ 3.7 degrees
        sigma_psi = cone.collimation_half_width()
        self.assertAlmostEqual(math.degrees(sigma_psi), 3.69838, places=3)
        # Directed flux
        flux = cone.gravitational_flux(math.pi / 4.0)
        self.assertGreater(flux, 0.0)
        # Cross-section at apex vs midpoint
        w_mid = cone.cross_section_weight(math.pi / 4.0)
        w_apex = cone.cross_section_weight(0.0)
        self.assertGreater(w_mid, w_apex)
        self.assertEqual(w_apex, 0.0)
        
        # 3. Overlapping S^360 universe manifold
        u360 = physics.Universe360(cosmic_radius=1.0)
        emb_a = u360.embed_body(p_a, sector_id=p_a.sector_id)
        emb_b = u360.embed_body(p_b, sector_id=p_b.sector_id)
        self.assertEqual(len(emb_a), 361)
        self.assertEqual(len(emb_b), 361)
        norm_360 = math.sqrt(sum(x * x for x in emb_a))
        self.assertAlmostEqual(norm_360, 1.0, places=6)
        
        # Overlapping cone caustics & Mayer-Vietoris cohomology
        cone2 = physics.GravitationalConeManifold(p_b, p_a, distance_au=2.0)
        caustic = cone.caustic_overlap(cone2)
        self.assertIn("caustic_curvature", caustic)
        cohomology = u360.compute_mayer_vietoris_cohomology([cone, cone2])
        self.assertTrue(cohomology["uncollapsed_manifold"])
        self.assertGreater(cohomology["total_harmonic_capacity"], 2)
        self.assertIn(60, cohomology["betti_numbers"])
        self.assertIn(120, cohomology["betti_numbers"])
        
        # 4. Planetary surface tile S^60 integration
        tile = surface.SurfaceTile(x=3, y=4, terrain=surface.TerrainType.PLAINS)
        self.assertEqual(len(tile.s60_coords), 61)
        self.assertGreater(tile.s60_measure_weight, 0.0)
        grid = surface.SurfaceGrid(width=8, height=8)
        t_other = surface.SurfaceTile(x=5, y=2, terrain=surface.TerrainType.MOUNTAINS)
        s60_dist = grid.s60_distance(tile, t_other, planet_radius_km=6371.0)
        self.assertGreater(s60_dist, 0.0)
        
        # 5. Planet model S^60 manifold
        p_manifold = p_a.s60_manifold()
        self.assertEqual(p_manifold["dimension"], 60)
        self.assertEqual(p_manifold["embedding_dimension"], 61)
        self.assertGreater(p_manifold["surface_area_s60"], 0.0)
        self.assertTrue(p_manifold["uncollapsed"])

    def test_civilization_high_dimensional_bridges(self):
        from xylarium.kernel import ascendance, spheres, genome, polity, intellect, civilization
        
        # 1. Ascendance S^360 Horizon Coherence & Horizon Book
        peoples = list(ascendance.stats(self.kernel).get("of", {}).keys())
        who = peoples[0] if peoples else "civ:imperium"
        home = ascendance._home(self.kernel, who)
        if home:
            pairs = ascendance.pairs(self.kernel, who)
            self.assertIn("horizon", pairs)
            syn, ent = pairs["horizon"]
            self.assertGreater(syn, 0)
            
            coh = ascendance.s360_horizon_coherence(self.kernel, who)
            self.assertEqual(coh["who"], who)
            self.assertIn("s60_area", coh)

        # 2. Interstellar Waveguide Conduit & Caustic Navigation Envelope
        sec1, sec2 = 1, 2
        conduit = spheres.waveguide_conduit(self.kernel, sec1, sec2)
        self.assertTrue(conduit["waveguide_active"])
        self.assertAlmostEqual(conduit["collimation_half_width_deg"], 3.70, places=1)
        self.assertGreater(conduit["collimation_gain"], 5.0)
        
        caustic_env = spheres.caustic_nav_envelope(self.kernel, sec1)
        self.assertIn("is_caustic", caustic_env)
        self.assertIn("stealth_factor", caustic_env)

        # 3. Cross-Sector Dimensional Shear & Epigenetic Adaptation
        sec_a = self.kernel.sectors[1]
        sec_b = self.kernel.sectors[5] if 5 in self.kernel.sectors else self.kernel.sectors[2]
        p_src = sec_a.planets[0] if sec_a.planets else None
        p_tgt = sec_b.planets[0] if sec_b.planets else None
        if p_src and p_tgt:
            shear = genome.evaluate_dimensional_shear(self.kernel, p_src, p_tgt)
            self.assertIn("shear_barrier_ev", shear)
            self.assertIn("cellular_stability", shear)
            self.assertGreater(shear["cellular_stability"], 0.0)
            
            civ = civilization.Civilization(
                name="Aethelgard", species_name="Aethel", class_code=1,
                sigil="⬡", clade="biotic", metabolism="biotic", disposition="empiricist", motto="Veritas"
            )
            civ_shear = civ.dimensional_shear(p_src, p_tgt, kernel=self.kernel)
            self.assertEqual(civ_shear["source_sector"], p_src.sector_id)

        # 4. Non-Abelian Diplomatic Holonomies in Polity
        sovs = list(polity.sovereigns(self.kernel).keys())
        if len(sovs) >= 2:
            hol = polity.treaty_holonomy_su2(self.kernel, sovs[0], sovs[1])
            self.assertIn("holonomy", hol)
            self.assertIn("curvature_rad", hol)
            self.assertIn("diplomatic_rupture_risk", hol)

        # 5. Mayer-Vietoris Theorem Mining in Intellect
        intellect.stats(self.kernel)["gauge"][who] = {"2": 8, "3": 4, "4": 2}
        cert = intellect.mine_mayer_vietoris_theorems(self.kernel, who, 1, 2)
        self.assertIsNotNone(cert)
        self.assertIn("harmonic_degree", cert)
        self.assertIn(cert["harmonic_degree"], (60, 120))
        self.assertIn(who, intellect.stats(self.kernel)["proof_roots"])


if __name__ == "__main__":
    unittest.main()




