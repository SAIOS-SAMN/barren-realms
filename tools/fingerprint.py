"""
Layout-independent fingerprint of a harness run: what the game *is* after N cycles, not how it is stored.

Used to prove a refactor changed nothing (docs/STANDARDS.md, definition of done):

    python3 tools/fingerprint.py 7 1500 before_7.json      # prints a sha256; the JSON is kept for diffing
    ... refactor ...
    python3 tools/fingerprint.py 7 1500 after_7.json       # the same sha256, or diff the two JSON files
"""
import hashlib, json, random, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
import simulate_playtest as sp
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel import matter, realms, law, shipdesign, tourism

seed, cycles, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
random.seed(seed); k = GameKernel(seed=seed); rng = random.Random(seed)
bots = sp.make_players(k, rng); st = sp.RunStats()
real = k.tick_simulation; k.tick_simulation = lambda: None
for _ in range(cycles):
    for b in bots:
        b.act(k, st)
    real()

def r(x):
    return round(x, 6) if isinstance(x, float) else x

fp = {
    "money": {c: b for c, b in sorted(money_supply(k).items())},
    "matter": dict(sorted(matter.totals(k).items())),
    "matter_net": dict(sorted(k.matter.net().items())),
    "captains": {c.id: [c.credits, c.sector_id, c.ship.ship_type, c.ship.fuel, getattr(c.ship, "drive", "H"),
                        c.ship.cargo.ore, c.ship.cargo.organics, c.ship.cargo.equipment, sorted(c.ship.cargo.elements.items()),
                        r(c.cosmic_alignment), sorted(c.fx_wallet.items()), c.rank_tier]
                 for c in sorted(k.captains.values(), key=lambda c: c.id)},
    "planets": {p.id: [p.owner_id, p.population, p.treasury, p.household_purse, p.ore_silo, p.organics_silo, p.morale,
                       p.citadel_level, p.habitats, sorted(p.element_reserves.items()), p.growth_policy, p.faction_id,
                       json.dumps(p.society, sort_keys=True, default=str)]
                for s in sorted(k.sectors.values(), key=lambda s: s.id) for p in s.planets},
    "ports": {s.id: [s.port.treasury, sorted(s.port.stock.items()), json.dumps(s.port.leisure, sort_keys=True, default=str)]
              for s in sorted(k.sectors.values(), key=lambda s: s.id) if s.port},
    "sectors": {s.id: [sorted(s.warps), getattr(s, "gas", 0)] for s in sorted(k.sectors.values(), key=lambda s: s.id)},
    "chain_tip": k.settlement.blocks[-1]["hash"] if k.settlement.blocks else "",
    "chronicle": k.chronicle.next_id,
    "realms": json.dumps(realms.realms(k), sort_keys=True, default=str),
    "claims": sorted(realms.claims(k).items()),
    "docket": json.dumps(law.docket(k).get("stats", {}), sort_keys=True, default=str),
    "fx": {c: r(v) for c, v in sorted(k.fx_market.pools.items())} if hasattr(k.fx_market, "pools") else {},
    "designs": sorted(shipdesign.designs(k).keys()),
    "charters": len(tourism.charters(k)),
}
blob = json.dumps(fp, sort_keys=True, default=str)
open(out, "w").write(blob)
print(hashlib.sha256(blob.encode()).hexdigest())
