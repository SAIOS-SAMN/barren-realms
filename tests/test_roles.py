"""
The three seats of a new universe: a Captain berthed at Tradewards, a Steward ruling its own polity, a Progenitor
waking as one of the first minds - and a progress screen for each, read from what the laws keep.
"""

import asyncio
import builtins
import random
import unittest
from unittest import mock

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
        self.assertEqual(p["role"], "sovereign")
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
        self.assertEqual(rec["index"], min(1, len(roles.ancients(k)) - 1))   # the one asked for, or the last arisen
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
        self.assertTrue(anc)                                      # the seed's own number of them
        self.assertEqual([a["dawn_gyr"] for a in anc], sorted(a["dawn_gyr"] for a in anc))
        from xylarium.kernel import cosmos
        for a in anc:                                             # each on the core's first set of stars
            self.assertLess(cosmos.ring_radius(a["ring"]), cosmos.R_BULGE_KPC)
            self.assertTrue(cosmos.first_generation(k, tuple(a["cell"]), a["k"]))


class TestOpeningMenu(unittest.TestCase):
    def test_the_opening_offers_the_three_seats(self):
        from xylarium.client import roles as roles_ui
        real = builtins.input
        try:
            for raw, want in (("1", "progenitor"), ("2", "steward"), ("3", "sovereign"), ("4", "captain"),
                              ("5", roles_ui.EARLIER), ("", "captain")):
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
        asyncio.run(gw._process_client_message(c, {"action": "REGISTER", "name": "Remote Ruler", "role": "sovereign",
                                                   "rule": "commonwealth"}))
        self.assertEqual(sent[-1]["seat"]["role"], "sovereign")
        from xylarium.kernel import stewardship
        asyncio.run(gw._process_client_message(Client(), {"action": "REGISTER", "name": "Keeper", "role": "steward",
                                                          "realm": stewardship.realms(k)[0]}))
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


class TestHistoryStreams(unittest.TestCase):
    def _people(self):
        from xylarium.kernel import annals, knowledge
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        who = knowledge.holder_of_planet(ages.homeworld(k, "player_1"))
        k.cycle_count -= k.cycle_count % 100                 # an annals season
        annals.season(k)                                     # its record begins
        return k, who, annals.stats(k)["of"][who]

    def test_however_its_time_is_cut_a_people_lives_the_same_history(self):
        from xylarium.kernel import annals
        k1, who1, rec1 = self._people()
        rec1["advanced"] -= 2e5
        annals.season(k1)                                    # one stretch of 200,000 years
        k2, who2, rec2 = self._people()
        for _ in range(10):
            rec2["advanced"] -= 2e4
            annals.season(k2)                                # ten stretches of 20,000
        self.assertEqual(who1, who2)
        self.assertEqual(rec1["passed"], rec2["passed"])
        self.assertAlmostEqual(rec1["hist"]["P"], rec2["hist"]["P"], places=6)
        self.assertAlmostEqual(rec1["hist"]["H"], rec2["hist"]["H"], places=6)
        self.assertEqual(rec1["hist"]["T"], rec2["hist"]["T"])


class TestInverseCompaction(unittest.TestCase):
    """The realm held folded: a folded world caught up is exactly the world that was stepped."""

    def _run(self, all_open):
        from xylarium.kernel import cosmos, geology, zones
        zones.ALL_OPEN = all_open
        try:
            random.seed(3)
            k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
            home = ages.homeworld(k, "player_1")
            for nb in cosmos.neighbours_now(k, cosmos.cell_of_sector(k, home.sector_id)):
                cosmos.materialise(k, nb, "a test looks further")
            for _ in range(4 * 25):
                k.tick_simulation()
            folded = sum(1 for sid in k.sectors if zones.level(k, sid) < zones.WORLD)
            zones.settle_all(k)
        finally:
            zones.ALL_OPEN = False
        return ({p.id: dict(p.element_deposits) for s in k.sectors.values() for p in s.planets},
                dict(geology.stats(k)), dict(k.matter.sources), folded)

    @unittest.expectedFailure    # task #149: place clocks run at a pace set by who watches, so a star near a folded
    # world dies at another cycle than near a stepped one; pace must come from the place's galactic position alone
    def test_a_folded_world_caught_up_is_the_world_that_was_stepped(self):
        stepped, folded = self._run(True), self._run(False)
        self.assertGreater(folded[3], 10)                          # most of the charted realm was held folded
        self.assertEqual(stepped[0], folded[0])
        self.assertEqual(stepped[1], folded[1])
        self.assertEqual(stepped[2], folded[2])

    def test_each_seat_holds_open_what_its_office_reaches(self):
        from xylarium.kernel import zones
        self.assertLess(zones.ASPECT["progenitor"].get(zones.WORLD, 0), zones.ASPECT["sovereign"][zones.WORLD])
        self.assertIn(zones.SURFACE, zones.ASPECT["sovereign"])
        self.assertNotIn(zones.SURFACE, zones.ASPECT["progenitor"])
        random.seed(5)
        k = roles.start_steward(42, "Queen", pick=0, rule="council")
        realm = roles.stats(k)["realms"]["player_1"]
        for wid in realm["worlds"]:
            self.assertGreaterEqual(zones.level(k, k.get_planet(wid).sector_id), zones.SURFACE)


