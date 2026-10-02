"""
The steward's console: a people on its homeworld, before it has ships (ages.py).

Seasons are the turn. Each screen shows the people's world, its way of life, what it knows and what has first
happened in the galaxy; the steward decides what the council would (inquiry, growth, farming, a state, works) or
lets the clock run until something happens to its people. When its yards are raised, the steward may become the
people's first captain - and the TradeWars console opens.
"""

from typing import Any, Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_red
from xylarium.kernel import ages


DOMAINS = ("energy", "materials", "biology", "information")


def _screen(kernel: Any, pid: str) -> None:
    s = ages.status(kernel, pid)
    print()
    print(bold(c_cyan(f"=== {s['people']} of {s['world']} - year {s['year']} ===")))
    print(f"  {c_gold('People')} {s['population']:,} of {s['room']:,} the land feeds    "
          f"{c_gold('Way')} {s['way']}    {c_gold('Morale')} {s['morale']}")
    if s["way"] != "state":
        print(f"  {c_gold('Crops')} {s['crop_share']:.0%} of their land's potential    "
              f"{c_gold('Surplus')} {s['surplus']:.0%}    {c_gold('Domestication known')} {s['domestication']:.0%}")
    else:
        print(f"  {c_gold('Citadel')} {s['citadel']}    {c_gold('Treasury')} {s['treasury']:,}    "
              f"{c_gold('Yards')} {'raised' if s['yards'] else 'none'}")
    g, st = s["gauges"], s["stress"]
    print(f"  {c_gold('Gauges')} temple {g['temple']:.0%}  levy {g['levy']:.0%}  openness {g['openness']:.0%}  "
          f"commerce {g['commerce']:.0%}    {c_gold('Creed')} {s['dogma']:.0%}    {c_gold('Trades')} {s['trades']}")
    rising = st.get("rising", 0.0)
    print(f"  {c_gold('Stress')} would rise {rising:.0%} vs {g['levy']:.0%} under arms"
          f"{c_red('  - unrest!') if rising > g['levy'] else ''}    (hunger {st.get('immiseration', 0):.0%}, "
          f"unheld order {st.get('illegitimacy', 0):.0%}, distress {st.get('distress', 0):.0%})")
    if s["myths"]:
        m = s["myths"][-1]
        print(c_gray(f"  They tell how {m['text']} (year {m['year']})"))
    know = ", ".join(f"{d} {v}" for d, v in sorted(s["knowledge"].items()) if v) or "nothing written down"
    print(f"  {c_gold('Knowledge')} {know}    {c_gold('Inquiry')} {s['focus'] or 'as needs call'}    "
          f"{c_gold('Growth')} {s['policy']}")
    firsts = s["firsts"]
    if firsts:
        recent = sorted(firsts.items(), key=lambda kv: kv[1]["cycle"])[-3:]
        print(c_gray("  Galaxy: " + "; ".join(f"{k.replace('_', ' ')} y{v['year']:.0f}" for k, v in recent)))


def _menu(kernel: Any, pid: str) -> None:
    s = ages.status(kernel, pid)
    opts = [("Z", "Wake me when something happens"), ("A", "Advance one season"),
            ("R", "Point their inquiry"), ("P", "Set their growth (expand / steady)"),
            ("G", "Set a gauge (temple / levy / openness / commerce)"), ("M", "Their myths")]
    if s["way"] == "forage":
        opts.append(("F", "Take up farming"))
    if s["way"] == "farm":
        opts.append(("S", "Found a state"))
    if s["way"] == "state":
        opts.append(("W", "Weigh the council's works now"))
    if kernel.get_player(pid) is not None:
        opts.append(("C", "Return to your ship"))
    elif s["yards"]:
        opts.append(("C", "Take ship as your people's captain (the lanes open; HOMEWORLD brings you back)"))
    opts.append(("Q", "Save and quit"))
    print("  " + "   ".join(f"{c_gold('[' + k + ']')} {t}" for k, t in opts))


