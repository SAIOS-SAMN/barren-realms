"""
A crossed people's dominion is the systems it has settled: a bubble that grows as fast as its people can fill a world
and send the next party, holds only its own side where it meets another, and holds its home alone when it crosses
inside another's dominion.
"""
import math
import unittest
from types import SimpleNamespace
from unittest import mock

from xylarium.kernel import annals, settling


def _galaxy(places):
    """A kernel with only what settling reads: places in the galaxy and the annals' bubbles."""
    k = _K()
    k.__dict__.update(state={"annals": {"of": {}, "falls": 0, "wars": 0, "pacts": 0},
                               "cosmos": {"place": {str(s): {"r": r, "theta0": th} for s, (r, th) in places.items()}}},
                      sectors={}, cycle_count=0)
    return k


class _K:
    pass


def _bubble(k, who, sid, t0, hop=0.002, g=1e3, metab="biotic"):
    b = {"sid": sid, "metab": metab, "r0": float(k.state["cosmos"]["place"][str(sid)]["r"]), "crossed": t0, "t0": t0, "share": 1.0,
         "hop": hop, "g": g, "rmax": 30.0, "cuts": {}, "enclosed": None, "fell": None}
    b["v"] = hop * g
    settling.stats(k)[who] = b
    return b


class TestSystems(unittest.TestCase):
    def test_the_galaxy_holds_tens_of_billions_of_systems(self):
        self.assertTrue(3e10 < settling.galaxy_systems() < 3e11)          # the Milky Way's 1e11 stars, give or take

    def test_a_reach_past_every_star_holds_the_galaxy(self):
        self.assertGreater(settling.systems_in(8.0, 60.0), 0.97 * settling.galaxy_systems())

    def test_a_reach_wider_than_the_galaxy_holds_about_all_of_it(self):
        got = settling.systems_in(8.0, 40.0)
        self.assertTrue(0.5 * settling.galaxy_systems() < got <= settling.galaxy_systems(), got)

    def test_sphere_and_disc_meet_at_the_disc_thickness(self):
        h = settling.DISC_HALF_THICKNESS_PC / 1000.0
        lo, hi = settling.systems_in(8.0, h * 0.999), settling.systems_in(8.0, h * 1.001)
        self.assertLess(abs(hi - lo) / lo, 0.1)

    def test_a_core_home_reaches_more_systems_than_an_outer_one(self):
        self.assertGreater(settling.systems_in(1.0, 2.0), settling.systems_in(12.0, 2.0))


class TestPace(unittest.TestCase):
    def test_settle_rate_from_filling_a_world(self):
        # K = 1e7, N0 = 2e4 (the emigrant cap): one new world each ln(500) ~ 6.2 generations
        home = SimpleNamespace()
        import xylarium.kernel.biosphere as bio
        real = bio.carrying_capacity
        bio.carrying_capacity = lambda kernel, planet, *a, **kw: 1e7
        try:
            self.assertAlmostEqual(settling.settle_rate(None, home), 1.0 / math.log(500.0), places=6)
        finally:
            bio.carrying_capacity = real


@mock.patch("xylarium.kernel.history.event", lambda *a, **kw: {})
@mock.patch("xylarium.kernel.spheres.style", lambda *a, **kw: "federation")
class TestMeeting(unittest.TestCase):
    def test_two_bubbles_meet_where_their_fronts_come_in_step(self):
        k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.5)})
        _bubble(k, "civ:A", 1, 1.0)
        _bubble(k, "civ:B", 2, 1.0)
        tc, sa, sb, enc = settling.contact_time(k, "civ:A", "civ:B")
        d = 2 * 8.0 * math.sin(0.25)
        self.assertIsNone(enc)
        self.assertAlmostEqual(sa + sb, d, places=6)
        self.assertAlmostEqual(sa, sb, places=6)
        settling.meet(k, "civ:A", "civ:B", (tc, sa, sb, enc), [])
        later = tc + 1.0
        whole = settling.systems_in(8.0, settling.radius(settling.stats(k)["civ:A"], later))
        self.assertLess(settling.held(k, "civ:A", later), whole)

    def test_a_people_crossing_inside_another_holds_its_home(self):
        k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.01)})
        _bubble(k, "civ:Old", 1, 1.0)
        _bubble(k, "civ:New", 2, 1.5)
        when = settling.contact_time(k, "civ:Old", "civ:New")
        self.assertEqual(when[3], "civ:New")
        settling.meet(k, "civ:Old", "civ:New", when, [])
        self.assertEqual(settling.held(k, "civ:New", 1.6), 1.0)
        settling.fall(k, "civ:Old", 1.7)                       # its encloser falls: it grows from that day
        self.assertGreater(settling.held(k, "civ:New", 1.8), 1.0)

    def test_a_people_of_another_niche_settles_inside_anothers_dominion(self):
        k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.01)})
        _bubble(k, "civ:Old", 1, 1.0, metab="biotic")
        _bubble(k, "civ:Cold", 2, 1.5, metab="cryogenic")
        when = settling.contact_time(k, "civ:Old", "civ:Cold")
        settling.meet(k, "civ:Old", "civ:Cold", when, [])
        self.assertGreater(settling.held(k, "civ:Cold", 1.6), 1.0)     # it takes the worlds the Old cannot use

    def test_settled_before_waking_is_the_settlers(self):
        k = _galaxy({1: (8.0, 0.0), 3: (8.0, 0.001)})
        _bubble(k, "civ:Old", 1, 1.0)
        self.assertEqual(settling.settled_by(k, 3, 1.2), "civ:Old")
        self.assertEqual(settling.settled_by(k, 3, 1.2, "TERRESTRIAL"), "civ:Old")
        self.assertIsNone(settling.settled_by(k, 3, 1.2, "ICE"))           # not a world it can live on
        self.assertIsNone(settling.settled_by(k, 3, 0.9))


