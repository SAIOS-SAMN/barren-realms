"""
The three seats of a new universe: a Captain berthed at Tradewards, a Steward ruling its own polity, a Progenitor
waking as one of the first minds - and a progress screen for each, read from what the laws keep.
"""

import asyncio
import builtins
import random
import unittest

from xylarium.kernel import ages, roles
from xylarium.kernel.models import ActionType


class TestCaptainSeat(unittest.TestCase):
    def test_a_captain_berths_at_the_densest_cluster_of_docks(self):
        random.seed(3)
        k = roles.start_captain(42, "Tester")
        tw = roles.tradewards(k)
        self.assertEqual(k.get_player("player_1").sector_id, tw["sector"])
        self.assertIsNotNone(k.sectors[tw["sector"]].port)
        self.assertGreater(tw["docks"], 1)
        self.assertEqual(roles.role_of(k, "player_1"), "captain")
        p = roles.progress(k, "player_1")
        self.assertEqual(p["role"], "captain")
        self.assertIn("History reads", roles.render_progress(p))


class TestStewardSeat(unittest.TestCase):
    def setUp(self):
        random.seed(3)
        self.k = roles.start_steward(42, "Ruler", pick=0, rule="throne", gauges={"levy": 0.2}, natal="propagation")
        self.realm = roles.stats(self.k)["realms"]["player_1"]

    def test_a_ruler_governs_every_world_of_its_polity_and_sets_how_it_is_ruled(self):
        for wid in self.realm["worlds"]:
            w = self.k.get_planet(wid)
            self.assertEqual(w.owner_id, "player_1")
            self.assertEqual(w.society["rent"], 0.5)
            self.assertTrue(w.society["rent_set"])
        cap = self.k.get_planet(self.realm["capital"])
        self.assertEqual(self.k.get_player("player_1").sector_id, cap.sector_id)

    def test_its_worlds_answer_to_it(self):
        cap = self.k.get_planet(self.realm["capital"])
        cap.treasury = 10 ** 6
        res = self.k.dispatch("player_1", ActionType.PLANET_BUILD_SHIELD, planet_id=cap.id, amount=10)
        msg = (res.message or "").lower()
        self.assertTrue(res.success or "capacity" in msg, msg)        # accepted, or refused only at its own limits
        self.assertNotIn("you do not", msg)                           # never refused as another's world
        p = roles.progress(self.k, "player_1")
        self.assertEqual(p["role"], "steward")
        self.assertEqual(p["rule"], "throne")
        self.assertGreaterEqual(p["worlds"], 1)

    def test_its_set_take_holds_until_its_order_falls(self):
        from xylarium.kernel import rent
        cap = self.k.get_planet(self.realm["capital"])
        rent.season(self.k, cap, 1.0, 1.0)                      # a generation passes: the council does not reset it
        self.assertEqual(rent.of(cap), 0.5)
        rent.overturned(self.k, cap)
        self.assertEqual(rent.of(cap), 0.0)
        self.assertNotIn("rent_set", cap.society)


class TestProgenitorSeat(unittest.TestCase):
    def test_a_progenitor_wakes_as_one_of_the_first_minds(self):
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=1, pace="teeming")
        self.assertIsNotNone(k)
        rec = roles.stats(k)["ancients"]["player_1"]
        self.assertEqual(rec["index"], 1)
        home = ages.homeworld(k, "player_1")
        self.assertIsNotNone(home)
        self.assertIsNotNone(home.civilization)
        self.assertEqual(roles.role_of(k, "player_1"), "progenitor")
        self.assertIsNotNone(ages.shape(k, "player_1", {"tolerance": 0.2}))   # at its own dawn it can be shaped
        self.assertIn("young worlds", ages.act(k, "player_1", "seed"))
        p = roles.progress(k, "player_1")
        self.assertEqual(p["role"], "progenitor")
        self.assertIn("minds_arisen", p)

    def test_the_ancients_are_the_universes_first_minds(self):
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=7, genesis="cosmic:neighbourly")
        k.activate()
        anc = roles.ancients(k)
        self.assertEqual(len(anc), roles.ANCIENTS)
        self.assertEqual([a["dawn_gyr"] for a in anc], sorted(a["dawn_gyr"] for a in anc))


