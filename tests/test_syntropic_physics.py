"""
The syntropic half of the board's physics: flows that build order against dispersal.

Hydromagnetics - a convecting core holds a field, the field holds off its star's wind and turns away the galaxy's
cosmic rays. Concentration - a world's flows (melting, hot water, rivers, life) gather what its formation scattered
into deposits, and rebuild them at the flows' pace. Rarity comes out in the right order, and it is a place's: where
the flows have stopped, a world holds only what it was born with.
"""

import random
import unittest

from xylarium.kernel import concentration as K
from xylarium.kernel import hydromagnetics as H


class TestHydromagnetics(unittest.TestCase):
    def test_the_unit_world_is_its_own_ruler(self):
        u = H._unit()
        self.assertAlmostEqual(H.moment(u), 1.0)
        self.assertAlmostEqual(H.standoff(u), H.EARTH_STANDOFF_R)
        self.assertAlmostEqual(H.dose(dict(u, p_bar=1.0, g=1.0)), 1.0)    # under one bar of its own air

    def test_without_a_field_the_wind_reaches_the_whole_sky(self):
        bare = dict(H._unit(), q_cmb=0.0)
        self.assertEqual(H.moment(bare), 0.0)
        self.assertEqual(H.exposure(bare), 1.0)
        self.assertGreater(H.dose(bare), H.dose(H._unit()))             # and more reaches the ground

    def test_a_harder_wind_presses_the_field_in(self):
        u = H._unit()
        self.assertLess(H.standoff(u, 64.0), H.standoff(u, 1.0))
        self.assertAlmostEqual(H.standoff(u, 64.0), H.standoff(u) / 2.0)   # (1/64)^(1/6) = 1/2

    def test_the_core_of_the_galaxy_rains_harder_and_air_shields(self):
        u = H._unit()
        self.assertGreater(H.dose(u, galactic=5.0), H.dose(u))
        thin = dict(u, p_bar=0.0)
        thick = dict(u, p_bar=10.0)
        self.assertGreater(H.dose(thin), H.dose(thick))

    def test_the_living_take_the_dose_where_they_live(self):
        from unittest import mock
        from xylarium.kernel import biosphere, relations, sustenance, worlds
        from xylarium.kernel.engine import GameKernel
        random.seed(4)
        k = GameKernel(seed=42)
        k.activate()
        home = max((p for s in k.sectors.values() for p in s.planets if p.population > 0),
                   key=lambda p: p.population)
        colony = next(p for s in k.sectors.values() for p in s.planets if p is not home and p.population > 0)
        people = sustenance.people_of(home)
        doses = {home.id: 1.0, colony.id: 300.0}

        def of(kk, w):
            return {"dose": doses[w.id]}

        def check(where):
            for w in (home, colony):
                w.society.pop("_rad", None)
            medium = None if where is None else {"where": where, "solvent": "H2O"}
            with mock.patch.object(H, "of_planet", side_effect=of), \
                    mock.patch.object(sustenance, "people_of", return_value=people), \
                    mock.patch.object(relations, "_peoples", return_value={people: [home, colony]}), \
                    mock.patch.object(worlds, "best", return_value=medium), \
                    mock.patch.object(biosphere, "open_share", return_value=1.0):
                return H.health(k, colony)
        self.assertLess(check("surface"), 0.1)                            # three hundred home doses, open sky
        self.assertEqual(check("under_ice"), 1.0)                         # the ice above shields its sea
        self.assertEqual(check(None), 1.0)                                # no medium under this sky: it lives enclosed


class TestConcentration(unittest.TestCase):
    def setUp(self):
        self.alive = K.channels(H._unit(), [{"solvent": "H2O", "where": "surface"}], True)
        self.dead = K.channels({"q": 0.0, "processed": 0.0}, [], False)

    def test_each_element_is_gathered_by_the_flows_its_bonds_answer_to(self):
        self.assertEqual(K.affinity("Ti"), "lithophile")                  # its oxide holds harder than iron's
        self.assertEqual(K.affinity("Cu"), "chalcophile")                 # it takes sulphur
        self.assertEqual(K.affinity("Pt"), "siderophile")
        self.assertEqual(K.affinity("C"), "atmophile")                    # its oxides are gases
        self.assertEqual(K.affinity("Xe"), "atmophile")
        self.assertEqual(K.affinity("chitinium"), "biogenic")

    def test_a_world_without_flows_holds_only_what_it_was_born_with(self):
        for sym in ("Fe", "Cu", "Pt", "U"):
            x = K.dispersed(sym)
            self.assertAlmostEqual(K.grade(x, K.strength(sym, self.dead)), x)
            self.assertGreater(K.grade(x, K.strength(sym, self.alive)), x)

    def test_rarity_runs_the_right_way(self):
        g = {s: K.grade(K.dispersed(s), K.strength(s, self.alive)) for s in ("Fe", "Ni", "Cu", "Pt", "U", "AdL")}
        self.assertGreater(g["Fe"], g["Ni"])
        self.assertGreater(g["Ni"], g["Cu"])
        self.assertGreater(g["Cu"], g["Pt"])
        self.assertGreater(g["Pt"], g["U"])
        self.assertGreater(g["U"], g["AdL"])
        # and flows lift the rare the most: concentration closes a share of the log-distance to purity
        lift = {s: g[s] / K.dispersed(s) for s in g}
        self.assertGreater(lift["Pt"], lift["Cu"])
        self.assertGreater(lift["Cu"], lift["Fe"])

    def test_melting_carries_what_does_not_fit_up_into_a_crust(self):
        u = H._unit()
        melted = dict(self.alive)
        unmelted = dict(self.alive, magmatic=0.0)
        self.assertGreater(K.crustal("U", u, melted), 10 * K.dispersed("U"))      # tens of times (D ~ 0.001)
        self.assertAlmostEqual(K.crustal("U", u, unmelted), K.dispersed("U"))
        self.assertLess(K.crustal("Si", u, melted) / K.dispersed("Si"), 1.2)     # a major element barely moves

    def test_the_air_and_the_ice_are_not_gathered_by_rock(self):
        x = K.dispersed("Xe")
        self.assertAlmostEqual(K.grade(x, K.strength("Xe", self.alive)), x)

    def test_a_taken_deposit_comes_back_only_where_the_flows_run(self):
        from xylarium.kernel import geology
        from xylarium.kernel.engine import GameKernel
        random.seed(3)
        k = GameKernel(seed=42)
        k.activate()
        w = next(p for s in k.sectors.values() for p in s.planets
                 if p.population > 0 and (p.society.get("standing") or {}).get("Fe"))
        cap = w.society["standing"]["Fe"]
        w.element_deposits["Fe"] = 0
        for _ in range(400):
            geology._rebuild(k, w, 1.0)
        regrown = w.element_deposits["Fe"]
        self.assertGreater(regrown, 0)
        self.assertLessEqual(regrown, cap)
        flows = K.of_planet(k, w)
        for c in flows:
            flows[c] = 0.0
        from unittest import mock
        w.element_deposits["Fe"] = 0
        with mock.patch.object(K, "of_planet", return_value=flows):
            for _ in range(400):
                geology._rebuild(k, w, 1.0)
        self.assertEqual(w.element_deposits["Fe"], 0)                     # a dead world gives nothing back


if __name__ == "__main__":
    unittest.main()
