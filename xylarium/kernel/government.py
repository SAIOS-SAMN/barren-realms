"""
Xylarium government: two engines - the public purse and private commerce.

Starports are government property: one per star system, seated at its host world (the most populous), run by the
system's government. Commercial orbital stations are private property: built at individual worlds by investors,
earning their owners' profit and paying commercial tax. So money runs through two engines:

  * The public engine. A government's starports pay it dues (a share of each port's seasonal surplus), commercial
    stations pay it tax, courts pay it fines. Each season its budget office spends part of the treasury back into
    its jurisdiction:
      - grants: social development for its worlds (half to the council's vault for works, half to households)
      - endowment: science and culture (civilizations' research, paid through their vaults)
      - security: garrisons' pay to the worlds' households - and the law's presence rises with it (law.py)
      - infrastructure: its starports' treasuries (restocking, wages, credit)
      - a stipend to the office holder (politics is a career)
    How the budget divides follows the government's alignment (the Light funds its people, the Dark its guns) -
    unless a player holds the office and sets it by hand. Budgets run automated by default, so players who never
    touch politics still live under a working government.
  * The private engine. Investors build stations where travellers cannot find beds; receipts go to the owner, less
    the commercial tax. Owners compound their wealth; governments fund development from what they collect.

Jurisdiction: a great power's territory; else a sovereign civilization seated in the system (it runs the
system's starport, and its world's vault is its treasury); else the Federation (core) or the Frontier Compact
(borderlands); in the Deep Void there is no government - the starport is a syndicate free port and keeps what
it earns.

Offices: the Federation's budget office is the Senate's Master of Coin (elected); the Compact's goes each season
to the captain with the most lobbying influence at its Trade Council; great powers' offices are held by their
own hierarchies (automated). Every transfer here moves money between counted stocks - nothing is minted.
"""

from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import PRICE_LEVEL

PORT_DUES_SHARE = 0.3            # share of a starport's seasonal surplus paid to its government
COMMERCIAL_TAX = 0.12            # share of a commercial station's receipts paid to the system's government
BUDGET_SPEND_RATE = 0.25         # share of the spendable treasury a budget office spends each season
GREAT_POWER_FLOOR_SOL = 60_000   # a great power keeps this much (SOL-value) for its fleets before budgeting
STIPEND_SHARE = 0.02             # the office holder's pay, out of what the office spends
SECURITY_SOL_PER_PRESENCE = 20_000   # a season's security spending (SOL) per unit of the law's presence
CATEGORIES = ("grants", "endowment", "security", "infrastructure")
BUDGETED = ("FEDERATION", "COMPACT", "IMPERIUM", "ZEALOT")


# ---------------------------------------------------------------------- jurisdiction
def sovereign_civ_world(sector: Any) -> Optional[Any]:
    """The seat of a sovereign civilization in this system (unowned, not a great power's), if any."""
    seats = [p for p in sector.planets if getattr(p, "civilization", None) is not None and p.owner_id is None
             and not getattr(p, "faction_id", None) and not getattr(p.civilization, "faction_id", None)
             and not getattr(p, "natives", None) and p.population > 0]
    return max(seats, key=lambda p: p.population) if seats else None


def government_of(kernel: Any, sector: Any) -> Tuple[str, Any]:
    """('faction', Faction) | ('civ', seat planet) | ('syndicate', None) - read once a season per system."""
    season = getattr(kernel, "cycle_count", 0) // 25
    cache = getattr(kernel, "_gov_cache", None)
    if cache is None or cache[0] != season:
        cache = kernel._gov_cache = (season, {})
    hit = cache[1].get(sector.id)
    if hit is None:
        hit = cache[1][sector.id] = _government_of(kernel, sector)
    return hit


def _government_of(kernel: Any, sector: Any) -> Tuple[str, Any]:
    fm = kernel.factions
    owner = fm.owner_of(sector.id)
    if owner in ("IMPERIUM", "ZEALOT") and owner in fm.factions:
        return "faction", fm.factions[owner]
    seat = sovereign_civ_world(sector)
    if seat is not None:
        return "civ", seat
    auth = fm.authority_for(sector)
    if auth.id in ("FEDERATION", "COMPACT"):
        return "faction", auth
    return "syndicate", None


