"""
Client screens for the newer systems: the advisor, realms and government, the workbench, drives, stations and
charters - rendered from a live universe and driven with scripted input, as a player would.
"""

import builtins
import contextlib
import io
import random
import unittest

from xylarium.client import screens
from xylarium.kernel import advisor, shipdesign
from xylarium.kernel.engine import GameKernel


class FakeCLI:
    def __init__(self, kernel, pid):
        self.kernel, self.player_id, self.results = kernel, pid, []

    def _print_result(self, res):
        self.results.append(res)


def scripted(answers):
    it = iter(answers)
    return lambda prompt="": next(it, "")


class TestScreens(unittest.TestCase):
    def setUp(self):
        random.seed(181)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None
        self.cap = self.k.register_player("pilot", "Pilot")
        self.cli = FakeCLI(self.k, "pilot")
        self._input = builtins.input
        self._quiet = contextlib.redirect_stdout(io.StringIO())
        self._quiet.__enter__()

    def tearDown(self):
        self._quiet.__exit__(None, None, None)
        builtins.input = self._input

    def test_the_advisor_finds_something_to_do_at_sol_and_takes_it(self):
        adv = advisor.advise(self.k, "pilot")
        text = screens.render_advisor(adv)
        self.assertIn("ADVISOR", text)
        self.assertIn("WHO GOVERNS HERE", text)
        trades = adv["sections"]["here"]
        self.assertTrue(trades, "Sol always has something worth buying")
        builtins.input = scripted(["1", ""])
        screens.prompt_advisor(self.cli)
        self.assertTrue(self.cli.results)              # the first opportunity was dispatched

    def test_realms_screen_shows_the_government_and_offices(self):
        text = screens.render_realms(self.k, self.cap)
        self.assertIn("Terran Federation", text)
        self.assertIn("BUDGET OFFICES", text)
        self.assertIn("REALMS (", text)

    def test_a_player_drafts_and_registers_a_liner(self):
        self.cap.rank_tier, self.cap.credits = 3, 10 ** 6
        builtins.input = scripted(["D", "liner", "capital", "plasmic", "R", "Starwhale", "10", ""])
        screens.prompt_workbench(self.cli)
        spec = shipdesign.designs(self.k).get("Starwhale")
        self.assertIsNotNone(spec, [r.message for r in self.cli.results])
        self.assertGreater(spec["berths"], 0)
        self.assertGreater(spec["comfort"].get("plasmic", 0), 0.9)     # decks drawn for plasmic guests
        self.assertEqual(spec["royalty"], 0.1)

    def test_drive_and_station_screens_render(self):
        self.assertIn("DRIVES & FUEL CELLS", screens.render_drives(self.k, self.cap))
        self.assertIn("ORBITAL STATIONS", screens.render_stations(self.k, self.cap))

    def test_every_screen_word_opens_a_screen(self):
        from xylarium.client.cli import TerminalClient as GameClient
        for word, target in GameClient.WORD_COMMANDS.items():
            if target in ("ADVISOR", "REALMS", "WORKBENCH", "DRIVE", "STATION", "CHARTER"):
                self.assertIn(target, screens.SCREENS, word)


if __name__ == "__main__":
    unittest.main()
