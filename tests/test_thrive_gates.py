"""
Three gates that held every people still: a self-forecast misjudges only what moves (a flat gauge is foreseen as
flat); commerce prices by the market's mean where a side keeps no port (as its law says); an ancients' house answers
to no younger line.
"""

import unittest
from unittest import mock

from xylarium.kernel import ascendance, commerce, introspect, spheres, stewardship, transit
from xylarium.kernel.engine import GameKernel


class TestThriveGates(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)

    def test_a_flat_gauge_is_foreseen_as_flat(self):
        p = next(w for s in self.k.sectors.values() for w in s.planets if w.population > 0 and w.civilization)
        holder = "civ:Flat"
        g = {x: 0.5 for x in introspect.GAUGES}
        rec = {"last_gauges": dict(g), "forecast": None}
        introspect._forecast(self.k, holder, rec, dict(g), p)
        self.assertEqual(rec["forecast"], g)                         # nothing moved: no error to make

    def test_a_world_with_no_port_is_priced_at_the_markets_mean(self):
        w = next(w for s in self.k.sectors.values() for w in s.planets if w.population > 0 and s.port is None)
        with mock.patch.object(transit, "price", return_value=7.0):
            self.assertEqual(commerce._worth(self.k, w, "ORE"), 7.0)

    def test_an_ancient_does_not_petition_a_younger_line(self):
        spheres.ensure(self.k)
        realm = stewardship.realms(self.k)[0]
        who = next(w for w in spheres.stats(self.k)["nets"] if spheres.presence(self.k, realm) != w)
        with mock.patch.object(ascendance, "_ancient", return_value=True):
            ascendance.petition(self.k, who, realm)
        self.assertIsNone(ascendance.ruling(self.k, who))
        ascendance.petition(self.k, who, realm)
        with mock.patch.object(ascendance, "_ancient", side_effect=lambda k, w2: w2 == who):
            self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100
            ascendance.season(self.k)
        self.assertIsNone(ascendance.ruling(self.k, who))           # withdrawn on becoming ancient


if __name__ == "__main__":
    unittest.main()


class TestPricesInOneMoney(unittest.TestCase):
    def test_a_ports_price_is_carried_to_the_hub_by_its_moneys_rate(self):
        k = GameKernel(seed=42)
        sec = next(s for s in k.sectors.values() if s.port is not None and s.port.currency != k.fx_market.hub
                   and any(w.population > 0 for w in s.planets))
        w = next(x for x in sec.planets if x.population > 0)
        from xylarium.kernel.economy import EconomyManager
        comm = next(c for c in ("ORE", "EQUIPMENT", "ORGANICS") if EconomyManager.get_unit_prices(sec.port, c)[1] > 0)
        with mock.patch("xylarium.kernel.staples.of", return_value="none"):
            got = commerce._worth(k, w, comm)
        sells = EconomyManager.get_unit_prices(sec.port, comm)[1]
        self.assertAlmostEqual(got, sells / k.fx_market.rate(sec.port.currency))
