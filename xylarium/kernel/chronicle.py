"""
Xylarium: the Civilizational Chronicle Engine and the Galactic Library.

Civilizations write their own history. Milestones in the simulation - a long haul
across the frontier, a crew that survived famine, a colony that held out against a
siege, a native people's first Iron Age forge, a zealot purge, an Imperial tithe
report, a captain's turn toward the Light or the Dark - are composed into
procedurally written chronicle entries in the voice of whoever lived them:

  CAPTAINS_LOG        a captain's own log of the journey
  PLANETARY_ANNALS    the annals of a world: founding, sieges, collapse, conquest
  FIELD_NOTES         observers' notes on non-spacefaring locals
  FACTION_DECREE      great-power decrees, crusades, purges, tithe reports
  GENESIS_MANIFESTO   a new lineage (cognitive cleave, first flight) declares itself
  GALACTIC_HISTORY    the era-by-era history of the galaxy
  PERSONAL_LOG        entries written by players themselves
  LINEAGE_LEGACY      the sealed record of a player lineage that ended (and the Hall of Lineages)

Entries are stored in the kernel (bounded) and browsed at any starport through the
Galactic Library console ([L]ibrary).
"""

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import CHRONICLE_MAX_ENTRIES, NATIVE_STAGES

KINDS = ["CAPTAINS_LOG", "PLANETARY_ANNALS", "FIELD_NOTES", "FACTION_DECREE",
         "GENESIS_MANIFESTO", "GALACTIC_HISTORY", "PERSONAL_LOG", "LINEAGE_LEGACY"]


def stardate(cycle: int) -> str:
    return f"{2400 + cycle / 1000:.3f}"


class ChronicleEngine:
    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []
        self.next_id: int = 1
        self.counts: Counter = Counter()
        self.last_era_cycle: int = 0

    # ------------------------------------------------------------------ store
    def record(self, kernel: Any, kind: str, subject_id: Optional[str], subject: str, title: str, body: str,
               sector_id: Optional[int] = None, tags: Optional[List[str]] = None,
               alignment: Optional[float] = None, author: Optional[str] = None) -> Dict[str, Any]:
        cycle = int(getattr(kernel, "cycle_count", 0)) if kernel is not None else 0
        from xylarium.kernel.alignment import band
        entry = {
            "id": f"CHR-{self.next_id:05d}",
            "cycle": cycle,
            "stardate": stardate(cycle),
            "kind": kind,
            "subject_id": subject_id,
            "subject": subject,
            "title": title,
            "body": body,
            "sector_id": sector_id,
            "tags": list(tags or []),
            "alignment": None if alignment is None else round(alignment, 3),
            "band": None if alignment is None else band(alignment),
            "author": author or subject,
        }
        self.next_id += 1
        self.entries.append(entry)
        self.counts[kind] += 1
        if len(self.entries) > CHRONICLE_MAX_ENTRIES:
            # Keep the galaxy's memory bounded: drop the oldest routine logs first, never history or manifestos
            for i, e in enumerate(self.entries):
                if e["kind"] not in ("GALACTIC_HISTORY", "GENESIS_MANIFESTO", "PERSONAL_LOG", "LINEAGE_LEGACY"):
                    self.entries.pop(i)
                    break
            else:
                self.entries.pop(0)
        return entry

    def query(self, kind: Optional[str] = None, subject: Optional[str] = None, text: Optional[str] = None,
              page: int = 0, per_page: int = 8) -> Tuple[List[Dict[str, Any]], int]:
        rows = self.entries
        if kind:
            kind = kind.upper()
            rows = [e for e in rows if e["kind"] == kind or e["kind"].startswith(kind)]
        if subject:
            s = subject.lower()
            rows = [e for e in rows if s in (e.get("subject") or "").lower() or s == (e.get("subject_id") or "").lower()]
        if text:
            t = text.lower()
            rows = [e for e in rows if t in e["title"].lower() or t in e["body"].lower()]
        total = len(rows)
        newest = list(reversed(rows))
        start = max(0, page) * per_page
        return newest[start:start + per_page], total

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        key = str(entry_id).upper()
        return next((e for e in self.entries if e["id"] == key), None)

    def to_dict(self) -> Dict[str, Any]:
        return {"entries": [dict(e) for e in self.entries], "next_id": self.next_id,
                "counts": dict(self.counts), "last_era_cycle": self.last_era_cycle}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChronicleEngine":
        eng = cls()
        eng.entries = [dict(e) for e in data.get("entries", [])]
        eng.next_id = int(data.get("next_id", len(eng.entries) + 1))
        eng.counts = Counter(data.get("counts", {}))
        eng.last_era_cycle = int(data.get("last_era_cycle", 0))
        return eng


