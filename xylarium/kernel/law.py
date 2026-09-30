"""
Xylarium law: jurisdictions, presence, a docket, courts - and money that can be recalled.

  * Jurisdiction. Every sector answers to an authority (FactionManager.authority_for): the Federation,
    the Frontier Compact, the Imperium, the Choir of the Pyre - or no one (anarchy space keeps no court).
  * Presence. How much of the law is actually there: the authority's enforcement standing, the planetary
    security operatives and garrisons of the sector's worlds, the authority's warships present, and Sol's
    turrets. presence = x / (1 + x) - it saturates, it never reaches certainty.
  * The docket. Offences are filed where they happen: defaults on margin debt, piracy (hostile acts),
    theft by covert operations, fraud (forged charts sold), embezzlement. Whether a crime is detected is
    decided by the presence where it happened (a seeded draw): lawless space is a haven because nobody is
    watching, not because a rule says so.
  * Courts sit each fiscal quarter. A conviction orders restitution to the victim and a fine to the
    jurisdiction's treasury (the harm again: double damages).
  * Recall. Money is digital: the court garnishes the offender's wallet directly - its own currency first,
    SOL next, then any other money through the clearing union where that money's central bank cooperates
    (the Deep Void's does not: VOID is where the dark keep their savings). Shares are seized and sold back
    to their company. What still cannot be recovered becomes a warrant (a bounty) and an asset freeze
    (no trading at that authority's ports) until it is settled.
  * Nothing is minted or destroyed: restitution and fines are transfers; an unpaid judgment is a claim.
    Docket law: judged = recovered + outstanding + written off, per case.
"""

import random
import zlib
from typing import Any, Dict, List, Optional

COURTS = ("FEDERATION", "COMPACT", "IMPERIUM", "ZEALOT")
NON_COOPERATING = {"VOID"}            # central banks that refuse foreign garnishment (except their own court)
FINE_MULTIPLE = 1.0                   # the fine equals the harm (with restitution: double damages)


def docket(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "law")


# ---------------------------------------------------------------------- presence
def authority(kernel: Any, sector: Any) -> Optional[Any]:
    factions = getattr(kernel, "factions", None)
    if factions is None or sector is None:
        return None
    return factions.authority_for(sector)


def presence(kernel: Any, sector: Any) -> float:
    auth = authority(kernel, sector)
    if auth is None or auth.id not in COURTS:
        return 0.0
    x = float(getattr(auth, "warrant", 0) or 0) / 5000.0      # the authority's own standing (its warrant size)
    for p in getattr(sector, "planets", []):
        x += getattr(p, "security_operatives", 0) / 10.0 + getattr(p, "garrison_troops", 0) / 500.0
    fleet = set(getattr(auth, "fleet", []) or [])
    x += sum(0.5 for cid in getattr(sector, "captains", []) if cid in fleet)
    if sector.id == 1:
        x += 3.0                          # Sol's turrets
    from xylarium.kernel import government
    x += government.security_presence(kernel, sector)     # what its government's security budget pays for
    return x / (1.0 + x)


# ---------------------------------------------------------------------- filing
def file(kernel: Any, kind: str, offender: Any, sector: Any, harm_sol: int, victim: Optional[Dict[str, Any]] = None,
         note: str = "") -> Optional[Dict[str, Any]]:
    """Record an offence. Detection is drawn against the presence where it happened."""
    if offender is None or harm_sol <= 0 or getattr(offender, "faction_id", None):
        return None
    d = docket(kernel)
    st = d["stats"]
    st["filed"] += 1
    st["by_kind"][kind] = st["by_kind"].get(kind, 0) + 1
    auth = authority(kernel, sector)
    pr = presence(kernel, sector)
    rng = random.Random(zlib.crc32(f"{kernel.cycle_count}:{offender.id}:{kind}:{d['next']}".encode()))
    if auth is None or auth.id not in COURTS or rng.random() >= pr:
        st["unsolved"] += 1
        if pr < 0.2:
            st["haven"] += 1
        return None
    case = {"id": d["next"], "kind": kind, "offender": offender.id, "court": auth.id,
            "currency": getattr(auth, "currency", "SOL") or "SOL", "sector": getattr(sector, "id", None),
            "harm_sol": int(harm_sol), "victim": victim or {}, "cycle": kernel.cycle_count, "status": "OPEN",
            "note": note, "recovered_sol": 0}
    d["next"] += 1
    d["cases"].append(case)
    st["detected"] += 1
    return case


