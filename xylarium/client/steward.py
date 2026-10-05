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
    life = s.get("life") or {}
    if life.get("expectancy_years") is not None:
        age = life.get("age") or {}
        co = life["cohorts"]
        print(f"  {c_gold('Life')} {life['expectancy_years']:.0f} years expected, health {life['thr']:.0%}; "
              f"young {co['youth']:.0%} / prime {co['prime']:.0%} / old {co['elder']:.0%}; "
              f"{life['ancestors']:,} ancestors" + (f"; they {('lay their dead to rest' if life['practice'] == 'rest' else 'burn their dead for warmth' if life['practice'] == 'pyre' else 'return their dead to the ground')}" if life.get("practice") else ""))
        if age:
            print(c_gray(f"  Their age: {age['years']:,.0f} years, {age['local_years']:,.0f} of their own world's, "
                         f"{age['galactic_myr']:,.1f} Myr of the galaxy's"))
        if life.get("remembered"):
            print(c_gray("  They remember " + ", ".join(life["remembered"])))
    firsts = s["firsts"]
    if firsts:
        recent = sorted(firsts.items(), key=lambda kv: kv[1]["cycle"])[-3:]
        print(c_gray("  Galaxy: " + "; ".join(f"{k.replace('_', ' ')} y{v['year']:.0f}" for k, v in recent)))


def _menu(kernel: Any, pid: str, seat: Optional[str] = None) -> None:
    s = ages.status(kernel, pid)
    opts = [("Z", "Wake me when something happens"), ("A", "Advance one season"),
            ("R", "Counsel their inquiry"), ("P", "Counsel their growth (expand / steady)"),
            ("G", "Counsel a gauge (temple / levy / openness / commerce)"), ("M", "Their myths"),
            ("K", "Counsel (what your people's minds can see, and how they heed you)"),
            ("U", "Urge an aim (grow / deepen / secure / hold / reach)"), ("X", "Caution against a choice"),
            ("N", "Fall silent"), ("L", "Your progress")]
    if s.get("forecast"):
        opts.append(("E", f"Counsel the exodus (their sun: {s['forecast']['years_left']:,.0f} years left at the reckoning)"))
    if s["way"] == "forage":
        opts.append(("F", "Speak for farming"))
    if s["way"] == "farm":
        opts.append(("S", "Speak for a state"))
    if s["way"] == "state":
        opts.append(("W", "Speak for great works"))
    if seat == "progenitor":
        opts += [("T", "Look away: let an age pass (a thousand to a billion years)"),
                 ("B", "Seal what is appealed to you (fold space and time)"),
                 ("O", "Read the board (the watcher's and the progenitors' books)"),
                 ("S", "Send or recall your line's stewards; fold or yield in a war of the progenitors"),
                 ("Y", "Counsel seeding young worlds"), ("V", "Counsel uplifting younger minds"),
                 ("H", "Write into your chronicle")]
    if kernel.get_player(pid) is not None:
        opts.append(("C", "Return to your ship"))
    elif s["yards"]:
        opts.append(("C", "Take ship as your people's captain (the lanes open; HOMEWORLD brings you back)"))
    opts.append(("Q", "Save and quit"))
    print("  " + "   ".join(f"{c_gold('[' + k + ']')} {t}" for k, t in opts))


AGES = (("a thousand years", 1e3), ("ten thousand", 1e4), ("a hundred thousand", 1e5), ("a million", 1e6),
        ("ten million", 1e7), ("a hundred million", 1e8), ("a billion", 1e9))


