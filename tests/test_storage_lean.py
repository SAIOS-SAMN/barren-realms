"""
Stored state is what can still act (Concordance 1.13): what no law reads again is not kept - an ended line's
dealings - and what any law can recompute is not stored at all.
"""

import unittest

from xylarium.kernel import polity
from xylarium.kernel.engine import GameKernel


class TestEndedLinesForgotten(unittest.TestCase):
    def test_an_ended_sovereigns_books_go_and_the_living_keep_theirs(self):
        k = GameKernel(seed=42)
        st = polity.stats(k)
        from xylarium.kernel import mindcore as mc
        books = lambda *others: {o: {a: ["1", "0"] for a in mc.CONDUCT_AXES} for o in others}
        st["sovereigns"] = {
            "S-1": {"id": "S-1", "books": books("S-2", "S-3"), "heard": {"S-2": 1.0, "S-3": 0.5}, "mind": {"c": 1}},
            "S-2": {"id": "S-2", "books": books("S-1", "S-3"), "heard": {"S-1": 1.0, "S-3": 0.5}},
            "S-3": {"id": "S-3", "books": books("S-1", "S-2"), "heard": {"S-1": 0.5}, "ended": 7, "mind": {"c": 2}}}
        polity._forget_the_ended(k)
        sv = st["sovereigns"]
        self.assertEqual((sv["S-3"]["books"], sv["S-3"]["heard"], sv["S-3"]["mind"]), ({}, {}, {"c": 2}))
        self.assertEqual(set(sv["S-1"]["books"]), {"S-2"})
        self.assertEqual(set(sv["S-2"]["heard"]), {"S-1"})
        self.assertTrue(polity.trusts(sv["S-1"], sv["S-2"]))                 # what the living read, unchanged


class TestDerivedNotStored(unittest.TestCase):
    def test_a_surface_is_stored_as_what_was_built_and_drawn_again_from_its_world(self):
        from xylarium.kernel.surface import DistrictType, SurfaceManager
        k = GameKernel(seed=42)
        p = next(p for s in k.sectors.values() for p in s.planets)
        grid = SurfaceManager.ensure_surface_grid(p)
        grid.tiles[5].district = DistrictType.RESORT_DOME
        p.surface_grid = grid.to_dict()
        stored = p.to_dict()["surface_grid"]
        self.assertEqual(set(stored["built"]), {"5"})                       # one tile built: one thing stored
        self.assertEqual(type(p).from_dict(p.to_dict()).surface_grid, p.surface_grid)

    def test_a_worlds_keyed_caches_are_not_stored(self):
        from xylarium.kernel.models import DERIVED_SOCIETY
        k = GameKernel(seed=42)
        p = next(p for s in k.sectors.values() for p in s.planets)
        p.society.update({key: {"key": [1]} for key in DERIVED_SOCIETY}, kept=1)
        self.assertEqual(set(p.to_dict()["society"]) & set(DERIVED_SOCIETY), set())
        self.assertEqual(p.to_dict()["society"]["kept"], 1)


if __name__ == "__main__":
    unittest.main()