class TestWhoDecidesTurnings(unittest.TestCase):
    def test_an_unguided_people_turns_by_its_history_and_a_guided_one_by_its_councils(self):
        from xylarium.kernel import annals, knowledge, ways
        random.seed(3)
        k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        home = ages.homeworld(k, "player_1")
        mine = knowledge.holder_of_planet(home)
        self.assertTrue(annals.guided(k, mine))                      # the progenitor's people: its councils choose
        self.assertFalse(annals.history_decides(k, mine))
        self.assertTrue(annals.guided(k, "captain:someone"))          # a holding answers to its holder
        ages.stats(k)["stewards"].pop("player_1")                    # the seat leaves: its people is unguided
        self.assertTrue(annals.history_decides(k, mine))
        home.society["way"] = "forage"
        home.society["crop_z"] = 50.0                                 # a council would sow at once...
        ways.quarter(k)
        self.assertEqual(home.society["way"], "forage")               # ...but its history has not come to it

    def test_in_a_settled_universe_councils_choose_as_ever(self):
        from xylarium.kernel import annals
        random.seed(5)
        k = roles.start_steward(42, "Queen", pick=0, rule="council")
        self.assertFalse(annals.history_decides(k, "civ:anyone"))


class TestTiersAndOffices(unittest.TestCase):
    def test_offices_are_the_sovereigns_specializations_and_each_sees_as_its_office_does(self):
        from xylarium.kernel import zones
        self.assertEqual([o["tier"] for o in roles.OFFICES], ["T4", "T5", "T6", "T7", "T8", "T9"])
        random.seed(3)
        k = roles.start_captain(42, "Spy", office="intelligence")
        self.assertEqual(roles.tier_of(k, "player_1"), "T8")
        self.assertEqual(roles.office_of(k, "player_1")["name"], "Intelligence")
        p = roles.progress(k, "player_1")
        self.assertIn("INTELLIGENCE (T8)", roles.render_progress(p))
        here = k.get_player("player_1").sector_id
        two = zones._ring(k, [here], 2) - zones._ring(k, [here], 1)
        if two:
            self.assertTrue(any(zones.open_at(k, s) for s in two))      # it sees a lane further than a trader


class TestPress(unittest.TestCase):
    def _e(self, i, kind, who="civ:Aru", mag=0, cause="", title=None):
        return {"id": f"H-{i:06d}", "cycle": i * 100, "year": float(i), "kind": kind, "title": title or kind.title(),
                "actors": [who], "magnitude": mag, "cause": cause, "age": "the long age"}

    def test_a_records_shape_makes_its_genre(self):
        from xylarium.kernel import press
        rise_fall = [self._e(1, "FARMING"), self._e(2, "STATEHOOD"), self._e(3, "ASCENT", mag=10 ** 6),
                     self._e(4, "STRIFE", mag=10 ** 6, cause="40% would rise"),
                     self._e(5, "ABANDONED", mag=10 ** 6, cause="could have carried them and did not")]
        self.assertEqual(press.genre(rise_fall)["genre"], "tragedy")
        fall_rescue = [self._e(1, "FARMING"), self._e(2, "EPIDEMIC", mag=10 ** 5), self._e(3, "PERISHED", mag=10 ** 5),
                       self._e(4, "RESCUE", mag=10 ** 5), self._e(5, "PACT"), self._e(6, "ERA")]
        self.assertEqual(press.genre(fall_rescue)["genre"], "comedy")
        found = [self._e(i, k) for i, k in enumerate(("FIRST", "CAPABILITY", "PROVEN", "FIRST_SIGNAL"), 1)]
        self.assertEqual(press.genre(found)["genre"], "science fact")
        told = [self._e(i, "MYTH") for i in range(1, 5)]
        self.assertEqual(press.genre(told)["genre"], "science fiction")

    def test_every_line_of_a_published_volume_cites_the_record(self):
        import tempfile, os, re
        from xylarium.kernel import press
        evs = [self._e(i, k) for i, k in enumerate(("FARMING", "STATEHOOD", "FIRST", "MYTH", "PACT"), 1)]
        with tempfile.TemporaryDirectory() as d:
            cat = press.publish(evs, d, "Test Annals")
            self.assertEqual([c["volume"] for c in cat], ["Aru"])
            book = open(os.path.join(d, cat[0]["file"])).read()
            for line in book.splitlines():
                if line.startswith("- "):
                    self.assertTrue(re.search(r"\[H-\d{6}", line), line)
            self.assertIn("Aru", open(os.path.join(d, "index.md")).read())


