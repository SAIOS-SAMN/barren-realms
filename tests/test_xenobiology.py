"""
Unit and integration test suite for Xylarium Xenobiology & Alien Trophic Ecosystems:
- Polymer Backbone Classifications (Phospho-Ribose, Siloxane-Peptide, Boron, Plasma)
- Lindeman Trophic Levels (Producer, Grazer, Predator, Decomposer) & Shannon Entropy
- Bioprospecting Specimen Extraction and Cargo Hold Integration
- Bioreactor Culturing and Value-Added Bio-Synthesis
- Transgenic Gene Grafting & Planetary Biosphere Yield Enhancements
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.xenobiology import (
    PolymerBackbone,
    TrophicLevel,
    generate_xeno_ecosystem,
    XENO_CULTURE_RECIPES,
)


class TestXenobiology(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player_id = "captain_darwin"
        self.player = self.kernel.register_player(self.player_id, "Captain Darwin")
        self.player.sector_id = 1
        self.player.credits = 50000

        # Ensure planet in current sector
        self.sector = self.kernel.sectors[1]
        if not self.sector.planets:
            self.sector.planets.append(
                Planet(
                    id="P-TEST-01",
                    sector_id=1,
                    name="Avalon Prime",
                    planet_type="TERRESTRIAL",
                    owner_id=self.player_id,
                )
            )
        self.planet = self.sector.planets[0]

    def test_ecosystem_generation_and_diversity(self):
        """Test deterministic generation of alien trophic webs across diverse planetary environments."""
        # 1. Terrestrial World: Phospho-Ribose backbone
        eco_terr = generate_xeno_ecosystem(self.planet, self.kernel)
        self.assertEqual(eco_terr.backbone, PolymerBackbone.PHOSPHO_RIBOSE)
        self.assertGreater(eco_terr.shannon_entropy, 0.5)
        self.assertEqual(len(eco_terr.taxa), 4)

        trophic_types = {t.trophic_level for t in eco_terr.taxa}
        self.assertIn(TrophicLevel.PRODUCER, trophic_types)
        self.assertIn(TrophicLevel.GRAZER, trophic_types)
        self.assertIn(TrophicLevel.PREDATOR, trophic_types)
        self.assertIn(TrophicLevel.DECOMPOSER, trophic_types)

        # 2. Gas Giant: Magneto-Ionic Plasma backbone
        giant = Planet(id="P-GIANT", sector_id=1, name="Jovian Eye", planet_type="GAS_GIANT")
        eco_giant = generate_xeno_ecosystem(giant, self.kernel)
        self.assertEqual(eco_giant.backbone, PolymerBackbone.MAGNETO_IONIC_PLASMA)

        # 3. Barren / Cryogenic: Siloxane-Peptide backbone
        cryo_w = Planet(id="P-CRYO", sector_id=1, name="Boreas", planet_type="BARREN", society={"surface_t": 110.0})
        eco_cryo = generate_xeno_ecosystem(cryo_w, self.kernel)
        self.assertEqual(eco_cryo.backbone, PolymerBackbone.SILOXANE_PEPTIDE)

    def test_xenobiology_survey_action(self):
        """Test XENOBIOLOGY_SURVEY action dispatch and telemetry generation."""
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_SURVEY,
            planet_id=self.planet.id,
        )
        self.assertTrue(res.success, res.message)
        self.assertIn("XENOBIOLOGY SURVEY COMPLETE", res.message)
        eco_data = res.data.get("ecosystem", {})
        self.assertTrue(eco_data.get("surveyed"))
        self.assertGreater(len(eco_data.get("taxa", [])), 0)

    def test_xenobiology_sample_and_hold_integration(self):
        """Test bioprospecting specimen sampling and cargo hold loading."""
        init_space = self.player.ship.cargo.available_space
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_SAMPLE,
            planet_id=self.planet.id,
        )
        self.assertTrue(res.success, res.message)
        metab = res.data.get("metabolite")
        units = res.data.get("units_yielded")
        self.assertGreater(units, 0)
        self.assertIn(metab, self.player.ship.cargo.elements)
        self.assertEqual(self.player.ship.cargo.elements[metab], units)
        self.assertEqual(self.player.ship.cargo.available_space, init_space - units)

    def test_biosphere_vessel_sampling_yield_multiplier(self):
        """Test that Biosphere Vessel hulls provide +50% extra bioprospecting yield."""
        self.player.ship.hull_class = "BIOSPHERE_VESSEL"
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_SAMPLE,
            planet_id=self.planet.id,
        )
        self.assertTrue(res.success, res.message)
        units = res.data.get("units_yielded")
        # Base yield 4 * 1.5 = 6
        self.assertGreaterEqual(units, 6)

    def test_xenobiology_bioreactor_culturing(self):
        """Test bioreactor culturing and synthesis recipes."""
        # Setup inputs for ADAPTIVE_BIOMASS (2 XENOPROTEIN + 2 ORGANICS -> 6 ORGANICS)
        self.player.ship.cargo.elements["XENOPROTEIN"] = 3
        self.player.ship.cargo.organics = 4

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_CULTURE,
            recipe_id="ADAPTIVE_BIOMASS",
        )
        self.assertTrue(res.success, res.message)
        self.assertEqual(self.player.ship.cargo.elements["XENOPROTEIN"], 1)
        # 4 - 2 + 6 = 8
        self.assertEqual(self.player.ship.cargo.organics, 8)

        # Test CRYO_STABILIZER (2 CRYOPROTECTANT + 1 cryogenite -> 2 M1_SUPERCONDUCTOR)
        self.player.ship.cargo.elements["CRYOPROTECTANT"] = 2
        self.player.ship.cargo.elements["cryogenite"] = 1
        res_cryo = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_CULTURE,
            recipe_id="CRYO_STABILIZER",
        )
        self.assertTrue(res_cryo.success, res_cryo.message)
        self.assertEqual(self.player.ship.cargo.elements.get("CRYOPROTECTANT", 0), 0)
        self.assertEqual(self.player.ship.cargo.elements.get("cryogenite", 0), 0)
        self.assertEqual(self.player.ship.cargo.elements.get("M1_SUPERCONDUCTOR", 0), 2)

    def test_transgenic_gene_grafting(self):
        """Test transgenic gene grafting of alien metabolites into planetary agriculture/society."""
        # 1. Graft CRYOPROTECTANT
        self.player.ship.cargo.elements["CRYOPROTECTANT"] = 5
        init_fert = float(self.planet.society.get("fertility", 1.0))
        res_graft = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_GRAFT,
            planet_id=self.planet.id,
            metabolite="CRYOPROTECTANT",
        )
        self.assertTrue(res_graft.success, res_graft.message)
        self.assertEqual(self.player.ship.cargo.elements["CRYOPROTECTANT"], 3)
        self.assertAlmostEqual(float(self.planet.society.get("fertility")), init_fert + 0.30)
        self.assertIn("CRYOPROTECTANT", res_graft.data.get("grafted_traits", []))

        # 2. Cannot graft same trait twice
        res_dup = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_GRAFT,
            planet_id=self.planet.id,
            metabolite="CRYOPROTECTANT",
        )
        self.assertFalse(res_dup.success)
        self.assertIn("already incorporated", res_dup.message)

        # 3. Graft RADIOTROPHIC_MELANIN (+0.20 habitability)
        self.player.ship.cargo.elements["RADIOTROPHIC_MELANIN"] = 2
        init_hab = self.planet.habitability
        res_rad = self.kernel.dispatch(
            self.player_id,
            ActionType.XENOBIOLOGY_GRAFT,
            planet_id=self.planet.id,
            metabolite="RADIOTROPHIC_MELANIN",
        )
        self.assertTrue(res_rad.success, res_rad.message)
        self.assertAlmostEqual(self.planet.habitability, init_hab + 0.20)


if __name__ == "__main__":
    unittest.main()