def host_world(sector: Any) -> Optional[Any]:
    live = [p for p in sector.planets if p.population > 0]
    return max(live, key=lambda p: p.population) if live else (sector.planets[0] if sector.planets else None)


FOUNDING_PEOPLES = {"Terran Federation": "FEDERATION"}    # the peoples who are a government's own citizens


def assign_ports(kernel: Any) -> None:
    """Each starport is bound to its system: its host world and the government that runs it."""
    for sec in kernel.sectors.values():
        for p in sec.planets:
            civ = getattr(p, "civilization", None)
            if civ is not None and not civ.faction_id and civ.name in FOUNDING_PEOPLES:
                civ.faction_id = FOUNDING_PEOPLES[civ.name]
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None:
            continue
        kind, gov = government_of(kernel, sec)
        port.leisure["owner"] = gov.id if kind == "faction" else (f"CIV:{gov.id}" if kind == "civ" else "SYNDICATE")
        host = host_world(sec)
        port.leisure["host"] = host.id if host is not None else None
        port.leisure["host_type"] = host.planet_type if host is not None else None


# ---------------------------------------------------------------------- paying a government
def _convert(kernel: Any, from_cur: str, to_cur: str, amount: int) -> int:
    if from_cur == to_cur or amount <= 0:
        return amount
    out, _ = kernel.fx_market.convert(from_cur, to_cur, amount)
    return out


def pay_government(kernel: Any, sector: Any, currency: str, amount: int, source: str) -> str:
    """Money owed to the system's government (starport dues, commercial tax). Returns who received it.
    Where there is no government (the Deep Void) the payer keeps it and the caller is told so."""
    if amount <= 0:
        return "none"
    kind, gov = government_of(kernel, sector)
    st = stats(kernel)
    if kind == "faction":
        gov.vault[currency] = gov.vault.get(currency, 0) + amount
        rec = st["revenue"].setdefault(gov.id, {})
        rec[source] = rec.get(source, 0) + int(kernel.fx_market.to_sol_value(currency, amount))
        return gov.id
    if kind == "civ":
        # A sovereign civilization runs its own stardock; inside the Federation's or the Compact's space it is a
        # member, and a third of what it collects is its membership dues
        auth = kernel.factions.authority_for(sector)
        if auth.id in ("FEDERATION", "COMPACT"):
            share = amount // 3
            auth.vault[currency] = auth.vault.get(currency, 0) + share
            rec = st["revenue"].setdefault(auth.id, {})
            rec["membership_dues"] = rec.get("membership_dues", 0) + int(kernel.fx_market.to_sol_value(currency, share))
            amount -= share
        gov.treasury += _convert(kernel, currency, gov.currency, amount)
        st["civ_revenue"] = st.get("civ_revenue", 0) + int(kernel.fx_market.to_sol_value(currency, amount))
        return f"CIV:{gov.id}"
    return "none"


# ---------------------------------------------------------------------- offices and budgets
def stats(kernel: Any) -> Dict[str, Any]:
    s = getattr(kernel, "government_stats", None)
    if s is None:
        s = kernel.government_stats = {"revenue": {}, "spent": {}, "stipends": 0, "grants_directed": 0}
    return s


def offices(kernel: Any) -> Dict[str, Dict[str, Any]]:
    o = getattr(kernel, "offices", None)
    if o is None:
        o = kernel.offices = {}
    for fid in BUDGETED:
        o.setdefault(fid, {"holder": None, "auto": True, "shares": None})
    return o


def auto_shares(alignment: float) -> Dict[str, float]:
    """How a government divides its budget when nobody sets it by hand: the Light funds its people and its
    learning, the Dark its guns; everyone keeps the ports running."""
    light, dark = max(0.0, alignment), max(0.0, -alignment)
    raw = {"grants": 0.30 + 0.30 * light - 0.15 * dark, "endowment": 0.15 + 0.15 * light,
           "security": 0.25 + 0.35 * dark, "infrastructure": 0.20}
    total = sum(max(0.0, v) for v in raw.values())
    return {k: round(max(0.0, v) / total, 4) for k, v in raw.items()}