class TestOpeningMenu(unittest.TestCase):
    def test_the_opening_offers_the_three_seats(self):
        from xylarium.client import roles as roles_ui
        real = builtins.input
        try:
            for raw, want in (("1", "progenitor"), ("2", "steward"), ("3", "captain"), ("4", roles_ui.EARLIER),
                              ("", "captain")):
                builtins.input = lambda *_a, r=raw: r
                self.assertEqual(roles_ui.choose_role(), want)
        finally:
            builtins.input = real


class TestBridgeSeats(unittest.TestCase):
    def test_a_remote_player_takes_a_seat(self):
        from bridge.websocket_server import WebSocketGateway
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=999)
        gw = WebSocketGateway(k, host="127.0.0.1", port=0)
        sent = []

        class Client:
            player_id = None

            async def send_json(self, data):
                sent.append(data)
        c = Client()
        asyncio.run(gw._process_client_message(c, {"action": "ROLES"}))
        self.assertEqual([r["key"] for r in sent[-1]["roles"]], list(roles.KEYS))
        asyncio.run(gw._process_client_message(c, {"action": "REGISTER", "name": "Remote Ruler", "role": "steward",
                                                   "rule": "commonwealth"}))
        self.assertEqual(sent[-1]["seat"]["role"], "steward")
        asyncio.run(gw._process_client_message(Client(), {"action": "REGISTER", "name": "Remote Pilot"}))
        self.assertEqual(sent[-1]["seat"]["role"], "captain")
        asyncio.run(gw._process_client_message(Client(), {"action": "REGISTER", "name": "Elder", "role": "progenitor"}))
        self.assertEqual(sent[-1]["status"], "error")


if __name__ == "__main__":
    unittest.main()


class TestPlaytestFixes(unittest.TestCase):
    def test_a_captains_net_worth_counts_every_money_and_profit_is_reported_in_one(self):
        random.seed(11)
        from xylarium.kernel import fx
        k = roles.start_captain(42, "Vex")
        cap = k.get_player("player_1")
        nw0 = fx.net_worth(cap, k.fx_market)["total"]
        self.assertAlmostEqual(nw0, cap.credits, delta=1)
        cap.fx_wallet["VOID"] = 3500
        self.assertGreater(fx.net_worth(cap, k.fx_market)["total"], nw0 + 500)    # foreign money counts
        self.assertIn("net_worth", k.get_player_view("player_1")["fx"])
        res = k.dispatch("player_1", ActionType.TRADE, type="BUY", commodity="ORE", amount=5)
        if res.success:
            self.assertNotIn(" Cr", res.message.split("(sales")[0])                # the port's own money, named

    def test_a_ruler_pays_from_its_realms_treasury_and_its_people_keep_their_history(self):
        random.seed(5)
        from xylarium.kernel import alignment, sustenance
        k = roles.start_steward(42, "Queen", pick=1, rule="council")
        realm = roles.stats(k)["realms"]["player_1"]
        cap = k.get_planet(realm["capital"])
        me = k.get_player("player_1")
        cap.treasury, purse = 20000, me.credits
        res = k.dispatch("player_1", ActionType.PLANET_UPGRADE_CITADEL, planet_id=cap.id)
        self.assertTrue(res.success, res.message)
        self.assertLess(cap.treasury, 20000)
        self.assertEqual(me.credits, purse)                                         # the realm paid, not the ruler
        before = cap.civilization.light
        sustenance.flow_civ(cap, light=10, why="work")
        self.assertGreater(cap.civilization.light, before)                         # a ruled world's deeds are its people's


class TestRealmDashboard(unittest.TestCase):
    def test_a_ruler_sees_its_realm_and_can_change_how_it_is_governed(self):
        random.seed(5)
        k = roles.start_steward(42, "Queen", pick=0, rule="throne")
        r = roles.realm(k, "player_1")
        self.assertEqual(len(r["worlds"]), len(roles.stats(k)["realms"]["player_1"]["worlds"]))
        for w in r["worlds"]:
            self.assertGreaterEqual(w["bearable"], 0.0)
            self.assertGreaterEqual(w["room"], 0)
        self.assertIn(r["stage"], ("forage", "farm", "state", "works", "yards", "crossed"))
        self.assertIn("REALM OF THE", roles.render_realm(r))
        self.assertIn("Commonwealth", roles.set_take(k, "player_1", "commonwealth"))
        self.assertTrue(all(w["rent"] == 0.0 for w in roles.realm(k, "player_1")["worlds"]))
        self.assertIsNone(roles.realm(k, "nobody"))


