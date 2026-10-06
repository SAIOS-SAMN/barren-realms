"""
The progenitors' seat: write a universe's laws, begin it, and watch - never reach into it.

A progenitor chooses the four laws (fundamental.py: alpha, beta, alpha_G, the nuclear yield - as ratios to ours),
whether space can be folded at all (ftl), the kind of Big Bang (measured, or lush) and the pace the galaxy turns
at between minds, and begins. From then on it watches: the years run, the peoples rise and fall, and their lore is
written. It may set steward intelligences beside peoples (steward_ai.py) - voices in their minds, heeded as far as
they serve - or withdraw them. It does not act on any people: progenitors set laws; stewards counsel; peoples
choose.
"""

from typing import Any, Dict, List, Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_red

WATCHED = ("EMERGENCE", "ERA", "ASCENT", "FTL_CROSSED", "CAPABILITY", "FALL", "GALACTIC_WAR", "DOMINION",
           "FEDERATION", "KINSHIP", "SCHISM", "LIFE_ENDED", "ICE_AGE", "STAR_DEATH", "SETTLEMENT", "SEEDING",
           "CONTACT", "FIRST_SIGNAL", "WORLD_STRIPPED", "WORLD_SHATTERED", "POSTURE")


def genesis_key(pace: str, kind: str, laws: Dict[str, float]) -> str:
    tag = ",".join(f"{k}={v:g}" for k, v in sorted(laws.items()) if (k == "ftl" and v != 1.0) or
                   (k != "ftl" and abs(v - 1.0) > 1e-12))
    return f"cosmic:{pace}:{kind}" + (f":{tag}" if tag else "")