# ---------------------------------------------------------------------- courts
def quarter(kernel: Any) -> List[str]:
    """The courts sit: every open case is judged, garnished, and what remains becomes a warrant."""
    d = docket(kernel)
    logs: List[str] = []
    still: List[Dict[str, Any]] = []
    for case in d["cases"]:
        if case["status"] == "OPEN":
            _judge(kernel, case, logs)
        if case["status"] in ("OPEN", "WARRANT"):
            _collect(kernel, case, logs)
        if case["status"] != "CLOSED":
            still.append(case)
    d["cases"] = still[-400:]
    st = d["stats"]
    st["outstanding_sol"] = sum(c["owed_sol"] for c in d["cases"] if c["status"] == "WARRANT")
    return logs


def _judge(kernel: Any, case: Dict[str, Any], logs: List[str]) -> None:
    st = docket(kernel)["stats"]
    case["restitution_sol"] = case["harm_sol"] if case["victim"] else 0
    case["fine_sol"] = int(case["harm_sol"] * FINE_MULTIPLE)
    case["owed_sol"] = case["restitution_sol"] + case["fine_sol"]
    case["status"] = "WARRANT"
    st["convicted"] += 1
    st["judged_sol"] += case["owed_sol"]
    cap = kernel.captains.get(case["offender"])
    if cap is not None:
        from xylarium.kernel import alignment
        alignment.deed(kernel, cap, "convicted")
        logs.append(f"[COURT:{case['court']}] {cap.name} convicted of {case['kind']} "
                    f"({case['owed_sol']:,} SOL restitution and fine).")


def _collect(kernel: Any, case: Dict[str, Any], logs: List[str]) -> None:
    """Garnish the judgment from the offender's wallets and shares; freeze and warrant what remains."""
    st = docket(kernel)["stats"]
    cap = kernel.captains.get(case["offender"])
    if cap is None:
        # the offender is gone (dead or struck off): the claim dies with them
        st["written_off_sol"] += case["owed_sol"]
        case["owed_sol"] = 0
        case["status"] = "CLOSED"
        return
    got = garnish(kernel, cap, case["owed_sol"], case["court"], case["currency"])
    if got < case["owed_sol"]:
        got += _seize_shares(kernel, cap, case["owed_sol"] - got)
    if got > 0:
        _disburse(kernel, case, got)
        case["owed_sol"] -= got
        case["recovered_sol"] += got
        st["recovered_sol"] += got
    frozen = getattr(cap, "frozen_by", None)
    if frozen is None:
        frozen = cap.frozen_by = []
    if case["owed_sol"] > 0:
        if case["court"] not in frozen:
            frozen.append(case["court"])
            st["freezes"] += 1
        if not case.get("warranted"):
            case["warranted"] = True
            cap.bounty += case["owed_sol"] // 2
            st["warrants"] += 1
            logs.append(f"[WARRANT:{case['court']}] {cap.name}: {case['owed_sol']:,} SOL unpaid - assets frozen, "
                        f"bounty posted.")
    else:
        case["status"] = "CLOSED"
        if not any(c["offender"] == cap.id and c["court"] == case["court"] and c["status"] == "WARRANT"
                   and c is not case for c in docket(kernel)["cases"]):
            if case["court"] in frozen:
                frozen.remove(case["court"])
        from xylarium.kernel import alignment
        alignment.deed(kernel, cap, "restitution")


def garnish(kernel: Any, cap: Any, owed_sol: int, court: str, court_currency: str) -> int:
    """Recall up to ``owed_sol`` (SOL value) from the offender's wallets into SOL held for the court."""
    fxm = kernel.fx_market
    got = 0
    order = [court_currency] + ["SOL"] + [c for c in cap.fx_wallet if c not in (court_currency, "SOL")]
    for cur in order:
        if got >= owed_sol:
            break
        if cur in NON_COOPERATING and court_currency != cur:
            continue
        if cur == "SOL":
            take = min(max(0, cap.credits), owed_sol - got)
            cap.credits -= take
            got += take
            continue
        held = cap.fx_wallet.get(cur, 0)
        if held <= 0:
            continue
        need_local = int((owed_sol - got) * fxm.rate(cur)) + 1
        take = min(held, need_local)
        cap.fx_wallet[cur] = held - take
        got += fxm.swap_to_sol(cur, take)          # cleared through the exchange (conserved)
    if got > owed_sol:                              # rounding surplus stays with the offender
        cap.credits += got - owed_sol
        got = owed_sol
    return got


