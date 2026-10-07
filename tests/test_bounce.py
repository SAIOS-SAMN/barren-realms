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
        self.assertEqual(ch["elements"], {"Fe": 100, "Si": 50})                 # a tenth crosses
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


if __name__ == "__main__":
    unittest.main()