# =============================================================================
# Voices
# =============================================================================
def _chron(kernel: Any) -> Optional[ChronicleEngine]:
    return getattr(kernel, "chronicle", None) if kernel is not None else None


def _pick(options: List[str]) -> str:
    return random.choice(options)


def _opener(captain: Any, kernel: Any) -> str:
    cycle = int(getattr(kernel, "cycle_count", 0))
    sd = stardate(cycle)
    faction = getattr(captain, "faction_id", None)
    clade = getattr(captain, "clade", "BIOTIC")
    if faction == "ZEALOT":
        return f"Litany of the Pyre, verse {cycle}. "
    if faction == "IMPERIUM" or clade == "IMPERIAL":
        return f"By the Throne's leave, entered into the Tithe-Ledger at stardate {sd}: "
    if clade == "LITHIC":
        return f"Strata-record, layer {sd}. "
    if clade == "PLASMIC":
        return f"Flare-memory {sd}. "
    if clade == "CRYOGENIC":
        return f"Cold-log, entropy index {sd}. "
    if getattr(captain, "cosmic_alignment", 0.0) <= -0.5:
        return f"Private record, sealed, {sd}. "
    return f"Captain's log, stardate {sd}. "


def _closer(alignment: float) -> str:
    if alignment >= 0.5:
        return _pick(["We go on, and we share what we find.",
                      "May whoever reads this find the lanes a little kinder than we did.",
                      "Every chart we file is a lantern for someone behind us."])
    if alignment >= 0.15:
        return _pick(["The work is honest, and the crew sleeps well.",
                      "We keep our word; the frontier remembers that.",
                      "Onward, and fair winds on the solar tide."])
    if alignment > -0.15:
        return _pick(["Credits in, credits out. The void does not care, so neither do I.",
                      "Survive the next jump; worry about the one after later.",
                      "Nothing is free out here, and nothing is forgiven."])
    if alignment > -0.5:
        return _pick(["They will call it theft. I call it the price of being slow.",
                      "The strong eat. That is the only law I have seen enforced.",
                      "Let the Federation keep its charters; I keep what I take."])
    return _pick(["Let them burn their little lanterns. The dark was here first.",
                  "Fear is the only currency that never devalues.",
                  "When the last light goes out, I will still be here."])


def _place(kernel: Any, sector_id: Optional[int]) -> str:
    if sector_id is None or kernel is None or sector_id not in kernel.sectors:
        return "the void"
    sec = kernel.sectors[sector_id]
    return f"{sec.name} (Sector {sector_id:03d})"


def _record_captain(kernel: Any, captain: Any, kind: str, title: str, body: str, tags: List[str]) -> Optional[Dict[str, Any]]:
    chron = _chron(kernel)
    if chron is None:
        return None
    return chron.record(kernel, kind, captain.id, captain.name, title, body, sector_id=captain.sector_id,
                        tags=tags, alignment=captain.cosmic_alignment)