def _seize_shares(kernel: Any, cap: Any, owed_sol: int) -> int:
    mm = kernel.market_manager
    got = 0
    for ticker in list(getattr(cap, "portfolio", {}) or {}):
        if got >= owed_sol:
            break
        comp = mm.companies.get(ticker)
        held = cap.portfolio.get(ticker, 0)
        if comp is None or held <= 0 or comp.share_price <= 0:
            continue
        n = min(held, (owed_sol - got) // max(1, comp.share_price) + 1)
        before = cap.credits
        ok, _, _ = mm.sell_shares(cap, ticker, n)
        if ok:
            proceeds = cap.credits - before
            take = min(proceeds, owed_sol - got)
            cap.credits -= take
            got += take
    return got


def _disburse(kernel: Any, case: Dict[str, Any], sol: int) -> None:
    """Restitution to the victim first; the rest is the fine, to the jurisdiction's treasury."""
    victim = case["victim"]
    rest = sol
    owed_victim = max(0, case["restitution_sol"] - case.get("paid_victim", 0))
    to_victim = min(rest, owed_victim)
    if to_victim > 0 and _pay(kernel, victim, to_victim):
        case["paid_victim"] = case.get("paid_victim", 0) + to_victim
        rest -= to_victim
    if rest > 0:
        _pay_court(kernel, case["court"], rest)


def _pay(kernel: Any, victim: Dict[str, Any], sol: int) -> bool:
    kind, vid = victim.get("kind"), victim.get("id")
    from xylarium.kernel import fx
    if kind == "captain" and vid in kernel.captains:
        kernel.captains[vid].credits += sol
        return True
    if kind == "company" and vid in kernel.market_manager.companies:
        kernel.market_manager.companies[vid].treasury += sol
        return True
    if kind == "port":
        sec = kernel.sectors.get(vid)
        if sec is not None and sec.port is not None:
            kernel._stardock_revenue(sec, sol)
            return True
    if kind == "planet":
        p = kernel.get_planet(vid)
        if p is not None:
            p.treasury += fx.ACTIVE_FX.swap_sol_to(p.currency, sol) if (fx.ACTIVE_FX and p.currency != "SOL") else sol
            return True
    return False


def _pay_court(kernel: Any, court: str, sol: int) -> None:
    f = kernel.factions.factions.get(court)
    if f is None:
        kernel.federal_reserve.receive(sol, "fines")
        return
    cur = getattr(f, "currency", "SOL") or "SOL"
    from xylarium.kernel import fx
    amount = fx.ACTIVE_FX.swap_sol_to(cur, sol) if (fx.ACTIVE_FX and cur != "SOL") else sol
    f.vault[cur] = f.vault.get(cur, 0) + amount


def frozen_here(kernel: Any, captain: Any, sector: Any) -> bool:
    """A frozen captain cannot trade at the ports of the authority that froze its assets."""
    frozen = getattr(captain, "frozen_by", None)
    if not frozen:
        return False
    auth = authority(kernel, sector)
    return auth is not None and auth.id in frozen


def summary(kernel: Any) -> Dict[str, Any]:
    st = dict(docket(kernel)["stats"])
    st["open_cases"] = sum(1 for c in docket(kernel)["cases"] if c["status"] != "CLOSED")
    return st


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="law",
    state=lambda: {"cases": [], "next": 1, "stats": {"filed": 0, "detected": 0, "unsolved": 0, "convicted": 0,
                                                     "judged_sol": 0, "recovered_sol": 0, "outstanding_sol": 0,
                                                     "written_off_sol": 0, "warrants": 0, "freezes": 0,
                                                     "by_kind": {}, "haven": 0}},
    season=quarter,
    summary=summary,
))
