"""
The Steward's seat (T2): keep a realm - a quadrant of the 3-sphere (kernel/stewardship.py) - for no people of your
own. Read its peoples at the level of history, hear its sovereigns' disputes, rule between them (your rulings bind
them), and send what reaches beyond your realm up to the progenitors.
"""

from typing import Any, Callable, Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_red
from xylarium.kernel import stewardship


def _ask(prompt: str, default: str = "") -> str:
    try:
        return input(c_gold(prompt)).strip() or default
    except (KeyboardInterrupt, EOFError):
        return default


def choose_realm(kernel: Any) -> str:
    print(bold(c_cyan("\n=== WHICH REALM WILL YOU KEEP? ===")))
    print(c_gray("The universe is cut into quadrants; this galaxy into its own four. A steward keeps one, for none of "
                 "its peoples."))
    keys = stewardship.realms(kernel)
    for i, r in enumerate(keys, 1):
        o = stewardship.overview(kernel, r)
        print(f"  {c_gold(f'[{i}]')} {o['name']:<22} {len(o['peoples'])} peoples, {len(o['disputes'])} disputes")
    raw = _ask("Realm [1] > ", "1")
    return keys[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(keys) else keys[0]


def run(kernel: Any, pid: str, save: Optional[Callable[[], Any]] = None) -> None:
    realm = stewardship.realm_held(kernel, pid)
    while True:
        o = stewardship.overview(kernel, realm)
        print(stewardship.render(o))
        print(c_gray("  [R]ule on a dispute | [C]laim a realm | [W]ithdraw a claim | [G]rant a house | [P]ass a season | "
                     "[Y]ear passes | [Q]uit (saves)"))
        cmd = _ask("Steward > ").upper()
        if cmd == "Q":
            if save:
                save()
            return
        if cmd == "P":
            for _ in range(25):
                kernel.tick_simulation()
        elif cmd == "Y":
            for _ in range(100):
                kernel.tick_simulation()
        elif cmd in ("C", "W", "G"):
            from xylarium.kernel import command
            if cmd == "C":
                others = [r for r in stewardship.realms(kernel) if r != realm]
                for i, r in enumerate(others, 1):
                    print(f"  {c_gold(f'[{i}]')} {stewardship.realm_name(r)}")
                raw = _ask("Claim which > ")
                if not raw.isdigit() or not 1 <= int(raw) <= len(others):
                    continue
                res = command.claim(kernel, pid, others[int(raw) - 1])
            elif cmd == "W":
                res = command.withdraw(kernel, pid)
            else:
                res = command.grant(kernel, pid, _ask("House (name) > "))
            print(c_green(f"  Done: {res}") if res["ok"] else c_red("  " + res["why"]))
        elif cmd == "R":
            if not o["disputes"]:
                print(c_gray("  No dispute is before you."))
                continue
            raw = _ask("Dispute number > ")
            if not raw.isdigit() or not 1 <= int(raw) <= len(o["disputes"]):
                continue
            d = o["disputes"][int(raw) - 1]
            kind = _ask(f"Ruling ({' / '.join(stewardship.RULINGS)}) > ", "ceasefire").lower()
            res = stewardship.rule(kernel, pid, kind, d["a"], d["b"])
            if not res["ok"]:
                print(c_red("  " + res["why"]))
            elif res["appealed"]:
                print(c_gray(f"  It reaches beyond your realm: {res['ruling']['id']} goes up to the progenitors."))
            else:
                print(c_green(f"  {res['ruling']['id']}: your {kind} binds them."))


def begin(seed: int, name: str, player_id: str = "player_1") -> Optional[Any]:
    from xylarium.kernel.engine import GameKernel
    print(c_gray(f"Generating a settled galaxy (seed {seed})..."))
    kernel = GameKernel(seed=seed)
    realm = choose_realm(kernel)
    title = _ask(f"Your name, steward [{name}] > ", name)
    seat = stewardship.seat_steward(kernel, player_id, title, realm)
    print(c_green(f"\nYou keep {seat['name']}: {seat['peoples']} peoples. Their sovereigns bend to your rulings."))
    return kernel