class TestFoldedPeoples(unittest.TestCase):
    def setUp(self):
        from xylarium.kernel import relations, zones
        random.seed(5)
        self.k = roles.start_progenitor(7, "Elder", pick=0, pace="neighbourly")
        ages.sleep(self.k, "player_1", 1e9)                      # a galaxy of peoples
        self.folded = sorted(zones.folded_peoples(self.k))
        self.by = relations._peoples(self.k)

    def test_peoples_no_seat_reaches_are_folded_and_the_engines_laws_do_not_see_them(self):
        from xylarium.kernel import zones
        self.assertTrue(self.folded)
        who = next(w for w in self.folded if w in self.by)
        world = self.by[who][0]
        sec = self.k.sectors[world.sector_id]
        before = list(sec.planets)
        with zones.hidden(self.k):
            self.assertNotIn(world, sec.planets)                 # off the map the engine's laws walk
        self.assertEqual(sec.planets, before)                     # put back as it was, in its place
        self.assertIs(sec.planets[before.index(world)], world)
        self.assertEqual(ColonyStub.tick(self.k, world), {})      # its colony is not ticked

    def test_a_seat_coming_near_unfolds_a_people(self):
        from xylarium.kernel import zones
        who = next(w for w in self.folded if w in self.by)
        world = self.by[who][0]
        self.k.register_player("player_9", "Visitor")
        roles.seat_captain(self.k, "player_9", "intelligence")
        roles.place(self.k, "player_9", world.sector_id)
        self.k.caches.pop("zones", None)                          # the next quarter reads the realm afresh
        self.assertNotIn(who, zones.folded_peoples(self.k))
        self.assertFalse(zones.is_folded(self.k, world))


class ColonyStub:
    @staticmethod
    def tick(kernel, planet):
        from xylarium.kernel.colony import ColonyManager
        return ColonyManager.tick_colony(planet, kernel=kernel)


class TestStewardship(unittest.TestCase):
    def setUp(self):
        from xylarium.kernel import stewardship
        random.seed(5)
        self.k = roles.start_sovereign(42, "Queen", pick=0, rule="council")
        self.st = stewardship
        self.realm = next(r for r in stewardship.realms(self.k) if len(stewardship.peoples_of(self.k, r)) >= 2)
        self.peoples = sorted(stewardship.peoples_of(self.k, self.realm))

    def test_realms_are_held_by_first_arrival_and_move_only_by_war(self):
        from xylarium.kernel import realmwars, spheres
        seen = {}
        for r in self.st.realms(self.k):
            for sid in spheres.stats(self.k)["realms"][r]["sectors"]:
                self.assertEqual(self.st.realm_of(self.k, sid), r)
                seen[sid] = r
            self.assertTrue(spheres.crossed(self.k, spheres.presence(self.k, r)))   # only those who fold space
        self.assertTrue(seen)
        for _ in range(2 * 100):
            self.k.tick_simulation()                                            # the networks grow
        self.assertGreaterEqual(len(spheres.stats(self.k)["owner"]), len(seen))
        taken = {w.get("sector") for w in realmwars.stats(self.k)["wars"].values()}
        lapsed = {w for w, n in spheres.stats(self.k)["nets"].items() if not n["held"]}
        for sid, r in seen.items():
            now = self.st.realm_of(self.k, sid)
            if now != r:                                                        # by war - or its people fell
                self.assertTrue(sid in taken or spheres.presence(self.k, r) in lapsed)

    def test_a_stewards_ceasefire_binds_raids_holds_and_a_sovereigns_guns(self):
        from xylarium.kernel import relations
        self.st.seat_steward(self.k, "player_7", "Keeper", self.realm)
        self.assertEqual(roles.role_of(self.k, "player_7"), "steward")
        self.assertEqual(roles.tier_of(self.k, "player_7"), "T2")
        a, b = self.peoples[:2]
        res = self.st.rule(self.k, "player_7", "ceasefire", a, b)
        self.assertTrue(res["ok"])
        self.assertFalse(res["appealed"])
        self.assertIsNotNone(self.st.binds(self.k, a, b))
        self.assertIsNotNone(self.st.binds(self.k, b, a))
        by = relations._peoples(self.k)
        self.assertIsNone(relations.offer(self.k, a, b, by))                        # no hold across a ruling
        o = self.st.overview(self.k, self.realm)
        self.assertTrue(any(r["id"] == res["ruling"]["id"] for r in o["rulings"]))
        self.assertIn("Rulings", self.st.render(o))

    def test_what_reaches_beyond_a_realm_goes_up_and_a_progenitor_seals_it(self):
        self.st.seat_steward(self.k, "player_7", "Keeper", self.realm)
        other = next(r for r in self.st.realms(self.k) if r != self.realm and self.st.peoples_of(self.k, r))
        far = sorted(self.st.peoples_of(self.k, other))[0]
        res = self.st.rule(self.k, "player_7", "ceasefire", self.peoples[0], far)
        self.assertTrue(res["appealed"])
        self.assertIsNone(self.st.binds(self.k, self.peoples[0], far))           # not yet: it waits on the progenitors
        rid = res["ruling"]["id"]
        self.assertFalse(self.st.seal(self.k, "player_1", rid)["ok"])            # a sovereign cannot seal
        roles.stats(self.k)["of"]["player_0"] = "progenitor"
        self.assertTrue(self.st.seal(self.k, "player_0", rid)["ok"])
        rec = self.st.binds(self.k, self.peoples[0], far)
        self.assertTrue(rec["sealed"])
        self.k.cycle_count += self.st.span_cycles(self.k, self.realm) + 500
        self.assertIsNotNone(self.st.binds(self.k, self.peoples[0], far))       # sealed: it stands for good


