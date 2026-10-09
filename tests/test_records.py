"""
The save is the record set: a universe written as its record stream and read back is the same universe, value for
value (exact, floats bit for bit), and its commitment is the hash of the records as they lie.
"""

import json
import math
import os
import shutil
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.persistence import records
from xylarium.persistence.store import StatePersistence


class TestRecords(unittest.TestCase):
    def test_values_round_trip_exactly_with_their_types_and_shapes(self):
        v = {"a": {"1": [1, 2.5, None, {}, [], True, "x"], "b": 0.1, "c": 10 ** 30, "d": float("inf"), "e": -3}}
        back = records.decode(records.encode(v))
        self.assertEqual(back, json.loads(json.dumps(v)))
        self.assertIsInstance(back["a"]["1"][0], int)
        self.assertEqual(back["a"]["b"].hex(), (0.1).hex())                # a float, bit for bit
        self.assertTrue(math.isinf(back["a"]["d"]))

    def test_a_universe_saved_as_records_loads_as_the_same_universe(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        k = GameKernel(seed=42)
        for _ in range(5):
            k.tick_simulation()
        js, rec = os.path.join(d, "u.json"), os.path.join(d, "u" + ".rec.zst")
        self.assertTrue(StatePersistence.save_to_file(k, js))
        self.assertTrue(StatePersistence.save_to_file(k, rec))
        a, b = StatePersistence.load_from_file(js), StatePersistence.load_from_file(rec)
        StatePersistence.save_to_file(a, js + "2")
        StatePersistence.save_to_file(b, js + "3")
        with open(js + "2") as f2, open(js + "3") as f3:
            x, y = json.load(f2), json.load(f3)
        x.pop("radio"), y.pop("radio")                       # re-broadcast on load, stamped with Earth's wall clock
        self.assertEqual(x, y)                               # the same universe either way


if __name__ == "__main__":
    unittest.main()
