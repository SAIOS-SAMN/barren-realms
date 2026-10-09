"""
Xylarium smt: the state's commitment - the SPARSE MERKLE TREE the network confirmed for the ledger (mycelium 78.154).

  PATH     blake3(key), 256 bits, most significant first; bit 0 is the left branch at the root.
  LEAF     derive_key("mycelium ledger leaf v1") over the record as it lies: key length (u16 LE) || key ||
           put_args(values). Every leaf sits at depth 256 - no short-cut.
  NODE     32 zero bytes where both children are empty, else derive_key("mycelium ledger node v1") over left || right.
  EMPTY    the root of no records is 32 zero bytes.

Memory stays O(n): only BRANCH nodes (both children non-empty) and each record's leaf are kept; a subtree holding a
single leaf is recomputed from that leaf, its path and the zero siblings (256 - depth hashes). A change re-hashes
its record's path: O(256) per changed entity, inserts and deletes included. The root is the full tree's.
"""

import struct
from typing import Dict, Iterable, List, Optional, Tuple

import blake3

LEAF, NODE = "mycelium ledger leaf v1", "mycelium ledger node v1"
ZERO = bytes(32)
DEPTH = 256


def _leaf(record: bytes) -> bytes:
    h = blake3.blake3(derive_key_context=LEAF)
    h.update(record)
    return h.digest()


def _node(left: bytes, right: bytes) -> bytes:
    if left == ZERO and right == ZERO:
        return ZERO
    h = blake3.blake3(derive_key_context=NODE)
    h.update(left + right)
    return h.digest()


def path_of(key: bytes) -> int:
    return int.from_bytes(blake3.blake3(key).digest(), "big")


def _bit(path: int, depth: int) -> int:
    return (path >> (DEPTH - 1 - depth)) & 1


def _lone(path: int, leaf: bytes, depth: int) -> bytes:
    """The root of a subtree at `depth` holding one leaf: up from depth 256 against zero siblings."""
    h = leaf
    for d in range(DEPTH - 1, depth - 1, -1):
        h = _node(ZERO, h) if _bit(path, d) else _node(h, ZERO)
    return h


def _record_key(record: bytes) -> bytes:
    (kl,) = struct.unpack_from("<H", record, 0)
    return record[2:2 + kl]


class Tree:
    """The state's SMT, kept incrementally: leaves by path, and the hashes of branch nodes by (depth, prefix)."""

    def __init__(self) -> None:
        self.leaves: Dict[int, bytes] = {}                 # path -> leaf hash
        self.keys: Dict[bytes, int] = {}                   # key -> path
        self.branches: Dict[Tuple[int, int], bytes] = {}   # (depth, path prefix) -> hash, where both sides hold
        self._root: Optional[bytes] = None

    def _sub(self, paths: List[int], depth: int) -> bytes:
        """The root of the subtree at `depth` over these (sorted) paths, keeping its branch nodes."""
        if not paths:
            return ZERO
        if len(paths) == 1:
            return _lone(paths[0], self.leaves[paths[0]], depth)
        split = 0
        while split < len(paths) and not _bit(paths[split], depth):
            split += 1
        left, right = self._sub(paths[:split], depth + 1), self._sub(paths[split:], depth + 1)
        h = _node(left, right)
        if split and split < len(paths):
            self.branches[(depth, paths[0] >> (DEPTH - depth))] = h
        return h

    def build(self, records: Iterable[bytes]) -> bytes:
        self.leaves, self.keys, self.branches = {}, {}, {}
        for r in records:
            k = _record_key(r)
            if k in self.keys:
                raise ValueError(f"duplicate record key {k[:64]!r}")
            p = path_of(k)
            self.keys[k], self.leaves[p] = p, _leaf(r)
        self._root = self._sub(sorted(self.leaves), 0)
        return self._root

    def root(self) -> bytes:
        if self._root is None:
            self._root = self._sub(sorted(self.leaves), 0)
        return self._root

    def update(self, changed: Iterable[bytes], removed: Iterable[bytes] = ()) -> bytes:
        """Records changed or added, and keys removed: only their paths are re-hashed."""
        touched = []
        for k in removed:
            p = self.keys.pop(k, None)
            if p is not None:
                self.leaves.pop(p, None)
                touched.append(p)
        for r in changed:
            k = _record_key(r)
            p = path_of(k)
            self.keys[k], self.leaves[p] = p, _leaf(r)
            touched.append(p)
        if touched:
            self._root = self._recompute(sorted(self.leaves), sorted(set(touched)))
        return self.root()

    def _recompute(self, ordered: List[int], touched: List[int]) -> bytes:
        """The root again, re-hashing only the subtrees a touched path falls in: a subtree is stale exactly when a
        touched path lies in its range of paths (one binary search on the sorted touched paths) - nothing per depth
        is materialised. Cached branch nodes off the touched paths are reused as they are."""
        import bisect

        def stale(prefix: int, depth: int) -> bool:
            lo = prefix << (DEPTH - depth)
            i = bisect.bisect_left(touched, lo)
            return i < len(touched) and touched[i] < lo + (1 << (DEPTH - depth))

        def sub(lo: int, hi: int, depth: int) -> bytes:
            if lo >= hi:
                return ZERO
            if hi - lo == 1:
                return _lone(ordered[lo], self.leaves[ordered[lo]], depth)
            prefix = ordered[lo] >> (DEPTH - depth)
            key = (depth, prefix)
            if key in self.branches and not stale(prefix, depth):
                return self.branches[key]
            mid_path = (prefix << (DEPTH - depth)) | (1 << (DEPTH - 1 - depth))
            mid = bisect.bisect_left(ordered, mid_path, lo, hi)
            h = _node(sub(lo, mid, depth + 1), sub(mid, hi, depth + 1))
            if lo < mid < hi:
                self.branches[key] = h
            else:
                self.branches.pop(key, None)              # no longer a branch: not kept
            return h
        return sub(0, len(ordered), 0)


def root_of(records: Iterable[bytes]) -> bytes:
    return Tree().build(records)


# ---------------------------------------------------------------------- the daemon's tree, kept in its own process
_TREE: Optional[Tree] = None


def worker_build(records: List[bytes]) -> bytes:
    """Build the tree from every record (once); it stays in this process for the updates that follow."""
    global _TREE
    _TREE = Tree()
    return _TREE.build(records)


def worker_build_file(path: str) -> bytes:
    """Build the tree from a saved record stream on disk (its committed records): no record list crosses between
    processes - the worker reads the save the daemon just wrote."""
    from compression import zstd
    from xylarium.persistence import records
    with open(path, "rb") as f:
        stream = zstd.decompress(f.read())
    recs = records.committed([stream[a:b] for a, b, _ in records.split(stream)])
    del stream
    return worker_build(recs)


def worker_update(changed: List[bytes], removed: List[bytes]) -> bytes:
    """Apply what changed since the last commit (records changed or added, keys removed); the new root."""
    if _TREE is None:
        raise RuntimeError("the tree is not built")
    return _TREE.update(changed, removed)
