"""
The Steward's seat: choose a polity of the settled galaxy, say how it is governed, and rule it (kernel/roles.py).
Ruling happens in the ship's console: your worlds answer to you - their shields, fighters and citadels, their
birth policy, their wars and their new settlements.
"""

from typing import Any, Dict, Optional, Tuple

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green
from xylarium.kernel import roles

LEANINGS = (("temple", "how much common effort goes to rites rather than inquiry"),
            ("levy", "the share of adults under arms (they guard; they do not work)"),
            ("openness", "how much it takes from strangers: goods, words, ideas"),
            ("commerce", "how free its markets are to make trades of their own"))


def _ask(prompt: str, default: str = "") -> str:
    try:
        return input(c_gold(prompt)).strip() or default
    except (KeyboardInterrupt, EOFError):
        return default


def choose_polity(kernel: Any) -> Optional[Dict[str, Any]]:
    ps = roles.polities(kernel)[:12]
    if not ps:
        return None
    print(bold(c_cyan("\n=== WHICH POLITY WILL YOU RULE? ===")))
    print(c_gray("Independent peoples of this galaxy. The great powers rule themselves."))
    for i, p in enumerate(ps, 1):
        print(f"  {c_gold(f'[{i:>2}]')} {p['name']:<24} {p['worlds']} world(s)  {p['population']:>9,} people  "
              f"capital {p['capital_name']} (sector {p['sector']})  citadel {p['citadel']}")
    raw = _ask("Polity [1] > ", "1")
    return ps[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(ps) else ps[0]


def choose_rule() -> str:
    print(bold(c_cyan("\n=== HOW IS IT GOVERNED? ===")))
    for i, f in enumerate(roles.RULE_FORMS, 1):
        print(f"  {c_gold(f'[{i}]')} {bold(f['name'])}  {c_gray(f['blurb'])}")
    raw = _ask("Rule [2] > ", "2")
    return roles.RULE_FORMS[int(raw) - 1]["key"] if raw.isdigit() and 1 <= int(raw) <= len(roles.RULE_FORMS) \
        else "council"


def choose_leanings() -> Dict[str, float]:
    print(bold(c_cyan("\n=== ITS LEANINGS (0 to 1; Enter keeps what its council chose) ===")))
    out: Dict[str, float] = {}
    for key, what in LEANINGS:
        raw = _ask(f"{key:<9} {what} > ", "")
        try:
            out[key] = max(0.0, min(1.0, float(raw)))
        except ValueError:
            pass
    return out


def choose_natal() -> Optional[str]:
    from xylarium.config import NATAL_POLICIES
    opts = [(k, v) for k, v in NATAL_POLICIES.items() if not v.get("zealot_only")]
    print(bold(c_cyan("\n=== BIRTH POLICY ===")))
    print(f"  {c_gold('[0]')} None (its people decide)")
    for i, (k, v) in enumerate(opts, 1):
        print(f"  {c_gold(f'[{i}]')} {v['name']}")
    raw = _ask("Policy [0] > ", "0")
    return opts[int(raw) - 1][0] if raw.isdigit() and 1 <= int(raw) <= len(opts) else None


def begin(seed: int, name: str, player_id: str = "player_1") -> Tuple[Optional[Any], str]:
    """A settled universe; the player takes the ruler's seat of a polity it chooses. Returns (kernel, player_id)."""
    from xylarium.kernel.engine import GameKernel
    print(c_gray(f"Generating a settled galaxy (seed {seed})..."))
    kernel = GameKernel(seed=seed)
    pol = choose_polity(kernel)
    if pol is None:
        print("This galaxy has no independent polity to rule.")
        return None, player_id
    rule = choose_rule()
    leanings = choose_leanings()
    natal = choose_natal()
    title = _ask(f"Your name, ruler [{name}] > ", name)
    seat = roles.seat_ruler(kernel, player_id, title, pol["holder"], rule, leanings, natal)
    print(c_green(f"\nYou rule the {seat['polity']} as {seat['rule']}: {seat['worlds']} world(s), capital "
                  f"{seat['capital']} (sector {seat['sector']})."))
    print(c_gray("Your worlds answer to you: from the Planet menu raise shields, recruit fighters and upgrade "
                 "citadels; claim new worlds to settle them; attack your rivals' worlds; set birth policy. Your "
                 "councils no longer build for you."))
    return kernel, player_id