class TestSovereignMinds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(12 * 100):
            cls.k.tick_simulation()                           # twelve years of a settled galaxy

    def test_every_polity_has_a_sovereign_and_peoples_can_have_many(self):
        from xylarium.kernel import polity
        live = [s for s in polity.sovereigns(self.k).values() if not s.get("ended")]
        self.assertEqual(len(live), len(polity._polities(self.k)))
        for s in live:
            self.assertTrue(s["people"].startswith(("civ:", "captain:")))
            self.assertIn(s["realm"], polity._polities(self.k))

    def test_sovereigns_meet_and_treaties_serve_both_sides(self):
        from xylarium.kernel import history, polity
        kinds = {e["kind"] for e in history.stats(self.k)["recent"]}
        self.assertIn("SOVEREIGNS_MEET", kinds)
        ts = list(polity.stats(self.k)["treaties"].values())
        self.assertTrue(ts)
        for t in ts:
            self.assertIn(t["kind"], polity.TREATIES)
            a, b = polity.sovereigns(self.k)[t["a"]], polity.sovereigns(self.k)[t["b"]]
            self.assertIn(t["b"], a["books"])                   # both keep the other in their conduct books
            self.assertIn(t["a"], b["books"])

    def test_a_sovereigns_line_goes_on(self):
        from xylarium.kernel import polity
        s = next(iter(polity.sovereigns(self.k).values()))
        crystals, line = dict(s["mind"]["crystals"]), s["line"]
        polity._succeed(self.k, s)
        self.assertEqual(s["line"], line)
        self.assertEqual(s["mind"]["crystals"], crystals)       # the chronicle inherited, never edited
        self.assertGreaterEqual(s["generation"], 2)

    def test_the_realms_own_stewards_rule_and_keep_their_lines(self):
        from xylarium.kernel import stewardship
        minds = stewardship.stats(self.k)["minds"]
        self.assertLessEqual(set(stewardship.realms(self.k)), set(minds))     # every held realm has its steward
        rulings = list(stewardship.stats(self.k)["rulings"].values())
        for r in rulings:
            self.assertIn(r["kind"], stewardship.RULINGS)
        pairs = [frozenset((r["a"], r["b"])) | {r["kind"]} for r in stewardship.stats(self.k)["appeals"]]
        self.assertEqual(len(pairs), len(set(pairs)))           # each dispute goes up once


class TestRealmOverTheBridge(unittest.TestCase):
    def test_a_remote_steward_reads_its_realm_and_rules(self):
        from bridge.websocket_server import WebSocketGateway
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=42)
        gw = WebSocketGateway(k, host="127.0.0.1", port=0)
        sent = []

        class Client:
            player_id = None

            async def send_json(self, data):
                sent.append(data)
        c = Client()
        from xylarium.kernel import stewardship
        realm = next(r for r in stewardship.realms(k) if len(stewardship.peoples_of(k, r)) >= 2)
        asyncio.run(gw._process_client_message(c, {"action": "REGISTER", "name": "Keeper", "role": "steward",
                                                   "realm": realm}))
        c.player_id = sent[-1].get("player_id") or next(pid for pid, r in roles.stats(k)["of"].items() if r == "steward")
        asyncio.run(gw._process_client_message(c, {"action": "REALM"}))
        self.assertEqual(sent[-1]["realm"]["realm"], realm)
        peoples = [r["people"] for r in sent[-1]["realm"]["peoples"]]
        asyncio.run(gw._process_client_message(c, {"action": "RULE", "kind": "ceasefire", "a": peoples[0],
                                                   "b": peoples[1]}))
        self.assertEqual(sent[-1]["status"], "ok")
        asyncio.run(gw._process_client_message(c, {"action": "SOVEREIGNS"}))
        self.assertIn("sovereigns", sent[-1])


class TestStewardBooks(unittest.TestCase):
    def test_a_steward_measures_its_realm_in_books_and_its_rulings_are_its_memory(self):
        from xylarium.kernel import mindcore as mc, stewardship
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        k = GameKernel(seed=42)
        for _ in range(7 * 100):
            k.tick_simulation()
        ruled_before = sum(m["ruled"] for m in stewardship.stats(k)["envoys"].values())
        for _ in range(100):                                   # a year for what was ruled to be measured
            k.tick_simulation()
        for realm in stewardship.realms(k):
            res = stewardship.books(k, realm)
            for (site, book), v in res.items():
                self.assertIn(book, stewardship.STEWARD_BOOKS)
                self.assertIsInstance(v, mc.Fraction)
            m = stewardship.mind(k, realm)
            self.assertIn("mind", m)
        envoys = list(stewardship.stats(k)["envoys"].values())
        ruled = sum(m["ruled"] for m in envoys)
        learned = sum(len(m["mind"]["crystals"]) + len(m["mind"]["walls"]) for m in envoys)
        if ruled_before:
            self.assertGreater(learned, 0)                     # what its rulings did, measured since, is its memory
        elif ruled:
            pass                                               # ruled only this year: not yet measured
        else:                                                  # a quiet realm: nothing a ruling could answer
            for realm in stewardship.realms(k):
                for (site, book), v in stewardship.books(k, realm).items():
                    if v > 0:
                        self.assertEqual(book, "power")
                        self.assertIsNone(stewardship._victim(k, site, realm))