def run(kernel: Any, pid: str, name: str, save: Optional[Any] = None, aboard: bool = False,
        seat: Optional[str] = None) -> Optional[Any]:
    """The steward's loop. Returns the captain if the steward takes (or returns to) ship, else None (quit).
    Taking ship does not end the stewardship: the people stays the player's, and HOMEWORLD returns here."""
    while True:
        _screen(kernel, pid)
        _menu(kernel, pid, seat)
        try:
            cmd = input(c_gold(("Progenitor" if seat == "progenitor" else "Steward") + " > ")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            cmd = "Q"
        if cmd == "Q":
            if aboard:
                return kernel.get_player(pid)
            if save:
                save()
            print(c_green("Your people will be here when you return."))
            return None
        if cmd == "L":
            from xylarium.kernel import roles
            print(roles.render_progress(roles.progress(kernel, pid)))
            continue
        if seat == "progenitor" and cmd in ("T", "Y", "V", "H", "B", "O", "S"):
            if cmd == "S":
                from xylarium.kernel import command, realmwars, spheres, stewardship, transit
                print(spheres.render(kernel))
                print(transit.render(kernel))
                held = command.line_of(kernel, pid)
                if held is None:
                    print(c_gray("  Your people has not yet raised its progenitors."))
                    continue
                mine = [k.split("@", 1)[1] for k in stewardship.stats(kernel).get("envoys", {}) if k.startswith(held[0] + "@")]
                print(f"  {held[1]['name']}: stewards in {', '.join(stewardship.realm_name(r) for r in mine) or 'no realm'}")
                wars = [w for w in realmwars.stats(kernel)["wars"].values()
                        if w["status"] == "open" and held[0] in w.get("lines", [])]
                for w in wars:
                    print(f"  Fold war {w['id']} over {stewardship.realm_name(w['against'])}"
                          f" (stands: {w.get('stands') or 'none yet'})")
                act = input(c_gold("[S]end / [R]ecall <realm>, [F]old / [Y]ield <war>, [H]andle <open|tolled|guarded|"
                                   "closed>, [G] forge <mouth> <system> > ")).strip().split()
                if len(act) == 3 and act[0].upper() == "G":
                    res = command.forge(kernel, pid, int(act[1]), int(act[2])) if act[1].isdigit() and act[2].isdigit() \
                        else {"ok": False, "why": "forge <mouth sector> <target sector>"}
                    print("  " + ("Done." if res["ok"] else res["why"]))
                elif len(act) == 2 and act[0].upper() == "H":
                    res = command.handle(kernel, pid, act[1].lower())
                    print("  " + ("Done." if res["ok"] else res["why"]))
                elif len(act) == 2:
                    verb = {"S": "send", "R": "recall", "F": "fold", "Y": "fold"}.get(act[0].upper())
                    kw = ({"war": act[1], "deed": "yield" if act[0].upper() == "Y" else "fold"}
                          if act[0].upper() in ("F", "Y") else {"realm": act[1]})
                    res = command.dispatch(kernel, pid, verb or "", **kw)
                    print("  " + ("Done." if res["ok"] else res["why"]))
            elif cmd == "O":
                from xylarium.kernel import board
                print(board.render(kernel))
            elif cmd == "B":
                from xylarium.kernel import stewardship
                ap = stewardship.appeals(kernel)
                for r in ap:
                    print(f"  {r['id']} {r['kind']}: {r['a'].split(':', 1)[-1]} / {r['b'].split(':', 1)[-1]} "
                          f"(from {stewardship.realm_name(r['realm'])})")
                if not ap:
                    print(c_gray("  Nothing is appealed to you."))
                    continue
                rid = input(c_gold("Seal which ruling (id) > ")).strip()
                res = stewardship.seal(kernel, pid, rid)
                print("  " + ("Sealed: it stands for good." if res["ok"] else res["why"]))
            elif cmd == "T":
                print("  " + "   ".join(f"{c_gold(f'[{i}]')} {n}" for i, (n, _y) in enumerate(AGES, 1)))
                raw = input(c_gold("How long [3] > ")).strip() or "3"
                if raw.isdigit() and 1 <= int(raw) <= len(AGES):
                    print(c_gray("  You look away..."))
                    for line in ages.sleep(kernel, pid, AGES[int(raw) - 1][1]):
                        print("  " + line)
            elif cmd == "Y":
                print("  " + ages.act(kernel, pid, "seed"))
            elif cmd == "V":
                print("  " + ages.act(kernel, pid, "uplift"))
            else:
                from xylarium.kernel import progenitor as chronicle
                title = input(c_gold("Title > ")).strip()
                text = input(c_gold("Entry > ")).strip()
                if title:
                    e = chronicle.write(kernel, name, title, text, planet=ages.homeworld(kernel, pid))
                    print(c_green(f"  Written: entry {e['n']}, year {e['year']:,}."))
            continue
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
        elif cmd == "E":
            print("  " + ages.act(kernel, pid, "exodus"))
        elif cmd == "K":
            for line in ages.act(kernel, pid, "counsel").split("\n"):
                print("  " + line)
        elif cmd == "M":
            myths = ages.status(kernel, pid)["myths"]
            for m in myths or [{"year": "-", "text": "they have no stories yet"}]:
                print(c_gray(f"  year {m['year']}: they say that {m['text']}."))
        elif cmd == "U":
            raw = input(c_gold("Aim (grow / deepen / secure / hold / reach) > ")).strip().lower()
            print("  " + ages.act(kernel, pid, "urge", raw))
        elif cmd == "X":
            raw = input(c_gold("Caution against (e.g. expand, raise_citadel, exodus) > ")).strip()
            print("  " + ages.act(kernel, pid, "caution", raw))
        elif cmd == "N":
            print("  " + ages.act(kernel, pid, "withdraw"))
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
    kept = {pace: ages.cached(seed, pace=pace) for pace in ("lonely", "neighbourly", "teeming")}
    for i, a in enumerate(ages.AGES, 1):
        paces = [pace for pace, keys in kept.items() if a["key"] in keys]
        ready = c_green(f" [kept: {', '.join(paces)}]") if paces else ""
        print(f"  {c_gold(f'[{i}]')} {bold(a['name'])}{ready}  {c_gray(a['blurb'])}")
    print(c_gray("  Ages not yet kept for this seed are reached by running the clock (it can take a while; each is "
                 "kept for next time)."))
    try:
        raw = input(c_gold("Age [1] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    return ages.AGES[int(raw) - 1]["key"] if raw.isdigit() and 1 <= int(raw) <= len(ages.AGES) else "forager"


def choose_pace() -> str:
    print(bold(c_cyan("\n=== HOW CROWDED IS THIS COSMOS? ===")))
    print(c_gray("A law of the universe, chosen once: how much deep time - the evolution of life, the turning of the "
                 "galaxy, the lives of stars - passes for each year of history."))
    opts = [("lonely", "0.1 Myr a year: your people may reach the stars long before another mind arises"),
            ("neighbourly", "1 Myr a year: neighbours arise while you build (the default)"),
            ("teeming", "10 Myr a year: minds arise within lifetimes of each other; the galaxy visibly turns, "
                        "and stars die within a reign")]
    for i, (k, t) in enumerate(opts, 1):
        print(f"  {c_gold(f'[{i}]')} {bold(k.title())}  {c_gray(t)}")
    try:
        raw = input(c_gold("Pace [2] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    return opts[int(raw) - 1][0] if raw.isdigit() and 1 <= int(raw) <= 3 else "neighbourly"


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
