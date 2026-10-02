"""
Xylarium institutions: money, the exchange and the Reserve are founded by peoples - not found waiting for them.

In a cosmic universe (cosmos.py) nothing of the money layer exists at the clock's year 0: no currency in
circulation, no central bank, no exchange, no Reserve, no great powers' vaults. Each is founded when the problem it
solves first appears:

  COIN      a people founds its money when it founds its state (ways.py): a state taxes, and a tax needs a unit.
            It is issued by the people's own treasury on commodity backing (the reserve regime - a coin is a claim
            on the staple or metal at par, regimes.py); its supply is what its taxes mint from then on. A people
            takes up a money already in its region only if it has met that money's issuers (contact.py: one cannot
            use a coin from people one has never traded with) - a union, recorded as such; otherwise it strikes its
            own, under a code of its own name, and every world of the people - and every daughter it settles -
            uses it. A people may later change its regime by the one rule (regimes.py).
  EXCHANGE  long-distance trade needs a clearing house: the exchange is founded when two peoples with different
            monies first meet (contact.py), or when the first starport opens, whichever comes first. Each issuing
            state deposits a quarter of its treasury as the local side of its money's pool; the exchange's own
            unit (SOL) is issued against it at par - a declared mint, the house's founding. A money issued later
            opens its pool the same way when it is founded.
  RESERVE   a lender of last resort for the exchange's unit, founded once the exchange stands and two central banks
            trade through it (the Federal Reserve: SOL's central bank).

Until then the money seasons (policy, banks, re-anchoring, prices, liquidity, regimes, the Reserve) have nothing to
act on, and do nothing. Every founding is a ledger event. Settled, primordial and forager universes keep the
institutions their genesis gives them.
"""

from typing import Any, Dict, List, Optional

DEPOSIT_SHARE = 0.25            # of an issuing state's treasury, put up as its money's side of the exchange pool


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "institutions")


def founding(kernel: Any) -> bool:
    """Whether this universe founds its institutions (a cosmic one) rather than starting with them."""
    return bool(stats(kernel).get("founding"))


def issued(kernel: Any, cur: str) -> bool:
    return not founding(kernel) or cur in stats(kernel)["currencies"] or (cur == "SOL" and stats(kernel)["exchange"])


def reserve_founded(kernel: Any) -> bool:
    return not founding(kernel) or bool(stats(kernel)["reserve"])


def depth(kernel: Any, cur: str, side: str, default: float) -> float:
    """The depth a pool was founded with (its bank's reference), or the settled galaxy's seed."""
    rec = stats(kernel)["pools"].get(cur)
    return float(rec[side]) if rec else default


# ---------------------------------------------------------------------- genesis: nothing yet
def genesis(kernel: Any) -> None:
    """Before the money baseline is read: unfound every institution and empty every vault."""
    st = stats(kernel)
    st["founding"] = True
    fxm = kernel.fx_market
    fxm.pools.clear()
    fxm.cross_pools.clear()
    kernel.banking.banks.clear()
    kernel.banking.stamp.clear()
    fed = kernel.federal_reserve
    fed.treasury = 0
    fed.bounty_escrow.clear()
    for f in kernel.factions.factions.values():
        f.vault.clear()
    for s in kernel.sectors.values():
        for p in s.planets:
            p.treasury = 0
            p.household_purse = 0
    mp = getattr(kernel, "monetary_policy", None)
    if mp is not None and hasattr(mp, "targets"):
        mp.targets.clear()
    state.of(kernel, "regimes")["by_currency"].clear()


# ---------------------------------------------------------------------- foundings
def _event(kernel: Any, kind: str, title: str, actors: List[str], planet: Any = None, cause: str = "",
           what: Optional[str] = None) -> None:
    from xylarium.kernel import history, primordial
    history.event(kernel, kind, title, actors=actors, planet=planet, cause=cause)
    if what:
        primordial.first(kernel, what, title)


