"""
In a cosmic universe money, the exchange and the Reserve are founded by peoples: a people strikes its coin when it
must settle with others (institutions.need), the exchange opens when two monies meet or the first starport opens, the Reserve when two banks
trade through the exchange. Before that there is nothing to circulate, and the money seasons do nothing.
"""

import unittest

from xylarium.kernel import institutions, ledger
from xylarium.kernel.engine import GameKernel


def _money(k):
    return {c: b["total"] for c, b in ledger.money_supply(k).items() if b["total"]}


class TestFounding(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.home = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0)

    def test_nothing_exists_before_anyone_founds_it(self):
        self.assertEqual(_money(self.k), {})
        self.assertEqual(self.k.banking.banks, {})
        self.assertEqual(self.k.fx_market.pools, {})
        self.assertFalse(institutions.reserve_founded(self.k))

    def test_a_state_strikes_its_coin_and_the_exchange_opens_with_deposits(self):
        p = self.home
        p.society["way"] = "state"
        self.assertIn("found their money", institutions.found_currency(self.k, p))
        cur = p.currency
        self.assertIn(cur, self.k.banking.banks)
        self.assertEqual(institutions.found_currency(self.k, p), None)              # once
        p.treasury = 40000
        before = p.treasury
        line = institutions.found_exchange(self.k, "the first starport opens")
        self.assertIsNotNone(line)
        pool = self.k.fx_market.pools[cur]
        self.assertEqual(before - p.treasury, pool["local"])                       # a deposit: moved, not made
        self.assertGreater(pool["sol"], 0)                                         # the house's unit, minted against it
        self.assertIsNone(institutions.found_reserve(self.k))                       # one bank: no Reserve yet

    def test_a_stranger_coin_is_not_taken_up_and_a_saved_founding_reloads_as_it_was(self):
        import os
        import tempfile
        from xylarium.persistence.store import StatePersistence
        p = self.home
        p.society["way"] = "state"
        institutions.found_currency(self.k, p)
        from xylarium.kernel import cosmos
        if not any(w is not p and w.population == 0 for s in self.k.sectors.values() for w in s.planets):
            m = cosmos.stats(self.k)["minds"][1]                                   # a stranger's system, charted
            cosmos.build_slot(self.k, tuple(m["cell"]), int(m["k"]))
        other = next(w for s in self.k.sectors.values() for w in s.planets if w is not p and w.population == 0)
        from xylarium.kernel.civilization import CivilizationIntelligenceEngine
        other.civilization = CivilizationIntelligenceEngine.create_civilization({
            "name": "Strangers", "species_name": "x", "clade": "bimaniform", "class_code": 0, "sigil": "*",
            "metabolism": "biotic", "disposition": "industry", "motto": "", "station": "arisen", "tech_level": 0})
        other.population, other.currency = 1000, p.currency
        other.society["way"] = "state"
        institutions.found_currency(self.k, other)
        self.assertNotEqual(other.currency, p.currency)                            # never met: its own money
        self.assertIn(other.currency, self.k.banking.banks)
        path = os.path.join(tempfile.mkdtemp(), "s.json")
        StatePersistence.save_to_file(self.k, path)
        k2 = StatePersistence.load_from_file(path)
        self.assertEqual(k2.fx_market.pools, {})                                   # no exchange appears on load

    def test_unfounded_moneys_are_not_governed(self):
        from xylarium.kernel import regimes
        for _ in range(400):
            self.k.tick_simulation()
        founded = set(institutions.stats(self.k).get("currencies", {}))
        for cur in regimes.stats(self.k)["by_currency"]:          # only moneys some people founded are governed
            self.assertIn(cur, founded)                           # (a people may found one in its annals' ages)


if __name__ == "__main__":
    unittest.main()


class TestRehome(unittest.TestCase):
    def test_a_world_moving_money_reforms_what_it_holds_never_relabels(self):
        from simulate_playtest import ledger_net
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        p = next(p for s in k.sectors.values() for p in s.planets if p.population > 0)
        p.society["way"] = "state"
        institutions.found_currency(k, p)
        old = p.currency
        p.household_purse = 320
        ledger.mint("test", 320, old)

        def residual():
            ms, ln = ledger.money_supply(k), ledger_net(k)
            return {c: ms.get(c, {}).get("total", 0) - ln.get(c, 0) for c in set(ms) | set(ln)}
        before = residual()
        institutions.rehome(k, p, "SOL", "test")
        self.assertEqual(p.currency, "SOL")
        self.assertEqual({c: v for c, v in residual().items() if v}, {c: v for c, v in before.items() if v})


class TestCoinWeighed(unittest.TestCase):
    """A money is weighed, never staged: what settling without one costs a people against what one would lock."""

    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.home = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0)

    def _meet(self, other="civ:Strangers"):
        from xylarium.kernel import contact, knowledge
        me = knowledge.holder_of_planet(self.home)
        contact.stats(self.k)["familiarity"][contact._key(me, other)] = 0.5

    def test_a_state_with_no_one_outside_to_pay_has_nothing_to_save(self):
        self.home.society["way"] = "state"
        sec = self.k.sectors[self.home.sector_id]
        if sec.port is not None:
            self.skipTest("a port in its system")
        self.assertEqual(institutions.friction(self.k, self.home)["value"], 0.0)
        self.assertIsNone(institutions.weigh_money(self.k, self.home))

    def test_strangers_make_barter_costly_and_more_goods_cost_more(self):
        self._meet()
        fr = institutions.friction(self.k, self.home)
        self.assertGreater(fr["value"], 0.0)
        self.assertLess(fr["moved"], 1.0)
        self.assertGreaterEqual(fr["loss"], 0.0)

    def test_kin_settle_among_themselves(self):
        from xylarium.kernel import descent, knowledge
        me = knowledge.holder_of_planet(self.home)
        descent.stats(self.k)["of"]["civ:Daughters"] = {"root": descent.line(self.k, me)["root"], "parent": me,
                                                        "split": 0.0, "chemistry": None}
        self._meet("civ:Daughters")
        if self.k.sectors[self.home.sector_id].port is None:
            self.assertEqual(institutions.friction(self.k, self.home)["moved"], 0.0)

    def test_no_backing_in_its_ground_no_money(self):
        self._meet()
        self.home.element_deposits["ORE"] = 0
        self.assertIsNone(institutions.weigh_money(self.k, self.home))

    def test_a_chosen_money_is_minted_only_against_backing_moved_from_its_ground(self):
        from unittest import mock
        from xylarium.kernel import decide, matter
        self._meet()
        self.home.element_deposits["ORE"] = 10 ** 9
        matter0 = matter.totals(self.k)
        with mock.patch.object(decide, "choose", side_effect=lambda k, opts, m, *s: opts[0]):
            line = institutions.strike_if_weighed(self.k, self.home)
        self.assertIsNotNone(line)
        cur = self.home.currency
        bank = self.k.banking.banks[cur]
        held = sum(bank.warehouse.values())
        self.assertGreater(held, 0)
        self.assertEqual(_money(self.k).get(cur, 0), self.home.treasury)     # its whole supply: the founding issue
        self.assertEqual(matter.totals(self.k), matter0)                     # the backing moved, not made
