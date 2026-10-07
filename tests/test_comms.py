"""Word never outruns what carries it: ships trade what they have heard at the ports they reach; relay posts carry it
a hop a cycle, cost goods and upkeep, go dark unpaid, and join other lines only where one protocol is spoken."""

import random
import unittest
from unittest import mock

from xylarium.kernel import comms, endowments, ledger, matter
from xylarium.kernel.engine import GameKernel


def fresh():
    random.seed(5)
    k = GameKernel(seed=42)
    k.activate()
    return k


def _ports(k):
    return [sid for sid, s in sorted(k.sectors.items()) if s.port is not None]


class TestCarriers(unittest.TestCase):
    def test_a_ship_trades_what_it_has_heard_and_newest_word_wins(self):
        k = fresh()
        a, b = _ports(k)[:2]
        comms.arrive(k, "captain:x", a)                         # it docks at a: it now carries a's prices
        carried = comms.stats(k)["carried"]["captain:x"]
        self.assertTrue(any(key.startswith(f"{a}|") for key in carried))
        self.assertFalse(any(key.startswith(f"{a}|") for key in comms.stats(k)["views"].get(str(b), {})))
        comms.arrive(k, "captain:x", b)                         # and lands it at b
        self.assertTrue(any(key.startswith(f"{a}|") for key in comms.stats(k)["views"][str(b)]))

    def test_merge_keeps_the_newer_word(self):
        dst = {"1|ORE": [10, 5]}
        comms.merge(dst, {"1|ORE": [12, 3]})
        self.assertEqual(dst["1|ORE"], [10, 5])
        comms.merge(dst, {"1|ORE": [14, 9]})
        self.assertEqual(dst["1|ORE"], [14, 9])


class TestRelays(unittest.TestCase):
    def setUp(self):
        self.k = fresh()
        self.a, self.b = _ports(self.k)[:2]
        comms.stats(self.k)["posts"][comms._lane(self.a, self.b)] = {"keeper": "civ:Keepers", "built": 0,
                                                                     "goods": {"EQUIPMENT": comms.POST_HOLDS},
                                                                     "upkeep": "10", "dark": False}

    def test_a_live_post_carries_word_across_its_lane(self):
        with mock.patch.object(comms, "_keeper_of", return_value=None):
            comms.relay(self.k)
            comms.relay(self.k)
        self.assertTrue(any(key.startswith(f"{self.a}|") for key in comms.stats(self.k)["views"][str(self.b)]))

    def test_a_dark_post_carries_nothing(self):
        comms.stats(self.k)["posts"][comms._lane(self.a, self.b)]["dark"] = True
        comms.relay(self.k)
        self.assertFalse(any(key.startswith(f"{self.a}|")
                             for key in comms.stats(self.k)["views"].get(str(self.b), {})))

    def test_a_seam_between_protocols_is_not_crossed_by_the_post(self):
        with mock.patch.object(comms, "_keeper_of", return_value="civ:Others"), \
                mock.patch.object(comms, "_protocol", side_effect=lambda k, h: "p-" + str(h)):
            comms.relay(self.k)
            comms.relay(self.k)
        self.assertFalse(any(key.startswith(f"{self.a}|")
                             for key in comms.stats(self.k)["views"].get(str(self.b), {})))

    def test_upkeep_is_burned_and_an_unpaid_post_goes_dark(self):
        endowments.stats(self.k)["funds"]["civ:Keepers"] = {"sol": 15.0, "in": 15.0}
        before = ledger.money_supply(self.k).get("SOL", {}).get("total", 0)
        comms.upkeep(self.k)
        post = comms.stats(self.k)["posts"][comms._lane(self.a, self.b)]
        self.assertFalse(post["dark"])
        self.assertEqual(before - ledger.money_supply(self.k).get("SOL", {}).get("total", 0), 10)   # burned
        comms.upkeep(self.k)                                    # 5 left: it cannot pay
        self.assertTrue(post["dark"])

    def test_a_posts_goods_are_counted(self):
        self.assertEqual(comms.posts_goods(self.k).get("EQUIPMENT"), comms.POST_HOLDS)
        self.assertEqual(matter.census(self.k)["EQUIPMENT"].get("relay_posts"), comms.POST_HOLDS)


if __name__ == "__main__":
    unittest.main()
