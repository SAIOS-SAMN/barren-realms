"""
The universe's upward ledger on its own axis: entries chain by parent, carry the canonical commitment to the state
(exact values, never a file's bytes), and are the hypha's act signed over its wire preimage.
"""

import json
import os
import shutil
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction

from nacl.signing import VerifyKey

from xylarium.persistence.store import StatePersistence
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import anastome as an, commitment, ledger


class TestCommitment(unittest.TestCase):
    def test_the_same_values_commit_the_same_root_however_written_and_any_change_moves_it(self):
        a = {"b": [1, Fraction(5, 2), None], "a": {"x": "hi", "y": True, "z": {}}}
        b = json.loads('{"a": {"z": {}, "y": true, "x": "hi"}, "b": [1, 2.50, null]}', parse_float=Fraction)
        self.assertEqual(commitment.root_of(a), commitment.root_of(b))
        self.assertNotEqual(commitment.root_of({"a": None}), commitment.root_of({"a": ""}))
        self.assertNotEqual(commitment.root_of({"q": Fraction(1, 3)}),
                            commitment.root_of({"q": Fraction(1, 3) + Fraction(1, 10 ** 30)}))

    def test_the_network_form_one_record_is_its_leaf_and_none_is_zeros(self):
        import struct
        import blake3
        from xylarium.uplink import seat_wire as w
        empty = blake3.blake3(struct.pack("<H", 2) + b"[]" + w.args([(w.BYTES, b"{}")]),
                              derive_key_context="mycelium ledger leaf v1").digest()
        self.assertEqual(commitment.root_of({}), empty)              # an empty object is one record, its own leaf
        key = b'["a"]'
        leaf = blake3.blake3(struct.pack("<H", len(key)) + key + w.args([(w.Q_, Fraction(7))]),
                             derive_key_context="mycelium ledger leaf v1").digest()
        self.assertEqual(commitment.root_of({"a": 7}), leaf)


class TestLedger(unittest.TestCase):
    def test_entries_chain_and_are_the_hypha_act_signed_by_the_reserve(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        save, led = os.path.join(d, "u.json"), os.path.join(d, "u.ledger.jsonl")
        StatePersistence.save_to_file(GameKernel(seed=42), save)
        with ProcessPoolExecutor(max_workers=1) as pool:              # as the daemon runs it: off its own time
            shutil.copyfile(save, save + ".1")
            e1 = pool.submit(ledger.entry, 0, save + ".1", led, None).result()
            shutil.copyfile(save, save + ".2")
            e2 = pool.submit(ledger.entry, 10, save + ".2", led, None).result()
        self.assertEqual(e1["commitment"], commitment.of_save(save).hex())
        self.assertEqual((e1["parent"], e2["parent"]), ("00" * 32, e1["hash"]))
        act = bytes.fromhex(e2["act"])
        self.assertEqual((act[0], act[33:36]), (0x3E, bytes([0x80, 0, 8])))
        VerifyKey(an.vk(an.key("ancients"))).verify(an.LEDGER_TAG + act[1:33] + act[36:-64], act[-64:])


if __name__ == "__main__":
    unittest.main()