class TestEnvoys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(2 * 100):
            cls.k.tick_simulation()

    def test_a_realms_stewards_are_its_networks_people_and_its_federation_partners(self):
        from fractions import Fraction
        from xylarium.kernel import spheres, stewardship
        env = stewardship.stats(self.k)["envoys"]
        self.assertTrue(env)
        for key, e in env.items():
            self.assertEqual(key, f"{e['sender']}@{e['realm']}")    # one per sender per realm
            self.assertIn(e["sender"], stewardship.senders_of(self.k, e["realm"]))
            self.assertEqual(set(e["authority"]), {"granted", "earned", "grown", "taken"})
        for realm in stewardship.realms(self.k):
            senior = stewardship.mind(self.k, realm)
            self.assertEqual(senior["sender"], spheres.presence(self.k, realm))   # the network's own steward first
            self.assertEqual(Fraction(senior["authority"]["granted"]), 1)
        for b in spheres.stats(self.k)["bonds"].values():
            if b["kind"] == "federation":                           # partners keep stewards in each other's realms
                for r in stewardship.realms(self.k):
                    if spheres.presence(self.k, r) == b["a"]:
                        self.assertIn(b["b"], stewardship.senders_of(self.k, r))

    def test_a_terms_span_is_its_senders_generation(self):
        from xylarium.kernel import spheres, stewardship
        for r in stewardship.realms(self.k):
            who = spheres.presence(self.k, r)
            self.assertAlmostEqual(stewardship.term_years(self.k, r),
                                   spheres.stats(self.k)["nets"][who]["gen"])   # one clock on the settled board

    def test_a_steward_whose_people_fell_keeps_only_what_it_earned_and_grew(self):
        from fractions import Fraction
        from xylarium.kernel import stewardship
        rec = {"sender": "civ:Gone", "since": self.k.cycle_count - 250,
               "mind": {"crystals": {"a|b|+": {"deed": "pact", "delivers": "3"}}}}
        stewardship._authority(self.k, rec, {})
        self.assertEqual(rec["authority"]["granted"], "0")
        self.assertEqual(Fraction(rec["authority"]["earned"]), 3)
        self.assertEqual(Fraction(rec["authority"]["grown"]), Fraction(5, 2))


class TestDynasties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(4 * 100):
            cls.k.tick_simulation()

    def test_houses_emerge_from_lines_that_outgrow_one_reign(self):
        from fractions import Fraction
        from xylarium.kernel import dynasties, polity, stewardship, spheres
        hs = dynasties.standing(self.k)
        self.assertTrue(hs)
        for line, h in hs.items():
            a = h["authority"]
            self.assertEqual(set(a), {"granted", "earned", "grown", "taken"})
            self.assertTrue(Fraction(a["grown"]) > 1 or Fraction(a["taken"]) or Fraction(a["granted"]))
            self.assertIn(h["realm"], spheres.stats(self.k)["realms"])   # founded there (war may since have emptied it)
            for sid in h["polities"]:
                self.assertEqual(polity.sovereigns(self.k)[sid]["line"], line)

    def test_captains_serve_a_standing_house_or_keep_a_ronins_way(self):
        from xylarium.kernel import dynasties
        st = dynasties.stats(self.k)
        for cid, line in st["serves"].items():
            self.assertIn(line, dynasties.standing(self.k))
            self.assertNotIn(cid, st["ronin"])
            self.assertFalse(dynasties._raider(self.k.captains[cid]))
        for cid, r in st["ronin"].items():
            self.assertIn(r["way"], ("band", "pirate", "solo"))
            if dynasties._raider(self.k.captains[cid]):
                self.assertEqual(r["way"], "pirate")
        ai = {c for c, cap in self.k.captains.items() if cap.is_ai}
        self.assertEqual(ai, set(st["serves"]) | set(st["ronin"]))   # every crew is one or the other

    def test_a_houses_duty_comes_before_a_captains_own_books(self):
        from xylarium.kernel import dynasties, offices
        st = dynasties.stats(self.k)
        line = next(iter(dynasties.standing(self.k)))
        h = dynasties.houses(self.k)[line]
        h["duty"], work = "room", h.get("work")               # the house needs room; it has learned building answers it
        h["work"] = "works"
        cap = next(c for c in self.k.captains.values() if c.is_ai)
        was, duty = st["serves"].get(cap.id), h["duty"]
        st["serves"][cap.id] = line
        try:
            self.assertEqual(dynasties.duty_of(self.k, cap.id), "works")
            options = [(5.0, {"kind": "haul"}, None), (1.0, {"kind": "settle"}, None)]
            self.assertEqual(offices.choose(self.k, cap, options)[1]["kind"], "settle")
        finally:
            h["duty"], h["work"] = duty, work
            if was is None:
                st["serves"].pop(cap.id)
            else:
                st["serves"][cap.id] = was


