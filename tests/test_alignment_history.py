"""
A people's alignment is the truth of its whole history - light (lives made and kept, spared) against dark (taken) -
never faded; its own telling of it fades as its records do, and the gap between them is measured. Its few take rent
from its many as far as the many bear it and their horizon makes it worth it; a rising ends it. A relic mind comes
to hold what its finders have done, not what they say.
"""

import random
import unittest
from types import SimpleNamespace

from xylarium.kernel import alignment, cohabit, decide, knowledge, memory, relics, rent, society, syntropy, \
    technology
from xylarium.kernel.engine import GameKernel


def _civ():
    return SimpleNamespace(alignment=0.0, light=0.0, dark=0.0, told_light=0.0, told_dark=0.0)


class TestHistory(unittest.TestCase):
    def test_a_turn_does_not_undo_a_long_history(self):
        c = _civ()
        for _ in range(400):                                   # four hundred generations of taking half
            alignment.flow(c, light=1000, dark=1000)
            alignment.fade(c, 1.0, 1.0 - memory.TELL_ERR)
        for _ in range(4):                                     # then four of taking nothing
            alignment.flow(c, light=1000)
            alignment.fade(c, 1.0, 1.0 - memory.TELL_ERR)
        self.assertLess(alignment.character(c), 0.01)           # the audit reads the whole history
        self.assertGreater(alignment.doctrine(c), 0.05)          # its own telling has already turned
        self.assertGreater(alignment.gap(c), 0.04)

    def test_the_history_itself_never_fades(self):
        c = _civ()
        alignment.flow(c, light=10, dark=30)
        alignment.fade(c, 10 ** 6)
        self.assertAlmostEqual(alignment.character(c), -0.5)
        self.assertAlmostEqual(c.light, 10.0)

    def test_weight_is_kept_and_nothing_is_pinned(self):
        a, b = _civ(), _civ()
        alignment.flow(a, dark=1)
        alignment.flow(b, dark=1000)
        alignment.flow(a, light=10)
        alignment.flow(b, light=10)
        self.assertGreater(alignment.character(a), alignment.character(b))
        self.assertGreater(alignment.character(b), -1.0)

    def test_a_given_alignment_holds_until_a_history_outweighs_it(self):
        c = _civ()
        alignment.set_people(c, 0.6)
        self.assertAlmostEqual(c.alignment, 0.6)
        alignment.flow(c, dark=1)
        self.assertAlmostEqual(c.alignment, -1.0)                # no weight: what it does is all that counts
        alignment.set_people(c, 0.6, weight=1000)
        alignment.flow(c, dark=1)
        self.assertGreater(c.alignment, 0.59)


class _World(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0
                      and p.civilization is not None), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)

    def _always(self):
        real = decide.choose

        def best(kernel, options, m, *salt):
            top = max(options, key=lambda o: o["value"] - o["cost"]) if options else None
            return top if top is not None and top["value"] - top["cost"] > 0 else None
        decide.choose = best
        self.addCleanup(lambda: setattr(decide, "choose", real))

    def _horizon(self, years):
        real = decide.horizon
        decide.horizon = lambda m: 4.0 * years
        self.addCleanup(lambda: setattr(decide, "horizon", real))


class TestRent(_World):
    def setUp(self):
        super().setUp()
        self._always()
        soc = self.p.society
        soc["way"] = "state"
        soc["self_sufficiency"] = 3.0
        self.p.morale = 100
        self.p.civilization.dogma = 0.0
        syntropy.stats(self.k)["peoples"][self.who] = {"slope": 0.01}

    def test_a_people_without_a_state_has_no_few(self):
        self.p.society["way"] = "forage"
        self.assertEqual(rent.choose(self.k, self.p), 0.0)

    def test_a_short_horizon_takes_all_the_many_bear(self):
        self._horizon(1.0)
        rho = rent.choose(self.k, self.p)
        self.assertGreater(rho, 0.0)
        self.assertLessEqual(rho, rent.bearable(self.k, self.p) + 1e-9)
        self.assertGreater(rho + 1.0 / rent.LEVELS, rent.bearable(self.k, self.p))

    def test_a_long_horizon_in_a_growing_people_takes_less(self):
        self._horizon(1.0)
        short = rent.choose(self.k, self.p)
        self._horizon(2000.0)
        self.p.society["rent"] = 0.0
        long = rent.choose(self.k, self.p)
        self.assertLess(long, short)

    def test_rent_presses_the_many_and_a_rising_ends_it(self):
        before = society.stress(self.k, self.p)["immiseration"]
        self.p.society["rent"] = 0.9
        self.assertGreater(society.stress(self.k, self.p)["immiseration"], before)
        rent.overturned(self.k, self.p)
        self.assertEqual(rent.of(self.p), 0.0)

    def test_a_take_within_the_surplus_moves_order_and_beyond_it_starves(self):
        civ = self.p.civilization
        self.p.society["rent_cycle"] = self.k.cycle_count
        self.p.society["rent"] = 0.5                           # ss 3: half leaves the many 1.5 - a transfer
        d0 = civ.dark
        rent.season(self.k, self.p, 1.0, 10 ** 9)
        self.assertEqual(civ.dark, d0)
        self.p.society["rent"] = 0.75                          # leaves them 0.75 of their need: a quarter starve
        rent.season(self.k, self.p, 1.0, 10 ** 9)
        self.assertAlmostEqual(civ.dark - d0, 0.25 * self.p.population, places=3)


