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
        asyncio.run(gw._process_client_message(Client(), {"action": "REGISTER", "name": "Keeper", "role": "steward",
                                                          "realm": "0.1"}))
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

    def test_realms_partition_the_galaxy_and_never_move(self):
        seen = {}
        for sid in self.k.sectors:
            r = self.st.realm_of(self.k, sid)
            self.assertIn(r, self.st.realms(self.k))
            seen[sid] = r
        for _ in range(50):
            self.k.tick_simulation()                                            # the map grows; realms stay put
        self.assertEqual({sid: self.st.realm_of(self.k, sid) for sid in seen}, seen)
        self.assertEqual(self.st.sphere_quadrant([1.0, 0.0, 0.0, 0.0]), 0)        # home at the sphere's pole

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
        self.k.cycle_count += 100 * (self.st.RULING_YEARS + 5)
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
        crystals, line = dict(s["crystals"]), s["line"]
        polity._succeed(self.k, s)
        self.assertEqual(s["line"], line)
        self.assertEqual(s["crystals"], crystals)               # the chronicle inherited, never edited
        self.assertGreaterEqual(s["generation"], 2)

    def test_the_realms_own_stewards_rule_and_keep_their_lines(self):
        from xylarium.kernel import stewardship
        minds = stewardship.stats(self.k)["minds"]
        self.assertEqual(sorted(minds), stewardship.realms(self.k))
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
        asyncio.run(gw._process_client_message(c, {"action": "REGISTER", "name": "Keeper", "role": "steward",
                                                   "realm": "0.1"}))
        c.player_id = sent[-1].get("player_id") or next(pid for pid, r in roles.stats(k)["of"].items() if r == "steward")
        asyncio.run(gw._process_client_message(c, {"action": "REALM"}))
        self.assertEqual(sent[-1]["realm"]["realm"], "0.1")
        peoples = [r["people"] for r in sent[-1]["realm"]["peoples"]]
        asyncio.run(gw._process_client_message(c, {"action": "RULE", "kind": "ceasefire", "a": peoples[0],
                                                   "b": peoples[1]}))
        self.assertEqual(sent[-1]["status"], "ok")
        asyncio.run(gw._process_client_message(c, {"action": "SOVEREIGNS"}))
        self.assertIn("sovereigns", sent[-1])