def found_currency(kernel: Any, planet: Any) -> Optional[str]:
    """A people founding its state founds its money (or adopts its region's, if a neighbour issued it first)."""
    if not founding(kernel):
        return None
    from xylarium.kernel import knowledge, regimes
    from xylarium.kernel.banking import CentralBank
    st = stats(kernel)
    cur = planet.currency
    people = getattr(planet.civilization, "name", planet.name)
    holder = knowledge.holder_of_planet(planet)
    if cur in st["currencies"]:
        rec = st["currencies"][cur]
        if holder in rec["peoples"]:
            return None
        if _met(kernel, holder, rec["peoples"]):
            rec["peoples"].append(holder)
            _event(kernel, "MONETARY_UNION", f"The {people} take up the {rec['name']}", [holder, rec["issuer"]],
                   planet, cause="a neighbour's money was already in their markets")
            return None
        cur = _code_for(kernel, people)                    # strangers' coin is no coin: it strikes its own
        _rebase(kernel, holder, cur)
    name = f"coin of the {people}"
    bank = CentralBank(currency=cur, name=f"Treasury of the {people}", federation=people,
                       governor=f"the first keeper of {planet.name}",
                       alignment=round(float(getattr(planet.civilization, "alignment", 0.0) or 0.0), 3), reserves=0)
    kernel.banking.banks[cur] = bank
    kernel.banking.stamp[cur] = 0.0
    st["currencies"][cur] = {"name": name, "issuer": holder, "peoples": [holder], "founded": kernel.cycle_count,
                             "world": planet.id}
    regimes.stats(kernel)                                    # its regime record
    regimes.adopt(kernel, cur, "reserve")                    # a coin is a claim on a commodity at par
    _event(kernel, "COINAGE", f"The {people} strike the first {name}", [holder], planet,
           cause="a state taxes, and a tax needs a unit", what="first_coin")
    if st["exchange"]:
        _open_pool(kernel, cur)
    return f"[MONEY] The {people} of {planet.name} found their money ({cur})."


def _met(kernel: Any, holder: str, peoples: List[str]) -> bool:
    from xylarium.kernel import contact
    fam = contact.stats(kernel)["familiarity"]
    return any(contact._key(holder, q) in fam for q in peoples)


def _code_for(kernel: Any, people: str) -> str:
    """A money's code from its people's name (three letters), unique among every money there is or was meant to be."""
    from xylarium.config import CURRENCIES
    taken = set(CURRENCIES) | set(stats(kernel)["currencies"])
    letters = [c for c in people.upper() if "A" <= c <= "Z"] or ["X"]
    for i in range(1, len(letters)):
        for j in range(i + 1, len(letters)):
            code = letters[0] + letters[i] + letters[j]
            if code not in taken:
                return code
    n = 2
    while f"{letters[0]}{letters[-1]}{n}" in taken:
        n += 1
    return f"{letters[0]}{letters[-1]}{n}"


def _rebase(kernel: Any, holder: str, cur: str) -> None:
    """Every world of a people takes its own money (they were stateless: nothing in them was money yet)."""
    from xylarium.kernel import knowledge
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and knowledge.holder_of_planet(p) == holder:
                p.currency = cur


def _issuers(kernel: Any, cur: str) -> List[Any]:
    from xylarium.kernel import ways
    return [p for s in kernel.sectors.values() for p in s.planets
            if p.currency == cur and p.population > 0 and getattr(p, "civilization", None) is not None
            and not ways.stateless(p)]


