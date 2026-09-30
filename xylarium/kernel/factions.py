"""
Xylarium: Great powers, the Galactic Policy Deck, and the doctrines that bind them.

Authorities
-----------
Every sector falls under an authority whose doctrine card governs how captains may deal
with non-spacefaring locals (see natives.py):

  * Terran Federation Senate (Federation space)   - card BETA, INTERDICTs violations outright
  * ISSE Frontier Compact (Borderland)            - card GAMMA, issues WARRANTs
  * Aurelian Imperium (Imperial territory)        - card GAMMA, the INQUISITION hunts violators
  * Choir of the Pyre (zealot territory)          - card EPSILON (missionary conversion)
  * no authority (Deep Void)                      - DELTA de facto: nobody enforces anything

A system whose own spacefaring civilization keeps a stricter local custom overrides a laxer
galactic card (solar-system diplomacy). Federation and Compact re-draw their card once per
era along ALPHA <-> DELTA, pulled by the alignment of the captains who sail their space.

The Aurelian Imperium
---------------------
A gothic-bureaucratic human superpower. Each fiscal quarter every Imperial world sets aside
a tithe (ore, organics, Fe, Ti) and drafts manpower; a Bulk Goliath hauls the manifests to
the Segmentum Fortress (without one, half the tithe is lost in transit). Materiel at the
Fortress commissions warships (goods consumed, crew float paid from the Imperial treasury
through the ISSE). Tithes grind morale; worlds below the secession threshold break away.
Techno-heresy (thinking machines, xeno-tech, alien relics) triggers Inquisitorial crises.

The Choir of the Pyre (the Dogma Engine)
----------------------------------------
A zealot theocracy whose dogma consumes prosperity: world surpluses above a reserve are
tithed to the Pyre, feasts burn food, and research freezes above dogma 0.7. The Pyre's
treasury commissions Fanatic Boarding Vessels (paid to its capital's shipyard). The faith
must expand: after ZEALOT_STAGNATION_GRACE cycles without new converts or conquests its
stability decays until a purge burns its own people and shrine worlds secede.

All money here moves between existing stocks (world vaults, faction vaults, shipyards,
captains, ISSE pools). Nothing is minted.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    AUTHORITIES,
    POLICY_CARDS,
    POLICY_ORDER,
    POLICY_REVIEW_INTERVAL,
    PRICE_LEVEL,
    SHIP_CATALOG,
    MAX_AI_CAPTAINS,
    IMPERIUM_CAPITAL_RANGE,
    IMPERIUM_TERRITORY_HOPS,
    IMPERIUM_TITHE_RATE,
    IMPERIUM_MANPOWER_RATE,
    IMPERIUM_TITHE_MORALE_COST,
    IMPERIUM_UNHAULED_LOSS,
    IMPERIUM_FLEET_MAX,
    IMPERIUM_WARSHIP_COST,
    IMPERIUM_CREW_FLOAT,
    IMPERIUM_SECESSION_MORALE,
    HERESY_TECHS,
    IMPERIUM_COMMISSARIAT_MORALE,
    SECESSION_UNREST_QUARTERS,
    ZEALOT_OVEREXTENSION_WORLDS,
    ZEALOT_OVEREXTENSION_DECAY,
    ZEALOT_MUSTER_TROOPS,
    ZEALOT_HALLOW_TROOPS,
    ZEALOT_CONVERT_TROOPS,
    ZEALOT_HALLOW_COST,
    ZEALOT_EXPANSION_COOLDOWN,
    POLICY_BOUNDS,
    HERESY_CRISIS_MORALE,
    HERESY_WARRANT_LEVEL,
    ZEALOT_CAPITAL_RANGE,
    ZEALOT_TERRITORY_HOPS,
    ZEALOT_START_DOGMA,
    ZEALOT_SURPLUS_RESERVE,
    ZEALOT_SURPLUS_TITHE,
    ZEALOT_DOGMA_PER_TITHE,
    ZEALOT_FEAST_ORGANICS,
    ZEALOT_STAGNATION_GRACE,
    ZEALOT_STABILITY_DECAY,
    ZEALOT_CRUSADER_COST,
    ZEALOT_FLEET_MAX,
    ZEALOT_TRIBUTE_SHARE,
    ZEALOT_HERETIC_CLADES,
    ZEALOT_PURGE_LOSS,
    ZEALOT_CRUSADE_RANGE,
    IMPERIAL_POLITY,
    ZEALOT_POLITY,
    IMPERIAL_WORLD_NAMES,
    ZEALOT_WORLD_NAMES,
    CRUSADER_NAMES,
    IMPERIAL_CAPTAIN_NAMES,
    CAPTAIN_RATIONS,
)
from xylarium.kernel.models import (
    ActionType, AIPersonality, Captain, CargoHold, Planet, Sector, SecurityLevel, Ship,
)

FISCAL_QUARTER = 25
GREAT_POWERS = ("IMPERIUM", "ZEALOT")


@dataclass
class Faction:
    id: str
    name: str
    kind: str
    card: str
    sapience_threshold: float
    uplift_limit: int
    enforcement: str
    warrant: int
    alignment: float
    capital_sector: Optional[int] = None
    capital_planet: Optional[str] = None
    fortress_planet: Optional[str] = None
    territory: List[int] = field(default_factory=list)
    worlds: List[str] = field(default_factory=list)
    vault: Dict[str, int] = field(default_factory=dict)
    currency: str = "SOL"
    dogma: float = 0.0
    stability: float = 1.0
    last_expansion_cycle: int = 0
    fleet: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    card_history: List[List[Any]] = field(default_factory=list)
    ship_serial: int = 0
    unrest: Dict[str, int] = field(default_factory=dict)   # consecutive quarters of low morale per world
    lost_worlds: List[str] = field(default_factory=list)   # seceded worlds the faction means to reclaim

    @property
    def hand(self) -> Dict[str, Any]:
        return {"authority": self.id, "name": self.name, "card": self.card,
                "card_name": POLICY_CARDS[self.card]["name"], "motto": POLICY_CARDS[self.card]["motto"],
                "sapience_threshold": self.sapience_threshold, "uplift_limit": self.uplift_limit,
                "enforcement": self.enforcement, "warrant": self.warrant}

    def bump(self, stat: str, amount: int = 1) -> None:
        self.stats[stat] = self.stats.get(stat, 0) + int(amount)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "kind": self.kind, "card": self.card,
            "sapience_threshold": self.sapience_threshold, "uplift_limit": self.uplift_limit,
            "enforcement": self.enforcement, "warrant": self.warrant, "alignment": self.alignment,
            "capital_sector": self.capital_sector, "capital_planet": self.capital_planet,
            "fortress_planet": self.fortress_planet, "territory": list(self.territory),
            "worlds": list(self.worlds), "vault": dict(self.vault), "currency": self.currency,
            "dogma": self.dogma, "stability": self.stability, "last_expansion_cycle": self.last_expansion_cycle,
            "fleet": list(self.fleet), "stats": dict(self.stats),
            "card_history": [list(x) for x in self.card_history], "ship_serial": self.ship_serial,
            "unrest": dict(self.unrest),
            "lost_worlds": list(self.lost_worlds),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Faction":
        f = cls(id=d["id"], name=d["name"], kind=d["kind"], card=d["card"],
                sapience_threshold=float(d["sapience_threshold"]), uplift_limit=int(d["uplift_limit"]),
                enforcement=d["enforcement"], warrant=int(d["warrant"]), alignment=float(d["alignment"]))
        f.capital_sector = d.get("capital_sector")
        f.capital_planet = d.get("capital_planet")
        f.fortress_planet = d.get("fortress_planet")
        f.territory = list(d.get("territory", []))
        f.worlds = list(d.get("worlds", []))
        f.vault = {k: int(v) for k, v in d.get("vault", {}).items()}
        f.currency = d.get("currency", "SOL")
        f.dogma = float(d.get("dogma", 0.0))
        f.stability = float(d.get("stability", 1.0))
        f.last_expansion_cycle = int(d.get("last_expansion_cycle", 0))
        f.fleet = list(d.get("fleet", []))
        f.stats = {k: int(v) for k, v in d.get("stats", {}).items()}
        f.card_history = [list(x) for x in d.get("card_history", [])]
        f.ship_serial = int(d.get("ship_serial", 0))
        f.unrest = {k: int(v) for k, v in d.get("unrest", {}).items()}
        f.lost_worlds = list(d.get("lost_worlds", []))
        return f


def _new_authority(key: str) -> Faction:
    cfg = AUTHORITIES[key]
    return Faction(id=key, name=cfg["name"], kind=key, card=cfg["card"],
                   sapience_threshold=cfg["sapience_threshold"], uplift_limit=cfg["uplift_limit"],
                   enforcement=cfg["enforcement"], warrant=cfg["warrant"], alignment=cfg["alignment"])


def _bfs(kernel: Any, start: int, limit: int = 99) -> Tuple[Dict[int, int], Dict[int, Optional[int]]]:
    dist = {start: 0}
    parent: Dict[int, Optional[int]] = {start: None}
    frontier = [start]
    while frontier:
        nxt = []
        for cur in frontier:
            if dist[cur] >= limit:
                continue
            for w in kernel.sectors[cur].warps:
                if w in kernel.sectors and w not in dist:
                    dist[w] = dist[cur] + 1
                    parent[w] = cur
                    nxt.append(w)
        frontier = nxt
    return dist, parent


def _first_hop(parent: Dict[int, Optional[int]], start: int, goal: int) -> Optional[int]:
    if goal not in parent or goal == start:
        return None
    node = goal
    while parent[node] is not None and parent[node] != start:
        node = parent[node]
    return node


class FactionManager:
    def __init__(self) -> None:
        self.factions: Dict[str, Faction] = {k: _new_authority(k) for k in ("FEDERATION", "COMPACT", "NONE")}
        self.territory_index: Dict[int, str] = {}
        self.last_review_cycle: int = 0

    # ------------------------------------------------------------------ jurisdiction
    def reindex(self) -> None:
        self.territory_index = {}
        for f in self.factions.values():
            for sid in f.territory:
                self.territory_index[sid] = f.id

    def owner_of(self, sector_id: int) -> Optional[str]:
        return self.territory_index.get(sector_id)

    def authority_for(self, sector: Sector) -> Faction:
        owner = self.territory_index.get(sector.id)
        if owner and owner in self.factions:
            return self.factions[owner]
        if sector.security == SecurityLevel.FEDERATION:
            return self.factions["FEDERATION"]
        if sector.security == SecurityLevel.BORDERLAND:
            return self.factions["COMPACT"]
        return self.factions["NONE"]

    def hand_for(self, sector: Sector) -> Dict[str, Any]:
        """The doctrine in force here: the authority's card, unless a local civilization keeps a stricter custom."""
        auth = self.authority_for(sector)
        hand = dict(auth.hand)
        for p in sector.planets:
            civ = getattr(p, "civilization", None)
            local = getattr(civ, "native_policy", None) if civ else None
            if local in POLICY_ORDER and hand["card"] in POLICY_ORDER \
                    and POLICY_ORDER.index(local) < POLICY_ORDER.index(hand["card"]):
                hand.update({"card": local, "card_name": POLICY_CARDS[local]["name"],
                             "motto": POLICY_CARDS[local]["motto"], "local_custom": civ.name})
        return hand

    # ------------------------------------------------------------------ genesis
    def found_great_powers(self, kernel: Any, seed: int) -> None:
        """Seats the Aurelian Imperium in the Borderland and the Choir of the Pyre in the Deep Void."""
        from xylarium.kernel.civilization import CivilizationIntelligenceEngine
        from xylarium.kernel.universe import habitability
        rng = random.Random(seed * 7919 + 17)
        taken: set = set()
        for spec in (("IMPERIUM", IMPERIUM_CAPITAL_RANGE, IMPERIUM_TERRITORY_HOPS),
                     ("ZEALOT", ZEALOT_CAPITAL_RANGE, ZEALOT_TERRITORY_HOPS)):
            key, (lo, hi), hops = spec
            forbidden = set(taken)

            def free_system(sid: int) -> bool:
                sec = kernel.sectors[sid]
                return (sec.kind == "SYSTEM" and sid != 1 and sid not in forbidden and bool(sec.planets)
                        and not any(p.civilization is not None or p.owner_id for p in sec.planets))

            cands = [sid for sid in range(lo, hi + 1) if sid in kernel.sectors and free_system(sid)
                     and kernel.sectors[sid].port is not None]
            if not cands:
                continue

            def reach(sid: int) -> List[int]:
                dist, _ = _bfs(kernel, sid, hops)
                return [s for s in dist if free_system(s)]

            capital = max(cands, key=lambda sid: (len(reach(sid)), rng.random()))
            # A realm needs provinces: widen the reach until enough free systems lie within it
            wanted = 4 if key == "IMPERIUM" else 2
            while len(reach(capital)) < wanted and hops < spec[2] + 3:
                hops += 1
            systems = sorted(reach(capital), key=lambda s: (_bfs(kernel, capital, hops)[0].get(s, 99), s))
            systems = systems[:5] if key == "IMPERIUM" else systems[:3]
            dist, _ = _bfs(kernel, capital, hops)
            territory = sorted({s for s in dist if (s in systems or (kernel.sectors[s].kind == "NULL" and dist[s] <= 1)
                                                    or s == capital) and s not in forbidden
                                and kernel.sectors[s].security != SecurityLevel.FEDERATION} - {1})
            faction = _new_authority(key)
            faction.capital_sector = capital
            faction.territory = territory
            taken.update(territory)
            polity = IMPERIAL_POLITY if key == "IMPERIUM" else ZEALOT_POLITY
            names = list(IMPERIAL_WORLD_NAMES if key == "IMPERIUM" else ZEALOT_WORLD_NAMES)
            if key == "IMPERIUM":
                faction.currency = "THR"
            else:
                faction.currency = kernel.sectors[capital].port.currency
                faction.dogma = ZEALOT_START_DOGMA
            level = PRICE_LEVEL.get(faction.currency, 1.0)

            world_specs: List[Tuple[Planet, int, int]] = []
            cap_sec = kernel.sectors[capital]
            throne = cap_sec.planets[0]
            world_specs.append((throne, 60000 if key == "IMPERIUM" else 25000, 3 if key == "IMPERIUM" else 2))
            if key == "IMPERIUM":
                fortress = cap_sec.planets[1] if len(cap_sec.planets) > 1 else None
                if fortress is None:
                    other = next((s for s in systems if s != capital), None)
                    fortress = kernel.sectors[other].planets[0] if other else None
                if fortress is not None:
                    world_specs.append((fortress, 18000, 3))
            for sid in systems:
                if sid == capital:
                    continue
                p = kernel.sectors[sid].planets[0]
                if all(p is not w[0] for w in world_specs):
                    world_specs.append((p, rng.randint(4000, 12000) if key == "IMPERIUM" else rng.randint(3000, 8000), 1))

            for i, (p, pop, citadel) in enumerate(world_specs):
                if p.planet_type not in ("TERRESTRIAL", "OCEANIC"):
                    p.planet_type = "TERRESTRIAL"
                p.habitability = habitability("biotic", p.planet_type)
                civ = CivilizationIntelligenceEngine.create_civilization(dict(polity))
                civ.faction_id = key
                civ.alignment = faction.alignment
                civ.dogma = faction.dogma
                p.civilization = civ
                p.faction_id = key
                p.name = names[i % len(names)]
                p.population = pop
                p.citadel_level = citadel
                p.shields = p.max_shields = 800 * citadel
                p.fighters = 120 * citadel
                p.garrison_troops = 300 * citadel
                p.morale = 90
                p.ore_silo = rng.randint(200, 600)
                p.organics_silo = rng.randint(300, 800)
                p.element_reserves.update({"Fe": rng.randint(60, 160), "Ti": rng.randint(20, 80)})
                p.natives = None
                p.ruins = None
                p.currency = faction.currency
                p.treasury = int(rng.randint(3000, 9000) * level)
                faction.worlds.append(p.id)
            faction.capital_planet = world_specs[0][0].id
            if key == "IMPERIUM" and len(world_specs) > 1:
                faction.fortress_planet = world_specs[1][0].id
            else:
                faction.fortress_planet = faction.capital_planet

            # Territory settles in the faction's money; its starports fly its banner
            for sid in territory:
                sec = kernel.sectors[sid]
                for p in sec.planets:
                    p.currency = faction.currency
                if sec.port is not None:
                    old_level = PRICE_LEVEL.get(sec.port.currency, 1.0)
                    sec.port.treasury = int(sec.port.treasury / old_level * level)
                    sec.port.currency = faction.currency
                    sec.port.faction_id = key
            faction.vault = {faction.currency: int((250_000 if key == "IMPERIUM" else 90_000) * level)}
            self.factions[key] = faction
        self.reindex()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _planet(kernel: Any, pid: Optional[str]) -> Optional[Planet]:
        if not pid:
            return None
        for s in kernel.sectors.values():
            for p in s.planets:
                if p.id == pid:
                    return p
        return None

    def worlds(self, kernel: Any, fid: str) -> List[Planet]:
        f = self.factions.get(fid)
        if f is None:
            return []
        out = []
        for s in kernel.sectors.values():
            for p in s.planets:
                if p.faction_id == fid:
                    out.append(p)
        f.worlds = [p.id for p in out]
        return out

    def vault_sol(self, kernel: Any, f: Faction) -> float:
        fxm = kernel.fx_market
        return sum(fxm.to_sol_value(cur, amt) for cur, amt in f.vault.items())

    def _pay_from_vault(self, kernel: Any, f: Faction, sol_value: float) -> Dict[str, int]:
        """Withdraws about ``sol_value`` SOL-equivalent from the vault (home currency first). Returns what was paid."""
        fxm = kernel.fx_market
        paid: Dict[str, int] = {}
        need = sol_value
        for cur in sorted(f.vault, key=lambda c: c != f.currency):
            if need <= 0:
                break
            have = f.vault[cur]
            if have <= 0:
                continue
            take = min(have, int(need * fxm.rate(cur)) + 1)
            f.vault[cur] -= take
            paid[cur] = paid.get(cur, 0) + take
            need -= fxm.to_sol_value(cur, take)
        return paid

    def _to_sol(self, kernel: Any, amounts: Dict[str, int]) -> int:
        fxm = kernel.fx_market
        total = 0
        for cur, amt in amounts.items():
            total += amt if cur == "SOL" else fxm.swap_to_sol(cur, amt)
        return total

    def note_expansion(self, kernel: Any, fid: str, sector_id: Optional[int] = None) -> None:
        f = self.factions.get(fid)
        if f is None:
            return
        f.last_expansion_cycle = kernel.cycle_count
        f.stability = min(1.0, f.stability + 0.25)
        f.bump("expansions")
        if sector_id is not None and sector_id not in f.territory and self.territory_index.get(sector_id) is None:
            f.territory.append(sector_id)
            self.territory_index[sector_id] = fid

    def is_heretic(self, captain: Captain) -> bool:
        if captain.faction_id == "ZEALOT":
            return False
        return captain.clade in ZEALOT_HERETIC_CLADES or captain.cosmic_alignment >= 0.5

    # ------------------------------------------------------------------ techno-heresy
    def heresy_check(self, kernel: Any, captain: Captain, action: ActionType, kwargs: Dict[str, Any],
                     result: Any) -> Optional[str]:
        """Imperial captains who touch thinking machines, xeno-veils or alien relics commit techno-heresy."""
        if "IMPERIUM" not in self.factions or not result.success:
            return None
        if captain.clade != "IMPERIAL" and captain.faction_id != "IMPERIUM":
            return None
        heretical = False
        if action == ActionType.RESEARCH_SELECT and str(kwargs.get("tech_key", "")).upper() in HERESY_TECHS:
            heretical = True
        elif action in (ActionType.ANOMALY_INVESTIGATE, ActionType.ALCHEMY_TRANSMUTE):
            heretical = True
        elif action == ActionType.STUDY_ARTIFACT:
            heretical = True  # every relic of a dead xeno culture is heresy to the Throne
        if not heretical:
            return None
        imp = self.factions["IMPERIUM"]
        captain.heresy += 1
        imp.bump("heresies")
        for w in self.worlds(kernel, "IMPERIUM"):
            w.morale = max(0, w.morale - HERESY_CRISIS_MORALE // 2)
        msg = f"[INQUISITION] Techno-heresy recorded against {captain.name} ({captain.heresy}/{HERESY_WARRANT_LEVEL})."
        if captain.heresy >= HERESY_WARRANT_LEVEL and not captain.alignment_record.get("inquisition"):
            captain.alignment_record["inquisition"] = True
            captain.bounty += imp.warrant
            captain.bounty_placed_by = "Imperial Inquisition"
            captain.adjust_reputation("Imperium", -30.0)
            from xylarium.kernel import chronicle
            chronicle.decree(kernel, imp, f"Inquisitorial Crisis: {captain.name}",
                             f"{captain.name} is declared Excommunicate Traitoris for techno-heresy. "
                             f"A warrant of {imp.warrant:,} Cr is issued; the Battle-Cruisers are informed.",
                             ["heresy", "inquisition"])
            msg += f" EXCOMMUNICATE TRAITORIS: warrant +{imp.warrant:,} Cr."
        return msg

    # ------------------------------------------------------------------ world tick
    def tick(self, kernel: Any) -> List[str]:
        logs: List[str] = []
        cycle = kernel.cycle_count
        if cycle % FISCAL_QUARTER == 0:
            if "IMPERIUM" in self.factions:
                logs += self._imperium_quarter(kernel, self.factions["IMPERIUM"])
            if "ZEALOT" in self.factions:
                logs += self._zealot_quarter(kernel, self.factions["ZEALOT"])
        if cycle - self.last_review_cycle >= POLICY_REVIEW_INTERVAL:
            self.last_review_cycle = cycle
            logs += self._review_doctrines(kernel)
        for f in self.factions.values():
            f.fleet = [cid for cid in f.fleet if cid in kernel.captains]
        return logs

    # --- Imperium
    def _imperium_quarter(self, kernel: Any, f: Faction) -> List[str]:
        logs: List[str] = []
        worlds = self.worlds(kernel, "IMPERIUM")
        if not worlds:
            return logs
        fortress = self._planet(kernel, f.fortress_planet) or self._planet(kernel, f.capital_planet)
        if fortress is None or fortress.faction_id != "IMPERIUM":
            fortress = worlds[0]
            f.fortress_planet = fortress.id
        has_hauler = any(kernel.captains[c].ship.ship_type == "Bulk Goliath" for c in f.fleet if c in kernel.captains)
        for w in worlds:
            if w.id in (f.capital_planet, f.fortress_planet):
                if w.organics_silo > 50:
                    w.morale = min(100, w.morale + 2)
                continue
            manifest = w.tithe_manifest
            for key, attr in (("ORE", "ore_silo"), ("ORGANICS", "organics_silo")):
                take = int(getattr(w, attr) * IMPERIUM_TITHE_RATE)
                if take > 0:
                    setattr(w, attr, getattr(w, attr) - take)
                    manifest[key] = manifest.get(key, 0) + take
            for elem in ("Fe", "Ti"):
                take = int(w.element_reserves.get(elem, 0) * IMPERIUM_TITHE_RATE)
                if take > 0:
                    w.element_reserves[elem] -= take
                    manifest[elem] = manifest.get(elem, 0) + take
            draft = int(w.population * IMPERIUM_MANPOWER_RATE)
            if draft > 0 and w.population - draft > 500:
                w.population -= draft
                manifest["MANPOWER"] = manifest.get("MANPOWER", 0) + draft
            # The tithe grinds; the Commissariat's sermons and garrisons hold the line
            w.morale = max(0, min(100, w.morale - IMPERIUM_TITHE_MORALE_COST + IMPERIUM_COMMISSARIAT_MORALE))
            if not has_hauler and manifest:
                self._deliver_tithe(kernel, f, fortress, manifest, IMPERIUM_UNHAULED_LOSS)
                w.tithe_manifest = {}
            # Only sustained unrest breaks a world away (morale swings within a quarter are noise)
            f.unrest[w.id] = f.unrest.get(w.id, 0) + 1 if w.morale < IMPERIUM_SECESSION_MORALE else 0
            if f.unrest[w.id] >= SECESSION_UNREST_QUARTERS:
                f.unrest.pop(w.id, None)
                logs.append(self._secede(kernel, f, w, "tithe riots and heresy"))
        logs += self._commission_imperial(kernel, f, fortress)
        return [l for l in logs if l]

    def _deliver_tithe(self, kernel: Any, f: Faction, fortress: Planet, goods: Dict[str, int], loss: float = 0.0) -> int:
        delivered = 0
        for key, qty in goods.items():
            qty = int(qty * (1.0 - loss))
            if qty <= 0:
                continue
            delivered += qty
            if key == "ORE":
                fortress.ore_silo += qty
            elif key == "ORGANICS":
                fortress.organics_silo += qty
            elif key == "MANPOWER":
                fortress.garrison_troops += qty // 10
                fortress.population += qty
            else:
                fortress.element_reserves[key] = fortress.element_reserves.get(key, 0) + qty
        f.bump("tithe_delivered", delivered)
        if loss:
            f.bump("tithe_lost", int(sum(goods.values()) * loss))
        return delivered

    def _commission_imperial(self, kernel: Any, f: Faction, fortress: Planet) -> List[str]:
        live = [c for c in f.fleet if c in kernel.captains]
        if len(live) >= IMPERIUM_FLEET_MAX or sum(1 for c in kernel.captains.values() if c.is_ai) >= MAX_AI_CAPTAINS:
            return []
        stock = {"Fe": fortress.element_reserves.get("Fe", 0), "Ti": fortress.element_reserves.get("Ti", 0),
                 "ORE": fortress.ore_silo}
        if any(stock[k] < v for k, v in IMPERIUM_WARSHIP_COST.items()):
            return []
        if self.vault_sol(kernel, f) < IMPERIUM_CREW_FLOAT * 2:
            return []
        for k, v in IMPERIUM_WARSHIP_COST.items():
            if k == "ORE":
                fortress.ore_silo -= v
            else:
                fortress.element_reserves[k] -= v
        has_hauler = any(kernel.captains[c].ship.ship_type == "Bulk Goliath" for c in live)
        hull = "Gothic Battle-Cruiser" if has_hauler else "Bulk Goliath"
        float_sol = self._to_sol(kernel, self._pay_from_vault(kernel, f, IMPERIUM_CREW_FLOAT))
        cap = self._spawn_ship(kernel, f, hull, IMPERIAL_CAPTAIN_NAMES, AIPersonality.IMPERIAL, "IMPERIAL",
                               "human-imperial", fortress.sector_id, float_sol)
        f.bump("warships")
        from xylarium.kernel import chronicle
        chronicle.decree(kernel, f, f"The Commissioning of {cap.name}",
                         f"From the tithes of the faithful worlds, the {hull} under {cap.name} is launched from "
                         f"{fortress.name}. Let the xeno and the traitor take note.", ["fleet", "tithe"],
                         sector_id=fortress.sector_id)
        return [f"[IMPERIUM] {hull} commissioned at {fortress.name}: {cap.name}."]

    def _secede(self, kernel: Any, f: Faction, w: Planet, cause: str) -> str:
        w.faction_id = None
        if f.id == "IMPERIUM" and w.id not in f.lost_worlds:
            f.lost_worlds.append(w.id)
        if w.civilization is not None:
            w.civilization.faction_id = None
            w.civilization.name = f"Free {w.name.split()[0]} Secession"
            w.civilization.dogma = 0.0
            w.civilization.alignment = min(1.0, w.civilization.alignment + 0.25)
        w.morale = 60
        if w.sector_id in f.territory and w.sector_id not in (f.capital_sector,):
            f.territory.remove(w.sector_id)
            self.territory_index.pop(w.sector_id, None)
            sec = kernel.sectors[w.sector_id]
            if sec.port is not None:
                sec.port.faction_id = None
        f.bump("secessions")
        from xylarium.kernel import chronicle
        chronicle.decree(kernel, f, f"The Secession of {w.name}",
                         f"{w.name} has broken from the realm ({cause}). The traitor world shall be remembered.",
                         ["secession"], sector_id=w.sector_id)
        chronicle.record_planet(
            kernel, w, f"Liberty on {w.name}",
            f"Annals of {w.name}. The banners of the old realm came down at dawn ({cause}). "
            "By noon the square was full, and for once no one counted the tithe.", ["secession", "liberty"], 0.2)
        return f"[SECESSION] {w.name} has broken from the {f.name}."

    # --- Choir of the Pyre
    def _zealot_quarter(self, kernel: Any, f: Faction) -> List[str]:
        logs: List[str] = []
        worlds = self.worlds(kernel, "ZEALOT")
        fxm = kernel.fx_market
        tithed_sol = 0.0
        for w in worlds:
            reserve = int(ZEALOT_SURPLUS_RESERVE * PRICE_LEVEL.get(w.currency, 1.0))
            surplus = w.treasury - reserve
            if surplus > 0:
                tithe = int(surplus * ZEALOT_SURPLUS_TITHE)
                w.treasury -= tithe
                f.vault[w.currency] = f.vault.get(w.currency, 0) + tithe
                tithed_sol += fxm.to_sol_value(w.currency, tithe)
            if w.organics_silo > ZEALOT_FEAST_ORGANICS:
                burned = w.organics_silo - ZEALOT_FEAST_ORGANICS
                w.organics_silo = ZEALOT_FEAST_ORGANICS
                f.bump("feast_burned", burned)
                f.dogma = min(1.0, f.dogma + 0.002)
        f.bump("surplus_tithed", int(tithed_sol))
        f.dogma = max(0.0, min(1.0, f.dogma + ZEALOT_DOGMA_PER_TITHE * tithed_sol / 10000 - 0.003))
        for w in worlds:
            if w.civilization is not None:
                w.civilization.dogma = f.dogma
        # Surplus must be cleared by crusade
        logs += self._commission_crusader(kernel, f)
        # The expansion imperative: conquer or collapse. And every conquest is another wall to hold.
        if kernel.cycle_count - f.last_expansion_cycle > ZEALOT_STAGNATION_GRACE and worlds:
            f.stability -= ZEALOT_STABILITY_DECAY + 0.03 * f.dogma
        f.stability -= ZEALOT_OVEREXTENSION_DECAY * max(0, len(worlds) - ZEALOT_OVEREXTENSION_WORLDS)
        if f.stability <= 0 and worlds:
            logs.append(self._purge(kernel, f, worlds))
        # Crusaders remit plunder to the Pyre
        for cid in f.fleet:
            cap = kernel.captains.get(cid)
            if cap is not None and cap.credits > 5000:
                excess = cap.credits - 3000
                cap.credits -= excess
                f.vault["SOL"] = f.vault.get("SOL", 0) + excess
        return [l for l in logs if l]

    def _commission_crusader(self, kernel: Any, f: Faction) -> List[str]:
        live = [c for c in f.fleet if c in kernel.captains]
        worlds = self.worlds(kernel, "ZEALOT")
        if not worlds or len(live) >= ZEALOT_FLEET_MAX:
            return []
        if sum(1 for c in kernel.captains.values() if c.is_ai) >= MAX_AI_CAPTAINS:
            return []
        if self.vault_sol(kernel, f) < ZEALOT_CRUSADER_COST * 1.3:
            return []
        capital = self._planet(kernel, f.capital_planet)
        if capital is None or capital.faction_id != "ZEALOT":
            capital = worlds[0]
        yard = kernel.sectors[capital.sector_id].port
        cost = self._pay_from_vault(kernel, f, ZEALOT_CRUSADER_COST)
        if yard is not None:
            # The hull is built (and paid for) at the capital's shipyard
            fxm = kernel.fx_market
            for cur, amt in cost.items():
                if cur == yard.currency:
                    yard.treasury += amt
                else:
                    sol = amt if cur == "SOL" else fxm.swap_to_sol(cur, amt)
                    yard.treasury += sol if yard.currency == "SOL" else fxm.swap_sol_to(yard.currency, sol)
        else:
            for cur, amt in cost.items():
                capital.treasury += amt if cur == capital.currency else 0
        float_sol = self._to_sol(kernel, self._pay_from_vault(kernel, f, 1500))
        cap = self._spawn_ship(kernel, f, "Fanatic Boarding Vessel", CRUSADER_NAMES, AIPersonality.CRUSADER, "BIOTIC",
                               "ardent-bimaniform", capital.sector_id, float_sol)
        cap.troops = 200
        f.bump("crusaders")
        from xylarium.kernel import chronicle
        chronicle.decree(kernel, f, "A Holy Crusade Is Declared",
                         f"The surplus of the faithful has been made into fire. {cap.name} sails from {capital.name} "
                         f"to carry the Pyre to the heretic (dogma {f.dogma:.2f}).", ["crusade"], sector_id=capital.sector_id)
        if getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(sender="CHOIR-OF-THE-PYRE",
                                             text=f"HOLY CRUSADE: {cap.name} launches from {capital.name}. Repent, or burn.",
                                             channel="ALERT", sector_id=capital.sector_id)
        return [f"[CRUSADE] {cap.name} commissioned at {capital.name}."]

    def _purge(self, kernel: Any, f: Faction, worlds: List[Planet]) -> str:
        lost = 0
        for w in worlds:
            loss = int(w.population * ZEALOT_PURGE_LOSS)
            w.population = max(100, w.population - loss)
            lost += loss
            w.morale = max(10, w.morale - 20)
        f.dogma = max(0.2, f.dogma - 0.3)
        f.stability = 0.6
        f.last_expansion_cycle = kernel.cycle_count
        f.bump("purges")
        from xylarium.kernel import chronicle
        chronicle.decree(kernel, f, "The Burning Purge",
                         f"The faith, finding no new heretics beyond its walls, found them within. {lost:,} of the "
                         f"faithful were given to the Pyre. Dogma falls to {f.dogma:.2f}.", ["purge", "civil war"])
        seceded = ""
        shrines = [w for w in worlds if w.id != f.capital_planet]
        if shrines:
            dist, _ = _bfs(kernel, f.capital_sector or shrines[0].sector_id)
            shrines.sort(key=lambda w: -dist.get(w.sector_id, 99))
            breakaway = shrines[:max(1, (len(shrines) + 2) // 3)]
            for far in breakaway:
                if far.civilization is not None:
                    far.civilization.alignment = 0.0
                if far.natives:
                    far.natives["converted"] = False
                self._secede(kernel, f, far, "schism after the purge")
            seceded = f" {len(breakaway)} shrine world(s) broke away in the schism."
        return f"[PURGE] The Choir of the Pyre burned {lost:,} of its own.{seceded}"

    def _spawn_ship(self, kernel: Any, f: Faction, hull: str, names: List[str], personality: AIPersonality,
                    clade: str, species: str, sector_id: int, float_sol: int) -> Captain:
        cfg = SHIP_CATALOG[hull]
        f.ship_serial += 1
        name = f"{names[(f.ship_serial - 1) % len(names)]}" + (f" {f.ship_serial}" if f.ship_serial > len(names) else "")
        cargo = CargoHold(capacity=cfg["holds"])
        cargo.organics = 20
        cap = Captain(
            id=f"{f.id.lower()}_{f.ship_serial}_{kernel.cycle_count}", name=name, is_ai=True, personality=personality,
            ship=Ship(ship_type=hull, cargo=cargo, shields=cfg["max_shields"], max_shields=cfg["max_shields"],
                      fighters=cfg["max_fighters"]),
            credits=int(float_sol), sector_id=sector_id, turns_left=300, home_sector=sector_id, species=species,
            metabolism="biotic", clade=clade, rank_tier=3,
        )
        cap.faction_id = f.id
        cap.cosmic_alignment = f.alignment
        cap.alignment_record["baseline"] = f.alignment
        cap.faction_reputation[f.name.split()[-1]] = 90.0
        kernel.captains[cap.id] = cap
        kernel.sectors[sector_id].captains.append(cap.id)
        f.fleet.append(cap.id)
        return cap

    # --- doctrine review
    def _review_doctrines(self, kernel: Any) -> List[str]:
        logs = []
        caps = [c for c in kernel.captains.values() if c.faction_id is None]
        for key, zone in (("FEDERATION", SecurityLevel.FEDERATION), ("COMPACT", SecurityLevel.BORDERLAND)):
            f = self.factions[key]
            here = [c.cosmic_alignment for c in caps if kernel.sectors[c.sector_id].security == zone]
            pool = here if len(here) >= 3 else [c.cosmic_alignment for c in caps]
            if not pool:
                continue
            # A light-leaning public and a wave of violations both move the authority to protect the locals
            mood = sum(pool) / len(pool) + min(0.3, 0.02 * f.stats.get("violations_era", 0))
            f.stats["violations_era"] = 0
            idx = POLICY_ORDER.index(f.card) if f.card in POLICY_ORDER else 1
            lo, hi = (POLICY_ORDER.index(c) for c in POLICY_BOUNDS.get(key, ("ALPHA", "DELTA")))
            new = idx
            if mood >= 0.2 and idx > lo:
                new = idx - 1
                f.sapience_threshold = min(9.0, f.sapience_threshold + 0.5)
            elif mood <= -0.2 and idx < hi:
                new = idx + 1
                f.sapience_threshold = max(2.0, f.sapience_threshold - 0.5)
            if new != idx:
                old = f.card
                f.card = POLICY_ORDER[new]
                f.card_history.append([kernel.cycle_count, old, f.card, round(mood, 3)])
                from xylarium.kernel import chronicle
                chronicle.decree(kernel, f, f"Directive {f.card.title()} Adopted",
                                 f"After a season of debate the {f.name} sets aside Directive {old.title()} "
                                 f"({POLICY_CARDS[old]['name']}) for Directive {f.card.title()} "
                                 f"({POLICY_CARDS[f.card]['name']}): \"{POLICY_CARDS[f.card]['motto']}\" "
                                 f"Contact now requires sapience {f.sapience_threshold:.1f}.", ["policy", "prime directive"],
                                 sector_id=1 if key == "FEDERATION" else None)
                logs.append(f"[POLICY] {f.name} adopts Directive {f.card}.")
        return logs

    # ------------------------------------------------------------------ AI doctrine loops
    def execute_faction_ai(self, kernel: Any, cap: Captain) -> bool:
        if cap.personality == AIPersonality.CRUSADER:
            return self._crusader_turn(kernel, cap)
        if cap.personality == AIPersonality.IMPERIAL:
            return self._imperial_turn(kernel, cap)
        return False

    def _move(self, kernel: Any, cap: Captain, goal: int) -> bool:
        dist, parent = _bfs(kernel, cap.sector_id, 30)
        hop = _first_hop(parent, cap.sector_id, goal)
        if hop is None:
            return False
        res = kernel.dispatch(cap.id, ActionType.MOVE, destination=hop)
        return bool(res.success)

    def _provision(self, kernel: Any, cap: Captain) -> bool:
        """Faction crews draw rations from their own worlds' silos, or buy at a port."""
        ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
        if cap.ship.cargo.unbonded(ration) >= 5:
            return False
        sec = kernel.sectors[cap.sector_id]
        for p in sec.planets:
            if p.faction_id == cap.faction_id and p.organics_silo > 40:
                take = min(20, p.organics_silo - 20, cap.ship.cargo.available_units_for("ORGANICS"))
                if take > 0:
                    p.organics_silo -= take
                    cap.ship.cargo.organics += take
                    if cap.hunger > 0:
                        kernel._feed_crew(cap)
                    return True
        if sec.port is not None and sec.port.sells.get(ration) and sec.port.stock.get(ration, 0) > 10:
            res = kernel.dispatch(cap.id, ActionType.TRADE, type="BUY", commodity=ration, amount=15)
            if res.success:
                return True
        home = [p for p in self.worlds(kernel, cap.faction_id) if p.organics_silo > 60]
        if home:
            dist, _ = _bfs(kernel, cap.sector_id, 30)
            goal = min(home, key=lambda p: dist.get(p.sector_id, 99)).sector_id
            if goal != cap.sector_id and self._move(kernel, cap, goal):
                return True
        return False

    # --- Imperial fleet
    def _imperial_turn(self, kernel: Any, cap: Captain) -> bool:
        f = self.factions.get("IMPERIUM")
        if f is None:
            return False
        if self._provision(kernel, cap):
            return True
        sec = kernel.sectors[cap.sector_id]
        if cap.ship.ship_type == "Bulk Goliath":
            fortress = self._planet(kernel, f.fortress_planet)
            plan = cap.active_plan or {}
            if plan.get("kind") == "tithe" and plan.get("goods"):
                if fortress is not None and cap.sector_id == fortress.sector_id:
                    goods = plan["goods"]
                    self._unload_goliath(cap, goods)
                    self._deliver_tithe(kernel, f, fortress, goods)
                    cap.active_plan = None
                    return True
                return fortress is not None and self._move(kernel, cap, fortress.sector_id)
            worlds = [w for w in self.worlds(kernel, "IMPERIUM") if w.tithe_manifest]
            if not worlds:
                return False
            dist, _ = _bfs(kernel, cap.sector_id, 30)
            target = min(worlds, key=lambda w: dist.get(w.sector_id, 99))
            if cap.sector_id != target.sector_id:
                return self._move(kernel, cap, target.sector_id)
            goods: Dict[str, int] = {}
            for key, qty in list(target.tithe_manifest.items()):
                if key == "MANPOWER":
                    goods[key] = goods.get(key, 0) + qty
                    target.tithe_manifest.pop(key)
                    continue
                got = cap.ship.cargo.stow(key, qty)
                if got:
                    goods[key] = goods.get(key, 0) + got
                    target.tithe_manifest[key] -= got
                    if target.tithe_manifest[key] <= 0:
                        target.tithe_manifest.pop(key)
            plan = cap.active_plan if (cap.active_plan or {}).get("kind") == "tithe" else {"kind": "tithe", "goods": {}}
            for k, v in goods.items():
                plan["goods"][k] = plan["goods"].get(k, 0) + v
            cap.active_plan = plan
            return True
        # Battle-cruiser: reclaim seceded worlds that still stand free of any sovereign
        if cap.ship.ship_type == "Gothic Battle-Cruiser" and f.lost_worlds:
            lost = [p for p in (self._planet(kernel, pid) for pid in f.lost_worlds) if p is not None]
            f.lost_worlds = [p.id for p in lost if p.faction_id is None and not p.owner_id and p.population > 0]
            if f.lost_worlds:
                target = self._planet(kernel, f.lost_worlds[0])
                if cap.sector_id != target.sector_id:
                    if self._move(kernel, cap, target.sector_id):
                        return True
                else:
                    self._reclaim(kernel, f, target, cap)
                    return True
        # Battle-cruiser: hunt the wanted, the excommunicate, and crusaders in Imperial space
        prey = [kernel.captains[c] for c in sec.captains if c != cap.id and c in kernel.captains]
        prey = [p for p in prey if p.faction_id != "IMPERIUM" and
                (p.bounty > 0 or p.heresy >= HERESY_WARRANT_LEVEL or p.personality == AIPersonality.CRUSADER)]
        if prey and sec.security != SecurityLevel.FEDERATION:
            target = max(prey, key=lambda p: p.bounty)
            res = kernel.dispatch(cap.id, ActionType.ATTACK_SHIP, target_id=target.id)
            if res.success:
                f.bump("inquisitions")
                return True
        patrol = [s for s in f.territory if s != cap.sector_id]
        if patrol:
            return self._move(kernel, cap, random.choice(patrol))
        return False

    def _reclaim(self, kernel: Any, f: Faction, world: Planet, cap: Captain) -> None:
        """The Throne takes back a seceded world: the garrison lands, the old banners go back up."""
        world.faction_id = "IMPERIUM"
        if world.civilization is not None:
            world.civilization.faction_id = "IMPERIUM"
            world.civilization.name = "Aurelian Imperium"
            world.civilization.alignment = f.alignment
        world.morale = 55
        f.unrest.pop(world.id, None)
        if world.id in f.lost_worlds:
            f.lost_worlds.remove(world.id)
        if world.sector_id not in f.territory and self.territory_index.get(world.sector_id) is None:
            f.territory.append(world.sector_id)
            self.territory_index[world.sector_id] = "IMPERIUM"
            sec = kernel.sectors[world.sector_id]
            if sec.port is not None:
                sec.port.faction_id = "IMPERIUM"
        f.bump("reclamations")
        from xylarium.kernel import alignment, chronicle
        alignment.deed(kernel, cap, "conquest", scale=0.5)
        chronicle.decree(kernel, f, f"The Reclamation of {world.name}",
                         f"{cap.name}'s battle group stood over {world.name} until its gates opened. "
                         "The traitor council is gone; the tithe resumes.", ["reclamation", "war"],
                         sector_id=world.sector_id)

    @staticmethod
    def _unload_goliath(cap: Captain, goods: Dict[str, int]) -> None:
        cargo = cap.ship.cargo
        for key, qty in goods.items():
            if key == "MANPOWER":
                continue
            if key in ("ORE", "ORGANICS", "EQUIPMENT"):
                setattr(cargo, key.lower(), max(0, getattr(cargo, key.lower()) - qty))
            else:
                left = cargo.elements.get(key, 0) - qty
                if left > 0:
                    cargo.elements[key] = left
                else:
                    cargo.elements.pop(key, None)

    # --- Crusaders
    def _crusader_turn(self, kernel: Any, cap: Captain) -> bool:
        f = self.factions.get("ZEALOT")
        if f is None:
            return False
        if self._provision(kernel, cap):
            return True
        sec = kernel.sectors[cap.sector_id]
        # 1. Heretics in reach: demand tribute from the weak, fight the rest (outside Federation guns)
        if sec.security != SecurityLevel.FEDERATION:
            heretics = [kernel.captains[c] for c in sec.captains if c != cap.id and c in kernel.captains]
            heretics = [h for h in heretics if self.is_heretic(h)]
            if heretics:
                h = random.choice(heretics)
                if h.ship.fighters < cap.ship.fighters * 0.7 and h.credits > 500:
                    tribute = int(h.credits * ZEALOT_TRIBUTE_SHARE)
                    h.credits -= tribute
                    f.vault["SOL"] = f.vault.get("SOL", 0) + tribute
                    f.bump("tribute", tribute)
                    from xylarium.kernel import alignment
                    alignment.deed(kernel, cap, "tribute_extorted")
                    if getattr(kernel, "event_bus", None):
                        kernel.event_bus.broadcast_radio(
                            sender=cap.name, text=f"TRIBUTE: {h.name} pays {tribute:,} Cr to the Pyre and is spared.",
                            channel="ALERT", sector_id=sec.id)
                    return True
                res = kernel.dispatch(cap.id, ActionType.ATTACK_SHIP, target_id=h.id)
                if res.success:
                    from xylarium.kernel import alignment
                    alignment.deed(kernel, cap, "crusade")
                    return True
        # 2. Muster: missionaries and settlers come from the faithful worlds
        if cap.troops < ZEALOT_CONVERT_TROOPS:
            for p in sec.planets:
                if p.faction_id == "ZEALOT" and p.population > 3000:
                    draft = min(ZEALOT_MUSTER_TROOPS, p.population - 2500)
                    p.population -= draft
                    cap.troops += draft
                    return True
            musters = [p for p in self.worlds(kernel, "ZEALOT") if p.population > 3000]
            if not musters:
                return False
            dist, _ = _bfs(kernel, cap.sector_id, 30)
            goal = min(musters, key=lambda p: dist.get(p.sector_id, 99)).sector_id
            return self._move(kernel, cap, goal)
        # 3. The crusade: convert natives, hallow empty worlds, besiege heretic colonies.
        # Consecration takes time: the faith absorbs one new world before reaching for the next.
        if kernel.cycle_count - f.last_expansion_cycle < ZEALOT_EXPANSION_COOLDOWN:
            patrol = [s for s in f.territory if s != cap.sector_id]
            return bool(patrol) and self._move(kernel, cap, random.choice(patrol))
        plan = cap.active_plan if (cap.active_plan or {}).get("kind") == "crusade" else None
        if plan is None or kernel.cycle_count - plan.get("since", 0) > 150:
            plan = self._crusade_target(kernel, cap)
            cap.active_plan = plan
        if plan is None:
            return False
        if cap.sector_id != plan["sector"]:
            if self._move(kernel, cap, plan["sector"]):
                return True
            cap.active_plan = None
            return False
        planet = next((p for p in sec.planets if p.id == plan["planet"]), None)
        cap.active_plan = None
        if planet is None:
            return False
        if plan["mode"] == "convert" and planet.natives:
            res = kernel.dispatch(cap.id, ActionType.NATIVE_INTERACT, sub_action="convert", planet_id=planet.id)
            if res.success:
                cap.troops = max(0, cap.troops - ZEALOT_CONVERT_TROOPS)
            return bool(res.success)
        if plan["mode"] == "hallow" and planet.owner_id is None and planet.population <= 0 and not planet.natives:
            # A new shrine world needs settlers and a consecrated treasury (paid from the Pyre's vault)
            if cap.troops < ZEALOT_HALLOW_TROOPS or self.vault_sol(kernel, f) < ZEALOT_HALLOW_COST * 1.5:
                return False
            cap.troops -= ZEALOT_HALLOW_TROOPS
            endowment = self._pay_from_vault(kernel, f, ZEALOT_HALLOW_COST)
            fxm = kernel.fx_market
            for cur, amt in endowment.items():
                if cur == planet.currency:
                    planet.treasury += amt
                else:
                    sol = amt if cur == "SOL" else fxm.swap_to_sol(cur, amt)
                    planet.treasury += sol if planet.currency == "SOL" else fxm.swap_sol_to(planet.currency, sol)
            self.hallow_world(kernel, f, planet, settlers=ZEALOT_HALLOW_TROOPS)
            return True
        if plan["mode"] == "siege" and planet.owner_id and planet.faction_id != "ZEALOT":
            res = kernel.dispatch(cap.id, ActionType.ATTACK_PLANET, planet_id=planet.id)
            if res.success and planet.owner_id == cap.id:
                self.hallow_world(kernel, f, planet, conquered=True)
            return bool(res.success)
        return False

    def _crusade_target(self, kernel: Any, cap: Captain) -> Optional[Dict[str, Any]]:
        from xylarium.kernel.universe import habitability
        dist, _ = _bfs(kernel, cap.sector_id, ZEALOT_CRUSADE_RANGE)
        best = None
        for sid, d in dist.items():
            sec = kernel.sectors[sid]
            if sec.security == SecurityLevel.FEDERATION or self.owner_of(sid) == "IMPERIUM":
                continue
            for p in sec.planets:
                mode = None
                if p.natives and not p.natives.get("converted") \
                        and p.natives.get("resisted_until", -1) < kernel.cycle_count:
                    mode, weight = "convert", 0
                elif p.owner_id is None and p.population <= 0 and not p.natives and p.faction_id is None \
                        and habitability("biotic", p.planet_type) >= 0.5:
                    mode, weight = "hallow", 1
                elif p.owner_id and p.faction_id != "ZEALOT" and p.owner_id in kernel.captains \
                        and not kernel.captains[p.owner_id].faction_id and p.fighters < cap.ship.fighters:
                    mode, weight = "siege", 2
                if mode and (best is None or (d + weight) < best[0]):
                    best = (d + weight, {"kind": "crusade", "sector": sid, "planet": p.id, "mode": mode,
                                         "since": kernel.cycle_count})
        return best[1] if best else None

    def hallow_world(self, kernel: Any, f: Faction, planet: Planet, conquered: bool = False, settlers: int = 0) -> None:
        """A world taken for the Pyre: settlers carried by the crusaders, the faith's civilization, its banner."""
        from xylarium.kernel.civilization import CivilizationIntelligenceEngine
        from xylarium.kernel.universe import habitability
        civ = CivilizationIntelligenceEngine.create_civilization(dict(ZEALOT_POLITY))
        civ.faction_id = "ZEALOT"
        civ.dogma = f.dogma
        civ.alignment = f.alignment
        planet.civilization = civ
        planet.faction_id = "ZEALOT"
        planet.owner_id = None
        planet.habitability = max(0.3, habitability("biotic", planet.planet_type))
        planet.population = max(planet.population, settlers)
        planet.morale = 70
        self.note_expansion(kernel, "ZEALOT", planet.sector_id)
        from xylarium.kernel import chronicle
        verb = "conquered and consecrated" if conquered else "hallowed"
        chronicle.decree(kernel, f, f"{planet.name} Is {verb.split()[0].title()}",
                         f"{planet.name} has been {verb} for the Pyre. Its fires are lit; its songs are ours.",
                         ["crusade", "expansion"], sector_id=planet.sector_id)

    # ------------------------------------------------------------------ persistence
    def to_dict(self) -> Dict[str, Any]:
        return {"factions": {k: f.to_dict() for k, f in self.factions.items()},
                "last_review_cycle": self.last_review_cycle}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactionManager":
        mgr = cls()
        for k, d in data.get("factions", {}).items():
            mgr.factions[k] = Faction.from_dict(d)
        mgr.last_review_cycle = int(data.get("last_review_cycle", 0))
        mgr.reindex()
        return mgr
