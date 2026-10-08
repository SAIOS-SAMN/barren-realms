"""
Our physics: what crosses the centre's horizon bounces at the Cartan density into a child universe - its white
hole is that universe's Big Bang - carrying the records of what fell; the disc's outflow returns the rest as jets.
Our own universe began as such a white hole.
"""

import unittest

from xylarium.kernel import blackhole, history
from xylarium.kernel.engine import GameKernel


class TestBounce(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()

    def test_our_big_bang_is_a_white_hole(self):
        kinds = [e.get("kind") for e in history.stats(self.k).get("recent", [])]
        self.assertIn("BIG_BANG", kinds)

    def test_what_crosses_the_horizon_is_carried_whole_into_a_child_universe(self):
        blackhole.capture(self.k, {"Fe": 1000, "Si": 500}, "the worlds of a dying star", records=["civ:Fallen"])
        st = blackhole.stats(self.k)
        ch = blackhole.child(self.k)
        self.assertEqual(ch["reservoir"], {"Fe": 100, "Si": 50})                # a tenth crosses, into the far core
        self.assertEqual(st["reservoir"], {"Fe": 900, "Si": 450})              # only the rest feeds the jets: once
        self.assertEqual(st.get("inbound", 0), 0)                              # nothing is sent back unless sent
        self.assertIsNotNone(ch["born"])
        self.assertEqual(ch["records"][0]["peoples"], ["civ:Fallen"])         # no information is destroyed
        kinds = [e.get("kind") for e in history.stats(self.k).get("recent", [])]
        self.assertIn("CHILD_UNIVERSE", kinds)

    def test_a_paired_universe_sends_only_what_it_sends(self):
        got = blackhole.receive(self.k, {"Fe": 40}, "a paired sphere")
        st = blackhole.stats(self.k)
        self.assertEqual(got, 40)
        self.assertEqual(st["reservoir"].get("Fe"), 40)
        self.assertEqual(st["inbound"], 40)

    def test_the_throat_is_two_faced_and_conserves_what_falls(self):
        blackhole.capture(self.k, {"Fe": 1000, "Si": 500}, "a dying star's worlds")
        blackhole.receive(self.k, {"C": 30}, "a paired sphere")
        self.assertEqual(blackhole.ledger(self.k)["balance"], 0)
        thr = blackhole.throat(self.k)
        self.assertEqual((thr["near"], thr["far"]), ("centre", "child"))
        self.assertEqual(thr["reservoir_far"], 150)
        self.assertEqual(blackhole.throat(self.k, "parent")["witnessed"], False)   # our Big Bang's far face
        for _ in range(400):                                   # the far core's engine sends back on its own clock
            blackhole.quarter(self.k)
            self.assertEqual(blackhole.ledger(self.k)["balance"], 0)    # matter in exactly one place, every season
        self.assertGreater(blackhole.child(self.k)["returned"], 0)
        self.assertLess(blackhole.ledger(self.k)["far"], 150)

    def test_an_older_save_s_crossed_store_becomes_the_far_reservoir(self):
        blackhole.stats(self.k)["child"] = {"born": 1.0, "elements": {"Fe": 7}, "records": [], "seed": "x"}
        self.assertEqual(blackhole.child(self.k)["reservoir"], {"Fe": 7})

    def test_a_heavy_star_leaves_a_throat_with_a_far_core_of_its_own(self):
        from unittest import mock
        from xylarium.kernel import cosmos
        sid = next(s.id for s in self.k.sectors.values() if s.planets)
        with mock.patch("xylarium.kernel.physics.star", lambda sec: {"mass": 40.0, "luminosity": 1.0}), \
                mock.patch.object(cosmos, "death_kind", lambda kernel, s: "core_collapse"), \
                mock.patch("xylarium.kernel.history.event", lambda *a, **kw: {}):
            cosmos._death(self.k, sid, True)
        thr = blackhole.stats(self.k)["throats"][f"star:{sid}"]
        self.assertEqual((thr["near"], thr["kind"]), (sid, "stellar"))
        self.assertGreater(thr["mass"], 0)                              # half its star's mass (scaled by the laws)
        blackhole.capture_into(self.k, f"star:{sid}", {"Fe": 5000}, "what fell into it")
        for _ in range(200):
            blackhole.quarter(self.k)
            self.assertEqual(blackhole.throat_ledger(self.k, f"star:{sid}")["balance"], 0)
        self.assertGreater(thr["core"]["returned"], 0)                  # two-way: its far core sends back too


if __name__ == "__main__":
    unittest.main()
