"""
The court: only an ancients' house meets a court task, and its mind answers with its OWN program over the crystals its
people holds - beyond it where they cannot express the coordinate; a solve is signed with the ancients' key, and every
meeting is a deed on the house's books.
"""

import os
import unittest
from unittest import mock

from xylarium.kernel import court, crystal as C, history, intellect
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import mind

TRANSPOSED = {"id": b"t1", "train": [([[1, 1, 2], [3, 4, 4]], [[1, 3], [1, 4], [2, 4]]),
                                     ([[5, 0, 0], [5, 6, 7]], [[5, 5], [0, 6], [0, 7]])],
              "test": [[[1, 0, 0], [0, 2, 2]]]}


class TestCourt(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.house = "civ:Elder"
        self.thought = mock.patch.object(court, "_thought", return_value=1e9)
        self.thought.start()
        self.addCleanup(self.thought.stop)

    def _vocab(self, ops):
        intellect.stats(self.k)["vocab"][self.house] = list(ops)

    def test_a_mind_without_the_crystal_cannot_close_the_task(self):
        self._vocab([C.ROT90])                                  # the quarter turn alone cannot write a transpose
        self.assertIn("beyond", court.meet(self.k, self.house, TRANSPOSED))
        self._vocab([C.ROT90, C.TRANSPOSE])
        got = court.meet(self.k, self.house, TRANSPOSED)
        self.assertEqual(got["outputs"], [[[1, 0], [0, 2], [0, 2]]])
        self.assertTrue(all("motion" in s for s in got["steps"]))

    def test_the_work_must_fit_the_year_of_thought(self):
        self._vocab([C.ROT90, C.TRANSPOSE])
        with mock.patch.object(court, "_thought", return_value=1.0):
            self.assertEqual(court.meet(self.k, self.house, TRANSPOSED)["beyond"], "the work exceeds its year's thought")

    def test_a_recolouring_is_a_hue_map_naming_every_hue_it_moves(self):
        cmap = tuple([0, 5, 2, 3, 4, 1, 6, 7, 8, 9])
        self.assertEqual(mind.steps_of([C.ROT90, (C.RECOLOR, cmap)]), [{"motion": "Rotate90"}, {"hue": [(1, 5), (5, 1)]}])
        self.assertIsNone(mind.steps_of([("per_layer", C.ROT90)]))

    def test_only_an_ancients_house_meets_the_court_and_it_signs_as_the_ancients(self):
        self._vocab([C.ROT90, C.TRANSPOSE])
        sent = []
        self.k.cycle_count = 0
        with mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch.object(court, "houses", return_value=[self.house]), \
                mock.patch("xylarium.uplink.anastome.speak", return_value=b""), \
                mock.patch("xylarium.uplink.anastome.read_task", return_value=TRANSPOSED), \
                mock.patch.object(mind, "submit", side_effect=lambda a, key, t, s, o: sent.append(key) or
                                  {"verdict": "bounty", "mu": [0, 6, 0, 0]}):
            court.season(self.k)
        self.assertEqual([os.path.basename(k) for k in sent], ["ancients.ed25519"])
        rec = court.stats(self.k)["of"][self.house]
        self.assertEqual((rec["closed"], rec["mu"]), (1, ["0", "6", "0", "0"]))
        self.assertTrue(any(e.get("kind") == "COURT" for e in history.of_people(self.k, self.house)))

    def test_with_no_endpoint_no_traffic_leaves(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("xylarium.uplink.anastome.speak") as speak:
            court.season(self.k)
        speak.assert_not_called()


if __name__ == "__main__":
    unittest.main()
