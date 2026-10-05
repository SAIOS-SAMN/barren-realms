"""
The opening of a new universe: which seat will you take? (xylarium/kernel/roles.py holds the seats.)
"""

from typing import Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray
from xylarium.kernel import roles

EARLIER = "earlier"             # the older entry: guide a young people as counsel, from an earlier age (ages.py)


def choose_role() -> str:
    print(bold(c_cyan("\n=== XYLARIUM: WHICH SEAT WILL YOU TAKE? ===")))
    print(c_gray("One universe, one set of laws. Your seat decides where you stand in it."))
    for i, r in enumerate(roles.ROLES, 1):
        print(f"  {c_gold(f'[{i}]')} {bold(r['name'])}")
        print(f"      {c_gray(r['blurb'])}")
    print(f"  {c_gold(f'[{len(roles.ROLES) + 1}]')} {bold('Counsel')}")
    print(f"      {c_gray('Guide a young people as one voice in its council, from an earlier age of the clock.')}")
    try:
        raw = input(c_gold("Seat [3] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    if raw.isdigit() and 1 <= int(raw) <= len(roles.ROLES):
        return roles.ROLES[int(raw) - 1]["key"]
    if raw == str(len(roles.ROLES) + 1):
        return EARLIER
    return "captain"


def choose_office() -> str:
    """Which office below the sovereign - a specialization of its work, played from a ship."""
    print(bold(c_cyan("\n=== WHICH OFFICE WILL YOU HOLD? ===")))
    for i, o in enumerate(roles.OFFICES, 1):
        print(f"  {c_gold(f'[{i}]')} {bold(o['name'])} ({o['tier']})  {c_gray(o['blurb'])}")
        print(f"      {c_gray('commands: ' + ', '.join(o['levers']))}")
    try:
        raw = input(c_gold("Office [1] > ")).strip()
    except (KeyboardInterrupt, EOFError):
        raw = ""
    return roles.OFFICES[int(raw) - 1]["key"] if raw.isdigit() and 1 <= int(raw) <= len(roles.OFFICES) else "trader"


def announce_tradewards(kernel, player_id: str) -> Optional[str]:
    tw = roles.tradewards(kernel)
    if not tw:
        return None
    line = (f"You berth at Tradewards: {tw['port']} (sector {tw['sector']}), with {tw['docks']} docks within "
            f"{roles.TRADEWARDS_REACH} jumps.")
    print(c_gray(line))
    return line
