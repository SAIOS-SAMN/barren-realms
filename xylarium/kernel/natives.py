"""
Xylarium: Non-spacefaring locals and the Prime Directive.

Many worlds carry native peoples who have not reached the stars: Stone Age hunters,
Bronze Age city-states, Industrial nations, Atomic-age powers with a lens pointed at the
sky. They live beside the colonists' galaxy but not in it. Each society has a sapience
index (0-10), a technological stage, cultural stability, awareness of outsiders, and
cultural contamination from contact.

Captains interact with them through NATIVE_INTERACT sub-actions:

  observe   study from orbit (science; field notes for the Library)
  contact   open relations (first contact)
  trade     barter goods for local produce and crafts
  uplift    gift tools and knowledge to lift them a stage (too far, and they shatter)
  protect   declare a protectorate (their tithe of produce for your shield)
  collect   the protector collects the protectorate's tithe
  exploit   strip-mine their world and displace them
  convert   (Choir of the Pyre only) missionary conversion

The authority whose space the world lies in plays a doctrine card from the Galactic
Policy Deck (factions.py). Its card and sapience threshold decide what is lawful:
"unless they have a certain level of intelligence, you cannot interact with them".
Unlawful deeds are INTERDICTED outright in Federation space, draw WARRANTs from the
Frontier Compact, or bring the Imperial INQUISITION. In the Deep Void, nobody enforces
anything - which is exactly why the natives there fare worst.

Native societies advance on their own; contamination and exploitation can break them
(their world becomes ruins for archaeologists). An Orbital-age people sapient enough
achieves First Flight and joins the galaxy as a spacefaring civilization.
"""

