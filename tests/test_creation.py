"""
Creation is fixed at the Big Bang: every cell is a pure function of the seed and its coordinates; systems are born
on their own dates; minds arise on worlds that exist, by the needs of their own biology; the map is charted only
where peoples that reach the stars go; and the expansion is one law, fixed in time.
"""

import math
import unittest

from xylarium.kernel import cosmos, creation, history, matter
from xylarium.kernel.engine import GameKernel


def _contents(k, cell):
    out = []
    for slot in range(creation.SLOTS):
        sec = k.sectors[cosmos.sector_of_slot(k, cell, slot)]
        out.append((sec.kind, sec.star_type, [(p.planet_type, sorted(p.element_deposits.items())) for p in sec.planets]))
    return out


class TestFixedAtTheBigBang(unittest.TestCase):
    def test_a_cell_is_the_same_whoever_charts_it_in_whatever_order(self):
        a, b = (14, 20), (15, 22)
        k1 = GameKernel(seed=7, genesis="cosmic")
        k1.activate()
        cosmos.materialise(k1, a, "first")
        cosmos.materialise(k1, b, "second")
        k2 = GameKernel(seed=7, genesis="cosmic")
        k2.activate()
        cosmos.materialise(k2, b, "first")
        cosmos.materialise(k2, a, "second")
        self.assertNotEqual(cosmos.region_of_cell(k1, a), cosmos.region_of_cell(k2, a))   # labels differ
        self.assertEqual(_contents(k1, a), _contents(k2, a))                              # the cell does not
        self.assertEqual(_contents(k1, b), _contents(k2, b))

    def test_the_rim_is_still_making_stars_and_the_core_is_not(self):
        early = sum(1 for j in range(10) for s in creation.cell(7, 2, j) if "born" in s and s["born"] > 13.8)
        late = sum(1 for j in range(10) for s in creation.cell(7, 26, j) if "born" in s and s["born"] > 13.8)
        self.assertEqual(early, 0)
        self.assertGreater(late, 0)
        core = [s for s in creation.cell(7, 1, 2) if "star" in s]
        rim = [s for s in creation.cell(7, 26, 40) if "star" in s]
        self.assertGreater(len(core), len(rim))                                           # the disc is denser inward

    def test_a_star_is_born_on_its_date_and_its_worlds_with_it(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        rim = next((26, j) for j in range(cosmos.slots(26))
                   if any(s.get("born", 0) > cosmos.deep_gyr(k) + 0.01 for s in creation.cell(7, 26, j)))
        cosmos.materialise(k, rim, "a test")
        st = cosmos.stats(k)
        sid, born = min(((int(s), b) for s, b in st["unborn"].items()), key=lambda x: x[1])
        self.assertEqual(k.sectors[sid].planets, [])                                      # gas, for now
        k.cycle_count = int((born - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100) + 1
        before = matter.ACTIVE.net() if matter.ACTIVE else None
        logs = cosmos._ignite(k)
        self.assertTrue(any("A star is born" in l for l in logs))
        self.assertEqual(k.sectors[sid].kind, "SYSTEM")
        slot = creation.cell(7, *st["place"][str(sid)]["cell"])[st["place"][str(sid)]["k"]]
        self.assertEqual(len(k.sectors[sid].planets), len(slot["worlds"]))
        self.assertNotIn(str(sid), st["unborn"])
        if before is not None and k.sectors[sid].planets:
            self.assertNotEqual(before, matter.ACTIVE.net())                              # declared: star formation

    def test_metals_rise_with_the_stars_already_made(self):
        self.assertLess(creation.metals_at(7, 8.0, 2.0), creation.metals_at(7, 8.0, 10.0))
        self.assertEqual(creation.metals_at(7, 8.0, 0.1), 0.0)                           # before the first stars


class TestBigBang(unittest.TestCase):
    def test_each_universe_draws_its_own_and_lumpier_ones_form_sooner(self):
        bbs = [creation.big_bang(s) for s in range(1, 30)]
        self.assertGreater(len({b["sigma8"] for b in bbs}), 20)
        for b in bbs:
            self.assertGreater(b["omega_minus_1"], 0)                                    # closed: a 3-sphere
            self.assertAlmostEqual(b["assembly"], (creation.SIGMA8 / b["sigma8"]) ** 1.5, places=3)
        lumpy = max(range(1, 30), key=lambda s: creation.big_bang(s)["sigma8"])
        smooth = min(range(1, 30), key=lambda s: creation.big_bang(s)["sigma8"])
        self.assertLess(creation.first_stars(lumpy), creation.first_stars(smooth))

    def test_the_expansion_is_one_law_fixed_in_time(self):
        self.assertAlmostEqual(creation.scale_factor(13.8), 1.0, delta=0.01)
        self.assertAlmostEqual(creation.hubble(13.8), creation.H0_KMS_MPC, delta=0.5)
        self.assertLess(creation.scale_factor(5.0), creation.scale_factor(10.0))
        self.assertGreater(creation.hubble(5.0), creation.hubble(13.8))                  # it was faster then
        d = creation.comoving_light_mpc(1.0, 13.8)
        self.assertTrue(8000 < d < 13000)                                                 # light since a = 0.18


class TestEachBiologyItsOwnNeeds(unittest.TestCase):
    def test_plasmic_minds_need_no_metals_and_shrug_off_supernovae(self):
        slot = {"z": 0.0, "born": 1.0, "mass": 0.8, "r": 1.0}
        bios = {m: (mean, live) for m, mean, live, _ in creation.needs(7, slot, {"type": "GAS_GIANT"})}
        self.assertIn("plasmic", bios)
        self.assertEqual(bios["plasmic"][1], 1.0)
        rocky = {m for m, *_ in creation.needs(7, slot, {"type": "TERRESTRIAL"})}
        self.assertNotIn("biotic", rocky)                                                 # no metals, no carbon life
        slot["z"] = 1.0
        bios = {m: live for m, _, live, _ in creation.needs(7, slot, {"type": "TERRESTRIAL"})}
        self.assertLess(bios["biotic"], bios["mineral"])                                  # molecules break first

    def test_every_mind_arises_on_a_world_the_cells_hold_in_a_biology_that_fits_it(self):
        from xylarium.config import HABITABILITY
        for m in creation.schedule(7)["minds"][:40]:
            slot = creation.cell(7, *m["cell"])[m["k"]]
            world = slot["worlds"][m["w"]]
            self.assertGreater(HABITABILITY[m["metab"]].get(world["type"], 0), 0)
            self.assertLessEqual(slot["born"] + creation.CRUST_GYR, m["epoch"])
            if world["type"] != "ROGUE":
                self.assertLessEqual(m["epoch"], slot["born"] + creation.SUN_MS_GYR * slot["mass"] ** -2.5)


    def test_minds_arise_only_where_a_viable_people_can_be_fed(self):
        from xylarium.kernel import biosphere
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        st = cosmos.stats(k)
        for m in creation.schedule(7)["minds"][:15]:
            k.cycle_count = int((m["epoch"] - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100) + 1
            cosmos._due(k)
        peoples = [p for s in k.sectors.values() for p in s.planets if p.civilization]
        self.assertEqual(len(peoples), 15)
        for p in peoples:
            self.assertGreaterEqual(biosphere.carrying_capacity(k, p), creation.VIABLE)  # Franklin's 500


class TestEveryStarItsOwn(unittest.TestCase):
    def test_stars_have_their_own_mass_and_light_and_minds_think_at_their_homeworlds_warmth(self):
        from fractions import Fraction
        from xylarium.kernel import laws
        stars = [s for j in range(20) for s in creation.cell(7, 16, j) if "spec" in s]
        self.assertGreater(len({s["spec"]["mass"] for s in stars}), len(stars) // 3)     # a continuum, not classes
        for s in stars:
            if s["star"] != "Binary pair":
                m = Fraction(s["spec"]["m"])
                self.assertEqual(Fraction(s["spec"]["luminosity"]), (m ** 7).limit_denominator(10 ** 6))
        warm = laws.cognition("biotic", home_flux=4.0)
        cold = laws.cognition("biotic", home_flux=0.25)
        self.assertGreater(warm["temperature"], cold["temperature"])
        self.assertGreater(warm["speed"], cold["speed"])                                  # hot minds quick
        self.assertGreater(cold["depth"], warm["depth"])                                  # cold minds deep


class TestChartedWhereTheyGo(unittest.TestCase):
    def test_a_mind_is_given_its_own_system_and_a_people_with_yards_charts_its_sky(self):
        from xylarium.kernel import sustenance
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        self.assertEqual(list(k.sectors), [1])
        p = next(p for p in k.sectors[1].planets if p.population > 0)
        p.citadel_level = sustenance.DAUGHTER_CITADEL_TIER
        cosmos._reach(k)
        self.assertTrue(cosmos.materialised(k, cosmos.cell_of_sector(k, 1)))
        self.assertGreater(len(k.sectors), creation.SLOTS)
        self.assertIn(p, k.sectors[1].planets)                                            # its own world untouched

    def test_lanes_where_no_one_linked_lives_are_not_told(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        before = history.stats(k)["counts"].get("LANE_OPEN", 0)
        cosmos.entered(k, 1)
        self.assertTrue(cosmos.stats(k)["cross"])                                         # lanes opened
        self.assertEqual(history.stats(k)["counts"].get("LANE_OPEN", 0), before)          # but nobody to tell


if __name__ == "__main__":
    unittest.main()
