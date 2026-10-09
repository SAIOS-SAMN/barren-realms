# Storage and the ledger

*Concordance 1.13 and 9.1; the operator's clock design (78.156); mycelium 78.154. Landed 2026-10-09.*

## What is stored

State is addressed by coordinate: the universe's own axis `u` (its cycle) and an entity's path. Every value is one of three kinds:

- **Derived:** orbits, places, sky, seasons, arrivals, and a world's keyed physics caches (`_media`, `_halite`, `_freeze`, `_rad`). These are recomputed on demand and never stored. A surface is drawn from its world's id, so only the tiles built on it are stored.
- **Path-dependent:** numbers, knowledge, shear, books. These are stored at checkpoints, and a checkpoint is a ledger entry.
- **Inputs:** a mind taking a seat, a seated mind's call, a player's order, and a body's redraw. These are stored as events at their coordinate and re-applied in order from the checkpoint before (`xylarium/kernel/inputs.py`).

What no law reads again is not kept. Examples are an ended sovereign's books, the living's entries about it, and the survey's withheld reasons.

## The save is the record set (`xylarium/persistence/records.py`)

- **Entities.** One record per object or list, keyed by its path: the JSON array of object keys (text) and list indices (integers).
- **Values.** `put_args([Count kind, Count parts, children…])`. An object's child is `Bytes(name)`, `Count(type)`, then its payload. Types are int, float (an exact dyadic, read back bit for bit), text, bool, null, `{}`, `[]`, a non-finite float, and a nested entity.
- **Order.** Object order is kept, because laws iterate it.
- **Parts.** An entity with more than 255 arguments continues in parts, at its path with a negative last index.
- **Stream.** Records are stored in key order as `(u16 key_len, key, values)`, which are exactly the bytes a ledger leaf hashes. The file is `runs/<universe>.rec.zst`, compressed with zstd at rest. JSON is an export only.
- **Cache.** Records the save keeps but the commitment does not cover (`records.is_cache`): a world's body. All 8,961 live bodies are proven equal to their creation draw.

## The commitment (`xylarium/persistence/smt.py`)

This is the network's sparse Merkle tree:

- **Path.** `blake3(key)`, most significant bit first; bit 0 is the left branch at the root.
- **Leaf.** `derive_key("mycelium ledger leaf v1")` over the record bytes. Every leaf sits at depth 256.
- **Node.** Zero when both children are zero, otherwise `derive_key("mycelium ledger node v1")` over left ‖ right. An empty tree is 32 zero bytes.

Only branch nodes and leaves are kept, so memory is O(n). An update costs O(256) per changed entity, inserts and deletes included. The daemon keeps the tree in its own process and sends it only the records that changed since the last commit.

## The ledger (`xylarium/uplink/ledger.py`)

The universe runs on its own clock, its cycle `u`, and is never bound to TUniversal's height. At each committed moment it appends the hypha's act to `runs/<universe>.ledger.rec`. The act is ACT_DOMAIN sub-kind 8, 320 bytes:

```
[0x3E][domain 32][0x80 0 8][u u64][commitment 32][events 32][final point 84][parent 32][nonce 32][sig 64]
```

- **Signature.** By the domain reserve, over `"mycelium domain ledger v1"` ‖ domain ‖ u ‖ commitment ‖ events ‖ point ‖ parent ‖ nonce.
- **Events digest.** A positional Merkle root over the inputs since the parent entry, in applied order. Each leaf is `derive_key("mycelium ledger event v1")` over point ‖ u ‖ key_len ‖ key ‖ put_args.
- **Inputs file.** The inputs themselves are appended, as those same bytes, to `runs/<universe>.inputs.rec`.
- **Posting.** Entries are kept locally until the hypha's act ships. When posted, each is re-signed with parent = the court's returned entry hash.

## Costs (the live universe, 2026-10-09)

| | before | after |
|---|---|---|
| save on disk | 137 MB JSON | 5.7 MB record stream |
| records | 3.48M fields | 270k entities |
| commitment | 56 s re-hash of the file's text | 88 s once, then 0.22 s per 100 changed entities |
| stop with save / resume | — | 6 s / 13 s |
