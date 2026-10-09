"""
The universe's upward ledger on its own axis, committed by the network's sparse Merkle tree over its entity records:
the root is the full 256-level tree's (bit 0 left at the root, a leaf at depth 256, zero for empty), kept
incrementally; entries chain by parent and are the hypha's act, signed over its wire preimage.
"""

import os
import random
import shutil
import struct
import tempfile
import unittest

from nacl.signing import VerifyKey

from xylarium.persistence import records, smt
from xylarium.uplink import anastome as an, ledger


def rec(key: bytes, v: int) -> bytes:
    return struct.pack("<H", len(key)) + key + bytes([1, 2]) + struct.pack("<Q", v)


def naive(recs):
    """The full tree, level by level: every node at every depth - the reference the root must equal."""
    leaves = {smt.path_of(smt._record_key(r)): smt._leaf(r) for r in recs}

    def sub(prefix, depth):
        ps = [p for p in leaves if (p >> (256 - depth)) == prefix] if depth else list(leaves)
        if not ps:
            return smt.ZERO
        if depth == 256:
            return leaves[ps[0]]
        return smt._node(sub(prefix << 1, depth + 1), sub((prefix << 1) | 1, depth + 1))
    return sub(0, 0)


class TestSparseMerkle(unittest.TestCase):
    def test_empty_one_and_many_equal_the_full_tree(self):
        self.assertEqual(smt.root_of([]), bytes(32))
        for n in (1, 2, 5):
            rs = [rec(('["k%d"]' % i).encode(), i) for i in range(n)]
            self.assertEqual(smt.root_of(rs), naive(rs))

    def test_an_update_equals_a_rebuild_inserts_and_deletes_included(self):
        random.seed(1)
        rs = [rec(('["e%d"]' % i).encode(), i) for i in range(500)]
        t = smt.Tree()
        t.build(rs)
        changed = [rec(('["e%d"]' % i).encode(), i + 1) for i in random.sample(range(500), 20)] + [rec(b'["new"]', 1)]
        removed = [b'["e5"]', b'["e6"]']
        keep = {smt._record_key(r): r for r in rs}
        for k in removed:
            keep.pop(k)
        keep.update({smt._record_key(r): r for r in changed})
        self.assertEqual(t.update(changed, removed), smt.root_of(keep.values()))

    def test_a_state_is_committed_by_its_entity_records(self):
        state = {"a": {"x": 1, "y": [1.5, None]}, "b": "t"}
        self.assertEqual(records.decode(records.encode(state)), state)
        self.assertNotEqual(smt.root_of(records.records_of(state)),
                            smt.root_of(records.records_of({"a": {"x": 2, "y": [1.5, None]}, "b": "t"})))


class TestLedger(unittest.TestCase):
    def test_entries_chain_and_are_the_hypha_act_signed_by_the_reserve(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        led = os.path.join(d, "u.ledger.jsonl")
        r1, r2 = smt.root_of([rec(b'["a"]', 1)]), smt.root_of([rec(b'["a"]', 2)])
        e1, e2 = ledger.entry(0, r1, led, None), ledger.entry(10, r2, led, None)
        self.assertEqual((e1["parent"], e2["parent"], e2["commitment"]), ("00" * 32, e1["hash"], r2.hex()))
        act = bytes.fromhex(e2["act"])
        self.assertEqual((act[0], act[33:36]), (0x3E, bytes([0x80, 0, 8])))
        VerifyKey(an.vk(an.key("ancients"))).verify(an.LEDGER_TAG + act[1:33] + act[36:-64], act[-64:])


if __name__ == "__main__":
    unittest.main()