def _peoples(kernel: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import annals, relations, steward, strategy
    out = []
    for who, worlds in sorted(relations._peoples(kernel).items()):
        home = max(worlds, key=lambda p: p.population)
        g = steward.of(kernel, who) or {}
        out.append({"people": who.split(":", 1)[-1], "worlds": len(worlds),
                    "population": sum(p.population for p in worlds), "stage": annals._stage(kernel, who, home),
                    "posture": strategy.of(kernel, who).get("posture") or "-",
                    "steward": g.get("steward") or "-", "aim": g.get("aim") or "-",
                    "heed": round(steward.heed(kernel, who), 2) if g else None, "holder": who})
    return out


def _show_galaxy(kernel: Any) -> None:
    from xylarium.kernel import cosmos, federation, tempo
    st = cosmos.stats(kernel)
    print(bold(c_cyan(f"=== {cosmos.deep_gyr(kernel):.4f} Gyr after the Big Bang - clock year "
                      f"{kernel.cycle_count // 100} ===")))
    print(f"  minds arisen {st['arisen']} of {st.get('ever', 0)} the galaxy will raise; "
          f"deep time runs {tempo.summary(kernel)['deep_years_per_year']:,.1f} years per clock year; "
          f"federations {len(federation.stats(kernel)['feds'])}")
    for r in _peoples(kernel):
        heed = "" if r["heed"] is None else f" heed {r['heed']}"
        print(f"  {c_gold(r['people']):<28} {r['stage']:<8} {r['posture']:<7} {r['worlds']:>4} worlds "
              f"{r['population']:>12,}   steward {r['steward']} ({r['aim']}){heed}")


def _watch(kernel: Any, years: int) -> None:
    from xylarium.kernel import history
    seen = int(history.stats(kernel).get("next", 0))
    for _ in range(max(1, years) * 100):
        kernel.tick_simulation()
    for e in history.stats(kernel).get("recent", []):
        if int(str(e.get("id", "H-0")).split("-")[-1] or 0) < seen:
            continue
        if e.get("kind") in WATCHED:
            print(c_gray(f"  year {e.get('year', '?')}: ") + f"{e.get('title', '')}" +
                  c_gray(f" - {e.get('cause', '')}" if e.get("cause") else ""))


def run(seed: int, save: Optional[Any] = None) -> Optional[Any]:
    """The progenitors' loop. Returns the kernel it began (or None)."""
    from xylarium.kernel import fundamental, steward, steward_ai
    from xylarium.kernel.engine import GameKernel
    laws: Dict[str, float] = {n: 1.0 for n in fundamental.NAMES}
    laws["ftl"] = 1.0
    pace, kind, kernel = "neighbourly", "measured", None
    print(bold(c_cyan("\n=== THE PROGENITORS' SEAT ===")))
    print(c_gray("Write the laws, begin the universe, and watch. You set laws; stewards counsel; peoples choose."))
    while True:
        if kernel is None:
            print(f"  laws (ratios to ours): {', '.join(f'{k}={v:g}' for k, v in laws.items())}; "
                  f"Big Bang {kind}; pace {pace}; seed {seed}")
            print("  " + "   ".join(f"{c_gold('[' + k + ']')} {t}" for k, t in (
                ("L", "Set a law (e.g. alpha=1.02, ftl=0)"), ("U", "Big Bang: measured / lush"),
                ("P", "Pace: lonely / neighbourly / teeming"), ("B", "Begin"), ("Q", "Leave"))))
        else:
            print("  " + "   ".join(f"{c_gold('[' + k + ']')} {t}" for k, t in (
                ("W", "Watch some years"), ("G", "The galaxy and its peoples"),
                ("H", "The chronicle, told in a people's own years"), ("O", "Open the universe to live play"),
                ("S", "Steward intelligences for all"),
                ("E", "Enlist a steward intelligence for one people"), ("D", "Dismiss a people's steward"),
                ("Q", "Save and leave"))))
        try:
            cmd = input(c_gold("Progenitor > ")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            cmd = "Q"
        if cmd == "Q":
            if kernel is not None and save:
                save(kernel)
            return kernel
        if kernel is None:
            if cmd == "L":
                got = fundamental.parse(input(c_gold("law=ratio > ")).strip())
                laws.update(got)
                print(c_green(f"  {got or 'nothing changed'}"))
            elif cmd == "U":
                raw = input(c_gold("measured / lush > ")).strip().lower()
                kind = raw if raw in ("measured", "lush") else kind
            elif cmd == "P":
                raw = input(c_gold("lonely / neighbourly / teeming > ")).strip().lower()
                pace = raw if raw in ("lonely", "neighbourly", "teeming") else pace
            elif cmd == "B":
                key = genesis_key(pace, kind, laws)
                print(c_gray(f"  Beginning universe {seed} under {key} (its first minds are worked out once)..."))
                kernel = GameKernel(seed=seed, genesis=key)
                kernel.activate()
                _show_galaxy(kernel)
            continue
        if cmd == "W":
            raw = input(c_gold("Years [10] > ")).strip()
            _watch(kernel, int(raw) if raw.isdigit() else 10)
            _show_galaxy(kernel)
        elif cmd == "G":
            _show_galaxy(kernel)
        elif cmd == "O":
            from xylarium.kernel import cosmos
            if cosmos.live(kernel):
                print(c_gray("  It is open: one clock, at the captains' scale."))
            else:
                rec = cosmos.open_universe(kernel, "the progenitors")
                print(c_green(f"  The deep era ends at {rec['epoch']:.4f} Gyr. From now on a clock year is a "
                              f"standard year, for every seat."))
        elif cmd == "H":
            from xylarium.kernel import history
            rows = _peoples(kernel)
            print(f"  [0] the galaxy (in turns of the galaxy)")
            for i, r in enumerate(rows, 1):
                print(f"  [{i}] the {r['people']}")
            raw = input(c_gold("Told to > ")).strip()
            reader = rows[int(raw) - 1]["holder"] if raw.isdigit() and 1 <= int(raw) <= len(rows) else None
            for line in history.chronicle(kernel, reader):
                print("  " + line)
        elif cmd == "S":
            steward_ai.enlist_all(kernel)
            print(c_green("  Every people, as it arises, will have a steward intelligence beside it."))
        elif cmd in ("E", "D"):
            rows = _peoples(kernel)
            for i, r in enumerate(rows, 1):
                print(f"  [{i}] {r['people']}")
            raw = input(c_gold("People > ")).strip()
            if raw.isdigit() and 1 <= int(raw) <= len(rows):
                who = rows[int(raw) - 1]["holder"]
                if cmd == "E":
                    steward_ai.enlist(kernel, who)
                    print(c_green(f"  A steward intelligence speaks among the {rows[int(raw) - 1]['people']}."))
                else:
                    steward.detach(kernel, who)
                    print(c_green(f"  The {rows[int(raw) - 1]['people']} choose by their own lights."))
        else:
            print(c_red("  Choose one of the letters above."))
