"""
The crystal lattice and fluid intelligence: coordinates instead of search, proofs by replay, vocabularies that
bound what a people can express, and minds steadied by what they can solve.
"""

import itertools
import random
import unittest

from xylarium.kernel import crystal as C
from xylarium.kernel import intellect as I


def grid(rng, rows, cols, k=4):
    return tuple(tuple(rng.randrange(k) for _ in range(cols)) for _ in range(rows))


class TestLattice(unittest.TestCase):
    def test_frame_ops_are_netstratums(self):
        g = grid(random.Random(1), 3, 4)
        rows, cols = 3, 4
        self.assertEqual(C.apply_frame(C.frame_of(C.ROT90), g),
                         tuple(tuple(g[rows - 1 - c][r] for c in range(rows)) for r in range(cols)))
        self.assertEqual(C.apply_frame(C.frame_of(C.TRANSPOSE), g),
                         tuple(tuple(g[c][r] for c in range(rows)) for r in range(cols)))
        self.assertEqual(C.apply_frame(C.frame_of(C.FLIPV), g), tuple(reversed(g)))

    def test_composition_is_exact(self):
        g = grid(random.Random(2), 3, 5)
        for a, b in itertools.product(C.D4, C.D4):
            self.assertEqual(C.apply_frame(C.compose(a, b), g), C.apply_frame(b, C.apply_frame(a, g)))

    def test_any_word_reads_back_to_its_coordinate(self):
        rng = random.Random(3)
        for _ in range(100):
            word = [rng.choice(C.FRAME_OPS) for _ in range(rng.randint(1, 8))]
            pairs = [(x, C.run(word, x)) for x in (grid(rng, 4, 4), grid(rng, 3, 5), grid(rng, 5, 3))]
            prog = C.address(C.read(pairs), C.FRAME_OPS, True)
            self.assertLessEqual(len(prog), 3)              # depth disappears into the point it names
            for x, y in pairs:
                self.assertEqual(C.run(prog, x), y)

    def test_a_chart_holds_only_what_its_crystals_generate(self):
        self.assertEqual(len(C.chart([C.ROT90])), 4)        # rotations only: no mirror image is reachable
        self.assertEqual(len(C.chart([C.FLIPH])), 2)
        self.assertEqual(len(C.chart([C.ROT90, C.FLIPH])), 8)


class TestForgeAndProof(unittest.TestCase):
    def test_the_forge_is_deterministic_from_history(self):
        a, b = I.forge("seal-1", "civ:x", 2, 5), I.forge("seal-1", "civ:x", 2, 5)
        self.assertEqual(a["id"], b["id"])
        self.assertNotEqual(a["id"], I.forge("seal-2", "civ:x", 2, 5)["id"])

    def test_a_claim_verifies_by_replay_and_forgeries_do_not(self):
        vocab = [C.ROT90, C.FLIPH, C.RECOLOR, C.FLIP_STACK, C.CYCLE_LAYERS]
        for rank in (2, 3):
            task = I.forge("seal", "civ:x", rank, 6)
            prog = I.decompact(vocab, task)
            if prog is None:
                continue
            cert = I.certificate(task, prog)
            self.assertTrue(I.verify(cert))
            self.assertFalse(I.verify(dict(cert, head="0" * 64)))
            self.assertFalse(I.verify(dict(cert, program=[])))           # no path, no proof
            self.assertFalse(I.verify(dict(cert, level=5)))              # a different task

    def test_a_vocabulary_bounds_what_can_be_expressed(self):
        task = None
        for level in range(1, 9):
            t = I.forge("seal-mirror", "civ:x", 2, level)
            coord = C.read(t["train"])
            if coord and coord[0][1] == 1 and tuple(coord[1]) == tuple(range(10)):
                task = t                                                 # needs a mirror and nothing else
                break
        if task is None:
            self.skipTest("no mirror-only task forged on this seed")
        self.assertIsNone(I.decompact([C.ROT90], task))
        self.assertIsNotNone(I.decompact([C.ROT90, C.FLIPH], task))


class TestTheGaugeInTheUniverse(unittest.TestCase):
    def setUp(self):
        from xylarium.kernel.engine import GameKernel
        random.seed(7)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_peoples_climb_and_prove_it(self):
        from xylarium.kernel import knowledge
        for _ in range(400):
            self.k.tick_simulation()
        st = I.stats(self.k)
        self.assertGreater(len(st["gauge"]), 0)
        self.assertGreater(st["stats"]["solved"], 0)
        for proofs in st["proofs"].values():
            for cert in proofs:
                self.assertTrue(I.verify(cert))
        self.assertGreater(knowledge.stats(self.k)["made"].get("useful_work", 0), 0)

    def test_fluid_intelligence_carries_learning_further_and_steadies_judgement(self):
        from xylarium.kernel import decide, knowledge
        holder = "captain:tester"
        knowledge.learn(self.k, holder, "energy", 20)
        before = knowledge.mastery(self.k, holder, "jump_drive")
        I.stats(self.k)["gauge"][holder] = {"2": 8, "3": 8}
        self.assertGreater(knowledge.mastery(self.k, holder, "jump_drive"), before)
        cap = self.k.register_player("tester", "Tester")
        self.assertLess(decide.mind_of_captain(self.k, cap)["noise"], decide.mind(self.k, "biotic")["noise"])

    def test_relics_carry_crystals(self):
        holder = "captain:digger"
        got = I.relic_crystal(self.k, holder, "R-1")
        self.assertIn(got, I.DISCOVERABLE)
        self.assertIn(got, I.vocabulary(self.k, holder))
        self.assertIsNone(I.relic_crystal(self.k, holder, "R-1"))      # one crystal is learned once


if __name__ == "__main__":
    unittest.main()