def _elect(kernel: Any) -> None:
    """Who holds each budget office this season."""
    o = offices(kernel)
    gm = getattr(kernel, "governance_manager", None)
    if gm is not None:
        coin = gm.offices.get(next((k for k in gm.offices if "COIN" in str(k).upper()), None)) if gm.offices else None
        holder = getattr(coin, "holder_id", None) if coin is not None else None
        o["FEDERATION"]["holder"] = holder if holder in kernel.captains else None
    tc = getattr(getattr(kernel, "market_manager", None), "trade_council", None)
    funds = getattr(tc, "lobbying_funds", None) or {}
    if funds:
        top = max(funds, key=lambda c: funds[c])
        o["COMPACT"]["holder"] = top if top in kernel.captains and funds[top] > 0 else None
    for fid in ("IMPERIUM", "ZEALOT"):
        o[fid]["holder"] = None


def shares_for(kernel: Any, fid: str) -> Dict[str, float]:
    o = offices(kernel)[fid]
    if not o.get("auto", True) and o.get("shares"):
        return o["shares"]
    return auto_shares(float(kernel.factions.factions[fid].alignment))


def set_budget(kernel: Any, captain: Any, fid: str, shares: Optional[Dict[str, float]] = None,
               auto: Optional[bool] = None) -> str:
    """The office holder sets the budget by hand, or hands it back to the automated steward."""
    fid = (fid or "").upper()
    o = offices(kernel).get(fid)
    if o is None:
        raise ValueError("Budget offices: " + ", ".join(BUDGETED) + ".")
    if o.get("holder") != captain.id:
        raise ValueError(f"You do not hold the {fid} budget office.")
    if auto:
        o["auto"], o["shares"] = True, None
        return f"{fid} budget returned to its steward (divided by the government's alignment)."
    clean = {k: max(0.0, float((shares or {}).get(k, 0.0))) for k in CATEGORIES}
    total = sum(clean.values())
    if total <= 0:
        raise ValueError("Give shares for grants, endowment, security and infrastructure.")
    o["auto"], o["shares"] = False, {k: round(v / total, 4) for k, v in clean.items()}
    return f"{fid} budget set: " + ", ".join(f"{k} {v:.0%}" for k, v in o["shares"].items()) + "."


def jurisdiction(kernel: Any, fid: str) -> List[Any]:
    out = []
    for s in kernel.sectors.values():
        kind, gov = government_of(kernel, s)
        if kind == "faction" and gov.id == fid:
            out.append(s)
    return out


def _spendable(kernel: Any, f: Any) -> Dict[str, int]:
    """What the office may spend this season, per currency held."""
    floor_sol = GREAT_POWER_FLOOR_SOL if f.id in ("IMPERIUM", "ZEALOT") else 0
    total_sol = sum(kernel.fx_market.to_sol_value(c, a) for c, a in f.vault.items() if a > 0)
    if total_sol <= floor_sol:
        return {}
    rate = BUDGET_SPEND_RATE * (total_sol - floor_sol) / total_sol
    return {c: int(a * rate) for c, a in f.vault.items() if a > 0 and int(a * rate) > 0}


def _pay_world(kernel: Any, f: Any, cur: str, amount: int, planet: Any, household_share: float) -> None:
    f.vault[cur] -= amount
    local = _convert(kernel, cur, planet.currency, amount)
    to_house = int(local * household_share)
    planet.household_purse += to_house
    planet.treasury += local - to_house