import zlib
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import matter
from xylarium.config import (
    NATIVE_WORLD_SHARE,
    NATIVE_STAGES,
    NATIVE_STAGE_WEIGHTS,
    NATIVE_FIRST_FLIGHT_SAPIENCE,
    NATIVE_COLLAPSE_CONTAMINATION,
    NATIVE_EXPLOIT_YIELD,
    NATIVE_TRADE_UNITS,
    NATIVE_UPLIFT_EQUIPMENT,
    NATIVE_TITHE_SHARE,
    NATIVE_SYLLABLES,
    NATIVE_VALUES,
    POLICY_CARDS,
    POLICY_CONTACT_READY_STAGE,
    PRICE_LEVEL,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector
from xylarium.kernel.experience import ExperienceManager
from xylarium.kernel import alignment as align

ORBITAL = len(NATIVE_STAGES) - 1
SPECIES_FORMS = {
    "biotic": ["hominid", "arthropod", "saurian", "avian", "cephalopod"],
    "mineral": ["silicoid", "crystallid", "lithovore"],
    "plasmic": ["flarekin", "ionborn"],
    "cryogenic": ["rimeborn", "glacier-kin"],
}
PRODUCE = {"biotic": "ORGANICS", "mineral": "ORE", "plasmic": "H", "cryogenic": "H2O"}
POPULATION_BY_STAGE = [(3_000, 20_000), (10_000, 80_000), (40_000, 250_000), (100_000, 900_000),
                       (500_000, 3_000_000), (1_000_000, 6_000_000), (2_000_000, 9_000_000)]
XP_OBSERVE = 3
XP_CONTACT = 8
XP_UPLIFT = 10


def _name(rng: random.Random) -> str:
    n = "".join(rng.choice(NATIVE_SYLLABLES) for _ in range(rng.randint(2, 3)))
    return n.capitalize()


def stage_name(natives: Dict[str, Any]) -> str:
    return NATIVE_STAGES[min(int(natives["stage"]), ORBITAL)]


class NativeManager:
    # ------------------------------------------------------------------ genesis
    @staticmethod
    def seed(sectors: Dict[int, Sector], rng: random.Random) -> int:
        """Native life on a share of uninhabited worlds whose type suits some metabolism."""
        from xylarium.kernel.universe import habitability
        placed = 0
        for sec in sectors.values():
            if sec.id == 1 or sec.kind != "SYSTEM":
                continue
            for p in sec.planets:
                if p.population > 0 or p.owner_id or p.civilization is not None or p.ruins or p.natives:
                    continue
                best = max(SPECIES_FORMS, key=lambda m: habitability(m, p.planet_type))
                if habitability(best, p.planet_type) < 0.6 or rng.random() >= NATIVE_WORLD_SHARE:
                    continue
                stage = rng.choices(range(len(NATIVE_STAGES)), weights=NATIVE_STAGE_WEIGHTS)[0]
                lo, hi = POPULATION_BY_STAGE[stage]
                name = _name(rng)
                p.natives = {
                    "name": name,
                    "species": f"{name.lower()}-{rng.choice(SPECIES_FORMS[best])}",
                    "metabolism": best,
                    "sapience": round(rng.uniform(2.0, 9.5), 1),
                    "stage": stage,
                    "progress": round(rng.random() * 0.5, 3),
                    "population": rng.randint(lo, hi),
                    "awareness": 0.0,
                    "contamination": 0.0,
                    "stability": round(rng.uniform(0.7, 1.0), 2),
                    "_": align.genesis_value(rng),      # a draw once spent on a given alignment, still taken
                    "temperament": rng.choice(["peaceful", "wary", "curious", "warlike", "devout"]),
                    "protector": None,
                    "contacted_by": [],
                    "converted": False,
                    "tribute": {},
                    "observations": 0,
                    "history": [],
                }
                p.natives.pop("_")                  # (the seed makes the same universe it always made)
                placed += 1
        return placed

    # ------------------------------------------------------------------ law
    @staticmethod
    def legality(kernel: Any, captain: Captain, sector: Sector, natives: Dict[str, Any], sub: str,
                 leap: int = 1) -> Tuple[bool, Dict[str, Any], str]:
        """Is this deed lawful here? Returns (lawful, hand, reason)."""
        hand = kernel.factions.hand_for(sector) if getattr(kernel, "factions", None) else {
            "card": "DELTA", "sapience_threshold": 0.0, "uplift_limit": 9, "enforcement": "NONE",
            "warrant": 0, "name": "No Authority", "authority": "NONE"}
        allows = POLICY_CARDS[hand["card"]]["allows"]
        if sub == "observe":
            return True, hand, ""
        if sub == "convert":
            return ("convert" in allows), hand, "Only the Choir of the Pyre sanctions missionary conversion."
        if sub == "contact" and "contact" not in allows:
            ready = ("contact_if_ready" in allows and natives["stage"] >= POLICY_CONTACT_READY_STAGE
                     and natives["sapience"] >= hand["sapience_threshold"])
            if not ready:
                return False, hand, (f"Directive {hand['card']} ({POLICY_CARDS[hand['card']]['name']}) forbids contact"
                                     + (f" before the {NATIVE_STAGES[POLICY_CONTACT_READY_STAGE]}"
                                        if "contact_if_ready" in allows else "") + ".")
            return True, hand, ""
        if sub in ("trade", "uplift", "protect", "collect", "exploit") and sub not in allows:
            return False, hand, f"Directive {hand['card']} ({POLICY_CARDS[hand['card']]['name']}) forbids {sub}."
        if sub in ("contact", "trade", "uplift", "protect") and natives["sapience"] < hand["sapience_threshold"]:
            return False, hand, (f"The {hand['name']} forbids dealings with peoples below sapience "
                                 f"{hand['sapience_threshold']:.1f} (the {natives['name']} measure {natives['sapience']:.1f}).")
        if sub == "uplift" and leap > hand["uplift_limit"]:
            return False, hand, f"The {hand['name']} permits uplift of at most {hand['uplift_limit']} stage(s) at a time."
        return True, hand, ""

    @staticmethod
    def _violation(kernel: Any, captain: Captain, planet: Planet, hand: Dict[str, Any], reason: str) -> str:
        """An unlawful deed that was not interdicted: the authority's enforcement follows."""
        align.deed(kernel, captain, "prime_violation")
        auth = kernel.factions.factions.get(hand.get("authority"))
        if auth is not None:
            auth.bump("violations")
            auth.bump("violations_era")
        warrant = int(hand.get("warrant", 0))
        enforcement = hand.get("enforcement", "NONE")
        note = ""
        if warrant > 0 and enforcement in ("WARRANT", "INQUISITION"):
            captain.bounty += warrant
            captain.bounty_placed_by = "Imperial Inquisition" if enforcement == "INQUISITION" else "Frontier Compact"
            captain.adjust_reputation("Federation", -5.0)
            captain.adjust_reputation("Indigenous", -10.0)
            if enforcement == "INQUISITION":
                captain.adjust_reputation("Imperium", -15.0)
            note = f" {hand['name']} issues a warrant: +{warrant:,} Cr."
            if getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(
                    sender=hand["name"].upper()[:20],
                    text=f"PRIME DIRECTIVE VIOLATION at {planet.name}: {captain.name}. {reason}{note}",
                    channel="ALERT", sector_id=planet.sector_id)
        from xylarium.kernel import chronicle
        chronicle.native_event(kernel, planet, planet.natives or {"name": planet.name, "alignment": 0.0},
                               f"The Violation of {planet.name}",
                               f"{captain.name} broke the {hand['name']}'s Directive {hand['card']} here. {reason}",
                               ["violation", "prime directive"])
        return f" [VIOLATION] {reason}{note}"

    # ------------------------------------------------------------------ interaction
    @classmethod
    def interact(cls, kernel: Any, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        sub = str(kwargs.get("sub_action") or "observe").lower()
        pid = kwargs.get("planet_id")
        worlds = [p for p in sector.planets if p.natives]
        if pid:
            worlds = [p for p in worlds if p.id == pid or p.name.lower() == str(pid).lower()]
        if not worlds:
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                "No native society lives on a world in this system.")
        planet = worlds[0]
        natives = planet.natives
        leap = max(1, int(kwargs.get("leap", 1) or 1))
        handler = getattr(cls, f"_do_{sub}", None)
        if handler is None:
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                "Unknown dealing. Choose observe, contact, trade, uplift, protect, collect, exploit or convert.")
        if sub == "convert" and captain.faction_id != "ZEALOT":
            return ActionResult(False, ActionType.NATIVE_INTERACT, "You carry no faith to spread.")
        if sub not in ("observe", "contact", "exploit", "convert") and captain.id not in natives["contacted_by"] \
                and not (sub == "collect" and natives.get("protector") == captain.id):
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                f"The {natives['name']} do not know you. Make contact first.")
        lawful, hand, reason = cls.legality(kernel, captain, sector, natives, sub, leap)
        if not lawful and hand.get("enforcement") == "INTERDICT":
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                f"FEDERATION INTERDICTION: {reason} Patrol cutters escort you back to the lanes.")
        res = handler(kernel, captain, sector, planet, natives, hand, lawful, leap)
        if res.success and not lawful:
            res.message += cls._violation(kernel, captain, planet, hand, reason)
        if res.success:
            natives["history"] = (natives.get("history", []) + [[kernel.cycle_count, sub, captain.id]])[-12:]
        res.data.setdefault("natives", dict(natives)) if planet.natives else None
        res.data["doctrine"] = hand
        return res

    # --- observe
    @classmethod
    def _do_observe(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        natives["observations"] = natives.get("observations", 0) + 1
        seen_before = captain.chronicle_stats.setdefault("observed", [])
        detect = 0.03 if natives["stage"] >= 5 else 0.01
        natives["awareness"] = min(1.0, natives["awareness"] + detect)
        ExperienceManager.award(captain, "science", XP_OBSERVE, kernel, key=f"observe:{planet.id}")
        from xylarium.config import RESEARCH_POINTS_PER_UNIT
        from xylarium.kernel import knowledge             # watching another people live teaches biology
        knowledge.learn(kernel, knowledge.holder_of_captain(captain), "biology",
                        (3 + natives["stage"]) / RESEARCH_POINTS_PER_UNIT, "observation")
        align.deed(kernel, captain, "native_observed")
        facts = [
            f"Population about {natives['population']:,}; their cities {'glow at night' if natives['stage'] >= 4 else 'are lit by fire'}.",
            f"Temperament: {natives['temperament']}. Stability {natives['stability']:.2f}.",
            f"They are {'aware of' if natives['awareness'] >= 0.5 else 'unaware of'} the ships above them.",
        ]
        if planet.id not in seen_before or random.random() < 0.05:
            if planet.id not in seen_before:
                seen_before.append(planet.id)
            from xylarium.kernel import chronicle
            chronicle.field_notes(kernel, captain, planet, natives, " ".join(facts))
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            f"ORBITAL OBSERVATION of the {natives['name']} on {planet.name} ({stage_name(natives)}, "
                            f"sapience {natives['sapience']:.1f}): " + " ".join(facts),
                            turns_spent=1)

    # --- contact
    @classmethod
    def _do_contact(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        if captain.id in natives["contacted_by"]:
            return ActionResult(False, ActionType.NATIVE_INTERACT, f"You already have relations with the {natives['name']}.")
        first = not natives["contacted_by"]
        natives["contacted_by"].append(captain.id)
        natives["awareness"] = 1.0
        gap = max(0, ORBITAL - natives["stage"])
        natives["contamination"] = min(1.0, natives["contamination"] + (0.05 * gap if first else 0.02 * gap))
        natives["stability"] = max(0.0, natives["stability"] - 0.02 * gap)
        ExperienceManager.award(captain, "science", XP_CONTACT, kernel, key=f"contact:{planet.id}")
        captain.adjust_reputation("Indigenous", 5.0)
        if lawful:
            align.deed(kernel, captain, "native_contact")
        if first:
            from xylarium.kernel import chronicle
            chronicle.first_contact(kernel, captain, planet, natives, lawful)
        greeting = {"peaceful": "They meet you with open hands.", "wary": "They watch your landing party from the treeline.",
                    "curious": "Their scholars swarm the landing party with questions.",
                    "warlike": "Their warriors form a line; their chief steps forward alone.",
                    "devout": "Their priests declare you an omen, though of what they cannot agree."}
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            f"FIRST CONTACT with the {natives['name']} of {planet.name}. "
                            f"{greeting.get(natives['temperament'], '')}" if first else
                            f"Relations opened with the {natives['name']} of {planet.name}.",
                            turns_spent=2)

    # --- trade (barter: goods for produce and crafts - no money changes hands)
    @classmethod
    def _do_trade(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        cargo = captain.ship.cargo
        wants = NATIVE_VALUES.get(natives["metabolism"], ["ORGANICS", "EQUIPMENT"])
        give = next((g for g in wants if cargo.unbonded(g) >= NATIVE_TRADE_UNITS), None)
        if give is None:
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                f"The {natives['name']} want {' or '.join(wants)} ({NATIVE_TRADE_UNITS} units); you carry none to spare.")
        deposits = {k: v for k, v in planet.element_deposits.items() if v > 0}
        produce = PRODUCE.get(natives["metabolism"], "ORGANICS")
        received: Dict[str, int] = {}
        if deposits:
            elem = max(deposits, key=deposits.get)
            qty = min(deposits[elem], NATIVE_TRADE_UNITS + natives["stage"] * 2)
            got = cargo.stow(elem, qty)
            if got:
                planet.element_deposits[elem] -= got
                received[elem] = got
        if not received:
            got = cargo.stow(produce, NATIVE_TRADE_UNITS)
            matter.source("native_produce", produce, got)          # grown and made by their hands
            if got:
                received[produce] = got
        _take(cargo, give, NATIVE_TRADE_UNITS)
        if give == "EQUIPMENT" and natives["stage"] <= 2:
            natives["contamination"] = min(1.0, natives["contamination"] + 0.08)  # tools beyond their age
        craft = None
        if random.random() < 0.15 + 0.03 * natives["stage"]:
            craft = cls._craft(kernel, planet, natives, lawful)
            captain.artifacts.append(craft)
        align.deed(kernel, captain, "native_trade")
        msg = (f"BARTER with the {natives['name']}: gave {NATIVE_TRADE_UNITS} {give}, received "
               + (", ".join(f"{v} {k}" for k, v in received.items()) or "their thanks"))
        if craft:
            msg += f", and a gift: {craft['name']} (appraised {craft['appraisal_sol']:,} SOL)"
        return ActionResult(True, ActionType.NATIVE_INTERACT, msg + ".", turns_spent=1,
                            data={"given": {give: NATIVE_TRADE_UNITS}, "received": received})

    @staticmethod
    def _craft(kernel: Any, planet: Planet, natives: Dict[str, Any], lawful: bool) -> Dict[str, Any]:
        from xylarium.kernel.archaeology import ArchaeologyManager
        forms = ["carved stone idol", "woven star-map", "bronze ceremonial blade", "painted hide scroll",
                 "clockwork orrery", "glass reliquary", "printed epic", "radio-crystal set"]
        form = forms[min(len(forms) - 1, natives["stage"] + random.randint(0, 1))]
        art = {
            "id": f"ETH-{planet.id}-{kernel.cycle_count}-{random.randint(100, 999)}",
            "name": f"{natives['name']} {form}", "kind": "ANTIQUITY", "culture": natives["name"],
            "era": "LIVING", "stratum": 1, "era_name": stage_name(natives), "tech_level": natives["stage"] + 1,
            "condition": 1.0, "provenance": "licensed" if lawful else "unlicensed",
            "origin_sector": planet.sector_id, "elements": [],
        }
        art["appraisal_sol"] = ArchaeologyManager.appraisal(art)
        return art

    # --- uplift
    @classmethod
    def _do_uplift(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        need = NATIVE_UPLIFT_EQUIPMENT * leap
        if captain.ship.cargo.unbonded("EQUIPMENT") < need:
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                f"Uplift needs {need} EQUIPMENT (tools, schematics, teachers' kits).")
        if natives["stage"] >= ORBITAL:
            return ActionResult(False, ActionType.NATIVE_INTERACT, f"The {natives['name']} already reach orbit.")
        _take(captain.ship.cargo, "EQUIPMENT", need)
        target = natives["stage"] + leap
        reckless = leap > 2 or (natives["stage"] <= 2 and target >= 5)
        from xylarium.kernel import chronicle
        if reckless:
            # Antimatter on a Bronze-Age altar: the society shatters, or reality does
            if random.random() < 0.6:
                shattered = natives.get("population", 0)
                cls.collapse(kernel, planet, "a gift of fire from the sky they could not hold")
                align.deed(kernel, captain, "reckless_gift", dark=shattered)   # a people's order, shattered
                return ActionResult(True, ActionType.NATIVE_INTERACT,
                                    f"CATASTROPHE: the {natives['name']} could not hold what you gave them. "
                                    f"Their civilization has torn itself apart; {planet.name} is ruins.", turns_spent=2)
            cls._temporal_anomaly(kernel, planet, natives)
            natives["stage"] = min(ORBITAL, target)
            natives["contamination"] = 0.9
            natives["stability"] = 0.2
            return ActionResult(True, ActionType.NATIVE_INTERACT,
                                f"TEMPORAL ANOMALY: the {natives['name']} leapt {leap} ages in a season; their history "
                                f"folded on itself and a rift opened over {planet.name}. They worship the cargo.",
                                turns_spent=2)
        old = stage_name(natives)
        natives["stage"] = min(ORBITAL, target)
        natives["progress"] = 0.0
        natives["contamination"] = min(1.0, natives["contamination"] + 0.12 * leap)
        natives["stability"] = max(0.0, natives["stability"] - 0.08 * leap)
        ExperienceManager.award(captain, "science", XP_UPLIFT, kernel, key=f"uplift:{planet.id}")
        from xylarium.config import COMMODITY_CONFIG
        align.deed(kernel, captain, "native_uplift",
                   light=align.lives_of_sol(kernel, need * COMMODITY_CONFIG["EQUIPMENT"]["base_price"]))
        chronicle.native_event(kernel, planet, natives, f"The Gift of {captain.name}",
                               f"Teachers from the sky came with tools and patience. The {natives['name']} passed "
                               f"from the {old} into the {stage_name(natives)}.", ["uplift"])
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            f"UPLIFT: the {natives['name']} advance from the {old} to the {stage_name(natives)} "
                            f"(contamination {natives['contamination']:.2f}).", turns_spent=2)

    @staticmethod
    def _temporal_anomaly(kernel: Any, planet: Planet, natives: Dict[str, Any]) -> None:
        rm = getattr(kernel, "research_manager", None)
        if rm is None:
            return
        from xylarium.kernel.research import CosmicAnomaly
        aid = f"ANOM-T{planet.sector_id:03d}{kernel.cycle_count % 1000:03d}"
        if aid in rm.anomalies:
            return
        rm.anomalies[aid] = CosmicAnomaly(
            id=aid, sector_id=planet.sector_id, name=f"{natives['name']} Temporal Fold",
            anomaly_type="TESSERACT_RIFT", difficulty=3, puzzle_type="RCF_CONJUGACY_MATRIX", status="UNDISCOVERED",
            reward_tech="JUMP_DRIVE", reward_research=80, reward_credits=0,
            reward_elements={"umbrite": 10}, description="A rift where a people's history folded under an impossible gift.",
            puzzle_target=45,
        )
        kernel.sectors[planet.sector_id].anomalies.append(aid)

    # --- protect / collect
    @classmethod
    def _do_protect(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        cur = natives.get("protector")
        if cur and cur != captain.id and cur in kernel.captains:
            return ActionResult(False, ActionType.NATIVE_INTERACT,
                                f"The {natives['name']} are already under {kernel.captains[cur].name}'s protection.")
        natives["protector"] = captain.id
        natives["stability"] = min(1.0, natives["stability"] + 0.1)
        captain.adjust_reputation("Indigenous", 10.0)
        align.deed(kernel, captain, "native_protect")
        from xylarium.kernel import chronicle
        chronicle.native_event(kernel, planet, natives, f"The Protectorate of {planet.name}",
                               f"{captain.name} has sworn to shield the {natives['name']}; in return, a tithe of "
                               f"their harvest is set aside each season.", ["protectorate"])
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            f"PROTECTORATE declared over the {natives['name']} of {planet.name}. "
                            f"Their tithe accrues each quarter; COLLECT it in orbit.", turns_spent=1)

    @classmethod
    def _do_collect(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        if natives.get("protector") != captain.id:
            return ActionResult(False, ActionType.NATIVE_INTERACT, "You are not this people's protector.")
        got: Dict[str, int] = {}
        for good, qty in list(natives.get("tribute", {}).items()):
            n = captain.ship.cargo.stow(good, qty)
            if n:
                got[good] = n
                natives["tribute"][good] -= n
                if natives["tribute"][good] <= 0:
                    natives["tribute"].pop(good)
        if not got:
            return ActionResult(False, ActionType.NATIVE_INTERACT, "No tithe has accrued yet (or your holds are full).")
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            "Protectorate tithe collected: " + ", ".join(f"{v} {k}" for k, v in got.items()) + ".",
                            turns_spent=1, data={"collected": got})

    # --- exploit
    @classmethod
    def _do_exploit(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        deposits = sorted(((k, v) for k, v in planet.element_deposits.items() if v > 0), key=lambda kv: -kv[1])
        taken: Dict[str, int] = {}
        budget = NATIVE_EXPLOIT_YIELD
        for elem, have in deposits:
            if budget <= 0:
                break
            n = captain.ship.cargo.stow(elem, min(have, budget))
            if n:
                taken[elem] = n
                planet.element_deposits[elem] -= n
                budget -= n
        if not taken:
            return ActionResult(False, ActionType.NATIVE_INTERACT, "Nothing left to strip, or your holds are full.")
        before = natives["population"]
        natives["population"] = int(natives["population"] * 0.85)
        natives["stability"] = max(0.0, natives["stability"] - 0.2)
        natives["contamination"] = min(1.0, natives["contamination"] + 0.05)
        natives["awareness"] = 1.0
        from xylarium.config import COMMODITY_CONFIG
        worth = sum(n * COMMODITY_CONFIG.get(e, {}).get("base_price", 20) for e, n in taken.items())
        align.act(kernel, captain, "native_exploit", harmed_sol=worth, lives_lost=before - natives["population"])
        captain.adjust_reputation("Indigenous", -15.0)
        from xylarium.kernel import chronicle
        if random.random() < 0.5:
            chronicle.native_event(kernel, planet, natives, f"The Stripping of {planet.name}",
                                   f"The sky-ships came for the {natives['name']}'s mountains. Villages were moved, "
                                   f"then emptied. {captain.name}'s crews did not learn their names.", ["exploitation"])
        msg = f"STRIP-MINING {planet.name}: extracted " + ", ".join(f"{v} {k}" for k, v in taken.items()) + \
              f". The {natives['name']} are displaced (stability {natives['stability']:.2f})."
        if natives["stability"] <= 0:
            cls.collapse(kernel, planet, "strip-mined and displaced until nothing held")
            msg += " Their civilization has collapsed."
        return ActionResult(True, ActionType.NATIVE_INTERACT, msg, turns_spent=1, data={"extracted": taken})

    # --- convert
    @classmethod
    def _do_convert(cls, kernel, captain, sector, planet, natives, hand, lawful, leap) -> ActionResult:
        if natives.get("converted"):
            return ActionResult(False, ActionType.NATIVE_INTERACT, f"The {natives['name']} already burn for the Pyre.")
        resist = 0.3 + 0.05 * natives["sapience"] - (0.2 if natives["temperament"] == "devout" else 0.0)
        natives["awareness"] = 1.0
        if captain.id not in natives["contacted_by"]:
            natives["contacted_by"].append(captain.id)
        if random.random() < resist:
            natives["stability"] = max(0.0, natives["stability"] - 0.08)
            natives["population"] = int(natives["population"] * 0.96)
            natives["resisted_until"] = kernel.cycle_count + 200   # the missionaries withdraw, for now
            align.deed(kernel, captain, "crusade")
            return ActionResult(True, ActionType.NATIVE_INTERACT,
                                f"The {natives['name']} resist the missionaries. The crusaders burn a temple in answer.",
                                turns_spent=2)
        # The faith absorbs a people rather than shattering it: its own rites give them cohesion
        natives["converted"] = True
        natives["contamination"] = min(0.5, natives["contamination"])
        natives["stability"] = min(1.0, natives["stability"] + 0.2)
        planet.faction_id = "ZEALOT"
        align.deed(kernel, captain, "native_converted")
        factions = getattr(kernel, "factions", None)
        if factions is not None:
            factions.note_expansion(kernel, "ZEALOT", planet.sector_id)
            factions.factions["ZEALOT"].bump("converts", natives["population"]) if "ZEALOT" in factions.factions else None
        from xylarium.kernel import chronicle
        chronicle.native_event(kernel, planet, natives, f"The Kindling of the {natives['name']}",
                               f"The missionaries of the Pyre came to {planet.name}. The old gods' shrines were "
                               f"broken and new fires lit. The {natives['name']} now sing the Choir's hymns.",
                               ["conversion", "crusade"])
        return ActionResult(True, ActionType.NATIVE_INTERACT,
                            f"CONVERSION: the {natives['name']} of {planet.name} now burn for the Pyre.", turns_spent=2)

    # ------------------------------------------------------------------ fate
    @staticmethod
    def collapse(kernel: Any, planet: Planet, cause: str) -> None:
        """A native society shatters; its world becomes ruins (no money: they had none)."""
        from xylarium.kernel.archaeology import _new_ruins, bury
        natives = planet.natives
        if not natives:
            return
        rng = random.Random(zlib.crc32(f"{planet.id}:{getattr(kernel, 'cycle_count', 0)}".encode()))
        planet.ruins = bury(planet, _new_ruins(natives["name"], natives["species"], natives["metabolism"], "RECENT",
                                               natives["stage"] + 1, [], "native collapse", kernel.cycle_count,
                                               rng.randint(1, 3), None, 0, rng))
        release_tribute(planet, inherit=False)
        planet.natives = None
        if planet.faction_id == "ZEALOT" and planet.population <= 0:
            planet.faction_id = None
        stats = getattr(kernel, "native_stats", None)
        if stats is not None:
            stats["collapses"] = stats.get("collapses", 0) + 1
        from xylarium.kernel import chronicle
        chronicle.annals_collapse(kernel, planet, f"{natives['name']} ({stage_name(natives)})", cause)
        if getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(sender="XENO-ARCHIVE",
                                             text=f"NATIVE COLLAPSE: the {natives['name']} of {planet.name} are gone ({cause}).",
                                             channel="COMM-1", sector_id=planet.sector_id)

    @classmethod
    def _practise(cls, kernel: Any, planet: Planet, n: Dict[str, Any]) -> float:
        """A native people learns as every people does before writing (ways.py): by living - a season's practice
        is its numbers (in thousands) at its minds' depth, as steady as its society and quickened by what outsiders
        show it; it fades as all knowledge does (knowledge.py). Its age is how many times it has doubled what it
        knows (Wright: each stage costs a doubling of experience): stage = log2(experience / unit + 1)."""
        import math
        from xylarium.config import HOUSEHOLD_INCOME_SHARE, KNOWLEDGE_UNIT
        from xylarium.kernel import biosphere, genome, knowledge, laws, ways
        from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
        holder = f"natives:{planet.id}"
        depth = laws.cognition(n["metabolism"])["depth"] * (n["sapience"] / 5.0)
        # its numbers in the units every people is counted in: no more than its world feeds them (its tales
        # count millions; its land, at its way of life, feeds what it feeds)
        farmed = "crop_z" not in n or n["stage"] >= 1
        crop = 1.0 if "crop_z" not in n else min(1.0, ways.TROPHIC_EFFICIENCY * math.exp(float(n["crop_z"])))
        try:
            fed = biosphere.carrying_capacity(kernel, planet, citadel=0, metabolism=n["metabolism"])
        except Exception:
            fed = n["population"]
        people = min(n["population"], fed * (crop if farmed else ways.TROPHIC_EFFICIENCY))
        units = people / 1000.0 * depth * n["stability"] * (1 + 0.5 * n["contamination"]) * FISCAL_QUARTER_CYCLES / 100.0
        for d in knowledge.DOMAINS:
            knowledge.learn(kernel, holder, d, units / len(knowledge.DOMAINS), "practice")
        experience = sum(knowledge.stocks(kernel, holder).values())
        level = math.log2(experience / KNOWLEDGE_UNIT + 1.0)
        if "crop_z" in n:
            # a forager universe's natives breed their crops as every people does (ways.py, Lande): they leave the
            # Stone Age when farming pays, and found kingdoms only when their surplus can bear one
            m = laws.mastery(knowledge.experience(kernel, holder, "biology"), KNOWLEDGE_UNIT)
            z = float(n["crop_z"]) + genome.VARIANCE * m * FISCAL_QUARTER_CYCLES / 100.0
            n["crop_z"] = round(min(math.log(1.0 / ways.TROPHIC_EFFICIENCY), z), 6)
            if math.exp(n["crop_z"]) - 1.0 <= 1.0 - m:
                level = min(level, 0.999)                          # farming does not yet pay: the Stone Age
            elif 1.0 - 1.0 / math.exp(n["crop_z"]) < 1.0 - HOUSEHOLD_INCOME_SHARE:
                level = min(level, 2.999)                          # no surplus to bear a kingdom yet
        return level

    @classmethod
    def first_flight(cls, kernel: Any, planet: Planet) -> None:
        """An Orbital-age people reaches the stars: they become a spacefaring civilization."""
        from xylarium.kernel.civilization import Civilization
        from xylarium.kernel import ledger
        natives = planet.natives
        forms = {"biotic": 1, "mineral": 2, "plasmic": 6, "cryogenic": 12}
        civ = Civilization(
            name=natives["name"], species_name=natives["species"], class_code=forms.get(natives["metabolism"], 1),
            sigil="✧", clade=natives["species"].split("-")[-1], metabolism=natives["metabolism"],
            disposition="empiricist", motto="we climbed the sky on our own ladder", station="unseated",
            era_index=0, tech_level=2,
        )
        planet.civilization = civ
        from xylarium.kernel import rent as _rent
        _rent.prehistory(kernel, planet)                       # the ladder they climbed, as they climbed it
        civ.native_policy = "ALPHA" if civ.alignment >= 0.3 else None  # they remember being watched
        from xylarium.kernel import biosphere
        biosphere.adapt(kernel, civ, planet)                   # adapted to the world they evolved on
        planet.population = max(planet.population, min(20000, natives["population"] // 200))
        planet.morale = 90
        # A new sovereign economy enters the galaxy: its founding treasury is declared new territory
        endowment = int(2000 * PRICE_LEVEL.get(planet.currency, 1.0))
        planet.treasury += endowment
        ledger.mint("cluster_genesis", endowment, planet.currency)
        release_tribute(planet, inherit=True)
        planet.natives = None
        stats = getattr(kernel, "native_stats", None)
        if stats is not None:
            stats["first_flights"] = stats.get("first_flights", 0) + 1
        from xylarium.kernel import chronicle
        chronicle.native_event(kernel, planet, natives, f"First Flight of the {natives['name']}",
                               f"On a column of fire the {natives['name']} rose from {planet.name} and did not "
                               f"fall back. They are a spacefaring people now.", ["first flight", "genesis"])
        chron = getattr(kernel, "chronicle", None)
        if chron is not None:
            chron.record(kernel, "GENESIS_MANIFESTO", planet.id, civ.name, f"The Genesis of the {civ.name}",
                         f"GENESIS MANIFESTO. We, the {civ.name} of {planet.name}, climbed the sky on our own ladder. "
                         f"We have watched your ships in our night for generations. Now we will speak.",
                         sector_id=planet.sector_id, tags=["genesis", "first flight"], alignment=civ.alignment)
        if getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(sender=civ.name, text=f"FIRST FLIGHT: the {civ.name} of {planet.name} have reached orbit!",
                                             channel="SYSTEM", sector_id=planet.sector_id)

    # ------------------------------------------------------------------ world tick
    @classmethod
    def tick(cls, kernel: Any) -> None:
        """Fiscal-quarter pass: progress, recovery, protectorate tithe, collapse and first flight."""
        from xylarium.kernel import chronicle
        for sec in kernel.sectors.values():
            for planet in sec.planets:
                n = planet.natives
                if not n:
                    continue
                n["contamination"] = max(0.0, n["contamination"] - 0.004)
                n["stability"] = max(0.0, min(1.0, n["stability"] + 0.02 - 0.05 * max(0.0, n["contamination"] - 0.4)))
                n["awareness"] = max(0.0, n["awareness"] - (0.0 if n["contacted_by"] else 0.002))
                if n["contamination"] >= NATIVE_COLLAPSE_CONTAMINATION and n["stability"] < 0.3:
                    cls.collapse(kernel, planet, "a culture drowned in outsiders' wonders")
                    continue
                level = cls._practise(kernel, planet, n)
                if n["stage"] < ORBITAL:
                    n["progress"] = round(max(0.0, level - n["stage"]), 5)
                    if level >= n["stage"] + 1:
                        old = stage_name(n)
                        n["stage"] += 1
                        n["progress"] = 0.0
                        n["population"] = int(n["population"] * 1.6)
                        stats = getattr(kernel, "native_stats", None)
                        if stats is not None:
                            stats["advances"] = stats.get("advances", 0) + 1
                        chronicle.native_event(kernel, planet, n, f"The {stage_name(n)} of the {n['name']}",
                                               _advance_text(n, old), ["advance"])
                elif n["sapience"] >= NATIVE_FIRST_FLIGHT_SAPIENCE:
                    n["progress"] = round(max(0.0, level - ORBITAL), 5)
                    if level >= ORBITAL + 1:                      # one more doubling of what they know: the sky
                        cls.first_flight(kernel, planet)
                        continue
                if n.get("protector"):
                    if n["protector"] not in kernel.captains:
                        n["protector"] = None
                    else:
                        good = PRODUCE.get(n["metabolism"], "ORGANICS")
                        amount = max(1, int(NATIVE_TITHE_SHARE * (10 + 6 * n["stage"])))
                        have = n["tribute"].get(good, 0)
                        added = max(0, min(200, have + amount) - have)
                        if added:
                            n["tribute"][good] = have + added
                            matter.source("native_produce", good, added)     # the people's labour, set aside


def release_tribute(planet: Any, inherit: bool) -> None:
    """A people leaves its natives record behind: its world inherits the tribute stores (first flight, annexation),
    or they are lost with the people (collapse)."""
    n = planet.natives or {}
    for good, qty in list((n.get("tribute") or {}).items()):
        if qty <= 0:
            continue
        if not inherit:
            matter.sink("native_collapse", good, qty)
        elif good == "ORGANICS":
            planet.organics_silo += qty
        elif good == "ORE":
            planet.ore_silo += qty
        else:
            planet.element_reserves[good] = planet.element_reserves.get(good, 0) + qty
    if n.get("tribute"):
        n["tribute"] = {}


def _advance_text(n: Dict[str, Any], old: str) -> str:
    new = stage_name(n)
    lines = {
        "Bronze Age": "The first furnaces burn in the river valleys; bronze replaces flint in the hands of kings.",
        "Iron Age": "Iron is cheap and war is cheaper; the old empires break and new ones are forged.",
        "Agrarian Kingdoms": "Great granaries rise; scribes count the harvest and the stars with equal care.",
        "Industrial": "The first engines scream. The rivers darken, and the cities double every generation.",
        "Atomic": "They split the atom. For one terrible season they almost ended themselves; then they looked up.",
        "Orbital": "A spark of their own making circles the world. They are listening now, and they have heard us.",
    }
    return f"The {n['name']} have passed from the {old} into the {new}. {lines.get(new, '')}"


def _take(cargo: Any, good: str, qty: int) -> None:
    """Goods handed to a native society leave the census (their society is not an account of ours)."""
    if good in ("ORE", "ORGANICS", "EQUIPMENT"):
        have = getattr(cargo, good.lower())
        taken = min(have, qty)
        setattr(cargo, good.lower(), have - taken)
        matter.sink("native_society", good, taken)
        return
    key = next((k for k in cargo.elements if k.lower() == good.lower()), good)
    have = cargo.elements.get(key, 0)
    taken = min(have, qty)
    if have - taken > 0:
        cargo.elements[key] = have - taken
    else:
        cargo.elements.pop(key, None)
    matter.sink("native_society", key, taken)