class TestSpheres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(3 * 100):
            cls.k.tick_simulation()

    def test_networks_grow_by_the_power_that_pays_for_their_passages(self):
        from xylarium.kernel import mastery, relations, spheres
        st = spheres.stats(self.k)
        for who, net in st["nets"].items():
            self.assertTrue(spheres.crossed(self.k, who))
            for sid in net["held"]:
                self.assertEqual(spheres.presence(self.k, spheres.owner(self.k, sid)), who)
        by = relations._peoples(self.k)
        big = max(st["nets"], key=lambda w: mastery.power_w(self.k, by.get(w, [])))
        small = min(st["nets"], key=lambda w: mastery.power_w(self.k, by.get(w, [])) if w in by else float("inf"))
        reach = lambda w: len(st["nets"][w]["held"]) + int(st["nets"][w].get("beyond", 0))
        self.assertGreater(reach(big), reach(small))                                     # power reaches farther
        self.assertGreater(spheres.radius(self.k, big), 0)

    def test_contact_is_a_bond_or_a_war_by_the_arrivals_style(self):
        from xylarium.kernel import realmwars, spheres
        st = spheres.stats(self.k)
        self.assertTrue(st["contacts"])
        for c in st["contacts"]:
            self.assertIn(c["kind"], spheres.BONDS + ("war",))
            if c["kind"] != "war":
                b = spheres.bond(self.k, c["a"], c["b"])
                if b is None:                                     # a party has since fallen: its bonds lapsed
                    self.assertTrue(any(not st["nets"][w]["held"] for w in (c["a"], c["b"]) if w in st["nets"]))
                else:
                    self.assertEqual(b["kind"], c["kind"])
        for w in realmwars.stats(self.k)["wars"].values():
            self.assertNotEqual(w["taker"], w["holder"])
            self.assertIn(w["status"], ("open", "taken", "spent", "withdrawn", "sealed", "undone", "lost", "exhausted"))

    def test_a_fallen_peoples_realms_lapse_and_no_war_is_fought_with_the_dead(self):
        from xylarium.kernel import spheres
        st = spheres.stats(self.k)
        who = next(w for w, n in st["nets"].items() if n["held"])
        held = list(st["nets"][who]["held"])
        spheres.lapse(self.k, who, [])
        for sid in held:
            self.assertIsNone(spheres.owner(self.k, sid))         # no one's: the next passage simply holds it
        self.assertFalse(any(who in (b["a"], b["b"]) for b in st["bonds"].values()))

    def test_growth_beyond_the_charts_holds_no_more_stars_than_the_galaxy_has(self):
        from xylarium.kernel import cluster, spheres
        st = spheres.stats(self.k)
        who = next(w for w, n in st["nets"].items() if n["held"])
        net = st["nets"][who]
        stars = cluster.HOME_MASS / spheres._mean_star()
        others = sum(len(x["held"]) + int(x.get("beyond", 0)) for x in st["nets"].values())
        before_bank = float(net.get("bank_j", 0.0))
        spheres.beyond(self.k, who, net, int(stars - others) + 10)
        self.assertLessEqual(sum(len(x["held"]) + int(x.get("beyond", 0)) for x in st["nets"].values()), stars)
        self.assertGreater(float(net["bank_j"]), before_bank)            # what found no star is kept as energy
        net["beyond"] = 0

    def test_a_war_is_a_reckoning_that_counts_its_own_dead_whatever_its_alignment(self):
        from xylarium.kernel import alignment, realmwars, spheres
        st = spheres.stats(self.k)
        live = [w for w in st["nets"] if spheres._home(self.k, w) is not None and st["nets"][w]["held"]]
        who, other = live[0], live[1]
        sid = st["nets"][other]["held"][0]
        civ = spheres._home(self.k, who).civilization
        with mock.patch.object(alignment, "character", return_value=-1.0):        # absolute darkness
            dark = realmwars.weigh(self.k, who, other, sid)
        with mock.patch.object(alignment, "character", return_value=1.0):
            light = realmwars.weigh(self.k, who, other, sid)
        if "gain" in dark:
            self.assertEqual(dark["order"], 0.0)                                  # the other's dead count nothing to it
            self.assertGreater(dark["own_dead"] + dark["troops"], 0.0)            # but its own still do
            self.assertGreaterEqual(light["order"], dark["order"])

    def test_war_inside_a_web_of_bonds_puts_the_shared_economy_at_stake(self):
        from xylarium.kernel import realmwars, spheres
        st = spheres.stats(self.k)
        saved = dict(st["bonds"])
        try:
            st["bonds"].clear()
            st["bonds"]["civ:A|civ:B"] = {"kind": "federation", "a": "civ:A", "b": "civ:B"}
            st["bonds"]["civ:B|civ:C"] = {"kind": "alliance", "a": "civ:B", "b": "civ:C"}
            st["bonds"]["civ:C|civ:D"] = {"kind": "standoff", "a": "civ:C", "b": "civ:D"}
            self.assertEqual(realmwars._web(self.k, "civ:A"), {"civ:A", "civ:B", "civ:C"})   # standoffs bind no one
        finally:
            st["bonds"].clear()
            st["bonds"].update(saved)

    def test_a_betrayed_people_owes_its_realm_nothing_and_a_dying_one_fights_for_room(self):
        from xylarium.kernel import exodus, realmwars, spheres
        st = spheres.stats(self.k)
        live = [w for w in st["nets"] if spheres._home(self.k, w) is not None and st["nets"][w]["held"]]
        who, other = live[0], live[1]
        sid = st["nets"][other]["held"][0]
        with mock.patch.object(realmwars, "_integration", return_value=(1e18, True)):
            r = realmwars.weigh(self.k, who, other, sid)
            if "gain" in r:
                self.assertFalse(r["war"])                         # an outbreak in its own body is not worth it
            exodus.stats(self.k).setdefault("unanswered", {})[who] = 0
            r = realmwars.weigh(self.k, who, other, sid)
            exodus.stats(self.k)["unanswered"].pop(who)
            if "gain" in r:
                self.assertEqual(r["integration"], 0.0)
                self.assertTrue(r["betrayed"])

    def test_the_fronts_and_their_seam_are_read_by_kind(self):
        from xylarium.kernel import spheres
        f = spheres.fronts(self.k)
        self.assertEqual(len(f["progenitor"]) + len(f["young"]), len(spheres.stats(self.k)["nets"]))
        self.assertEqual(f["progenitor"], [])                  # a settled board has no ancients' networks
        for c in f["seam"]:
            self.assertIn(c["met"], spheres.BONDS + ("war",))
        self.assertIn("THE SPHERES", spheres.render(self.k))

    def test_realms_are_shells_of_a_term_and_names_say_whose(self):
        from xylarium.kernel import spheres
        self.assertEqual(spheres.realm_name("Terran Federation#2"), "the Second Reach of the Terran Federation")
        for rid, r in spheres.stats(self.k)["realms"].items():
            self.assertEqual(rid, spheres.realm_id(r["presence"], r["ring"]))

    def test_a_war_that_takes_more_than_it_loses_wins_the_system(self):
        from xylarium.kernel import polity, realmwars, spheres
        st = spheres.stats(self.k)
        live = [w for w in st["nets"] if polity.of_people(self.k, w) and st["nets"][w]["held"]]
        taker, holder = live[0], live[1]
        sid = st["nets"][holder]["held"][0]
        mine = next(r for r in spheres.realms(self.k) if spheres.presence(self.k, r) == taker)
        w = realmwars.declare(self.k, mine, spheres.owner(self.k, sid), taker, sid)
        with mock.patch.object(realmwars, "_took", side_effect=lambda k, by, fr, since: 5 if by == taker else 1), \
                mock.patch.object(realmwars, "weigh", return_value={"war": True, "attack": 1.0, "defend": 1.0}):
            realmwars._fight(self.k, w, [])
        self.assertEqual(spheres.presence(self.k, spheres.owner(self.k, sid)), taker)
        self.assertEqual(w["status"], "taken")

    def test_a_fold_war_is_settled_by_which_fold_arrives_first_then_the_other_yields(self):
        from xylarium.kernel import board, realmwars
        lines = {"civ:Near": {"name": "Nearline", "ancient": "civ:Near"},
                 "civ:Far": {"name": "Farline", "ancient": "civ:Far"}}
        war = {"id": "G-T", "by": "Far#1", "sender": "civ:Far", "taker": "civ:Far", "from": "Far#1",
               "against": "Near#1", "sector": 1, "side": "dark", "since": 0, "status": "open", "taken": "1",
               "escalated": 1, "lines": ["civ:Far", "civ:Near"], "wills": {"civ:Far": "stands", "civ:Near": "undone"}}
        dist = {"civ:Near": 1.0, "civ:Far": 9.0}
        with mock.patch.object(board, "progenitors", return_value=lines), \
                mock.patch.object(board, "_distance", side_effect=lambda k, a, b: dist[a]):
            logs = []
            realmwars._fold(self.k, war, logs)                 # both fold: the nearer's stands
            self.assertEqual(war["stands"], "civ:Near")
            realmwars._fold(self.k, war, logs)                 # the farther's fold is walled: it yields
        self.assertEqual(war["status"], "undone")
        self.assertEqual(war["sealed_by"], "civ:Near")
        self.assertIn("fold", [d for ws in lines["civ:Far"]["fold_mind"]["walls"].values() for d in ws])


