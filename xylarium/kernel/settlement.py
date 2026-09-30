"""
Xylarium: the settlement chain - synthetic, in-game, and shaped for the mesh uplink.

The long-term plan is for kernels to uplink into the netstratum mesh and settle upstream
through the rail ladder (R2 Aperture -> R3 Strand -> R4 Court / pow++). Until then the
kernel keeps its own chain-shaped record, so nothing has to be re-plumbed when the mesh lands:

  * Receipts: institutional money movements (central-bank interventions, credit advances,
    repayments, write-offs) are appended as receipts - who, to whom, how much, which money,
    why, when - with a running sequence number.
  * Settlement blocks: every fiscal quarter the kernel seals a block: height, cycle, the previous
    block's hash, the quarter's receipts (hashed into a receipts root), each currency's money
    supply and the ledger's declared mints and burns, the clearing union's STAMP positions, and a
    state root hashing every account balance in the universe. Blocks link by hash; any tampering
    with a sealed block breaks verification.
  * Export: ``export_batch`` renders the blocks since a height as the batch a kernel would commit
    upstream - low frequency and per quarter, never per game tick (netstratum 01_ECONOMY: the
    chain never sees a game tick; players never need a wallet).

Nothing here touches real value. Real-world settlement belongs to the Anchor/Court rail alone,
behind the netstratum guardrails (opt-in, no pay-to-win, regulatory review first).
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from xylarium.config import SETTLEMENT_RECEIPTS_KEPT_BLOCKS

GENESIS_HASH = "0" * 64


def _h(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class SettlementChain:
    def __init__(self) -> None:
        self.blocks: List[Dict[str, Any]] = []
        self.pending: List[Dict[str, Any]] = []
        self.seq: int = 0

    # ------------------------------------------------------------------ receipts
    def add(self, kernel: Any, kind: str, frm: str, to: str, amount: int, currency: str, memo: str = "") -> Dict[str, Any]:
        self.seq += 1
        receipt = {"seq": self.seq, "cycle": int(getattr(kernel, "cycle_count", 0)), "kind": kind,
                   "from": frm, "to": to, "amount": int(amount), "currency": currency, "memo": memo}
        self.pending.append(receipt)
        return receipt

    # ------------------------------------------------------------------ blocks
    @staticmethod
    def state_root(kernel: Any) -> str:
        """A hash over every money-holding account in the universe (the balances a block attests to)."""
        accounts: Dict[str, Any] = {}
        for cid, c in kernel.captains.items():
            accounts[f"captain:{cid}"] = [c.credits, sorted(c.fx_wallet.items())]
        for sid, s in kernel.sectors.items():
            if s.port is not None:
                accounts[f"port:{sid}"] = [s.port.currency, s.port.treasury]
            for p in s.planets:
                if p.treasury:
                    accounts[f"planet:{p.id}"] = [p.currency, p.treasury]
        for t, comp in kernel.market_manager.companies.items():
            accounts[f"company:{t}"] = comp.treasury
        accounts["federal_reserve"] = kernel.federal_reserve.total_holdings
        banking = getattr(kernel, "banking", None)
        if banking is not None:
            for cur, b in banking.banks.items():
                accounts[f"bank:{cur}"] = [b.reserves, sorted((k, v["debt"]) for k, v in b.loans.items())]
        for cur, pool in kernel.fx_market.pools.items():
            accounts[f"pool:{cur}"] = [int(pool["sol"]), int(pool["local"])]
        for pair, pool in getattr(kernel.fx_market, "cross_pools", {}).items():
            accounts[f"pool:{pair}"] = [int(pool["a"]), int(pool["b"])]
        factions = getattr(kernel, "factions", None)
        if factions is not None:
            for fid, f in factions.factions.items():
                if f.vault:
                    accounts[f"faction:{fid}"] = sorted(f.vault.items())
        return _h(accounts)

    def seal(self, kernel: Any) -> Dict[str, Any]:
        from xylarium.kernel.ledger import money_supply
        supply = money_supply(kernel)
        banking = getattr(kernel, "banking", None)
        prev = self.blocks[-1]["hash"] if self.blocks else GENESIS_HASH
        body = {
            "height": len(self.blocks),
            "cycle": int(kernel.cycle_count),
            "kernel_seed": getattr(kernel, "seed", None),
            "prev_hash": prev,
            "receipts_root": _h(self.pending),
            "receipt_count": len(self.pending),
            "supply": {cur: b["total"] for cur, b in supply.items()},
            "declared": {f"{src}|{cur}": v for (src, cur), v in kernel.ledger.minted.items()},
            "burned": {f"{src}|{cur}": v for (src, cur), v in getattr(kernel.ledger, "burned", {}).items()},
            "stamp": {k: round(v, 6) for k, v in (banking.stamp.items() if banking else [])},
            "state_root": self.state_root(kernel),
        }
        block = dict(body, hash=_h(body), receipts=list(self.pending))
        self.blocks.append(block)
        self.pending = []
        # Keep every header forever; keep receipt bodies only for recent blocks (the batch window)
        for old in self.blocks[:-SETTLEMENT_RECEIPTS_KEPT_BLOCKS]:
            old["receipts"] = []
        return block

    def verify(self) -> Optional[str]:
        """Returns None if the chain is intact, else a description of the first broken link."""
        prev = GENESIS_HASH
        for block in self.blocks:
            body = {k: v for k, v in block.items() if k not in ("hash", "receipts")}
            if block["prev_hash"] != prev:
                return f"block {block['height']}: prev_hash does not match block {block['height'] - 1}"
            if _h(body) != block["hash"]:
                return f"block {block['height']}: contents do not match its hash"
            if block["receipts"] and _h(block["receipts"]) != block["receipts_root"]:
                return f"block {block['height']}: receipts do not match their root"
            prev = block["hash"]
        return None

    def export_batch(self, since_height: int = 0) -> Dict[str, Any]:
        """The settlement batch a kernel would commit upstream (R2/R3 synthetic today; R4 when pow++ lands)."""
        blocks = [b for b in self.blocks if b["height"] >= since_height]
        return {"format": "xylarium-settlement/1", "from_height": since_height,
                "to_height": blocks[-1]["height"] if blocks else since_height - 1,
                "tip": blocks[-1]["hash"] if blocks else (self.blocks[-1]["hash"] if self.blocks else GENESIS_HASH),
                "blocks": blocks}

    # ------------------------------------------------------------------ persistence
    def to_dict(self) -> Dict[str, Any]:
        return {"blocks": self.blocks, "pending": self.pending, "seq": self.seq}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SettlementChain":
        c = cls()
        c.blocks = list(d.get("blocks", []))
        c.pending = list(d.get("pending", []))
        c.seq = int(d.get("seq", 0))
        return c