def _spend(kernel: Any, f: Any, logs: List[str]) -> None:
    budget = _spendable(kernel, f)
    if not budget:
        return
    sectors = jurisdiction(kernel, f.id)
    worlds = [p for s in sectors for p in s.planets if p.population > 0 and not getattr(p, "natives", None)]
    ports = [s.port for s in sectors if s.port is not None]
    shares = shares_for(kernel, f.id)
    st = stats(kernel)
    spent = st["spent"].setdefault(f.id, {k: 0 for k in CATEGORIES + ("stipend",)})
    o = offices(kernel)[f.id]
    holder = kernel.captains.get(o.get("holder")) if o.get("holder") else None
    pop = sum(p.population for p in worlds) or 1
    for cur, amount in budget.items():
        sol_rate = kernel.fx_market.to_sol_value(cur, 1.0)
        if holder is not None:
            pay = int(amount * STIPEND_SHARE)
            if pay > 0:
                f.vault[cur] -= pay
                from xylarium.kernel.fx import credit
                credit(holder, cur, pay)
                spent["stipend"] += int(pay * sol_rate)
                st["stipends"] += int(pay * sol_rate)
                amount -= pay
        for cat in CATEGORIES:
            part = int(amount * shares.get(cat, 0.0))
            if part <= 0:
                continue
            if cat == "infrastructure":
                if not ports:
                    continue
                each = part // len(ports)
                for port in ports:
                    if each > 0:
                        f.vault[cur] -= each
                        port.treasury += _convert(kernel, cur, port.currency, each)
                spent[cat] += int(each * len(ports) * sol_rate)
                continue
            if not worlds:
                continue
            targets = worlds
            if cat == "endowment":
                targets = [p for p in worlds if getattr(p, "civilization", None) is not None] or worlds
            tpop = sum(p.population for p in targets) or 1
            paid = 0
            for p in targets:
                n = int(part * p.population / tpop)
                if n <= 0:
                    continue
                _pay_world(kernel, f, cur, n, p, {"grants": 0.5, "endowment": 0.0, "security": 1.0}[cat])
                paid += n
                if cat == "endowment" and getattr(p, "civilization", None) is not None:
                    p.civilization.research_points += max(1, int(n * sol_rate) // 100)
            spent[cat] += int(paid * sol_rate)
            if cat == "security":
                f.stats["security_q"] = f.stats.get("security_q", 0) + int(paid * sol_rate)
    _ = pop


def security_presence(kernel: Any, sector: Any) -> float:
    """The law's extra presence bought by its government's last security budget, spread over its systems."""
    kind, gov = government_of(kernel, sector)
    if kind != "faction":
        return 0.0
    q = float((gov.stats or {}).get("security_last", 0))
    n = max(1, int((gov.stats or {}).get("systems", 1)))
    return q / n / SECURITY_SOL_PER_PRESENCE


def direct_grant(kernel: Any, captain: Any, fid: str, planet: Any, amount_sol: int) -> str:
    """An office holder earmarks a grant to one world (within a season's spendable budget)."""
    fid = (fid or "").upper()
    o = offices(kernel).get(fid)
    if o is None or o.get("holder") != captain.id:
        raise ValueError(f"You do not hold the {fid} budget office.")
    f = kernel.factions.factions[fid]
    if planet.sector_id not in {s.id for s in jurisdiction(kernel, fid)}:
        raise ValueError(f"{planet.name} lies outside the {fid}'s jurisdiction.")
    budget = _spendable(kernel, f)
    cur = f.currency if f.currency in budget else next(iter(budget), None)
    if cur is None:
        raise ValueError("The treasury has nothing to spend this season.")
    amount = min(budget[cur], int(amount_sol * kernel.fx_market.rate(cur)))
    if amount <= 0:
        raise ValueError("Nothing to grant.")
    _pay_world(kernel, f, cur, amount, planet, 0.5)
    stats(kernel)["grants_directed"] += int(kernel.fx_market.to_sol_value(cur, amount))
    return f"Grant of {amount:,} {cur} from the {fid} treasury to {planet.name}."


def quarter(kernel: Any) -> List[str]:
    """Ports are bound to their systems, offices change hands, and every budget office spends its season."""
    logs: List[str] = []
    kernel._gov_cache = None                  # jurisdictions are re-read at each season's close
    assign_ports(kernel)
    _elect(kernel)
    for fid in BUDGETED:
        f = kernel.factions.factions.get(fid)
        if f is None:
            continue
        f.stats["security_q"] = 0
        _spend(kernel, f, logs)
        f.stats["security_last"] = f.stats.pop("security_q", 0)
        f.stats["systems"] = max(1, len(jurisdiction(kernel, fid)))
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    o = offices(kernel)
    owners: Dict[str, int] = {}
    for s in kernel.sectors.values():
        if s.port is not None:
            k = s.port.leisure.get("owner", "?")
            k = "CIV" if str(k).startswith("CIV:") else k
            owners[k] = owners.get(k, 0) + 1
    vaults = {fid: int(sum(kernel.fx_market.to_sol_value(c, a) for c, a in kernel.factions.factions[fid].vault.items()))
              for fid in BUDGETED if fid in kernel.factions.factions}
    return {"revenue": st["revenue"], "spent": st["spent"], "stipends": st["stipends"],
            "civ_revenue": st.get("civ_revenue", 0), "port_owners": owners, "vaults_sol": vaults,
            "holders": {k: v.get("holder") for k, v in o.items()},
            "auto": {k: v.get("auto", True) for k, v in o.items()}}
