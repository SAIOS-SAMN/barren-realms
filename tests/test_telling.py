"""
History is kept on the one coordinate clock and told in the reader's own years: turns of its own world about its
star (or, to a reader with no world, turns of the galaxy), oldest first, in plain words.
"""
import unittest
from unittest import mock

from xylarium.kernel import history


class TestTelling(unittest.TestCase):
    def test_a_galactic_year_is_a_turn_of_the_galaxy_at_the_suns_radius(self):
        self.assertAlmostEqual(history.galactic_year_gyr(), 0.2234, delta=0.002)

    def test_counts_read_as_words(self):
        self.assertEqual(history._count(1.9e6), "1.9 million")
        self.assertEqual(history._count(179e6), "179 million")
        self.assertEqual(history._count(4.2e9), "4.2 billion")
        self.assertEqual(history._count(812), "812")

    def test_an_event_is_dated_when_it_happened_not_when_it_was_written(self):
        rec = {"deep_gyr": 1.9, "data": {"epoch": 1.48}}
        self.assertEqual(history.when_gyr(rec), 1.48)
        self.assertEqual(history.when_gyr({"deep_gyr": 1.9}), 1.9)

    def test_the_chronicle_runs_oldest_first_without_the_cosmic_clock_in_its_words(self):
        recs = [{"id": "H-2", "kind": "FALL", "title": "The B fall", "deep_gyr": 1.9, "data": {"epoch": 1.6},
                 "cause": "at the level of history; its ruins lie on 1 world"},
                {"id": "H-1", "kind": "ASCENT", "title": "The A cross", "deep_gyr": 1.9, "data": {"epoch": 1.5},
                 "cause": "at the level of history, 1.5000 Gyr after the Big Bang"},
                {"id": "H-3", "kind": "EMERGENCE", "title": "The C look up", "deep_gyr": 1.95,
                 "cause": "after 3 hard steps"}]
        with mock.patch.object(history, "stats", lambda k: {"recent": recs}), \
                mock.patch("xylarium.kernel.cosmos.is_cosmic", lambda k: True):
            lines = history.chronicle(object(), None)
        self.assertEqual([l.split(": ", 1)[1].split(".")[0] for l in lines], ["The A cross", "The B fall",
                                                                             "The C look up"])
        self.assertTrue(all("Gyr" not in l for l in lines))
        self.assertTrue(lines[0].startswith("7 turns of the galaxy"), lines[0])


if __name__ == "__main__":
    unittest.main()