def _open_pool(kernel: Any, cur: str) -> bool:
    from xylarium.config import PRICE_LEVEL
    from xylarium.kernel import ledger
    if cur in kernel.fx_market.pools:
        return True
    local = 0
    for p in _issuers(kernel, cur):
        put = int(p.treasury * DEPOSIT_SHARE)
        p.treasury -= put
        local += put
    if local <= 0:
        return False
    sol = int(local / PRICE_LEVEL.get(cur, 1.0))
    if sol <= 0:
        for p in _issuers(kernel, cur)[:1]:
            p.treasury += local                               # too little to make a market: given back
        return False
    ledger.mint("exchange_founding", sol, "SOL")              # the house's own unit, issued against the deposit
    fxm = kernel.fx_market
    fxm.pools[cur] = {"sol": float(sol), "local": float(local)}
    from xylarium.config import FX_FEE
    fxm.volume_sol.setdefault(cur, 0.0)
    fxm.fees.setdefault(cur, FX_FEE)
    fxm.fees_collected.setdefault(cur, 0.0)
    stats(kernel)["pools"][cur] = {"sol": sol, "local": local, "opened": kernel.cycle_count}
    return True


def found_exchange(kernel: Any, why: str) -> Optional[str]:
    st = stats(kernel)
    if not founding(kernel) or st["exchange"] or not st["currencies"]:
        return None
    opened = [cur for cur in sorted(st["currencies"]) if _open_pool(kernel, cur)]
    if not opened:
        return None
    st["exchange"] = {"founded": kernel.cycle_count, "why": why}
    _event(kernel, "EXCHANGE", "The first exchange opens", [st["currencies"][c]["issuer"] for c in opened],
           cause=why, what="first_exchange")
    return f"[MONEY] The first exchange opens ({why}): {', '.join(opened)} trade through it."


def found_reserve(kernel: Any) -> Optional[str]:
    from xylarium.kernel.banking import CentralBank
    st = stats(kernel)
    if not founding(kernel) or st["reserve"] or not st["exchange"]:
        return None
    if len([c for c in kernel.banking.banks if c != "SOL"]) < 2:
        return None
    kernel.banking.banks["SOL"] = CentralBank(currency="SOL", name="the Reserve of the exchange",
                                              federation="the exchange", governor="the Reserve's board",
                                              alignment=0.0, reserves=0)
    kernel.banking.stamp["SOL"] = 0.0
    st["reserve"] = {"founded": kernel.cycle_count}
    _event(kernel, "RESERVE", "The Reserve is founded", sorted(st["currencies"][c]["issuer"] for c in st["currencies"]),
           cause="two central banks trade through one exchange: someone must lend when it runs dry",
           what="first_reserve")
    return "[MONEY] The Reserve is founded: the exchange's unit has a lender of last resort."


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    if not founding(kernel):
        return []
    from xylarium.kernel import contact, ways
    logs: List[str] = []
    st = stats(kernel)
    for s in kernel.sectors.values():                       # a state founded outside ways (seeded, freed) mints too
        for p in s.planets:
            if p.population > 0 and getattr(p, "civilization", None) is not None and not ways.stateless(p) \
                    and p.currency not in st["currencies"]:
                line = found_currency(kernel, p)
                if line:
                    logs.append(line)
    if not st["exchange"]:
        ports = any(s.port is not None for s in kernel.sectors.values())
        met = False
        if len(st["currencies"]) >= 2:
            issuers = {r["issuer"]: c for c, r in st["currencies"].items()}
            fam = contact.stats(kernel)["familiarity"]
            met = any(a in issuers and b in issuers and issuers[a] != issuers[b]
                      for a, _, b in (k.partition("|") for k in fam))
        if ports or met:
            line = found_exchange(kernel, "the first starport opens" if ports and not met else
                                  "two monies meet")
            if line:
                logs.append(line)
    else:
        for cur in st["currencies"]:
            _open_pool(kernel, cur)
    line = found_reserve(kernel)
    if line:
        logs.append(line)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"founding": bool(st.get("founding")), "currencies": {c: r["name"] for c, r in st["currencies"].items()},
            "exchange": bool(st["exchange"]), "reserve": bool(st["reserve"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="institutions",
    state=lambda: {"founding": False, "currencies": {}, "exchange": None, "reserve": None, "pools": {}},
    season=quarter,
    summary=summary,
))