class TestHazard(unittest.TestCase):
    def test_hazard_and_its_inverse_agree(self):
        f, g = 2e-4, 0.16
        cap = lambda t: min(1e9, math.exp(min(50.0, 0.5 * g * t)))   # noqa: E731
        ran, until = annals._dominion_hazard(f, 1.0, 1e5, cap, g=g)
        self.assertIsNone(until)
        self.assertAlmostEqual(ran, 2 * f / g, delta=0.02 * ran)   # bound by a cap growing at g/2
        need = 0.5 * ran
        _, t = annals._dominion_hazard(f, 1.0, 1e5, cap, need, g=g)
        self.assertAlmostEqual(annals._dominion_hazard(f, 1.0, t, cap, g=g)[0], need, delta=1e-3 * need)

    def test_a_bound_dominion_runs_more_hazard(self):
        f, g = 2e-4, 0.16
        free = annals._dominion_hazard(f, 1.0, 1e4, lambda t: 1e30, g=g)[0]
        held = annals._dominion_hazard(f, 1.0, 1e4, lambda t: 10.0, g=g)[0]
        self.assertGreater(held, free)

    def test_a_people_that_does_not_grow_shares_its_fall_over_what_it_holds(self):
        self.assertAlmostEqual(annals._dominion_hazard(1e-3, 4.0, 100.0, lambda t: 4.0, g=0.0)[0], 0.025)


if __name__ == "__main__":
    unittest.main()


def _job(k, who, sid, t_start, t_end, gen=25.0, fall_rate=2e-4, e=1.0):
    """A crossed people's stretch from t_start to t_end (coordinate Gyr), as pass 1 hands it to pass 2."""
    gens = (t_end - t_start) * 1e9 / gen
    rec = k.state["annals"]["of"].setdefault(who, {"advanced": 0.0, "passed": ["crossed"], "dominion": 1, "reach": 0.0,
                                                   "hist": {"P": 0.0, "H": 0.0, "E": e, "W": 1.0, "rate": fall_rate}})
    return {"who": who, "home": SimpleNamespace(sector_id=sid), "rec": rec, "hist": rec["hist"], "gens": gens,
            "gen": gen, "fell": None, "cross": 0.0, "lapse": 1.0, "fall_rate": fall_rate,
            "epoch_of": lambda tt, t_start=t_start, gen=gen: t_start + tt * gen / 1e9}


@mock.patch("xylarium.kernel.history.event", lambda *a, **kw: {})
@mock.patch("xylarium.kernel.spheres.style", lambda *a, **kw: "federation")
class TestOneClock(unittest.TestCase):
    """What the dominions do is the same however deep time is cut - one stretch or many."""

    G = 6.4e6                                           # 0.16 a generation at 25-year generations, per Gyr

    def _galaxy_of_four(self):
        k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.6), 3: (6.0, 2.0), 4: (8.0, 0.003)})
        _bubble(k, "civ:A", 1, 1.0000, g=self.G)
        _bubble(k, "civ:B", 2, 1.0001, g=self.G)
        _bubble(k, "civ:C", 3, 1.0002, g=self.G)
        _bubble(k, "civ:D", 4, 1.0010, g=self.G)        # crosses inside A's dominion
        return k

    def _run(self, cuts):
        from xylarium.kernel import annals
        k = self._galaxy_of_four()
        starts = {"civ:A": 1.0, "civ:B": 1.0001, "civ:C": 1.0002, "civ:D": 1.001}
        e = {"civ:A": 1.0, "civ:B": 1e-6, "civ:C": 1.0, "civ:D": 1.0}           # B's hazard comes due young
        for a, b in zip(cuts, cuts[1:]):
            jobs = [_job(k, w, s, max(a, starts[w]), b, e=e[w])
                    for w, s in (("civ:A", 1), ("civ:B", 2), ("civ:C", 3), ("civ:D", 4))
                    if b > starts[w] and settling.stats(k)[w]["fell"] is None]
            annals._settle(k, jobs, [])
        st = settling.stats(k)
        return {w: (sorted((c["by"], round(c["t"], 9), c["a"] and round(c["a"], 9)) for c in b["cuts"].values()),
                    b["enclosed"] and (b["enclosed"]["by"], round(b["enclosed"]["t"], 9)),
                    b["fell"] and round(b["fell"], 7), round(k.state["annals"]["of"][w]["hist"]["H"], 6))
                for w, b in st.items()}

    def test_one_stretch_or_many(self):
        whole = self._run([1.0, 2.0])
        cut = self._run([1.0, 1.00005, 1.00015, 1.0004, 1.0011, 1.003, 2.0])
        self.assertEqual(whole, cut)
        self.assertIsNotNone(whole["civ:B"][2])                   # B fell...
        self.assertEqual(whole["civ:D"][1][0], "civ:A")          # ...and D crossed inside A's dominion
