"""
The Progenitor's seat: one of the first minds the universe raises, near its galaxy's core (kernel/roles.py).
You shape your ancient people at its dawn and carry it through deep time from its own console: its councils still
choose, but they heed you. As it reaches the stars, urge it to seed young worlds and uplift the minds that come after
it; write your chronicle into the annals as you go.
"""

from typing import Any, Callable, Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_red
from xylarium.kernel import roles


def _ask(prompt: str, default: str = "") -> str:
    try:
        return input(c_gold(prompt)).strip() or default
    except (KeyboardInterrupt, EOFError):
        return default


def choose_ancient(seed: int, pace: str) -> Optional[int]:
    from xylarium.kernel.engine import GameKernel
    k = GameKernel(seed=seed, genesis=f"cosmic:{pace}")
    k.activate()
    anc = roles.ancients(k)
    if not anc:
        print(c_red("This universe raises no minds."))
        return None
    print(bold(c_cyan("\n=== THE FIRST MINDS: WHICH ANCIENT WILL YOU BE? ===")))
    print(c_gray("The universe of this seed raises these first, all near its galaxy's core. When each wakes, what its "
                 "life is made of, and its ring of the galaxy counted out from the core."))
    for a in anc:
        n = a["index"] + 1
        print(f"  {c_gold(f'[{n}]')} wakes {a['dawn_gyr']:.3f} Gyr after the Big Bang   "
              f"{a['metabolism']:<10} ring {a['ring']}   star {a['star_mass']} suns")
    raw = _ask("Ancient [1] > ", "1")
    return int(raw) - 1 if raw.isdigit() and 1 <= int(raw) <= len(anc) else 0


def begin(seed: int, name: str, player_id: str = "player_1", save: Optional[Callable[[Any], Any]] = None) -> None:
    from xylarium.client import steward as steward_ui
    pace = steward_ui.choose_pace()
    pick = choose_ancient(seed, pace)
    if pick is None:
        return
    title = _ask(f"Your name, progenitor [{name}] > ", name)
    print(c_gray("Running the young universe to your people's dawn..."))
    kernel = roles.start_progenitor(seed, title, pick, pace,
                                    progress=lambda k: print(c_gray(f"  year {k.cycle_count // 100}"), flush=True))
    if kernel is None:
        print(c_red("Your people never woke: its world was taken, or its star died, before its dawn."))
        return
    print(c_green(f"Your people wakes in year {kernel.cycle_count // 100} of the clock."))
    steward_ui.progenitor(kernel, player_id)               # shape its genome at its dawn
    print(c_gray("Its councils choose; they heed you. [Y] urges seeding young worlds, [V] uplifting younger minds, "
                 "[H] writes your chronicle."))
    steward_ui.run(kernel, player_id, title, save=(lambda: save(kernel)) if save else None, seat="progenitor")
