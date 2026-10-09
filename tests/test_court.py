"""
The court: all puzzle solving is the seated minds' (operator ruling). The house pulls a task under the ancients'
reserve key and puts it before every seated mind that has none; a task left past its patience is let go; the kernel
answers nothing itself; with no endpoint, no traffic leaves.
"""

import os
import unittest
from unittest import mock

from xylarium.kernel import court, seats, spheres, stewardship
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import anastome as an

TASK = {"id": bytes(range(32)), "train": [([[1, 2]], [[2, 1]])], "test": [[[3, 4]]]}


class TestCourt(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        from xylarium.kernel import relations
        world = next(p for s in self.k.sectors.values() for p in s.planets)
        for p in (mock.patch.object(court, "houses", return_value=["civ:Elder"]),
                  mock.patch.object(relations, "_peoples", return_value={"civ:Elder": [world]})):
            p.start()
            self.addCleanup(p.stop)
        self.seat = f"ancients:civ:Elder@{world.id}"

    def test_a_task_goes_only_before_a_seated_mind_and_is_pulled_under_the_reserve_key(self):
        asked = []
        speak = lambda act: asked.append(act) or b"task"
        with mock.patch.object(an, "read_task", return_value=TASK):
            self.assertEqual(court.hand_tasks(self.k, speak), 0)        # no one seated: nothing pulled
            self.assertEqual(asked, [])
            seats.take(self.k, self.seat, "ab" * 32)
            self.assertEqual(court.hand_tasks(self.k, speak), 1)
            self.assertEqual(court.hand_tasks(self.k, speak), 0)        # it has one before it already
        self.assertEqual(asked, [an.task_request(an.key("ancients"))])
        self.assertEqual(seats.percept(self.k, self.seat)["task"]["id"], TASK["id"].hex())
        self.assertEqual(seats.percept(self.k, self.seat)["counsel"], [])   # the kernel offers no answer of its own

    def test_a_task_left_past_its_patience_is_let_go(self):
        seats.take(self.k, self.seat, "ab" * 32)
        with mock.patch.object(an, "read_task", return_value=TASK):
            court.hand_tasks(self.k, lambda act: b"task")
            self.k.cycle_count += court.PATIENCE + 1
            with mock.patch.object(an, "read_task", return_value=None):
                court.hand_tasks(self.k, lambda act: b"")
        self.assertIsNone(seats.task_of(self.k, self.seat))
        self.assertEqual(court.stats(self.k)["let_go"], 1)

    def test_the_year_meets_nothing_itself(self):
        with mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch("xylarium.uplink.anastome.speak") as speak:
            self.assertEqual(court.season(self.k), [])
        speak.assert_not_called()


class TestWireV12Task(unittest.TestCase):
    def test_a_task_named_by_its_citation_reads_whole_and_a_misframe_is_no_task(self):
        from xylarium.uplink import anastome as an
        cit = bytes(range(32))
        body = cit + bytes([1]) + an.grid([[1, 2]]) + an.grid([[2, 1]]) + bytes([1]) + an.grid([[3, 4]])
        t = an.read_task(body)
        self.assertEqual((t["id"], t["train"], t["test"]), (cit, [([[1, 2]], [[2, 1]])], [[[3, 4]]]))
        self.assertIsNone(an.read_task(body[:-1]))                   # does not frame whole: no task, no crash
        self.assertIsNone(an.read_task(b""))


if __name__ == "__main__":
    unittest.main()