class TestHouseLearning(unittest.TestCase):
    def test_a_house_learns_which_work_answers_its_duty(self):
        from fractions import Fraction
        from xylarium.kernel import dynasties, mindcore as mc
        h = {"line": "L", "duty": "food", "mind": mc.new_mind()}
        first = dynasties.family_for(None, h)
        self.assertEqual(first, dynasties.FAMILIES[0])
        mc.intend(h["mind"], ("L", "food"), Fraction(5), first, "house")
        mc.seal(h["mind"], {("L", "food"): Fraction(5)})          # the work delivered nothing: walled
        self.assertNotEqual(dynasties.family_for(None, h), first)
        second = dynasties.family_for(None, h)
        mc.intend(h["mind"], ("L", "food"), Fraction(5), second, "house")
        mc.seal(h["mind"], {("L", "food"): Fraction(2)})          # it drained the need: a crystal
        self.assertEqual(dynasties.family_for(None, h), second)


class TestCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(4 * 100):
            cls.k.tick_simulation()

    def test_a_steward_claims_withdraws_and_grants(self):
        from xylarium.kernel import command, dynasties, realmwars, spheres, stewardship
        k = self.k
        h = next(h for h in dynasties.standing(k).values() if h["realm"] in stewardship.realms(k))
        stewardship.seat_steward(k, "keeper", "Keeper", h["realm"])
        try:
            mine = spheres.presence(k, h["realm"])
            other = next(r for r in stewardship.realms(k) if spheres.presence(k, r) != mine)
            res = command.claim(k, "keeper", other)
            self.assertTrue(res["ok"])
            w = realmwars.stats(k)["wars"][res["war"]]
            self.assertEqual((w["from"], w["against"], w["status"]), (h["realm"], other, "open"))
            self.assertFalse(command.claim(k, "keeper", other)["ok"])         # one claim at a time
            self.assertTrue(command.withdraw(k, "keeper")["ok"])
            self.assertEqual(w["status"], "withdrawn")
            before = h.get("grants", 0)
            self.assertTrue(command.grant(k, "keeper", h["name"])["ok"])
            self.assertEqual(h["grants"], before + 1)
        finally:
            stewardship.stats(k)["stewards"].pop(h["realm"], None)

    def test_a_sovereign_orders_its_house_and_its_commissions_meet_a_captains_agency(self):
        from xylarium.kernel import command, dynasties, polity
        k = self.k
        line, h = next(iter(dynasties.standing(k).items()))
        seat = polity.sovereigns(k)[h["polities"][0]]
        was = seat.get("player")
        seat["player"] = "liege"
        try:
            self.assertTrue(command.order(k, "liege", "room")["ok"])
            self.assertEqual(dynasties._duty(k, h), "room")
            self.assertFalse(command.order(k, "liege", "glory")["ok"])
            held = [s for s, l in dynasties._held(k).items() if l == line]
            c = next(c for c in k.captains.values() if c.is_ai and dynasties.stats(k)["serves"].get(c.id) != line)
            c.sector_id = held[0]
            res = command.commission(k, "liege", c.id)
            if dynasties._raider(c):
                self.assertFalse(res["ok"])                    # a raider serves no house
            elif res["ok"]:
                self.assertEqual(dynasties.duty_of(k, c.id), h["work"])   # the ordered duty reaches the captain
                self.assertIn(h["work"], dynasties.FAMILIES)          # as the work its house has learned answers it
                self.assertTrue(command.dismiss(k, "liege", c.id)["ok"])
        finally:
            seat["player"] = was
            h.pop("ordered", None)

    def test_a_captain_swears_forswears_and_keeps_a_ronins_way(self):
        from xylarium.kernel import command, dynasties
        k = self.k
        line, h = next(iter(dynasties.standing(k).items()))
        me = k.register_player("drifter", "Drifter")
        me.sector_id = next(s for s, l in dynasties._held(k).items() if l == line)
        self.assertTrue(command.swear(k, "drifter", h["name"])["ok"])
        self.assertEqual(dynasties.stats(k)["serves"]["drifter"], line)
        self.assertFalse(command.way(k, "drifter", "pirate")["ok"])           # it serves: forswear first
        self.assertTrue(command.forswear(k, "drifter")["ok"])
        self.assertTrue(command.way(k, "drifter", "pirate")["ok"])
        self.assertEqual(dynasties.stats(k)["ronin"]["drifter"]["way"], "pirate")
        dynasties._ways(k)
        self.assertEqual(dynasties.stats(k)["ronin"]["drifter"]["way"], "pirate")   # its choice is kept

    def test_a_progenitor_sends_and_recalls_its_lines_stewards(self):
        from xylarium.kernel import board, command, roles, spheres, stewardship
        k = self.k
        roles.stats(k).setdefault("of", {})["elder"] = "progenitor"
        try:
            realm = stewardship.realms(k)[0]
            self.assertFalse(command.send(k, "elder", realm)["ok"])   # the elders hold no network of their own
            who = spheres.presence(k, realm)
            line = {"name": "Testline", "ancient": who, "player": "elder"}
            with mock.patch.object(command, "line_of", return_value=(who, line)), \
                    mock.patch.object(board, "progenitors", return_value={who: line}):
                self.assertTrue(command.recall(k, "elder", realm)["ok"])
                stewardship.envoys(k, realm)
                self.assertNotIn(f"{who}@{realm}", stewardship.stats(k)["envoys"])   # a player's line sends by choice
                self.assertTrue(command.send(k, "elder", realm)["ok"])
                self.assertFalse(command.send(k, "elder", realm)["ok"])
                self.assertFalse(command.fold(k, "elder", "G-none")["ok"])
        finally:
            roles.stats(k)["of"].pop("elder", None)


