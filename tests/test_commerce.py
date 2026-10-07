"""
Commerce: a treaty of trade moves goods - the seller's surplus against the buyer's want, priced as the buyer heard it, paid
in the buyer's money through the exchanges, its route's tolls paid to the lanes' keepers. Nothing is minted. A route
a lane bars (a blockade, an embargo) or a quarantined party closes. A sovereign whose first need is wealth levies a
tariff into its capital. What a treaty delivered is what moved.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import ascendance, commerce, decide, polity, staples, transit
from xylarium.kernel.engine import GameKernel


def _accept(k, opts, m, *salt):
    return opts[0]


class TestCommerce(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        for _ in range(100):
            self.k.tick_simulation()
        live = [s for s in polity.sovereigns(self.k).values() if not s.get("ended") and polity._worlds_of(self.k, s)]
        live.sort(key=lambda s: s["id"])
        self.buyer = live[0]
        self.seller = next(s for s in live[1:] if s["people"] != self.buyer["people"])
        self.bw = polity._worlds_of(self.k, self.buyer)[0]
        self.sw = polity._worlds_of(self.k, self.seller)[0]
        self.comm = staples.of(self.k, self.bw)
        staples.move(self.bw, self.comm, -staples.held(self.bw, self.comm))         # the buyer's granary is bare
        staples.move(self.sw, self.comm, staples.reserve(self.k, self.sw, self.comm) + 5000 -
                     staples.held(self.sw, self.comm))                              # the seller holds 5000 beyond
        self.bw.treasury = self.sw.treasury = 10 ** 9
        from xylarium.kernel import comms                                            # a ship has brought word of the
        comms.arrive(self.k, "captain:test-courier", self.sw.sector_id)              # seller's port to the buyer's
        comms.arrive(self.k, "captain:test-courier", self.bw.sector_id)
        if self.k.sectors[self.bw.sector_id].port is None:
            comms.merge(comms.stats(self.k)["views"].setdefault(str(self.bw.sector_id), {}),
                        comms.own(self.k, self.sw.sector_id))

    def _rec(self):
        return {"value": 0.0, "tolls": 0.0, "tariff": 0.0, "closed": 0, "units": {}, "flows": {}}

    def test_goods_move_from_surplus_to_want_and_money_moves_back(self):
        units = staples.held(self.bw, self.comm) + staples.held(self.sw, self.comm)
        before_b, before_s = self.bw.treasury, self.sw.treasury
        rec = self._rec()
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(commerce, "_route", return_value=[]), \
                mock.patch.object(commerce, "_taxes", return_value=False):
            moved = commerce.trade(self.k, self.buyer, self.seller, rec)
        self.assertGreater(moved, 0)
        self.assertLessEqual(moved, 5000)                                            # never below what it keeps
        self.assertEqual(staples.held(self.bw, self.comm) + staples.held(self.sw, self.comm), units)   # moved, not made
        self.assertLess(self.bw.treasury, before_b)
        self.assertGreater(self.sw.treasury, before_s)
        if self.bw.currency == self.sw.currency:
            self.assertEqual(before_b - self.bw.treasury, self.sw.treasury - before_s)   # paid, not minted
        from xylarium.kernel import news                                             # priced as the buyer heard it
        word = news.heard(self.k, self.bw.sector_id, self.sw.sector_id, self.comm) \
            if self.k.sectors[self.sw.sector_id].port is not None else None
        unit = word[0] if word is not None else transit.price(self.k, self.comm)
        self.assertAlmostEqual(rec["value"], moved * unit, places=3)

    def test_a_council_that_judges_it_not_worth_buys_nothing(self):
        with mock.patch.object(decide, "choose", return_value=None), \
                mock.patch.object(commerce, "_route", return_value=[]):
            self.assertEqual(commerce.trade(self.k, self.buyer, self.seller, self._rec()), 0)

    def test_a_barred_lane_or_a_quarantine_closes_the_route(self):
        a = self.sw.sector_id
        b = next((w for w in self.k.sectors[a].warps if w in self.k.sectors), None)
        if b is None:
            self.skipTest("no lane")
        with mock.patch.object(self.k, "find_path", return_value=[a, b]), \
                mock.patch.object(transit, "blocks", side_effect=lambda k, who, x, y: who == self.buyer["people"]):
            self.assertIsNone(commerce._route(self.k, a, b, self.buyer["people"], self.seller["people"]))
        with mock.patch.object(self.k, "find_path", return_value=[a, b]), \
                mock.patch.object(transit, "blocks", return_value=False):
            self.assertEqual(commerce._route(self.k, a, b, self.buyer["people"], self.seller["people"]), [(a, b)])
            with mock.patch.object(ascendance, "ruling",
                                   side_effect=lambda k, who: "quarantine" if who == self.seller["people"] else None):
                self.assertIsNone(commerce._route(self.k, a, b, self.buyer["people"], self.seller["people"]))

    def test_a_sovereign_short_of_wealth_levies_a_tariff_into_its_capital(self):
        cap = next(w for s in self.k.sectors.values() for w in s.planets
                   if w.population > 0 and w is not self.bw and w is not self.sw)   # its capital, elsewhere
        realm = dict(polity._polities(self.k)[self.buyer["realm"]], capital=cap.id)
        before = cap.treasury
        rec = self._rec()
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(commerce, "_route", return_value=[]), \
                mock.patch.object(commerce, "_taxes", return_value=True), \
                mock.patch.object(commerce, "_worth", return_value=transit.price(self.k, self.comm) * 3), \
                mock.patch.object(polity, "_polities", return_value={self.buyer["realm"]: realm}), \
                mock.patch.object(polity, "_worlds_of", side_effect=lambda k, s: [self.bw] if s is self.buyer
                                  else [self.sw]):
            commerce.trade(self.k, self.buyer, self.seller, rec)
        self.assertGreater(rec["tariff"], 0)
        self.assertGreater(cap.treasury, before)

    def test_what_a_treaty_delivered_is_what_moved(self):
        self.assertIsNone(commerce.delivered(self.k, self.buyer["id"], self.seller["id"]))
        rec = self._rec()
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(commerce, "_route", return_value=[]), \
                mock.patch.object(commerce, "_taxes", return_value=False):
            moved = commerce.trade(self.k, self.buyer, self.seller, rec)
        commerce.stats(self.k)["last"][commerce._pair(self.buyer["id"], self.seller["id"])] = rec
        got = commerce.delivered(self.k, self.buyer["id"], self.seller["id"])
        self.assertEqual(got["food"], moved)
        self.assertEqual(commerce.delivered(self.k, self.seller["id"], self.buyer["id"])["food"], 0)
        self.assertGreater(commerce.delivered(self.k, self.seller["id"], self.buyer["id"])["earned"], 0)

    def test_a_peoples_model_is_read_from_its_measures(self):
        m = commerce.model(self.k, self.buyer["people"])
        for key in ("regime", "controls", "rent", "bearable", "extractive", "openness", "balance"):
            self.assertIn(key, m)
        self.assertEqual(m["extractive"], m["rent"] > m["bearable"])


if __name__ == "__main__":
    unittest.main()


class TestHeardPrices(unittest.TestCase):
    """A far market is weighed on old word: its long mean, and the drift its price can make over the light-time."""

    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        for _ in range(60):
            self.k.tick_simulation()
        from xylarium.kernel import news
        self.news = news
        self.key = next(iter(sorted(news.stats(self.k)["mem"])))
        self.sid, self.comm = int(self.key.split("|")[0]), self.key.split("|")[1]

    def test_word_is_as_old_as_its_carrier_left_it_and_none_without_a_carrier(self):
        from xylarium.kernel import comms
        unheard = [sid for sid in sorted(self.k.sectors) if sid != self.sid
                   and self.news.heard(self.k, sid, self.sid, self.comm) is None]    # nothing has carried it there
        if not unheard:
            self.skipTest("real traffic has already carried this port's word everywhere")
        other = unheard[0]
        comms.arrive(self.k, "captain:courier", self.sid)                              # a ship docks at the port...
        stamp = self.k.cycle_count
        self.k.cycle_count += 200                                                      # ...and sails two years
        comms.stats(self.k)["views"].setdefault(str(other), {})
        comms.merge(comms.stats(self.k)["views"][str(other)], comms.stats(self.k)["carried"]["captain:courier"])
        price, age, _ = self.news.heard(self.k, other, self.sid, self.comm)
        self.assertEqual(age, (self.k.cycle_count - stamp) / 100.0)
        self.assertGreater(price, 0)

    def test_old_word_costs_more_and_a_still_price_costs_nothing(self):
        self.assertGreater(self.news.age_cost(100.0, 400.0, 0.1), self.news.age_cost(100.0, 4.0, 0.1))
        self.assertEqual(self.news.age_cost(100.0, 400.0, 0.0), 0.0)
        self.assertEqual(self.news.age_cost(100.0, 0.0, 0.3), 0.0)

    def test_a_seller_keeps_goods_its_own_port_pays_more_for(self):
        live = [s for s in polity.sovereigns(self.k).values() if not s.get("ended") and polity._worlds_of(self.k, s)]
        if len(live) < 2:
            self.skipTest("one sovereign")
        live.sort(key=lambda s: s["id"])
        buyer, seller = live[0], next(s for s in live[1:] if s["people"] != live[0]["people"])
        bw, sw = polity._worlds_of(self.k, buyer)[0], polity._worlds_of(self.k, seller)[0]
        if self.k.sectors[sw.sector_id].port is None:
            self.skipTest("seller keeps no port")
        comm = staples.of(self.k, bw)
        staples.move(sw, comm, staples.reserve(self.k, sw, comm) + 500 - staples.held(sw, comm))
        bw.treasury = 10 ** 9
        from xylarium.kernel.economy import EconomyManager
        with mock.patch.object(self.news, "heard", return_value=(0.001, 0.0, 0.0)), \
                mock.patch.object(EconomyManager, "get_unit_prices", return_value=(50, 60)), \
                mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(commerce, "_route", return_value=[]):
            got = commerce._ship(self.k, buyer, seller, bw, sw, comm, 100, None, False,
                                 {"value": 0.0, "tolls": 0.0, "tariff": 0.0, "closed": 0, "units": {}, "flows": {}})
        self.assertEqual(got, 0)


class TestConvoys(TestCommerce):
    """A forward: paid at the price struck, the goods aboard for the haul, counted, and landed when it is sailed."""

    def test_goods_ride_the_haul_and_land(self):
        from xylarium.kernel import matter
        a = self.sw.sector_id
        before = matter.totals(self.k)
        held = staples.held(self.bw, self.comm)
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(commerce, "_route", return_value=[(a, a), (a, a)]), \
                mock.patch.object(commerce, "_taxes", return_value=False), \
                mock.patch("xylarium.kernel.transit.flow_passage", return_value=0.0):
            moved = commerce.trade(self.k, self.buyer, self.seller, self._rec())
        self.assertGreater(moved, 0)
        self.assertEqual(staples.held(self.bw, self.comm), held)                    # not yet landed
        self.assertEqual(commerce.in_transit(self.k).get(self.comm), moved)        # aboard, and counted
        self.assertEqual(matter.totals(self.k), before)
        self.k.cycle_count += 2
        self.assertEqual(commerce.land(self.k), moved)
        self.assertEqual(staples.held(self.bw, self.comm), held + moved)
        self.assertEqual(matter.totals(self.k), before)
