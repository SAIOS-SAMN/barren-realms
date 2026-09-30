"""
Xylarium: Federal Reserve of Sol.

A single public account that makes the money loop closed instead of minted:
  * Hull insurance: captains pay premiums each maintenance interval; destroyed
    insured hulls are paid a re-arm claim from the reserve (no respawn cash floors).
  * Relief loans: destitute captains borrow from the reserve (even with modest
    existing debt); repayments flow back into it.
  * Antitrust: each fiscal quarter, captains holding more than the absolute or
    relative wealth threshold (or chairing >40% of ISSE market cap) pay a
    progressive surtax into the reserve.
  * Public bounty board: a slice of the reserve is escrowed against wanted
    outlaws; claims are paid from escrow, then from the reserve, never minted.
  * Restitution payments land in the reserve.
"""

from collections import Counter
from typing import Any, Dict, List, Tuple

from xylarium.config import (
    FEDERAL_RESERVE_SEED,
    INSURANCE_PREMIUM_RATE,
    INSURANCE_MIN_PREMIUM,
    INSURANCE_PAYOUT,
    MAINTENANCE_INTERVAL_CYCLES,
    SHIP_CATALOG,
    BANK_LOAN_AMOUNT,
    BANK_DEBT_TOTAL,
    BANK_EMERGENCY_THRESHOLD,
    RELIEF_LOAN_MAX_DEBT,
    ANTITRUST_ABSOLUTE_THRESHOLD,
    ANTITRUST_SHARE_THRESHOLD,
    ANTITRUST_SURTAX_RATE,
    ANTITRUST_ISSE_SHARE_THRESHOLD,
    PUBLIC_BOUNTY_BUDGET_RATE,
    PUBLIC_BOUNTY_MAX_PER_TARGET,
)

# Relative antitrust only applies once the economy is large enough for shares to mean anything
ANTITRUST_MIN_ECONOMY = 200_000