class TestRelicMindLeaning(_World):
    def setUp(self):
        super().setUp()
        technology.stats(self.k)["of"].setdefault(self.who, {}).update({"computation": 1, "robotics": 1})
        knowledge.learn(self.k, self.who, "information", 10 ** 7)

    def _wake(self, makers_alignment, prey):
        self.p.ruins = {"relics": {"makers": "Elders", "mind": {"name": "civ:Elder Mind", "metab": "biotic",
                                                                "alignment": makers_alignment, "vocab": [],
                                                                "prey_plans": prey}}}
        relics._dig(self.k, self.who, [self.p])
        relics._minds(self.k)                                  # it takes a body
        return next(c for c in cohabit.communities(self.p) if c.get("relic_mind"))

    def test_it_comes_to_hold_what_its_finders_have_done(self):
        from xylarium.kernel import contact
        civ = self.p.civilization
        alignment.set_people(civ, 0.6, weight=1000)
        civ.told_light, civ.told_dark = 0.0, 1000.0             # whatever they tell of themselves
        mind = self._wake(-0.9, [])
        contact.stats(self.k)["familiarity"][contact._key("civ:Elder Mind", self.who)] = 1.0
        relics._minds(self.k)
        self.assertGreater(mind["alignment"], -0.9)

    def test_it_keeps_its_silence_when_nothing_is_worth_doing(self):
        alignment.set_people(self.p.civilization, 0.0)
        mind = self._wake(0.0, [])
        relics._minds(self.k)
        self.assertEqual(mind["choice"], "silence")

    def test_a_people_that_keeps_records_keeps_its_telling(self):
        mem = memory._of(self.k, self.who)
        mem["media"] = ["oral"]
        oral = memory.character_keep(self.k, self.who, self.p)
        mem["media"] = ["oral", "inscribed", "portable", "machine"]
        machine = memory.character_keep(self.k, self.who, self.p)
        self.assertLess(oral, 0.95)
        self.assertGreater(machine, 0.999)


class TestReputation(_World):
    def test_a_people_is_read_by_what_it_was_told_and_what_it_saw(self):
        from xylarium.kernel import reputation
        self.assertIsNone(reputation.read(self.k, "civ:A", "civ:B"))
        self.assertEqual(reputation.trust(self.k, "civ:A", "civ:B"), 0.5)       # a stranger: half its word
        reputation.witness(self.k, "civ:A", "civ:B", dark=30)
        reputation.witness(self.k, "civ:A", "civ:B", light=10)
        self.assertAlmostEqual(reputation.read(self.k, "civ:A", "civ:B"), -0.5)
        self.assertAlmostEqual(reputation.trust(self.k, "civ:A", "civ:B"), 0.25)
        self.assertIsNone(reputation.read(self.k, "civ:C", "civ:B"))              # another has seen nothing

    def test_the_seasons_carry_a_peoples_deeds_to_those_who_know_it(self):
        from xylarium.kernel import contact, reputation, syntropy
        self.k = GameKernel(seed=7)                                           # a settled board: many peoples
        self.k.activate()
        by = syntropy._peoples(self.k)
        a, b = sorted(by)[:2]
        real = contact.contacts
        contact.contacts = lambda kernel, by: {a: {b: 1}, b: {a: 1}}
        self.addCleanup(lambda: setattr(contact, "contacts", real))
        contact.stats(self.k)["familiarity"][contact._key(a, b)] = 1.0
        reputation.season(self.k)                                             # they meet: each hears the other's story
        civ_b = max(by[b], key=lambda p: p.population).civilization
        alignment.flow(civ_b, dark=10 ** 9)                                     # then b takes, and a watches
        reputation.season(self.k)
        self.assertLess(reputation.read(self.k, a, b), alignment.doctrine(civ_b) + 1e-9)


class TestPlacedPeoples(_World):
    def test_a_people_placed_grown_brings_the_history_of_its_ages(self):
        self.p.society["way"] = "state"
        self.p.citadel_level = max(1, self.p.citadel_level)                     # it has raised works
        rent.prehistory(self.k, self.p)
        civ = self.p.civilization
        self.assertGreater(civ.light + civ.dark, self.p.population * 20)       # its ages, not a draw
        self.assertLessEqual(alignment.character(civ), 1.0)


class TestCaptains(unittest.TestCase):
    def test_honest_work_is_light_and_taking_is_dark(self):
        random.seed(3)
        self.k = GameKernel(seed=42)
        cap = self.k.register_player("hero", "Hero")
        before = cap.credits
        cap.credits += 1000
        alignment.earned(self.k, cap, "fair_trade", before)
        self.assertGreater(cap.cosmic_alignment, 0.99)
        alignment.deed(self.k, cap, "tribute_extorted", dark=alignment.lives_of_sol(self.k, 1000))
        self.assertAlmostEqual(cap.cosmic_alignment, 0.0, places=4)
        alignment.deed(self.k, cap, "convicted")                                # a judgement weighs nothing
        self.assertAlmostEqual(cap.cosmic_alignment, 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