class TestDeepTime(unittest.TestCase):
    def test_a_progenitor_looks_away_and_the_galaxy_lives_an_age_in_a_few_clock_years(self):
        from xylarium.kernel import clocks, cosmos, knowledge
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        who = knowledge.holder_of_planet(ages.homeworld(k, "player_1"))
        mine0, galaxy0, cyc0 = clocks.now(k, who), cosmos.deep_gyr(k), k.cycle_count
        lines = ages.sleep(k, "player_1", 1e6)
        self.assertIn("years of your people's own time pass", lines[0])
        self.assertGreaterEqual((clocks.now(k, who) - mine0) * 1e9, 1e6 * 0.99)      # its own time: the whole span
        self.assertGreater((cosmos.deep_gyr(k) - galaxy0) * 1e9, 5e5)                 # the galaxy moved with it
        self.assertLessEqual(k.cycle_count - cyc0, ages.SLEEP_YEARS * 100)
        self.assertIsNone(clocks.away(k, who))                                      # it has looked back
        self.assertIsNone(clocks.away_pace(k))


class TestDeepTimeSafety(unittest.TestCase):
    def test_a_payment_into_a_money_no_exchange_lists_is_held_not_lost(self):
        from xylarium.kernel.fx import FXMarket
        m = FXMarket()
        out, venue = m.convert("SOL", "NOPE", 1000)
        self.assertEqual((out, venue), (0, "unsettled"))
        self.assertEqual(m.unsettled["SOL"], 1000)
        self.assertFalse(m.can_convert("SOL", "NOPE"))

    def test_a_steward_follows_its_people_when_its_world_is_lost(self):
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        home = ages.homeworld(k, "player_1")
        other = next(p for s in k.sectors.values() for p in s.planets if p is not home and p.population == 0)
        other.civilization, other.population = home.civilization, 500
        home.population = 0
        self.assertIs(ages.homeworld(k, "player_1"), other)


class TestZones(unittest.TestCase):
    def test_zones_hold_the_living_and_the_ports_and_the_sky_is_the_same_read_or_stepped(self):
        from xylarium.kernel import physics, zones
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        from xylarium.kernel import cosmos
        home = ages.homeworld(k, "player_1")
        for nb in cosmos.neighbours_now(k, cosmos.cell_of_sector(k, home.sector_id)):
            cosmos.materialise(k, nb, "a test looks further")  # empty space beyond the people's own system
        k.tick_simulation()
        for sid, sec in k.sectors.items():
            living = any(p.population > 0 or p.owner_id for p in sec.planets)
            self.assertEqual(sid in zones.peopled(k), living)
            self.assertEqual(sid in zones.watched(k), living or sec.port is not None)
        far = next(p for sid, s in k.sectors.items() if sid not in zones.watched(k) for p in s.planets
                   if getattr(p, "body", None))
        am = k.astronomy_manager
        self.assertAlmostEqual(am.angle_now(far),
                               physics.orbital_angle(k.sectors[far.sector_id], far, am.cycle_count))

    def test_a_dying_sun_is_held_to_its_frame_while_other_places_run_the_span(self):
        from xylarium.kernel import clocks, cosmos, knowledge, tempo, zones
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        who = knowledge.holder_of_planet(ages.homeworld(k, "player_1"))
        clocks.look_away(k, who, 1e9)
        for key in clocks.stats(k)["places"]:
            sid = int(key)
            pace = clocks.place_pace(k, sid)
            life = cosmos.star_life(k, sid)
            if pace is None or life is None:
                continue
            ahead = (life[1] - cosmos.deep_gyr(k, sector_id=sid)) * 1e9
            if sid in zones.peopled(k) and 0 < ahead < 1e9:
                self.assertLessEqual(pace, ahead / tempo.FRAMES * 1.0001)   # its people get their seasons
            elif sid not in zones.peopled(k):
                self.assertGreater(pace, 1e8)                              # nothing to watch: the span runs on