def run(kernel: Any, pid: str, name: str, save: Optional[Any] = None, aboard: bool = False) -> Optional[Any]:
    """The steward's loop. Returns the captain if the steward takes (or returns to) ship, else None (quit).
    Taking ship does not end the stewardship: the people stays the player's, and HOMEWORLD returns here."""
    while True:
        _screen(kernel, pid)
        _menu(kernel, pid)
        try:
            cmd = input(c_gold("Steward > ")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            cmd = "Q"
        if cmd == "Q":
            if aboard:
                return kernel.get_player(pid)
            if save:
                save()
            print(c_green("Your people will be here when you return."))
            return None
        if cmd == "Z":
            for line in ages.wake_when(kernel, pid):
                print("  " + line)
        elif cmd == "A":
            for _ in range(25):
                kernel.tick_simulation()
        elif cmd == "R":
            raw = input(c_gold(f"Inquiry ({' / '.join(DOMAINS)} / none) > ")).strip().lower()
            print("  " + ages.act(kernel, pid, "focus", raw if raw in DOMAINS else None))
        elif cmd == "P":
            raw = input(c_gold("Growth (expand / steady) > ")).strip().lower()
            print("  " + ages.act(kernel, pid, "policy", raw))
        elif cmd == "G":
            raw = input(c_gold("Gauge=value, e.g. temple=0.3 > ")).strip().lower()
            print("  " + ages.act(kernel, pid, "gauge", raw))
        elif cmd == "M":
            myths = ages.status(kernel, pid)["myths"]
            for m in myths or [{"year": "-", "text": "they have no stories yet"}]:
                print(c_gray(f"  year {m['year']}: they say that {m['text']}."))
        elif cmd == "F":
            print("  " + ages.act(kernel, pid, "farm"))
        elif cmd == "S":
            print("  " + ages.act(kernel, pid, "state"))
        elif cmd == "W":
            print("  " + ages.act(kernel, pid, "works"))
        elif cmd == "C":
            if kernel.get_player(pid) is not None:
                return kernel.get_player(pid)
            cap = ages.first_captain(kernel, pid, name)
            if cap is not None:
                print(c_green(f"You take ship from {ages.status(kernel, pid)['world']}. The lanes are yours to open."))
                return cap
            print(c_red("Your people have no yards yet."))
        else:
            print(c_gray("  Choose one of the letters above."))


def choose_age(seed: int = 0) -> str:
    print(bold(c_cyan("\n=== XYLARIUM: WHERE ON THE CLOCK WILL YOU STEP IN? ===")))
    print(c_gray("One universe, one clock: every age is this universe run to the moment its milestone first happens."))
    kept = ages.cached(seed)
    for i, a in enumerate(ages.AGES, 1):
        ready = c_green(" [kept]") if a["key"] in kept else ""
        print(f"  {c_gold(f'[{i}]')} {bold(a['name'])}{ready}  {c_gray(a['blurb'])}")
    print(c_gray("  Ages not yet kept for this seed are reached by running the clock (it can take a while; each is "
                 "kept for next time)."))
    try:
        raw = input(c_gold("Age [1] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    return ages.AGES[int(raw) - 1]["key"] if raw.isdigit() and 1 <= int(raw) <= len(ages.AGES) else "forager"


def choose_people(kernel: Any) -> Any:
    from xylarium.kernel import biosphere, ways
    worlds = ages.peoples(kernel)[:20]
    print(bold(c_cyan("\n=== WHICH PEOPLE WILL YOU STEWARD? ===")))
    print(c_gray("Nothing is balanced; everything is legible: their world's light, ground and room are their fortune."))
    for i, p in enumerate(worlds, 1):
        civ = p.civilization
        print(f"  {c_gold(f'[{i:>2}]')} {civ.name:<26} {biosphere.metabolism_of(kernel, p):<9} on {p.name:<16} "
              f"{p.planet_type.lower():<11} {p.population:>8,} people  room {biosphere.carrying_capacity(kernel, p):,}")
    try:
        raw = input(c_gold("People [1] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    return worlds[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(worlds) else worlds[0]


def progenitor(kernel: Any, pid: str) -> None:
    """Optionally reshape the chosen people at genesis (designer.py's axes, in full)."""
    from xylarium.kernel import genome
    try:
        raw = input(c_gold("Shape your people's genome before the first season? [y/N] > ")).strip().lower()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    if raw != "y":
        return
    print(c_gray("Log-offsets from their founding form (0 keeps it). light: the light they are tuned to (x e^v); "
                 "tolerance: wider tuning, lower peak; chemistry: fit to their ground; birth: natural increase; "
                 "temperature: deeper/slower (-) or quicker/noisier (+) minds; aptitude: how well they keep what "
                 "they learn."))
    asked = {}
    for axis in genome.AXES:
        try:
            v = input(c_gold(f"  {axis} [0] > ")).strip()
            asked[axis] = float(v) if v else 0.0
        except (ValueError, KeyboardInterrupt, EOFError):
            asked[axis] = 0.0
    got = ages.shape(kernel, pid, asked)
    print(c_green(f"Your people are shaped: {got}. Their world will select them from here."))