class TestBoard(unittest.TestCase):
    def test_the_watcher_brings_appeals_up_and_the_ancients_seal_them(self):
        from xylarium.kernel import board, mindcore as mc, stewardship
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        k = GameKernel(seed=42)
        for _ in range(10 * 100):
            k.tick_simulation()
        sealed = [r for r in stewardship.stats(k)["rulings"].values() if r.get("sealed")]
        self.assertTrue(sealed)                                  # what no steward could settle, settled
        for r in sealed:
            self.assertTrue(str(r["sealed_by"]).startswith("progenitor:"))
        for (site, book), v in board.progenitor_books(k).items():
            self.assertIsInstance(v, mc.Fraction)
        self.assertIn("THE BOARD", board.render(k))
        self.assertIn("watcher", board.summary(k))

    def test_a_seated_progenitor_decides_for_itself(self):
        from xylarium.kernel import board
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=42)
        roles.stats(k)["of"]["player_0"] = "progenitor"
        self.assertEqual(board.seated_progenitor(k), "player_0")


class TestAncientsAndProgenitors(unittest.TestCase):
    def test_ancients_raise_their_own_progenitors_once_they_cross(self):
        from xylarium.kernel import board
        random.seed(7)
        k = roles.start_progenitor(7, "Architect", pick=0, pace="neighbourly")
        ages.sleep(k, "player_1", 1e8)
        anc = board.ancient_peoples(k)
        lines = board.progenitors(k)
        self.assertTrue(anc)
        for who in lines:
            self.assertIn(who, anc)                             # every progenitor line is an ancient people's
        self.assertTrue(lines)                                  # and the ancients who crossed raised them