# =============================================================================
# Captains' logs
# =============================================================================
def log_long_haul(kernel: Any, captain: Any, jumps: int) -> None:
    visited = len(getattr(captain, "visited_sectors", []))
    zones = ", ".join(z.title() for z in getattr(captain, "zones_entered", [])) or "only the Federation core"
    cargo = captain.ship.cargo
    held = [(k, v) for k, v in cargo.to_dict().items() if isinstance(v, int) and v > 0 and k not in ("capacity", "available", "used")]
    manifest = ", ".join(f"{v} {k}" for k, v in held[:3]) or "empty holds"
    title = _pick([f"The Long Haul: {jumps:,} Jumps", f"{jumps:,} Warps and Counting", f"The Road of {jumps:,} Stars"])
    body = (
        f"{_opener(captain, kernel)}The {captain.ship.ship_type} has made its {jumps:,}th warp jump. "
        f"We have charted {visited} sectors and crossed into {zones}. "
        f"Today we hold at {_place(kernel, captain.sector_id)} carrying {manifest}. "
        + _pick([
            "The crew has stopped counting the stars and started naming them.",
            "Somewhere behind us, a port we once fed is feeding someone else.",
            "The drive coils hum in a key the engineers swear they can sing.",
            "Every jump is a small bet against the dark; so far we keep winning.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["journey", "milestone"])


def log_freight(kernel: Any, captain: Any, deliveries: int) -> None:
    title = _pick([f"The {deliveries}th Manifest", f"{deliveries} Cargoes Delivered", f"Ledger of {deliveries} Promises Kept"])
    body = (
        f"{_opener(captain, kernel)}Contract number {deliveries} signed off today at {_place(kernel, captain.sector_id)}. "
        + _pick([
            "Colonies we have never seen now eat bread we carried.",
            "The dockmasters know our hull by its scorch marks now.",
            "A freight broker bought the crew a round; that has never happened before.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["commerce", "milestone"])


def log_hunger(kernel: Any, captain: Any, missed: int) -> None:
    title = _pick(["The Hungry Watch", "Rations Restored", f"{missed} Empty Meals"])
    body = (
        f"{_opener(captain, kernel)}For {missed} ration bells the galley was empty. The deflector grid flickered; "
        f"tempers did worse. Today we ate again at {_place(kernel, captain.sector_id)}. "
        + _pick([
            "Nobody spoke during the meal. Nobody needed to.",
            "I have ordered a reserve stored that no captain may touch, myself included.",
            "Hunger teaches arithmetic faster than any academy.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["hardship", "famine"])


def log_ascension(kernel: Any, captain: Any, node_name: str, tier: int) -> None:
    title = f"Crystallization: {node_name}"
    body = (
        f"{_opener(captain, kernel)}The lineage has diverged. I am no longer what I was; the cochain has pitched "
        f"toward {node_name} (Tier {tier}). "
        + _pick([
            "The crew salutes differently now. I am not sure I like it.",
            "Every rank is a heavier ledger to keep honest.",
            "The old charts look smaller from here.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["ascension"])


def log_turning(kernel: Any, captain: Any, old_band: str, new_band: str, cause: str) -> None:
    from xylarium.config import ALIGNMENT_BANDS
    order = [t for _, t in ALIGNMENT_BANDS]
    toward_light = order.index(new_band) < order.index(old_band) if (new_band in order and old_band in order) else True
    title = f"The Turning: {old_band} to {new_band}"
    if toward_light:
        text = _pick([
            "Something in the crew has changed. They share rations with strangers now.",
            "I did not set out to be good. The ledger simply came out that way.",
            "The dockmasters' greetings have grown warmer; I find I have earned it.",
        ])
    else:
        text = _pick([
            "There is a coldness in the crew now. I put it there.",
            "The first time was necessary. The second was easier. I no longer count.",
            "Ports go quiet when we dock. I have decided I prefer it.",
        ])
    body = f"{_opener(captain, kernel)}{text} (Cause: {cause.replace('_', ' ')}.) {_closer(captain.cosmic_alignment)}"
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["alignment", "light" if toward_light else "dark"])


def log_loss(kernel: Any, captain: Any, victor_name: str, sector_id: int, hull: str) -> None:
    title = _pick([f"The Loss of the {hull}", "Escape Pod Log", f"Wreckage at Sector {sector_id:03d}"])
    body = (
        f"{_opener(captain, kernel)}The {hull} is gone, broken apart at {_place(kernel, sector_id)} by {victor_name}. "
        "What is left of the crew rides an escape pod home to Sol. "
        + _pick([
            "The debris field will be picked over by salvagers before the week is out.",
            "I keep replaying the last volley. There was nothing to be done.",
            "Ships are borrowed from the dark; eventually it asks for them back.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "CAPTAINS_LOG", title, body, ["combat", "loss"])


def log_discovery(kernel: Any, captain: Any, what: str, where: Optional[int] = None) -> None:
    title = _pick([f"Discovery: {what}", f"Notes on {what}"])
    body = (
        f"{_opener(captain, kernel)}Today we recorded {what} at {_place(kernel, where if where is not None else captain.sector_id)}. "
        + _pick([
            "The science officer has not slept since.",
            "I have filed the findings with the Library, so others need not start from nothing.",
            "The universe is larger this morning than it was last night.",
        ])
        + " " + _closer(captain.cosmic_alignment)
    )
    _record_captain(kernel, captain, "FIELD_NOTES", title, body, ["knowledge", "discovery"])


def genesis_manifesto(kernel: Any, child: Any, parent: Optional[Any], origin: str = "cleave") -> None:
    chron = _chron(kernel)
    if chron is None:
        return
    lineage = f"{child.species} / {child.metabolism}"
    if origin == "first_flight":
        opening = f"We, the {child.name}, rose from our own world on our own fire."
    elif parent is not None:
        opening = f"We, {child.name}, divided from {parent.name} as a seed divides from the tree."
    else:
        opening = f"We, {child.name}, declare ourselves."
    body = (
        f"GENESIS MANIFESTO. {opening} Our lineage is {lineage}; our clade is {child.clade}. "
        + _pick([
            "We will perceive what our forebears could not, and trade what they would not.",
            "We carry their memory, not their debts.",
            "Let the Library record that we began with little and owed nothing.",
        ])
        + " " + _closer(child.cosmic_alignment)
    )
    chron.record(kernel, "GENESIS_MANIFESTO", child.id, child.name, f"The Genesis of {child.name}", body,
                 sector_id=child.sector_id, tags=["genesis", origin], alignment=child.cosmic_alignment)


# =============================================================================
# Planetary annals
# =============================================================================
def record_planet(kernel: Any, planet: Any, title: str, body: str, tags: List[str],
                   alignment: Optional[float] = None, kind: str = "PLANETARY_ANNALS") -> None:
    chron = _chron(kernel)
    if chron is None:
        return
    if alignment is None:
        civ = getattr(planet, "civilization", None)
        alignment = getattr(civ, "alignment", 0.0) if civ else 0.0
    chron.record(kernel, kind, planet.id, planet.name, title, body, sector_id=planet.sector_id,
                 tags=tags, alignment=alignment)


def annals_colony_founded(kernel: Any, planet: Any, captain: Any) -> None:
    title = _pick([f"The Founding of {planet.name}", f"First Landfall on {planet.name}"])
    body = (
        f"Annals of {planet.name}, year one. Colonists sent by {captain.name} set down on this "
        f"{planet.planet_type.lower().replace('_', ' ')} world in {_place(kernel, planet.sector_id)}. "
        + _pick([
            "The first night the dome lights failed twice. By morning, the children had named every star.",
            "They buried a time capsule under the landing pad: seeds, a song, and a bill of lading.",
            "The first harvest was thin, but it was theirs.",
        ])
    )
    record_planet(kernel, planet, title, body, ["founding"], alignment=captain.cosmic_alignment)


def annals_collapse(kernel: Any, planet: Any, culture: str, cause: str) -> None:
    title = _pick([f"The Fall of {culture}", f"The Last Days of {planet.name}"])
    body = (
        f"Annals of {planet.name}, final entry. The {culture} is no more; {cause}. "
        + _pick([
            "Their cities are silent. In a hundred years, someone will dig here and wonder.",
            "Their vaults were sealed and buried beneath the ash; the archaeologists will come.",
            "They wrote their last songs on the walls. The walls remain.",
        ])
    )
    record_planet(kernel, planet, title, body, ["collapse", "ruins"])


def annals_conquest(kernel: Any, planet: Any, old_owner: str, conqueror: Any) -> None:
    title = f"The Conquest of {planet.name}"
    body = (
        f"Annals of {planet.name}. The shields fell and the vaults were opened to {conqueror.name}. "
        f"The former governor ({old_owner}) is gone. "
        + _pick([
            "The people are told nothing will change. They know better.",
            "New banners hang in the plaza; the old ones burn in the square.",
            "The markets reopened the next day, as markets always do.",
        ])
    )
    record_planet(kernel, planet, title, body, ["war", "conquest"], alignment=conqueror.cosmic_alignment)


def annals_siege_survived(kernel: Any, planet: Any, siege: Dict[str, Any]) -> None:
    title = _pick([f"The Iron Bastion of {planet.name}", f"The Symphony of {planet.name}'s Walls",
                   f"{planet.name} Stands"])
    days = siege.get("last", 0) - siege.get("start", 0)
    attackers = ", ".join(siege.get("attackers", [])[:3]) or "raiders"
    body = (
        f"Annals of {planet.name}. For {days} cycles the world was besieged by {attackers}: "
        f"{siege.get('assaults', 0)} orbital assaults, and the shields held. "
        + _pick([
            "Every child who lived through it can hum the alarm tone. They made it a song.",
            "The garrison was fed by the farmers' own rations; no one has forgotten it.",
            "They rebuilt the batteries higher, and painted the scorch marks gold.",
        ])
    )
    record_planet(kernel, planet, title, body, ["siege", "survival"])


# =============================================================================
# Locals: field notes and native annals
# =============================================================================
def _native_desc(natives: Dict[str, Any]) -> str:
    stage = NATIVE_STAGES[min(natives["stage"], len(NATIVE_STAGES) - 1)]
    return f"the {natives['name']} ({natives['species']}, {stage}, sapience {natives['sapience']:.1f})"


def field_notes(kernel: Any, captain: Any, planet: Any, natives: Dict[str, Any], observation: str) -> None:
    title = _pick([f"Field Notes: The {natives['name']}", f"Observing {planet.name}",
                   f"Among the {natives['name']}"])
    body = (
        f"{_opener(captain, kernel)}From high orbit over {planet.name} we watched {_native_desc(natives)}. "
        f"{observation} "
        + _pick([
            "They do not know we are here. The Directive says they must not, yet.",
            "One of their astronomers keeps pointing a lens at our quarter of the sky.",
            "I have logged their songs for the Library. Someday they may want them back.",
        ])
    )
    _record_captain(kernel, captain, "FIELD_NOTES", title, body, ["natives", "observation"])


def native_event(kernel: Any, planet: Any, natives: Dict[str, Any], title: str, text: str, tags: List[str]) -> None:
    body = f"Annals of the {natives['name']} of {planet.name}. {text}"
    record_planet(kernel, planet, title, body, ["natives"] + tags, alignment=natives.get("alignment", 0.0))


def first_contact(kernel: Any, captain: Any, planet: Any, natives: Dict[str, Any], lawful: bool) -> None:
    title = f"First Contact: The {natives['name']}"
    their = _pick([
        "Their elders met us with gifts of carved stone and a question none of us could answer.",
        "Their soldiers raised weapons; their children raised hands.",
        "They had a word for us before we landed. It translates, roughly, as 'late'.",
    ])
    law = "" if lawful else " No authority sanctioned this landing. It will be remembered."
    body = f"{_opener(captain, kernel)}We have made contact with {_native_desc(natives)} on {planet.name}. {their}{law}"
    _record_captain(kernel, captain, "FIELD_NOTES", title, body, ["natives", "contact"] + ([] if lawful else ["violation"]))


# =============================================================================
# Great powers
# =============================================================================
def decree(kernel: Any, faction: Any, title: str, text: str, tags: List[str], sector_id: Optional[int] = None) -> None:
    chron = _chron(kernel)
    if chron is None:
        return
    if faction.id == "IMPERIUM":
        head = "BY DECREE OF THE THRONE. "
    elif faction.id == "ZEALOT":
        head = "HEAR THE CHOIR OF THE PYRE. "
    else:
        head = f"{faction.name.upper()} ANNOUNCES. "
    chron.record(kernel, "FACTION_DECREE", faction.id, faction.name, title, head + text,
                 sector_id=sector_id if sector_id is not None else faction.capital_sector,
                 tags=tags, alignment=faction.alignment)


# =============================================================================
# Galactic history (one entry per era)
# =============================================================================
def galactic_history(kernel: Any) -> None:
    chron = _chron(kernel)
    if chron is None:
        return
    from xylarium.kernel.alignment import census, band
    cycle = kernel.cycle_count
    since = chron.last_era_cycle
    recent = [e for e in chron.entries if e["cycle"] > since]
    by_kind = Counter(e["kind"] for e in recent)
    tags = Counter(t for e in recent for t in e.get("tags", []))
    c = census(kernel)
    natives = [p.natives for s in kernel.sectors.values() for p in s.planets if p.natives]
    stage_mean = sum(n["stage"] for n in natives) / len(natives) if natives else 0
    powers = getattr(kernel, "factions", None)
    power_lines = []
    if powers is not None:
        for f in powers.factions.values():
            if f.kind in ("IMPERIUM", "ZEALOT"):
                power_lines.append(f"{f.name} holds {len(f.worlds)} worlds" +
                                   (f" (dogma {f.dogma:.2f})" if f.kind == "ZEALOT" else ""))
    era_no = cycle // 2500 + 1
    title = f"The History of the Galaxy, Age {era_no}"
    body = (
        f"GALACTIC HISTORY, cycles {since}-{cycle}. {c['n']} captains sail the lanes: {c['light']} walk in the Light, "
        f"{c['neutral']} keep to the grey middle, {c['dark']} have turned to the Dark (mean {c['mean']:+.2f}, "
        f"'{band(c['mean'])}'). The Library received {len(recent)} new records "
        f"({by_kind.get('CAPTAINS_LOG', 0)} captains' logs, {by_kind.get('PLANETARY_ANNALS', 0)} annals, "
        f"{by_kind.get('FIELD_NOTES', 0)} field notes, {by_kind.get('FACTION_DECREE', 0)} decrees). "
        f"{len(natives)} non-spacefaring peoples remain, their average age the {NATIVE_STAGES[int(round(stage_mean))]}. "
        + (" ".join(power_lines) + ". " if power_lines else "")
        + (f"The age was marked by {', '.join(t for t, _ in tags.most_common(3))}." if tags else "")
    )
    chron.record(kernel, "GALACTIC_HISTORY", None, "The Galaxy", title, body, tags=["history", "era"],
                 alignment=c["mean"], author="Galactic Library")
    chron.last_era_cycle = cycle


# =============================================================================
# Trigger bookkeeping on captains
# =============================================================================
def note_jump(kernel: Any, captain: Any) -> None:
    from xylarium.config import CHRONICLE_JUMP_MILESTONES
    stats = captain.chronicle_stats
    stats["jumps"] = stats.get("jumps", 0) + 1
    if stats["jumps"] in CHRONICLE_JUMP_MILESTONES:
        log_long_haul(kernel, captain, stats["jumps"])


def note_freight(kernel: Any, captain: Any) -> None:
    from xylarium.config import CHRONICLE_FREIGHT_MILESTONES
    n = getattr(captain, "freight_deliveries_completed", 0)
    if n in CHRONICLE_FREIGHT_MILESTONES and captain.chronicle_stats.get("freight_logged", 0) < n:
        captain.chronicle_stats["freight_logged"] = n
        log_freight(kernel, captain, n)
