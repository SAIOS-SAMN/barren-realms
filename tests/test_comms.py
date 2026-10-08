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


class TestChannelsAreData(unittest.TestCase):
    def test_a_new_kind_is_an_entry_and_its_latency_is_its_rule(self):
        k = fresh()
        a, b = _ports(k)[:2]
        with mock.patch.dict(comms.CHANNELS, {"slow": {"cap": "relays", "goods": {"EQUIPMENT": 1}, "joins": "lane",
                                                       "latency": "light"}}):
            comms.stats(k)["posts"][f"slow:{comms._lane(a, b)}"] = {"keeper": "civ:K", "channel": "slow",
                                                                    "goods": {"EQUIPMENT": 1}, "upkeep": "0",
                                                                    "dark": False}
            post = comms.stats(k)["posts"][f"slow:{comms._lane(a, b)}"]
            with mock.patch("xylarium.kernel.news.light_years", return_value=50.0):
                self.assertEqual(comms.latency_cycles(k, post, a, b), 5000)
                with mock.patch.object(comms, "_keeper_of", return_value=None):
                    comms.relay(k, tick=1)                     # its word has not crossed yet
                self.assertFalse(any(key.startswith(f"{a}|")
                                     for key in comms.stats(k)["views"].get(str(b), {})))
            self.assertGreater(comms.post_cost_sol(k, "slow"), 0)


class TestFeeds(unittest.TestCase):
    """Information is a market: a feed is paid as a transfer and delivers the network's word; a withheld feed may be
    tapped at the risk of the watch."""

    def setUp(self):
        from xylarium.kernel import commerce, spheres
        self.k = fresh()
        self.a, self.b = _ports(self.k)[:2]
        self.home = next(p for p in self.k.sectors[self.b].planets) if self.k.sectors[self.b].planets else None
        if self.home is None:
            self.skipTest("no world at the buyer's port")
        self.home.treasury = 10 ** 6
        comms.stats(self.k)["posts"][f"relays:{comms._lane(self.a, self.b)}"] = {
            "keeper": "civ:Line", "channel": "relays", "goods": {"EQUIPMENT": comms.POST_HOLDS}, "upkeep": "40",
            "dark": False}
        comms.stats(self.k)["nets"]["civ:Line"] = {str(self.a): comms.own(self.k, self.a)}
        commerce.stats(self.k).setdefault("stale_by", {})[f"civ:Buyer|{self.a}"] = 10 ** 6
        self.patch = [mock.patch.object(spheres, "_home", side_effect=lambda k, who: self.home),
                      mock.patch("xylarium.kernel.polity.sovereigns",
                                 return_value={"s": {"people": "civ:Buyer", "id": "s"}})]
        for p in self.patch:
            p.start()

    def tearDown(self):
        for p in getattr(self, "patch", []):
            p.stop()

    def _accept(self):
        return mock.patch("xylarium.kernel.decide.choose", side_effect=lambda k, opts, m, *s: opts[0])

    def test_a_feed_is_bought_paid_as_a_transfer_and_delivers_word(self):
        with self._accept(), mock.patch.object(comms, "_withholds", return_value=False):
            comms.subscribe(self.k)
        feed = next(iter(comms.stats(self.k)["feeds"].values()))
        self.assertFalse(feed["covert"])
        before = {c: b["total"] for c, b in ledger.money_supply(self.k).items()}
        comms.pay_feeds(self.k)
        self.assertEqual({c: b["total"] for c, b in ledger.money_supply(self.k).items()}, before)   # a transfer
        self.assertGreater(endowments.sol(endowments.stats(self.k)["funds"]["civ:Line"]), 0)
        comms.deliver(self.k)
        self.assertTrue(any(key.startswith(f"{self.a}|") for key in comms.stats(self.k)["views"][str(self.home.sector_id)]))

    def test_a_withheld_feed_is_tapped_and_the_watch_may_catch_it(self):
        from xylarium.kernel import covert
        with self._accept(), mock.patch.object(comms, "_withholds", return_value=True), \
                mock.patch.object(covert, "_caught", return_value=True), \
                mock.patch.object(covert, "_expose") as exposed:
            comms.subscribe(self.k)
        self.assertTrue(exposed.called)
        self.assertEqual(comms.stats(self.k)["feeds"], {})
