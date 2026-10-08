"""
A people that crosses inside another's dominion answers it, and is answered - by weighing, never a trigger: an
enclave, an alliance, absorption (a people transfer), war for the halfway seam (Lanchester at the margin, deaths booked
with their cause), or a leap through a gateway its own arrays banked for. The lower ledger speaks first.
"""
import math
import unittest
from types import SimpleNamespace
from unittest import mock

from xylarium.kernel import encircle, settling


class _K:
    pass


def _galaxy(places):
    k = _K()
    k.__dict__.update(state={"annals": {"of": {}, "falls": 0, "wars": 0, "pacts": 0},
                             "cosmos": {"place": {str(s): {"r": r, "theta0": th} for s, (r, th) in places.items()}}},
                      sectors={0: SimpleNamespace(planets=[])}, cycle_count=0)
    return k


def _bubble(k, who, sid, t0, hop=0.002, g=1e3):
    b = {"sid": sid, "metab": "biotic", "r0": 8.0, "crossed": t0, "t0": t0, "share": 1.0, "hop": hop, "g": g,
         "rmax": 30.0, "cuts": {}, "enclosed": None, "fell": None}
    b["v"] = hop * g
    settling.stats(k)[who] = b
    return b


def _pick(name):
    """A mind that takes the option named, or (answering) accepts."""
    def choose(kernel, opts, m, *salt):
        for o in opts:
            if o["name"] in (name, "accept"):
                return o
        return next(o for o in opts if o["kind"] == "enclave")
    return choose


class _Base(unittest.TestCase):
    def setUp(self):
        self.k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.01)})
        _bubble(self.k, "civ:Old", 1, 1.0)
        _bubble(self.k, "civ:New", 2, 1.5)
        self.when = settling.contact_time(self.k, "civ:Old", "civ:New")
        self.assertEqual(self.when[3], "civ:New")
        self.homes = {"civ:Old": SimpleNamespace(id="p_old", currency=None),
                      "civ:New": SimpleNamespace(id="p_new", currency=None)}
        self.heights = {"civ:Old": 5, "civ:New": 5}
        self.patches = [
            mock.patch("xylarium.kernel.history.event", lambda *a, **kw: {}),
            mock.patch("xylarium.kernel.spheres.style", lambda *a, **kw: "standoff"),
            mock.patch("xylarium.kernel.spheres._home", lambda k, who: self.homes.get(who)),
            mock.patch("xylarium.kernel.decide.mind_of_planet", lambda k, p: {"noise": 0.0}),
            mock.patch("xylarium.kernel.clocks.height", lambda k, who: self.heights[who]),
            mock.patch("xylarium.kernel.clocks.link", lambda *a, **kw: None),
            mock.patch.object(encircle, "_capacity", lambda k, who: 1000.0),
            mock.patch("xylarium.kernel.gateways.coalition_power_w", lambda k, m: 1e40),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def meet(self, chooser):
        with mock.patch("xylarium.kernel.decide.choose", side_effect=chooser):
            settling.meet(self.k, "civ:Old", "civ:New", self.when, [])
        return encircle.stats(self.k)[-1]


class TestAnswers(_Base):
    def test_an_enclave_changes_nothing(self):
        rec = self.meet(_pick("enclave"))
        self.assertEqual(rec["outcome"], "enclave")
        self.assertIsNone(settling.stats(self.k)["civ:New"]["fell"])
        self.assertEqual(encircle.deaths(self.k), {})

    def test_absorption_is_a_transfer_not_a_deletion(self):
        rec = self.meet(_pick("join"))
        self.assertEqual(rec["outcome"], "join")
        b = settling.stats(self.k)["civ:New"]
        self.assertEqual(b["absorbed_by"], "civ:Old")
        self.assertIsNotNone(b["fell"])                               # its dominion ends ...
        moved = self.k.state["annals"]["transfers"][-1]
        self.assertEqual((moved["from"], moved["to"], moved["why"]), ("civ:New", "civ:Old", "absorbed"))
        self.assertGreater(moved["people"], 0)                        # ... its people live on, counted
        self.assertEqual(encircle.deaths(self.k), {})                  # and none died of it

    def test_a_refused_alliance_leaves_the_enclave(self):
        def chooser(kernel, opts, m, *salt):
            names = [o["name"] for o in opts]
            if "alliance" in names:
                return next(o for o in opts if o["name"] == "alliance")
            return next(o for o in opts if o["kind"] == "enclave")       # the encloser declines
        rec = self.meet(chooser)
        self.assertEqual((rec["proposed"], rec["outcome"]), ("alliance", "enclave"))

    def test_the_lower_ledger_speaks_first(self):
        self.heights["civ:Old"] = 2
        rec = self.meet(_pick("tolerate"))
        self.assertEqual(rec["first"], "civ:Old")
        self.heights.update({"civ:Old": 9, "civ:New": 3})
        _bubble(self.k, "civ:Old", 1, 1.0)
        _bubble(self.k, "civ:New", 2, 1.5)
        rec = self.meet(_pick("enclave"))
        self.assertEqual(rec["first"], "civ:New")


class TestWar(_Base):
    def _war(self, grown):
        with mock.patch("math.exp", side_effect=lambda x: grown if x > 0 else math.e ** x):
            return self.meet(_pick("contest"))

    def test_a_young_margin_loses_the_seam(self):
        with mock.patch.object(encircle, "_worlds", lambda k, who, t: 50.0 if who == "civ:New" else 1e6):
            rec = self._war(grown=10.0)                                # the encloser's margin: ten worlds there
        self.assertEqual(rec["outcome"], "war")
        st = settling.stats(self.k)
        self.assertIsNotNone(st["civ:New"]["cuts"]["civ:Old"]["a"])      # enclosure became a seam
        self.assertIn("civ:New", st["civ:Old"]["cuts"])                   # and the encloser lost the far side
        self.assertIsNone(st["civ:New"]["fell"])
        d = encircle.deaths(self.k)
        self.assertGreater(d["civ:Old"]["war:encirclement"], 0)           # every death booked, with its cause
        self.assertGreater(d["civ:New"]["war:encirclement"], 0)
        self.assertEqual(d["civ:Old"]["war:encirclement"], 10 * 1000)     # the margin falls whole

    def test_a_developed_margin_holds(self):
        with mock.patch.object(encircle, "_worlds", lambda k, who, t: 5.0 if who == "civ:New" else 1e6):
            rec = self._war(grown=1e9)
        self.assertEqual(rec["outcome"], "war")
        self.assertIsNotNone(settling.stats(self.k)["civ:New"]["fell"])
        self.assertEqual(encircle.deaths(self.k)["civ:New"]["war:encirclement"], 5 * 1000)


class TestLeap(_Base):
    def test_a_leap_opens_a_two_way_gateway_paid_from_its_bank(self):
        rec = self.meet(_pick("leap"))
        self.assertEqual(rec["outcome"], "leap")
        from xylarium.kernel import gateways
        gate = gateways.stats(self.k)["gates"][-1]
        self.assertTrue(gate["two_way"])
        self.assertFalse(gate["court"])                                  # within the galaxy: kernel law only
        self.assertEqual(gateways.stats(self.k)["banks"]["civ:New"]["spent"], gateways.kindle_cost_j())
        b = settling.stats(self.k)["civ:New"]
        lp = b["leaps"][0]
        self.assertGreater(settling.held(self.k, "civ:New", lp["t"] + 1.0),
                           settling.held(self.k, "civ:New", lp["t"] - 1e-9))   # a second front, past the encloser


if __name__ == "__main__":
    unittest.main()