class FederalReserve:
    def __init__(self, treasury: int = FEDERAL_RESERVE_SEED):
        self.treasury: int = treasury
        self.bounty_escrow: Dict[str, int] = {}
        self.stats: Counter = Counter()

    # ------------------------------------------------------------------ insurance
    @staticmethod
    def hull_value(captain: Any) -> int:
        return int(SHIP_CATALOG.get(captain.ship.ship_type, {}).get("price", 0))

    def premium_for(self, captain: Any) -> int:
        return max(INSURANCE_MIN_PREMIUM, int(self.hull_value(captain) * INSURANCE_PREMIUM_RATE))

    def collect_premiums(self, kernel: Any) -> None:
        """Called every maintenance interval: captains who can afford it renew hull cover."""
        through = kernel.cycle_count + MAINTENANCE_INTERVAL_CYCLES
        for cap in kernel.captains.values():
            premium = self.premium_for(cap)
            if cap.credits >= premium * 2:
                cap.credits -= premium
                self.treasury += premium
                cap.insurance_paid_through = through
                self.stats["premiums"] += premium

    def is_insured(self, captain: Any, cycle: int) -> bool:
        return getattr(captain, "insurance_paid_through", 0) >= cycle

    def pay_hull_claim(self, captain: Any, cycle: int) -> int:
        if not self.is_insured(captain, cycle):
            return 0
        payout = min(INSURANCE_PAYOUT, self.treasury)
        if payout > 0:
            self.treasury -= payout
            captain.credits += payout
            self.stats["hull_claims"] += payout
        # A written-off policy must be renewed on the replacement hull
        captain.insurance_paid_through = 0
        return payout

    # --------------------------------------------------------------- relief loans
    def grant_relief_loan(self, captain: Any) -> Tuple[bool, str]:
        if captain.credits >= BANK_EMERGENCY_THRESHOLD:
            return False, (
                f"Federal emergency relief loans are reserved for destitute captains "
                f"(< {BANK_EMERGENCY_THRESHOLD} Cr). You currently have {captain.credits:,} Cr."
            )
        if captain.debt + BANK_DEBT_TOTAL > RELIEF_LOAN_MAX_DEBT:
            return False, (
                f"Relief credit exhausted: outstanding federal debt of {captain.debt:,} Cr would exceed "
                f"the {RELIEF_LOAN_MAX_DEBT:,} Cr relief ceiling."
            )
        if self.treasury < BANK_LOAN_AMOUNT:
            return False, "The Federal Reserve has insufficient liquidity for relief lending this quarter."
        self.treasury -= BANK_LOAN_AMOUNT
        captain.credits += BANK_LOAN_AMOUNT
        captain.debt += BANK_DEBT_TOTAL
        self.stats["relief_loans"] += BANK_LOAN_AMOUNT
        return True, (
            f"Federal Relief Loan approved! Disbursed +{BANK_LOAN_AMOUNT:,} Cr from the Federal Reserve. "
            f"Total debt: {captain.debt:,} Cr (includes 15% surcharge)."
        )

    def receive(self, amount: int, reason: str) -> None:
        if amount > 0:
            self.treasury += amount
            self.stats[reason] += amount

    # ------------------------------------------------------------------- bounties
    def settle_bounty(self, target_id: str, claimed: int) -> int:
        """Pays a bounty claim from escrow first, then the reserve. Returns credits actually payable."""
        funded = min(claimed, self.bounty_escrow.pop(target_id, 0))
        remainder = claimed - funded
        from_reserve = min(remainder, self.treasury)
        self.treasury -= from_reserve
        self.stats["bounties_paid"] += funded + from_reserve
        return funded + from_reserve

    def release_escrow(self, target_id: str) -> None:
        """Returns escrow to the reserve when a bounty is cleared without a claim (e.g. restitution)."""
        self.treasury += self.bounty_escrow.pop(target_id, 0)

    # -------------------------------------------------------------- fiscal quarter
    def fiscal_quarter(self, kernel: Any) -> List[str]:
        logs: List[str] = []
        captains = list(kernel.captains.values())
        total = sum(max(0, c.credits) for c in captains)

        # ISSE concentration by chairmanship
        companies = getattr(getattr(kernel, "market_manager", None), "companies", {}) or {}
        cap_total = sum(c.share_price * c.total_shares for c in companies.values()) or 1
        chaired: Counter = Counter()
        for comp in companies.values():
            chair = getattr(comp, "chairman_id", None)
            if chair:
                chaired[chair] += comp.share_price * comp.total_shares

        for cap in captains:
            thresholds = [ANTITRUST_ABSOLUTE_THRESHOLD]
            if total >= ANTITRUST_MIN_ECONOMY:
                thresholds.append(int(total * ANTITRUST_SHARE_THRESHOLD))
            excess = max(0, cap.credits - min(thresholds))
            rate = ANTITRUST_SURTAX_RATE
            if chaired.get(cap.id, 0) / cap_total > ANTITRUST_ISSE_SHARE_THRESHOLD:
                rate *= 2
                excess = max(excess, cap.credits // 10)
            surtax = int(excess * rate)
            if surtax > 0:
                cap.credits -= surtax
                self.treasury += surtax
                self.stats["antitrust_surtax"] += surtax
                logs.append(f"[ANTITRUST] Federal Monopoly Surtax: {cap.name} remitted {surtax:,} Cr to the Federal Reserve.")

        # Public bounty board: escrow reserve funds against the most-wanted outlaws
        budget = int(self.treasury * PUBLIC_BOUNTY_BUDGET_RATE)
        wanted = sorted((c for c in captains if c.bounty > 0), key=lambda c: -c.bounty)[:3]
        for cap in wanted:
            if budget <= 0:
                break
            topup = min(budget, PUBLIC_BOUNTY_MAX_PER_TARGET - self.bounty_escrow.get(cap.id, 0))
            if topup <= 0:
                continue
            self.treasury -= topup
            budget -= topup
            self.bounty_escrow[cap.id] = self.bounty_escrow.get(cap.id, 0) + topup
            cap.bounty += topup
            self.stats["bounties_posted"] += topup
            logs.append(f"[BOUNTY BOARD] Federal Reserve escrowed +{topup:,} Cr against wanted outlaw {cap.name}.")
        return logs

    # ------------------------------------------------------------------ persistence
    @property
    def total_holdings(self) -> int:
        return self.treasury + sum(self.bounty_escrow.values())

    def to_dict(self) -> Dict[str, Any]:
        return {"treasury": self.treasury, "bounty_escrow": dict(self.bounty_escrow), "stats": dict(self.stats)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FederalReserve":
        fr = cls(treasury=int(data.get("treasury", FEDERAL_RESERVE_SEED)))
        fr.bounty_escrow = {k: int(v) for k, v in data.get("bounty_escrow", {}).items()}
        fr.stats = Counter(data.get("stats", {}))
        return fr
