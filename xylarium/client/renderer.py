"""
ASCII / ANSI rendering engine for Xylarium terminal client.
Displays persistent HUD, Sector scans, Port trading tables, and Colony operations.
"""

import re
from typing import Dict, Any, List
from xylarium.client.ansi import (
    c_cyan, c_gold, c_green, c_red, c_magenta, c_white, c_gray, c_blue, bold,
    BRIGHT_WHITE, BRIGHT_CYAN, BRIGHT_YELLOW, BRIGHT_GREEN, BRIGHT_RED,
    BRIGHT_MAGENTA, BRIGHT_BLACK, RESET, BOLD
)
from xylarium.config import (
    CITADEL_CONFIG,
    SHIP_CATALOG,
    COMMODITY_CONFIG,
    COMMODITY_CATEGORIES,
    SPECIALIZED_HULLS,
    VC_SYNDICATES,
    TAKEOVER_MIN_CREDIT,
    TAKEOVER_MIN_EXP,
    SHORT_MIN_CREDIT,
    CREDIT_TIER_THRESHOLDS,
)
from xylarium.kernel.elements import PeriodicTable


def _render_bar(curr: int, maximum: int, length: int = 10, fill_char: str = "█", empty_char: str = "░") -> str:
    """Renders a simple ASCII progress bar."""
    if maximum <= 0:
        return empty_char * length
    pct = max(0.0, min(1.0, curr / maximum))
    fill_len = int(round(pct * length))
    return f"[{fill_char * fill_len}{empty_char * (length - fill_len)}]"


def _alignment_badge(cosmos: Dict[str, Any]) -> str:
    value = cosmos.get("alignment", 0.0)
    band = cosmos.get("band", "Neutral")
    text = f"{band} {value:+.2f}"
    if value >= 0.15:
        return c_cyan(f"☀ {text}")
    if value <= -0.15:
        return c_red(f"☾ {text}")
    return c_gray(f"◐ {text}")


def _mode_badge(mode: str) -> str:
    fly = bold(c_cyan("[F]LY SHIP")) if mode == "FLY" else c_gray("[F]ly ship")
    emp = bold(c_gold("[E]MPIRE")) if mode == "EMPIRE" else c_gray("[E]mpire")
    return f"Mode: {fly} / {emp}"


def _wrap(text: str, width: int = 76, indent: str = "  ") -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(indent + cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(indent + cur)
    return lines


class TerminalRenderer:
    """Formats game state data into high-contrast BBS terminal layouts."""

    # ------------------------------------------------------------------ Empire Building Mode (BRE)
    @classmethod
    def render_empire_hub(cls, dash: Dict[str, Any]) -> str:
        pl = dash.get("player", {})
        lin = dash.get("lineage") or {}
        colonies = dash.get("colonies", [])
        fleets = dash.get("fleets", {})
        rule = c_blue("=" * 80)
        house = lin.get("house") or f"Captain {pl.get('name', '')}"
        seat = next((c["name"] for c in colonies if c.get("seat")), "no seat yet (found a colony)")
        out = [
            rule,
            bold(c_gold(f"{'SOVEREIGN COMMAND OF THE ' + house.upper():^80}")),
            rule,
            f"  Lineage: {c_white(house)} ({pl.get('species')}, {pl.get('clade', '').title()} clade) │ "
            f"Tier {pl.get('tier')} {pl.get('title', '')} │ {_alignment_badge({'alignment': pl.get('alignment', 0.0), 'band': pl.get('band', 'Neutral')})}",
            f"  Seat: {c_cyan(seat)} │ Worlds: {c_gold(str(len(colonies)))} │ Haulers: {c_gold(str(fleets.get('haulers', 0)))} │ "
            f"Net worth: {c_gold(format(dash.get('net_equity', 0), ',') + ' Cr')}"
            + (f" │ Clones in vats: {c_green(str(lin.get('clones')))}" if lin else ""),
            c_blue("-" * 80),
            f"  {c_gold('[1]')} COLONIES & PLANETARY WORLDS   {c_gray('worlds, tax yield, defenses, surface grids')}",
            f"  {c_gold('[2]')} FLEETS & SHIP ASSIGNMENTS     {c_gray('haulers by class, escorts, pickets, probes')}",
            f"  {c_gold('[3]')} TRADE ROUTES & ARBITRAGE      {c_gray('automated loops, toll gates, route optimizer')}",
            f"  {c_gold('[4]')} DIPLOMACY, POWERS & WARS      {c_gray('standing, doctrines, tithes, crusades, rivals')}",
            f"  {c_gold('[5]')} TREASURY & FINANCIAL VAULTS   {c_gray('credits, FX, VC notes, ISSE shares, credit')}",
            "",
            f"  {c_gold('[F]')} Return to the flight deck     {c_gold('[L]')} Library     {c_gold('[Q]')} Save & quit",
            rule,
        ]
        return "\n".join(out)

    @classmethod
    def render_empire_colonies(cls, dash: Dict[str, Any]) -> str:
        out = [bold(c_cyan("[1] COLONIES & PLANETARY WORLDS"))]
        cols = dash.get("colonies", [])
        if not cols:
            out.append(c_gray("  Your lineage holds no worlds yet. Fly to an uninhabited world suited to your biology and CLAIM it."))
            return "\n".join(out)
        out.append(c_gray(f"  {'#':>2} {'World':<22}{'Sector':>7}{'Pop':>9}{'Morale':>7}{'Cit':>4}{'Shields':>8}{'Vault':>16}"))
        for i, c in enumerate(cols, 1):
            flag = c_gold("★") if c["seat"] else " "
            siege = c_red(" SIEGE") if c["under_siege"] else ""
            out.append(f"  {i:>2}{flag}{c['name'][:21]:<22}{c['sector_id']:>7}{c['population']:>9,}{c['morale']:>7}"
                       f"{c['citadel']:>4}{c['shields']:>8,}{c['vault']:>11,} {c['currency']:<4}{siege}")
        out.append(c_gray("  ★ = seat of the lineage. Enter a number to open that world's console."))
        return "\n".join(out)

    @classmethod
    def render_empire_fleets(cls, dash: Dict[str, Any]) -> str:
        f = dash.get("fleets", {})
        out = [bold(c_cyan("[2] FLEETS & SHIP ASSIGNMENTS")),
               f"  Flagship: {c_white(f.get('flagship', '?'))} ({f.get('flagship_fighters', 0)} fighters) │ "
               f"toll gates {f.get('toll_gates', 0)} │ survey probes {f.get('probes', 0)}"]
        by_class = f.get("by_class", {})
        if by_class:
            out.append(c_gray(f"  {'Hull class':<20}{'Ships':>6}{'Holds':>8}{'Escorts':>9}{'Underway':>10}"))
            for hull, row in sorted(by_class.items()):
                out.append(f"  {hull.replace('_', ' ').title():<20}{row['count']:>6}{row['capacity']:>8}{row['escorts']:>9}{row['in_transit']:>10}")
        else:
            out.append(c_gray("  No automated haulers commissioned yet."))
        if f.get("sentries"):
            out.append("  Sentry pickets: " + ", ".join(f"Sector {sid:03d} x{n}" for sid, n in f["sentries"].items()))
        return "\n".join(out)

    @classmethod
    def render_empire_routes(cls, dash: Dict[str, Any]) -> str:
        out = [bold(c_cyan("[3] TRADE ROUTES & ARBITRAGE"))]
        routes = dash.get("routes", [])
        if routes:
            out.append(c_gray(f"  {'Hauler':<18}{'Route':<14}{'Out/Back':<24}{'Trips':>6}{'Profit':>11}  Status"))
            for r in routes[:12]:
                out.append(f"  {r['name'][:17]:<18}{r['origin']:03d} -> {r['dest']:03d}   {(r['outbound'] + '/' + r['return'])[:23]:<24}"
                           f"{r['trips']:>6}{r['profit']:>11,}  {r['status'].lower()}")
        else:
            out.append(c_gray("  No automated routes. Commission haulers and assign loops from the route desk."))
        for g in dash.get("toll_gates", []):
            out.append(f"  Toll gate {g['id']}: {g['a']:03d}<->{g['b']:03d}, fee {g['fee']:,} Cr, revenue {g['revenue']:,} Cr")
        return "\n".join(out)

    @classmethod
    def render_empire_diplomacy(cls, dash: Dict[str, Any]) -> str:
        d = dash.get("diplomacy", {})
        pl = dash.get("player", {})
        rep = d.get("reputation", {})
        out = [bold(c_cyan("[4] DIPLOMACY, POWERS & WARS")),
               f"  Standing: " + " │ ".join(f"{k} {v:.0f}" for k, v in rep.items())
               + (f" │ {c_red('WANTED ' + format(d['bounty'], ',') + ' Cr')}" if d.get("bounty") else "")
               + (f" │ {c_red('heresy ' + str(d['heresy']))}" if d.get("heresy") else ""),
               f"  Your alignment: {_alignment_badge({'alignment': pl.get('alignment', 0.0), 'band': pl.get('band', 'Neutral')})}"]
        doc = d.get("doctrine", {})
        if doc:
            out.append(f"  Doctrine here: {doc.get('name')} - Directive {doc.get('card')} ({doc.get('card_name')}), {doc.get('enforcement')}")
        if d.get("treaties"):
            out.append("  Treaties: " + ", ".join(f"{t['type'].replace('_', ' ').lower()} with {t['with']}" for t in d["treaties"]))
        for p in d.get("powers", []):
            if p["id"] == "IMPERIUM":
                out.append(f"  {c_gold(p['name'])}: {p['worlds']} worlds, fleet {p['fleet']}, tithe hauled {p['tithe_delivered']:,}, "
                           f"secessions {p['secessions']}, reclaimed {p['reclamations']}"
                           + (c_red(" │ YOU ARE EXCOMMUNICATE") if p["heretic"] else ""))
            else:
                out.append(f"  {c_red(p['name'])}: {p['worlds']} worlds, dogma {p['dogma']:.2f}, stability {p['stability']:.2f}, "
                           f"crusaders {p['crusaders']}, purges {p['purges']}"
                           + (c_red(" │ THEY NAME YOU HERETIC") if p["heretic"] else ""))
        rivals = dash.get("rivals", [])
        if rivals:
            out.append(c_gray("  Rival lines (NPC houses):"))
            for r in rivals[:8]:
                out.append(f"    {r['name'][:26]:<27}{r['clade'].title():<10} gen {r.get('generation', 1):<2} "
                           f"x{r.get('members', 1):<2} worlds {r['worlds']:<3}{r['net_equity']:>11,} Cr  "
                           f"{r.get('creed', '')}, {r['alignment']}")
        return "\n".join(out)

    @classmethod
    def render_empire_treasury(cls, dash: Dict[str, Any]) -> str:
        t = dash.get("treasury", {})
        out = [bold(c_cyan("[5] TREASURY & FINANCIAL VAULTS")),
               f"  Credits: {c_gold(format(t.get('credits', 0), ',') + ' SOL')}"
               + "".join(f" │ {amt:,} {cur}" for cur, amt in t.get("fx_wallet", {}).items() if amt)
               + f" (foreign ≈ {t.get('fx_wallet_sol', 0):,} SOL)",
               f"  Colony vaults ≈ {t.get('colony_vaults_sol', 0):,} SOL │ ISSE portfolio {t.get('portfolio_value', 0):,} Cr │ "
               f"net worth {dash.get('net_equity', 0):,} Cr",
               f"  Debt: {t.get('debt', 0):,} Cr │ VC: {t.get('vc_syndicate') or 'none'}"
               + (f" ({t.get('vc_debt', 0):,} Cr owed, royalty {t.get('vc_royalty_pct', 0):.0%})" if t.get("vc_syndicate") else "")
               + f" │ Credit rating {t.get('credit_rating', 0)} │ insured through cycle {t.get('insured_through', 0)}"]
        if t.get("clones") is not None:
            out.append(f"  Backup clones in the Sol vats: {t['clones']}")
        for p in t.get("portfolio", [])[:8]:
            out.append(f"    {p['ticker']:<6} {p['shares']:>6} sh @ {p['price']:>5} = {p['value']:>9,} Cr")
        return "\n".join(out)

    @classmethod
    def render_banking(cls, banking: Dict[str, Any], fx: Dict[str, Any], chain_tip: Dict[str, Any]) -> str:
        out = [bold(c_cyan("FEDERATIONS, CENTRAL BANKS & THE GALACTIC CLEARING UNION"))]
        out.append(c_gray(f"  {'Federation':<22}{'Central bank':<34}{'Rate/q':>7}{'Reserves':>13}{'Loans':>11}{'STAMP':>10}"))
        for b in banking.get("banks", []):
            out.append(f"  {b['federation'][:21]:<22}{b['bank'][:33]:<34}{b['policy_rate_q']:>7.2%}"
                       f"{b['reserves']:>10,} {b['currency']:<3}{b['loans_outstanding']:>10,} {b['stamp_position']:>+10,.0f}")
            out.append(c_gray(f"      governor {b['governor']} ({b['band']}) │ exchange: {b['exchange']} │ "
                              f"{b['borrowers']} borrower(s)"))
        out.append(f"  Galactic ISSE STAMP position {banking.get('isse_stamp_position', 0):+,.0f} │ union imbalance "
                   f"{banking.get('clearing_imbalance', 0):+.4f} (always nets to zero) │ deficit penalty "
                   f"{banking.get('deficit_slope', 0):.4f}")
        rates = fx.get("rates", {})
        if rates:
            out.append("  Federation exchanges: " + " │ ".join(f"{cur} {r:.3f}/SOL" for cur, r in sorted(rates.items())))
        cross = fx.get("cross", {})
        if cross:
            out.append("  Galactic ISSE cross pairs: " + " │ ".join(f"{k} {v:.3f}" for k, v in sorted(cross.items())))
        if chain_tip:
            out.append(c_gray(f"  Settlement chain: height {chain_tip.get('height')} at cycle {chain_tip.get('cycle')} │ "
                              f"tip {str(chain_tip.get('hash', ''))[:16]}… │ {chain_tip.get('receipt_count', 0)} receipts last quarter"))
        out += _wrap("STAMP is the clearing union's unit of account: claims between central banks and the exchanges, "
                     "never circulating money. A federation that keeps buying back its own currency runs a STAMP "
                     "deficit, and its central bank lends dearer.")
        return "\n".join(out)

    @classmethod
    def render_lineage_extinct(cls, lineage: Dict[str, Any]) -> str:
        rule = c_red("=" * 80)
        out = [rule, bold(c_red(f"{'LINEAGE EXTINCTION EVENT':^80}")), rule]
        out += _wrap(lineage.get("epitaph") or "", width=76)
        out += ["", c_gray("  The record is sealed in the Galactic Library and the Hall of Lineages."), rule]
        return "\n".join(out)

    @classmethod
    def render_alignment(cls, view: Dict[str, Any], record: Dict[str, Any]) -> str:
        cosmos = view.get("cosmos", {})
        value = cosmos.get("alignment", 0.0)
        pos = int(round((value + 1) / 2 * 40))
        axis = "".join("◆" if i == pos else ("─" if i != 20 else "┼") for i in range(41))
        out = [bold(c_cyan("COSMIC ALIGNMENT: THE LIGHT AND THE DARK")),
               f"  Dark {c_red('☾')} {axis} {c_cyan('☀')} Light",
               f"  Standing: {_alignment_badge(cosmos)}"]
        deeds = record.get("deeds", {})
        if deeds:
            out.append(c_gray("  Deeds on record: ") + ", ".join(f"{k.replace('_', ' ')} x{v}" for k, v in
                                                                  sorted(deeds.items(), key=lambda kv: -kv[1])[:8]))
        out += _wrap("Luminous captains trade on goodwill (cheaper purchases); Shadowed captains pay friction, "
                     "neglect their hulls and draw Federal warrants. A quarter without dark deeds drifts you "
                     "toward the Light. At +0.90 you are bound by an oath of Light; at -0.90, the Dark owns you.")
        return "\n".join(out)

    @classmethod
    def render_doctrine(cls, view: Dict[str, Any], authorities: List[Dict[str, Any]]) -> str:
        from xylarium.config import POLICY_CARDS
        cosmos = view.get("cosmos", {})
        hand = cosmos.get("doctrine", {})
        out = [bold(c_cyan("THE GALACTIC POLICY DECK: DOCTRINES ON NON-SPACEFARING LOCALS"))]
        if hand:
            out.append(f"  In force here: {c_gold(hand.get('name', '?'))} plays Directive {c_white(hand.get('card', '?'))} "
                       f"- {hand.get('card_name', '')}" + (f" (local custom of the {hand['local_custom']})"
                                                          if hand.get("local_custom") else ""))
            out.append(f"    \"{hand.get('motto', '')}\" │ contact needs sapience >= {hand.get('sapience_threshold', 0):.1f} "
                       f"│ uplift <= {hand.get('uplift_limit', 0)} stage │ enforcement: {hand.get('enforcement', 'NONE')}")
        out.append(c_gray("  The deck:"))
        for key, card in POLICY_CARDS.items():
            allows = ", ".join(sorted(a.replace("_if_ready", " (if ready)") for a in card["allows"]))
            out.append(f"    {c_white(key):<8} {card['name']}: {c_gray(allows)}")
        out.append(c_gray("  The authorities:"))
        for a in authorities:
            out.append(f"    {c_gold(a['name'])}: Directive {a['card']} │ sapience >= {a['sapience_threshold']:.1f} │ "
                       f"{a['enforcement']}" + (f" │ dogma {a['dogma']:.2f}" if a.get("dogma") else ""))
        return "\n".join(out)

    @classmethod
    def render_natives(cls, view: Dict[str, Any]) -> str:
        cosmos = view.get("cosmos", {})
        natives = cosmos.get("natives", [])
        hand = cosmos.get("doctrine", {})
        out = [bold(c_cyan("LOCALS: NON-SPACEFARING PEOPLES IN THIS SYSTEM"))]
        if not natives:
            out.append(c_gray("  No native society lives here."))
            return "\n".join(out)
        for n in natives:
            out.append(f"  {c_magenta(n['name'])} of {c_white(n['planet'])} ({n['species']}) │ {n['stage']} │ "
                       f"sapience {n['sapience']:.1f} │ ~{n['population']:,} │ {n['temperament']}")
            out.append(f"    awareness {n['awareness']:.2f} │ contamination {n['contamination']:.2f} │ "
                       f"stability {n['stability']:.2f}" + (" │ you have contact" if n["contacted"] else "")
                       + (f" │ protector: {n['protector']}" if n.get("protector") else "")
                       + (" │ converted to the Pyre" if n.get("converted") else ""))
        out.append(f"  Doctrine: {hand.get('name', '?')} - Directive {hand.get('card', '?')} ({hand.get('card_name', '')}), "
                   f"{hand.get('enforcement', 'NONE')}")
        return "\n".join(out)

    @classmethod
    def render_library(cls, entries: List[Dict[str, Any]], total: int, page: int, counts: Dict[str, int]) -> str:
        out = [bold(c_cyan(f"THE GALACTIC LIBRARY - {total} record(s), page {page + 1}"))]
        if counts:
            out.append(c_gray("  Holdings: " + ", ".join(f"{k.replace('_', ' ').lower()} {v}" for k, v in sorted(counts.items()))))
        for e in entries:
            out.append(f"  {c_gold(e['id'])} {c_gray('SD ' + e['stardate'])} [{e['kind'].replace('_', ' ').title()}] "
                       f"{c_white(e['title'][:44])} - {e['subject'][:22]}")
        if not entries:
            out.append(c_gray("  No records match."))
        return "\n".join(out)

    @classmethod
    def render_chronicle_entry(cls, e: Dict[str, Any]) -> str:
        out = [bold(c_cyan(e["title"])),
               c_gray(f"  {e['id']} │ {e['kind'].replace('_', ' ').title()} │ stardate {e['stardate']} (cycle {e['cycle']}) │ "
                      f"by {e.get('author') or e['subject']}" + (f" │ {e['band']}" if e.get("band") else ""))]
        out += _wrap(e["body"])
        if e.get("tags"):
            out.append(c_gray("  tags: " + ", ".join(e["tags"])))
        return "\n".join(out)

    @classmethod
    def render_hud(cls, view: Dict[str, Any]) -> str:
        """Renders the top persistent status HUD."""
        player = view.get("player", {})
        sector = view.get("sector", {})
        ship = player.get("ship", {})
        cargo = ship.get("cargo", {})

        s_id = sector.get("id", 1)
        sec_level = sector.get("security", "FEDERATION")

        # Security badge color
        if sec_level == "FEDERATION":
            sec_badge = c_green("● FEDERATION CORE")
        elif sec_level == "BORDERLAND":
            sec_badge = c_gold("▲ THE BORDERLANDS")
        else:
            sec_badge = c_red("☠ DEEP VOID (ANARCHY)")

        # Turns and credits
        turns = player.get("turns_left", 0)
        credits = player.get("credits", 0)
        ship_type = ship.get("ship_type", "Scout")
        score = player.get("score", 0)
        rank_title = player.get("rank_title") or view.get("rank_title") or "Captain"
        rank_tier = player.get("rank_tier") or view.get("rank_tier") or 1
        rank_badge = c_gold(f"[{rank_title} T{rank_tier}]")

        # Shields and cargo
        shields = ship.get("shields", 0)
        max_shields = ship.get("max_shields", 100)
        shield_bar = _render_bar(shields, max_shields, length=8)
        shield_str = c_cyan(f"{shield_bar} {shields}/{max_shields}")

        fighters = ship.get("fighters", 0)
        fighter_str = c_red(f"{fighters}")

        used_holds = cargo.get("used", 0)
        cap_holds = cargo.get("capacity", 30)
        ore = cargo.get("ore", 0)
        org = cargo.get("organics", 0)
        eq = cargo.get("equipment", 0)
        cb = cargo.get("cost_basis", {})
        ore_cb = f"@{int(round(cb.get('ore', 0)))}" if ore > 0 and cb.get("ore", 0) > 0 else ""
        org_cb = f"@{int(round(cb.get('organics', 0)))}" if org > 0 and cb.get("organics", 0) > 0 else ""
        eq_cb = f"@{int(round(cb.get('equipment', 0)))}" if eq > 0 and cb.get("equipment", 0) > 0 else ""
        ore_disp = c_gold(f"Ore:{ore}{ore_cb}")
        org_disp = c_green(f"Org:{org}{org_cb}")
        eq_disp = c_magenta(f"Eq:{eq}{eq_cb}")

        debt = player.get("debt", 0)
        debt_str = f" │ Debt: {c_red(f'{debt:,} Cr')}" if debt > 0 else ""
        operatives = player.get("operatives", 0)
        ops_str = f" │ Spies: {c_magenta(str(operatives))}" if operatives > 0 else ""
        bounty = player.get("bounty", 0)
        bounty_str = f" │ {c_red(f'BOUNTY: {bounty:,} Cr')}" if bounty > 0 else ""
        embargoed = player.get("embargoed_by", [])
        embargo_str = f" │ {c_gold('[EMBARGOED]')}" if embargoed else ""

        fx_view = view.get("fx", {})
        wallet = fx_view.get("wallet", {})
        wallet_str = "".join(f" │ {c_gold(f'{amt:,} {cur}')}" for cur, amt in wallet.items() if amt)
        used_holds = round(cargo.get("holds_used", used_holds), 1)

        line_sep = c_blue("═" * 78)

        hud = [
            f"╔{line_sep}╗",
            (
                f"║ {c_cyan('XYLARIUM BBS')} │ {rank_badge} │ Sector: {c_gold(f'{s_id:03d}')} [{sec_badge}] "
                f"│ Cycle: {c_white(str(view.get('cycle', 0)))} "
                f"│ Turns: {c_gold(str(turns))} │ {_mode_badge(view.get('mode', 'FLY'))} ║"
            ),
            f"╠{line_sep}╣",
            (
                f"║ Credits: {c_gold(f'{credits:,} Cr')}{wallet_str}{debt_str}{bounty_str}{embargo_str} │ Ship: {c_white(ship_type)} "
                f"│ Shields: {shield_str} │ Fighters: {fighter_str}{ops_str} ║"
            ),
            (
                f"║ Holds: {c_cyan(f'[{used_holds}/{cap_holds}]')} "
                f"({ore_disp}, {org_disp}, {eq_disp}) "
                f"│ Score: {c_white(f'{score:,}')} "
                f"│ Free Holds: {c_white(str(cargo.get('available', 0)))} "
                f"│ {_alignment_badge(view.get('cosmos', {}))} ║"
            ),
            f"╚{line_sep}╝"
        ]
        return "\n".join(hud)

    @classmethod
    def render_sector(cls, view: Dict[str, Any], category_page: int = 0) -> str:
        """Renders the current sector view, ports, planets, warps, and other captains."""
        sector = view.get("sector", {})
        s_id = sector.get("id", 1)
        name = sector.get("name", "Unknown Sector")
        cluster_name = sector.get("cluster_name", "Federation Core")
        port = sector.get("port")
        planets = sector.get("planets", [])
        captains = sector.get("captains", [])
        warps = sector.get("warps", [])
        anomalies = sector.get("anomalies", [])
        logs = view.get("logs", [])
        radio = view.get("radio", [])

        out = []

        # Sector Title
        out.append(f"\n{c_cyan('SECTOR')} {c_gold(f'#{s_id:03d}')} [{c_magenta(cluster_name)}]: {bold(c_white(name))}")
        space = view.get("space", {})
        fx_view = view.get("fx", {})
        local_cur = fx_view.get("local_currency", "SOL")
        if space.get("kind") == "NULL":
            out.append(f"  {c_gray('░ NULL SPACE')} - deep space between star systems. {c_red('Open fire zone: no Federal protection.')}")
        elif space:
            protected = c_green("Protected space (opening fire is a hostile act)") if space.get("protected") else c_gold("Unclaimed system")
            out.append(f"  {c_gold('☀ STAR SYSTEM')} - {c_white(space.get('star_type') or 'star')} │ {protected} │ Currency: {c_cyan(local_cur)}")

        # Warp Lanes
        warp_strs = []
        for w in warps:
            w_id = w["sector_id"]
            flags = []
            if w["security"] == "FEDERATION":
                flags.append("Fed")
            elif w["security"] == "ANARCHY":
                flags.append("Anarchy")
            if w.get("kind") == "NULL":
                flags.append("Null" + ("·Belt" if w.get("has_belt") else ""))
            if w["has_port"]:
                flags.append("Port")
            if w.get("has_anomaly"):
                flags.append("Anomaly")
            if w.get("has_my_planet"):
                p_name = w.get("my_planet_name", "Colony")
                flags.append(f"★ My Colony: {p_name}")
            elif w["has_planet"]:
                flags.append("Planet")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            if w.get("has_my_planet"):
                warp_strs.append(f"{c_cyan(f'({w_id:03d})')}{c_green(flag_str)}")
            else:
                warp_strs.append(f"{c_gold(f'({w_id:03d})')}{c_gray(flag_str)}")

        warp_lines = []
        current_line = f"  {bold('Wormhole Warps:')} "
        cur_len = 18
        for w_s in warp_strs:
            raw_len = len(re.sub(r'\x1b\[[0-9;]*m', '', w_s))
            if cur_len + raw_len + 2 > 78 and cur_len > 18:
                warp_lines.append(current_line.rstrip())
                current_line = "    " + w_s + "  "
                cur_len = 4 + raw_len + 2
            else:
                current_line += w_s + "  "
                cur_len += raw_len + 2
        if current_line.strip():
            warp_lines.append(current_line.rstrip())
        out.extend(warp_lines)

        # Port Summary
        if space.get("kind") == "NULL":
            belts = space.get("belts", [])
            hidden = space.get("unscanned_belts", 0)
            if belts or hidden:
                out.append(f"\n  {c_cyan('► ASTEROID FIELD:')} yield {space.get('mining_yield', 0)} units/turn with your hull")
                for b in belts:
                    mix = ", ".join(f"{k} {int(v * 100)}%" for k, v in sorted(b["composition"].items(), key=lambda kv: -kv[1]))
                    out.append(f"    {c_gold(b['id'])} [{b['type']}] reserve {b['reserve']:,}/{b['max_reserve']:,} ({mix})")
                if hidden:
                    out.append(f"    {c_gray(f'{hidden} unresolved belt signature(s) - type SCAN to survey')}")
            if space.get("debris_fields"):
                out.append(f"  {c_magenta('► DEBRIS FIELD')} x{space['debris_fields']} - type SALVAGE to recover wreckage")
        if space.get("sentries"):
            out.append("  " + c_red("► SENTRY PICKETS: ") + ", ".join(f"{o} x{n}" for o, n in space["sentries"].items()))

        if port:
            p_name = port["name"]
            p_class = port["port_class"]
            p_cur = port.get("currency", local_cur)
            liq = port.get("treasury")
            liq_str = f" │ Liquidity: {liq:,} {p_cur}" if liq is not None else ""
            out.append(f"\n  {c_cyan('► TRADE PORT:')} {c_white(p_name)} [Class {p_class}]")
            out.append(f"    Prices in {c_gold(p_cur)}{liq_str}")
            divider = "    " + "-" * 74
            out.append(divider)
            cat = port.get("catalog", {})

            specs = [
                {
                    "id": "VOLATILES",
                    "title": "[1] VOLATILES & GASES:",
                    "order": ["H", "He-3", "C", "H2O", "Xe"],
                },
                {
                    "id": "METALS",
                    "title": "[2] STRUCTURAL METALS & ALLOYS:",
                    "order": ["Fe", "Ti", "Si", "Ni", "Cu", "AdL"],
                },
                {
                    "id": "EXOTICS",
                    "title": "[3] FISSIONABLES & EXOTICS:",
                    "order": ["U", "Pt", "SpR", "cryogenite", "stelalith", "umbrite", "chitinium", "pyrosite", "aetherium", "ferrolattice"],
                },
                {
                    "id": "MANUFACTURED",
                    "title": "[4] MANUFACTURED COMPONENTS:",
                    "order": ["M1_SUPERCONDUCTOR", "M2_BIOSPHERE_PACK", "M3_ENGINE_MANIFOLD", "M4_WARP_CORE"],
                },
                {
                    "id": "TRI_COMMODITIES",
                    "title": "[5] CORE TRI-COMMODITIES:",
                    "order": ["ORE", "ORGANICS", "EQUIPMENT"],
                },
            ]

            active_cats = []
            tri_goods = {"ORE", "ORGANICS", "EQUIPMENT"}
            for sp in specs:
                items = []
                for cid in sp["order"]:
                    if cid in cat:
                        info = cat[cid]
                        if info.get("port_buys") or info.get("port_sells"):
                            items.append((cid, info))
                # Catch any additional dynamic commodities matching category
                for cid, info in cat.items():
                    if cid not in sp["order"] and cid not in tri_goods and info.get("category") == sp["id"]:
                        if info.get("port_buys") or info.get("port_sells"):
                            items.append((cid, info))
                if items:
                    active_cats.append((sp, items))

            cats_per_page = 2
            page_val = view.get("port_category_page", category_page)
            if active_cats:
                num_pages = (len(active_cats) + cats_per_page - 1) // cats_per_page
                cur_page = page_val % num_pages
                start_idx = cur_page * cats_per_page
                end_idx = start_idx + cats_per_page
                page_cats = active_cats[start_idx:end_idx]

                for idx, (sp, items) in enumerate(page_cats):
                    if idx > 0:
                        out.append("")
                    out.append(f"    {bold(c_gold(sp['title']))}")
                    name_pad = max(19, max(len(inf.get("name", "")) for _, inf in items))
                    for cid, info in items:
                        if info.get("port_buys"):
                            mode = c_green("BUYS")
                            price = info.get("buy_price", 0)
                        else:
                            mode = c_gold("SELLS")
                            price = info.get("sell_price", 0)
                        stock = info.get("stock", 0)
                        name_str = f"{info.get('name', cid):<{name_pad}}"
                        out.append(f"        • {c_white(name_str)}: {mode} @ {price:>2} Cr  (Stock: {stock})")

                if len(active_cats) > cats_per_page:
                    next_page = (cur_page + 1) % num_pages
                    next_idx = next_page * cats_per_page
                    next_cat = active_cats[next_idx][0]
                    out.append("")
                    out.append(f"    {bold(c_gold(next_cat['title']))} {c_cyan('(Press [N] for Next Category)')}")
            else:
                out.append(f"    {c_gray('No commodities currently traded in this port inventory.')}")

            out.append(divider)
        else:
            out.append(f"\n  {c_gray('► No trade port in this sector.')}")

        # Planetary Bodies
        if planets:
            for p in planets:
                p_name = p["name"]
                owner = p.get("owner_id")
                natives = p.get("natives")
                if natives:
                    from xylarium.config import NATIVE_STAGES
                    stage = NATIVE_STAGES[min(natives["stage"], len(NATIVE_STAGES) - 1)]
                    status = c_magenta(f"[NATIVE WORLD - the {natives['name']}, {stage}]")
                elif p.get("faction_id") == "IMPERIUM":
                    status = c_gold("[IMPERIAL WORLD - Aurelian Imperium]")
                elif p.get("faction_id") == "ZEALOT":
                    status = c_red("[PYRE WORLD - Choir of the Pyre]")
                elif not owner:
                    status = c_green("[UNCLAIMED - Available for Colonization]")
                elif owner == view["player"]["id"]:
                    status = c_cyan(f"[YOUR COLONY - Level {p['citadel_level']} Citadel]")
                else:
                    status = c_red(f"[RIVAL COLONY - Governor: {owner}]")

                citadel_name = CITADEL_CONFIG.get(p.get("citadel_level", 0), {}).get("name", "Outpost")
                p_pop = p.get("population", 0)
                p_treasury = p.get("treasury", 0)
                out.append(
                    f"  {c_gold('► PLANET:')} {bold(c_white(p_name))} {status}\n"
                    f"    Citadel: {c_white(citadel_name)} │ Pop: {c_gold(f'{p_pop:,}')} │ "
                    f"Shields: {c_cyan(str(p.get('shields', 0)))}/{p.get('max_shields', 200)} │ "
                    f"Garrison: {c_red(str(p.get('fighters', 0)))} Fighters │ "
                    f"Vault: {c_gold(f'{p_treasury:,} ' + p.get('currency', 'SOL'))}"
                )
                out.append(f"    World: {c_white(p.get('planet_type', 'TERRESTRIAL').replace('_', ' ').title())} │ "
                           f"Currency: {c_cyan(p.get('currency', 'SOL'))}")
                if natives:
                    out.append(f"    {c_magenta('☼ LOCALS:')} {natives['species']} │ sapience {natives['sapience']:.1f} │ "
                               f"~{natives['population']:,} people │ {natives['temperament']} │ type NATIVES to deal with them")
                ruins = p.get("ruins")
                if ruins:
                    open_strata = len(ruins["strata"]) - ruins["dug_depth"]
                    out.append(f"    {c_magenta('☗ RUINS:')} {ruins['culture']} ({ruins['era'].lower()}, lost to {ruins['cause']}) │ "
                               f"{open_strata} stratum(s) open │ type RUINS to survey, DIG to excavate")
        else:
            out.append(f"  {c_gray('► No planetary bodies in orbital scan.')}")

        # Cosmic Anomalies
        if anomalies:
            out.append(f"\n  {c_magenta('► COSMIC ANOMALIES IN ORBIT:')}")
            for anom in anomalies:
                st = anom.get("status", "UNDISCOVERED")
                status_color = c_green if st == "SOLVED" else c_magenta
                tag = status_color(f"[{st}]")
                anom_type = anom.get("anomaly_type", "").replace("_", " ")
                puzzle_type = anom.get("puzzle_type", "").replace("_", " ")
                rew_cr = anom.get("reward_credits", 0)
                rew_rp = anom.get("reward_research", 0)
                rew_tech = str(anom.get("reward_tech", "None"))
                out.append(
                    f"    {tag} {bold(c_white(anom['name']))} [{c_gold(anom['id'])}]\n"
                    f"      Type: {c_gold(anom_type)} │ Puzzle: {c_cyan(puzzle_type)} │ "
                    f"Target Freq: {c_gold(str(anom.get('puzzle_target', '??')))}\n"
                    f"      Yield: +{c_gold(f'{rew_cr:,} Cr')} & +{c_cyan(str(rew_rp) + ' RP')} │ "
                    f"Blueprint: {c_magenta(rew_tech)}"
                )

        # Other Captains Present
        if captains:
            out.append(f"\n  {c_red('► SHIPS DETECTED IN SECTOR:')}")
            for c in captains:
                badge = c_red("[PIRATE]") if c["personality"] == "pirate" else c_gold(f"[{c['personality'].upper()}]")
                r_title = c.get("rank_title")
                r_tier = c.get("rank_tier")
                r_badge = f"[{r_title} T{r_tier}] " if r_title else ""
                out.append(
                    f"    {badge} {r_badge}{bold(c_white(c['name']))} piloting a {c['ship_type']} "
                    f"(Shields: {c_cyan(str(c['shields']))}, Fighters: {c_red(str(c['fighters']))})"
                )

        # Recent Subspace Radio Feed
        if radio:
            out.append(f"\n{c_blue('──[ Subspace Radio Feed ]' + '─' * 55)}")
            for r in radio[-3:]:
                sender = c_gold(f"[{r['sender']}]")
                txt = c_gray(r['text'])
                out.append(f"  {sender}: {txt}")

        # Recent Action Logs
        if logs:
            out.append(f"{c_blue('──[ Tactical Logs ]' + '─' * 62)}")
            for l in logs[-2:]:
                out.append(f"  {c_cyan('»')} {l}")

        return "\n".join(out)

    @classmethod
    def render_trade_screen(cls, view: Dict[str, Any], active_category: str = "1") -> str:
        """Renders the detailed port trading interface with hierarchical category navigation."""
        sector = view.get("sector", {})
        port = sector.get("port")
        player = view.get("player", {})
        cargo = player.get("ship", {}).get("cargo", {})

        if not port:
            return c_red("Error: No trade port present in this sector.")

        player_credits = player.get("credits", 0)

        # Tabs for categories
        tabs = [
            c_gold("[1] Volatiles") if active_category == "1" else c_gray("[1] Volatiles"),
            c_gold("[2] Metals") if active_category == "2" else c_gray("[2] Metals"),
            c_gold("[3] Exotics") if active_category == "3" else c_gray("[3] Exotics"),
            c_gold("[4] Manufactured") if active_category == "4" else c_gray("[4] Manufactured"),
            c_gold("[5] Tri-Commodities") if active_category == "5" else c_gray("[5] Tri-Commodities"),
        ]
        tab_header = "  " + " │ ".join(tabs)

        cat_title = "VOLATILES & LIFE PRECURSORS"
        rec_hull = "CRYO_TANKER (Volatile Tanker)"
        if active_category == "1":
            cat_title = "VOLATILES & LIFE PRECURSORS (Gases & Liquids)"
            rec_hull = "CRYO_TANKER (Volatile Tanker)"
            commodities = COMMODITY_CATEGORIES["1"]["commodities"]
        elif active_category == "2":
            cat_title = "STRUCTURAL METALS & ALLOYS (Heavy Ores)"
            rec_hull = "BULK_FREIGHTER (Bulk Freighter)"
            commodities = COMMODITY_CATEGORIES["2"]["commodities"]
        elif active_category == "3":
            cat_title = "FISSIONABLES, NOBLES & EXOTICS (Precious Specie)"
            rec_hull = "QUANTUM_SKIFF (Quantum Skiff)"
            commodities = COMMODITY_CATEGORIES["3"]["commodities"]
        elif active_category == "4":
            cat_title = "MANUFACTURED VALUE-ADDED COMPONENTS (Industrial Goods)"
            rec_hull = "QUANTUM_SKIFF (Quantum Skiff)"
            commodities = COMMODITY_CATEGORIES["4"]["commodities"]
        else:
            cat_title = "LEGACY TRADEWARS TRI-COMMODITIES"
            rec_hull = "STANDARD (Merchant Hauler)"
            commodities = ["ORE", "ORGANICS", "EQUIPMENT"]

        lines = [
            f"\n{bold(c_cyan('═════════════════════ [ PORT TRADING TERMINAL ] ═════════════════════'))}",
            f"Port: {c_white(port['name'])}  │  Class: {c_gold(port['port_class'])}",
            f"Your Credits: {c_gold(f'{player_credits:,} Cr')}  │  Available Holds: {c_cyan(str(cargo.get('available', 0)))}",
            "-" * 74,
            tab_header,
            f"Category: {bold(c_gold(cat_title))}",
            f"Recommended Specialized Hull: {c_cyan(rec_hull)}",
            "-" * 74,
            f"{'Symbol':<6} {'Commodity Name':<24} {'Mode':<10} {'Stock':<8} {'Price':<10} {'In Hold':<16}",
            "-" * 74,
        ]

        cat = port.get("catalog", {})
        cb = cargo.get("cost_basis", {})
        for comm_id in commodities:
            comm_data = cat.get(comm_id)
            if not comm_data:
                cfg = COMMODITY_CONFIG.get(comm_id, {})
                comm_data = {
                    "name": cfg.get("name", comm_id),
                    "symbol": cfg.get("symbol", comm_id),
                    "stock": 0,
                    "buy_price": None,
                    "sell_price": None,
                    "port_buys": False,
                    "port_sells": False,
                }

            sym = comm_data.get("symbol", comm_id)
            name = comm_data.get("name", comm_id)[:22]
            stock = comm_data.get("stock", 0)

            if comm_id == "ORE":
                in_hold = cargo.get("ore", 0)
            elif comm_id == "ORGANICS":
                in_hold = cargo.get("organics", 0)
            elif comm_id == "EQUIPMENT":
                in_hold = cargo.get("equipment", 0)
            else:
                in_hold = cargo.get("elements", {}).get(comm_id, 0)

            basis = cb.get(comm_id.lower(), 0.0)
            hold_str = str(in_hold)
            if in_hold > 0 and basis > 0:
                cost_int = int(round(basis))
                if comm_data.get("port_buys") and comm_data.get("buy_price"):
                    p_diff = comm_data["buy_price"] - cost_int
                    diff_sign = "+" if p_diff >= 0 else ""
                    color_fn = c_green if p_diff >= 0 else c_red
                    hold_str = f"{in_hold} ({color_fn(f'{diff_sign}{p_diff}')})"
                else:
                    hold_str = f"{in_hold} (@{cost_int})"

            if comm_data.get("port_buys"):
                mode = c_green("BUYS")
                price = c_gold(f"{comm_data.get('buy_price', 0)} Cr")
            elif comm_data.get("port_sells"):
                mode = c_cyan("SELLS")
                price = c_gold(f"{comm_data.get('sell_price', 0)} Cr")
            else:
                mode = c_gray("NONE")
                price = c_gray("--")

            lines.append(f"{sym:<6} {name:<24} {mode:<19} {str(stock):<8} {price:<19} {hold_str}")

        lines.append("-" * 74)
        lines.append(
            f"Commands: {c_gold('[B]uy <Comm> <Amt>')}  │  {c_gold('[S]ell <Comm> <Amt>')}  │  {c_gold('[1-5] Tab')}  │  {c_gold('[X] Exit')}"
        )
        return "\n".join(lines)

    @classmethod
    def render_hierarchical_trade_screen(cls, view: Dict[str, Any], active_category: str = "1") -> str:
        """Alias for hierarchical categorized port trade screen."""
        return cls.render_trade_screen(view, active_category=active_category)

    @classmethod
    def render_vc_investment_desk(cls, view: Dict[str, Any]) -> str:
        """Renders the Sector 1 Stardock Venture Capital and debt syndicate investment desk."""
        player = view.get("player", {})
        credits = player.get("credits", 0)
        vc_active = view.get("vc_active_syndicate") or player.get("vc_active_syndicate")
        vc_debt = view.get("vc_debt", 0) or player.get("vc_debt", 0)
        vc_royalty = view.get("vc_royalty_pct", 0.0) or player.get("vc_royalty_pct", 0.0)
        vc_paid = view.get("vc_principal_paid", 0) or player.get("vc_principal_paid", 0)

        cr = player.get("credit_rating", 500)
        tier = player.get("credit_tier", "SUBPRIME")
        exp = player.get("experience_score", 100)
        net_equity = view.get("net_equity", credits)
        vc_terms = view.get("vc_terms", {})

        # Build credit gauge: 300 to 850
        pct = max(0.0, min(1.0, (cr - 300) / 550.0))
        filled = int(pct * 20)
        gauge_str = "█" * filled + "░" * (20 - filled)

        tier_colors = {
            "PRIME_ALPHA": c_green,
            "TIER_1_SECURE": c_cyan,
            "TIER_2_FAIR": c_gold,
            "SUBPRIME": c_magenta,
            "DISTRESSED": c_red,
        }
        color_func = tier_colors.get(tier, c_gold)

        lines = [
            f"\n{bold(c_gold('╔══════════════════════════════════════════════════════════════════════════════╗'))}",
            f"{bold(c_gold('║         SECTOR 001 STARDOCK │ INTERSTELLAR VENTURE CAPITAL DESK              ║'))}",
            f"{bold(c_gold('╚══════════════════════════════════════════════════════════════════════════════╝'))}",
            f"  Treasury: {c_gold(f'{credits:,} Cr')}  │  Net Equity: {c_cyan(f'{net_equity:,} Cr')}  │  Experience: {c_white(f'{exp} Ξ')}",
            f"  Credit Rating: {bold(color_func(f'{cr} / 850'))} [{gauge_str}] Tier: {bold(color_func(tier))}",
            "-" * 78,
            f"  {bold(c_cyan('ACTIVE VENTURE DEBT COVENANT STATUS:'))}",
        ]

        if vc_debt > 0 and vc_active:
            syn_info = VC_SYNDICATES.get(vc_active, {})
            syn_name = syn_info.get("name", vc_active)
            lines.append(f"  ► Managing Syndicate:   {c_gold(syn_name)}")
            lines.append(f"  ► Outstanding Debt:     {c_red(f'{vc_debt:,} Cr')}")
            lines.append(f"  ► Automated Skim Rate:  {c_magenta(f'{vc_royalty:.1f}% of all automated trade route yields')}")
            lines.append(f"  ► Debt Amortized:       {c_green(f'{vc_paid:,} Cr repaid to date')}")
        else:
            lines.append(f"  {c_green('✔ No active venture debt covenants. High-credit interstellar standing.')}")
            lines.append(f"  {c_gray('Sol Guild underwriting lines available to finance commercial haulage expansion.')}")

        lines.append("-" * 78)
        lines.append(f"  {bold(c_white('INSTITUTIONAL SYNDICATES & DYNAMIC PRICING COVENANTS:'))}\n")

        idx = 1
        for syn_id, syn in VC_SYNDICATES.items():
            terms = vc_terms.get(syn_id, {})
            principal = terms.get("suggested_principal", syn["principal"])
            multiplier = terms.get("multiplier", syn["multiplier"])
            debt = int(principal * multiplier)
            royalty = terms.get("royalty_pct", syn["royalty_pct"])
            max_power = terms.get("max_borrowing_power", 0)
            eligible = terms.get("eligible", cr >= syn.get("min_credit_rating", 450) and exp >= syn.get("min_experience", 50))

            syn_name = syn["name"]
            syn_title = c_gold(f"[{idx}] {syn_name}")

            if eligible:
                status_badge = c_green(f"[ELIGIBLE │ Max Facility: {max_power:,} Cr]")
            else:
                req_parts = []
                if cr < syn.get("min_credit_rating", 450):
                    req_parts.append(f"CR ≥ {syn.get('min_credit_rating', 450)}")
                if exp < syn.get("min_experience", 50):
                    req_parts.append(f"Exp ≥ {syn.get('min_experience', 50)} Ξ")
                if req_parts:
                    status_badge = c_red(f"[LOCKED │ Requires {', '.join(req_parts)}]")
                else:
                    status_badge = c_red(f"[LOCKED │ Insufficient Net Equity (Facility Cap: {max_power:,} Cr)]")

            inj_str = c_green(f"+{principal:,} Cr")
            rep_str = c_red(f"{debt:,} Cr")
            roy_str = c_magenta(f"{royalty:.1f}%")
            eq_str = c_cyan(f"{syn['equity_dilution_pct']}%")
            desc_str = c_gray(syn["description"])

            lines.append(
                f"  {syn_title}  {status_badge}\n"
                f"      Capital Allocation: {inj_str}  │  Repayment Obligation: {rep_str} ({multiplier:.2f}x)\n"
                f"      Risk-Adjusted Royalty: {roy_str}  │  Equity Stake: {eq_str}\n"
                f"      {desc_str}\n"
            )
            idx += 1

        lines.append("-" * 78)
        lines.append(
            f"Commands: {c_gold('[1-3] Apply for VC Funding')}  │  {c_gold('[R]epay Debt <Amount>')}  │  {c_gold('[X] Return')}"
        )
        return "\n".join(lines)

    @classmethod
    def render_captain_profile_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the comprehensive Captain Dossier, Credit Risk, and Financial Integrity Profile."""
        player = view.get("player", {})
        pname = player.get("name", "Unknown Captain")
        pid = player.get("id", "000")
        ship = player.get("ship", {})
        stype = ship.get("ship_type", "Standard Ship")
        home = player.get("home_sector", 1)
        turns = player.get("turns_left", view.get("turns", 0))
        species = player.get("species", "human-sol")
        metabolism = player.get("metabolism", "biotic")
        crystals = len(player.get("grown_basis", []))
        clade = player.get("clade") or view.get("clade") or "BIOTIC"
        rank_tier = player.get("rank_tier") or view.get("rank_tier") or 1
        rank_title = player.get("rank_title") or view.get("rank_title") or "Scrap-Apprentice"
        rank_role = player.get("rank_role") or view.get("rank_role") or "Scout Salvager"
        full_title = player.get("full_title") or f"{rank_title} {pname}"
        alignment = player.get("alignment") or "Independent"
        transponder = player.get("forged_transponder", False) or view.get("forged_transponder", False)
        promo_info = view.get("promotion_requirements", {})
        can_promo = view.get("can_promote", False)

        cr = player.get("credit_rating", 500)
        tier = player.get("credit_tier", "SUBPRIME")
        exp = player.get("experience_score", 100)
        reps = player.get("faction_reputation", {"Federation": 50.0, "Corporate": 50.0, "Pirates": 20.0, "Indigenous": 50.0})

        # History
        repay_hist = player.get("loan_repayment_history", 0)
        freight_hist = player.get("freight_deliveries_completed", 0)
        default_hist = player.get("default_history", 0)

        # Asset Breakdown
        credits = player.get("credits", 0)
        ship_cfg = SHIP_CATALOG.get(stype, {})
        hull_val = ship_cfg.get("price", 1000)

        # Cargo value
        cargo_val = 0
        cargo = ship.get("cargo", {})
        for comm, qty in cargo.items():
            if comm in ["cost_basis", "holds", "elements"]:
                continue
            if isinstance(qty, (int, float)) and qty > 0:
                cfg = COMMODITY_CONFIG.get(comm.upper(), {})
                cargo_val += int(qty * cfg.get("base_price", 10))

        # Portfolio value
        port_val = 0
        companies = {c["ticker"]: c for c in view.get("market", {}).get("companies", [])}
        for ticker, shares in player.get("portfolio", {}).items():
            c_info = companies.get(ticker)
            if c_info:
                port_val += shares * c_info.get("share_price", 10)

        # Colony assets
        colony_val = 0
        for p in view.get("owned_planets", []):
            colony_val += p.get("treasury", 0) + (p.get("ore_silo", 0) * 5) + (p.get("organics_silo", 0) * 10)

        bank_debt = player.get("debt", 0)
        vc_debt = player.get("vc_debt", 0)
        total_liabilities = bank_debt + vc_debt
        gross_assets = credits + hull_val + cargo_val + port_val + colony_val
        net_equity = view.get("net_equity", max(1000, gross_assets - total_liabilities))

        # Credit gauge (300 to 850)
        pct = max(0.0, min(1.0, (cr - 300) / 550.0))
        filled = int(pct * 25)
        gauge_str = "█" * filled + "░" * (25 - filled)

        tier_colors = {
            "PRIME_ALPHA": c_green,
            "TIER_1_SECURE": c_cyan,
            "TIER_2_FAIR": c_gold,
            "SUBPRIME": c_magenta,
            "DISTRESSED": c_red,
        }
        color_func = tier_colors.get(tier, c_gold)

        def bar(val: float) -> str:
            n = int((max(0.0, min(100.0, val)) / 100.0) * 10)
            return "█" * n + "░" * (10 - n)

        tier_disp = tier.replace("_", " ")
        lines = [
            f"\n{bold(c_gold('╔══════════════════════════════════════════════════════════════════════════════╗'))}",
            f"{bold(c_gold('║                 CAPTAIN DOSSIER & FINANCIAL INTEGRITY PROFILE                ║'))}",
            f"{bold(c_gold('╚══════════════════════════════════════════════════════════════════════════════╝'))}",
            f"  Captain: {bold(c_white(full_title))} [ID: {c_gold(pid)}]       Vessel: {c_cyan(stype)}",
            f"  Home Sector: {c_gold(f'Sector {home:03d}')}                         Turns Remaining: {c_white(str(turns))}",
            f"  Species / Metabolism: {c_white(species)} / {c_magenta(metabolism)}      Basis Crystals: {c_cyan(str(crystals))}",
            f"  Clade / Rank: {c_gold(f'[{clade}]')} Tier {rank_tier} - {bold(c_white(rank_title))} ({c_cyan(rank_role)})",
            f"  Alignment: {c_white(alignment)} │ Transponder: {c_green('[FORGED TRANSPONDER SPOOF]') if transponder else c_gray('[Standard Transponder]')}",
            "-" * 78,
            f"  {bold(c_cyan('INTERSTELLAR CREDIT RISK PROFILE (FICO 300 - 850):'))}",
            f"  Credit Rating: {bold(color_func(f'{cr} / 850'))}   Tier: {bold(color_func(f'[{tier_disp}]'))}",
            f"  Trust Gauge:   [{gauge_str}] ({pct * 100:.1f}% Conductance)",
            f"  Experience Seniority (Ξ): {bold(c_gold(f'{exp} Ξ'))}",
            "  Experience by Domain: " + (" │ ".join(
                f"{k.capitalize()} {v}" for k, v in sorted(view.get("experience_domains", {}).items(), key=lambda kv: -kv[1])
            ) or c_gray("none yet - chart new sectors, trade at a profit, deliver freight, build colonies")),
            f"  Crew Rations: {c_red(f'HUNGRY x{view.get("hunger", 0)} (shields draining, no learning)') if view.get('hunger') else c_green('Fed')}"
            f"   │ Hull Insurance: {c_green('Insured') if view.get('federal', {}).get('insured') else c_red('Uninsured')}"
            f" (premium {view.get('federal', {}).get('premium', 0):,} Cr / 50 cycles)",
            "",
            f"  {bold(c_cyan('SOCIAL COHESION & FACTION REPUTATION (Σ):'))}",
            f"  ► Terran Federation:  [{c_cyan(bar(reps.get('Federation', 50.0)))}] {reps.get('Federation', 50.0):.1f}%  (Federal Banking & Clearances)",
            f"  ► Megacorporate ISSE: [{c_gold(bar(reps.get('Corporate', 50.0)))}] {reps.get('Corporate', 50.0):.1f}%  (Institutional VC & Margin Desk)",
            f"  ► Pirate Syndicates:  [{c_red(bar(reps.get('Pirates', 20.0)))}] {reps.get('Pirates', 20.0):.1f}%  (Bounty & Contraband Channels)",
            f"  ► Indigenous Clades:  [{c_green(bar(reps.get('Indigenous', 50.0)))}] {reps.get('Indigenous', 50.0):.1f}%  (Colony Cohesion & Biotics)",
            "-" * 78,
            f"  {bold(c_cyan('MARK-TO-MARKET ASSET & BALANCE SHEET VALUATION:'))}",
            f"  ► Liquid Treasury:          {credits:>10,} Cr   ► Federal Bank Loan:        {bank_debt:>10,} Cr",
            f"  ► Hull Market Valuation:    {hull_val:>10,} Cr   ► Active VC Debt:           {vc_debt:>10,} Cr",
            f"  ► Cargo Hold Inventory:     {cargo_val:>10,} Cr   ──────────────────────────────────────────",
            f"  ► ISSE Securities Portfolio:{port_val:>10,} Cr   Total Debt Liabilities:     {total_liabilities:>10,} Cr",
            f"  ► Sovereign Colony Reserves:{colony_val:>10,} Cr",
            f"  ──────────────────────────────────────────   ──────────────────────────────────────────",
            f"  Gross Sovereign Assets:     {gross_assets:>10,} Cr   {bold('NET SOVEREIGN EQUITY:')}   {bold(c_green(f'{net_equity:>10,} Cr'))}",
            "-" * 78,
            f"  {bold(c_cyan('HISTORICAL COMPLIANCE & COMMERCIAL TRACK RECORD:'))}",
            f"  ► Freight Contracts Fulfilled:   {freight_hist:<6d}    ► Default / Delinquency Events: {default_hist:<6d}",
            f"  ► Debt Covenants Discharged:     {repay_hist:<6d}    ► Active Automated Haulers:     {len(player.get('trade_haulers', [])):<6d}",
            "-" * 78,
        ]

        # Rank Ascension / Promotion status
        ascension_lines = []
        if promo_info:
            target_tier = promo_info.get("target_tier", rank_tier)
            target_title = promo_info.get("target_title", "")
            target_role = promo_info.get("target_role", "")
            target_perks = promo_info.get("target_perks", "")
            ascension_lines.append(f"  {bold(c_cyan('CLADE RANK PROGRESSION & INVARIANT ASCENSION MATRIX:'))}")
            if promo_info.get("max_rank"):
                ascension_lines.append(f"  {bold(c_gold('★ APEX SOVEREIGN (TIER 4) - MAXIMUM RANK ASCENDED ★'))}")
            elif can_promo:
                ascension_lines.append(f"  {bold(c_green(f'▲ ELIGIBLE FOR ASCENSION: Tier {target_tier} {target_title} ({target_role}) ▲'))}")
                ascension_lines.append(f"  Endowment: +{promo_info.get('reward_credits', 0):,} Cr, +{promo_info.get('reward_turns', 0)} Turns │ Perks: {target_perks}")
                ascension_lines.append(f"  {bold(c_white('PRESS [P] TO ASCEND AND PROMOTE RANK NOW!'))}")
            else:
                unmet = "; ".join(promo_info.get("reasons", []))
                ascension_lines.append(f"  ► Next Ascension: Tier {target_tier} {bold(c_white(target_title))} ({target_role})")
                ascension_lines.append(f"    {c_red('Pending Gates:')} {c_gold(unmet)}")
                ascension_lines.append(f"    Perks on Unlock: {c_gray(target_perks)}")
            ascension_lines.append("-" * 78)

        # Phylogenetic Cladogram & 4D Cochain Flux Vector
        phylo = view.get("phylogeny", {})
        cur_node = phylo.get("current_node", {})
        affinities = phylo.get("affinities", {})
        flux_dict = phylo.get("cochain_flux", {})
        phi_norm = flux_dict.get("normalized", {"mass": 0.25, "thermodynamic": 0.25, "exotic": 0.25, "entropic": 0.25}) if isinstance(flux_dict, dict) else {"mass": 0.25, "thermodynamic": 0.25, "exotic": 0.25, "entropic": 0.25}

        ascension_lines.append(f"  {bold(c_cyan('PHYLOGENETIC ASCENSION CLADOGRAM (DAG) & 4D COCHAIN FLUX:'))}")
        node_disp = f"[{cur_node.get('clade', clade)}-T{cur_node.get('tier', rank_tier)}] {cur_node.get('name', rank_title)}"
        m_flx = phi_norm.get("mass", 0.25)
        t_flx = phi_norm.get("thermodynamic", 0.25)
        e_flx = phi_norm.get("exotic", 0.25)
        s_flx = phi_norm.get("entropic", 0.25)
        ascension_lines.append(f"  Flux (Φ): [Mass: {c_cyan(f'{m_flx:.2f}')}] [Thermo: {c_gold(f'{t_flx:.2f}')}] [Exotic: {c_magenta(f'{e_flx:.2f}')}] [Entropy: {c_red(f'{s_flx:.2f}')}]")

        if affinities:
            branch_strs = []
            best_child_id = max(affinities, key=affinities.get)
            for b_id, aff_score in affinities.items():
                is_best = (b_id == best_child_id)
                tag = f"►► [{b_id.split('_')[-1].upper()}: {int(aff_score * 100)}%]" if is_best else f"── [{b_id.split('_')[-1]}: {int(aff_score * 100)}%]"
                branch_strs.append(c_green(tag) if is_best else c_gray(tag))
            ascension_lines.append(f"  Branch Gravitation: {' '.join(branch_strs)}")

        if cur_node.get("canopy_override"):
            ascension_lines.append(f"  {bold(c_gold('★ APEX CANOPY OVERRIDE UNLOCKED:'))} {bold(c_green(cur_node.get('canopy_perk_title', 'Universe Rewrite')))}")
            ascension_lines.append(f"    Effect: {c_gray(cur_node.get('canopy_perk_description', ''))}")

        ascension_lines.append("-" * 78)
        lines.extend(ascension_lines)
        lines.append(f"  {bold(c_cyan('REGULATORY STANDINGS & GATED FINANCIAL ACCESS:'))}")

        # Regulatory status badges
        r_comm = c_green("[✔] APPROVED: Tri-Commodity & Bulk Periodic Commerce")
        r_fleet = c_green("[✔] APPROVED: Automated Multi-Hauler Fleet Management")

        # VC Line
        if cr >= 700 and exp >= 500:
            r_vc = c_green("[✔] ACCREDITED: Prime Tier VC Facilities (Voss Trust / Aegis / Sol)")
        elif cr >= 600 and exp >= 200:
            r_vc = c_cyan("[✔] APPROVED: Institutional VC Line (Aegis Orbital Partners)")
        elif cr >= 450 and exp >= 50:
            r_vc = c_gold("[✔] APPROVED: Seed VC Line (Sol Guild Angel Syndicate)")
        else:
            r_vc = c_red("[✘] LOCKED: VC Access Denied (Requires CR ≥ 450, Exp ≥ 50)")

        # Short Margin
        if cr >= SHORT_MIN_CREDIT:
            margin_pct = 50 if cr == 500 else (max(25, round(50 - (cr - 500) / 10.0)) if cr > 500 else min(90, round(50 + (500 - cr) / 5.0)))
            r_short = c_green(f"[✔] APPROVED: ISSE Short Selling Desk ({margin_pct}% Margin Collateral)")
        else:
            r_short = c_red(f"[✘] LOCKED: ISSE Short Selling Desk (Requires CR ≥ {SHORT_MIN_CREDIT})")

        # Takeover
        if (cr >= TAKEOVER_MIN_CREDIT and exp >= TAKEOVER_MIN_EXP) or net_equity >= 250000:
            r_take = c_green("[✔] CLEARED: Hostile Corporate Boardroom Takeovers (>50% Float Coup)")
        else:
            r_take = c_red(f"[✘] RESTRICTED: Hostile Takeovers (Requires CR ≥ {TAKEOVER_MIN_CREDIT}, Exp ≥ {TAKEOVER_MIN_EXP} or Net Equity ≥ 250k)")

        p_cmd = c_green("[P]romote Rank") if can_promo else c_gray("[P]romote Rank")
        c_cmd = c_cyan("[C]ladogram DAG")
        o_cmd = c_gold("[O]verride Canopy") if cur_node.get("canopy_override") else c_gray("[O]verride Canopy")
        lines.extend([
            f"  {r_comm}",
            f"  {r_fleet}",
            f"  {r_vc}",
            f"  {r_short}",
            f"  {r_take}",
            "=" * 78,
            f"Commands: {p_cmd}  │  {c_cmd}  │  {o_cmd}  │  {c_gold('[V]iew VC Desk')}  │  {c_gold('[E]xchange')}  │  {c_gold('[Enter / X] Return')}",
        ])
        return "\n".join(lines)

    @classmethod
    def render_fleet_control_console(cls, view: Dict[str, Any]) -> str:
        """Renders the Multi-Hauler Fleet Management and Automated Logistics Dashboard."""
        player = view.get("player", {})
        ship = player.get("ship", {})
        ship_fighters = ship.get("fighters", 0)
        credits = player.get("credits", 0)

        trade_haulers = view.get("trade_haulers", [])
        total_profit = sum(h.get("lifetime_profit", 0) for h in trade_haulers)
        trips = sum(h.get("trips_completed", 0) for h in trade_haulers)

        vc_active = view.get("vc_active_syndicate") or player.get("vc_active_syndicate")
        vc_debt = view.get("vc_debt", 0) or player.get("vc_debt", 0)
        vc_royalty = view.get("vc_royalty_pct", 0.0) or player.get("vc_royalty_pct", 0.0)

        lines = [
            f"\n{bold(c_cyan('╔══════════════════════════════════════════════════════════════════════════════╗'))}",
            f"{bold(c_cyan('║        GALACTIC FREIGHT HAULAGE & MULTI-HAULER FLEET CONTROL CONSOLE         ║'))}",
            f"{bold(c_cyan('╚══════════════════════════════════════════════════════════════════════════════╝'))}",
            f"Fleet Haulers: {c_gold(str(len(trade_haulers)))} Active  │  Total Yields: {c_green(f'{total_profit:,} Cr')}  │  Trips: {c_cyan(str(trips))}",
            f"Treasury: {c_gold(f'{credits:,} Cr')}  │  Flagship Fighter Wings: {c_red(f'{ship_fighters} wings available')}",
        ]

        if vc_debt > 0 and vc_active:
            lines.append(f"VC Covenant: {c_magenta(vc_active)} │ Debt: {c_red(f'{vc_debt:,} Cr')} │ Royalty Skim: {c_magenta(f'{vc_royalty:.1f}%')}")
        else:
            lines.append(f"VC Covenant: {c_green('None (100% Retained Fleet Profits)')}")

        lines.append("-" * 78)
        lines.append(f"{'ID':<9} {'Hull & Name':<20} {'Status':<13} {'Sec':<5} {'Route':<13} {'Manifest':<10} {'Escort':<7} {'Profit':<10}")
        lines.append("-" * 78)

        if not trade_haulers:
            lines.append(f"  {c_gray('No automated trade haulers commissioned. Commission a specialized hauler below!')}")
        else:
            for h in trade_haulers:
                h_id = h.get("id", "HAUL-?")
                h_name = h.get("name", "Hauler")
                h_hull = h.get("hull_class", "STANDARD")
                hull_info = SPECIALIZED_HULLS.get(h_hull, {})
                icon = hull_info.get("icon", "🚚")
                disp_name = f"{icon} {h_name[:16]}"

                status = h.get("status", "IDLE")
                if status == "IN_TRANSIT":
                    status_badge = c_cyan("IN_TRANSIT")
                elif status == "COMBAT":
                    status_badge = c_red("COMBAT")
                elif status == "UNDER_ATTACK":
                    status_badge = c_red("UNDER_ATK")
                elif status == "RETREAT":
                    status_badge = c_magenta("RETREAT")
                else:
                    status_badge = c_gray("IDLE")

                sec = h.get("sector_id", 1)
                orig = h.get("origin_sector", 1)
                dest = h.get("dest_sector", 30)
                route_str = f"{orig:03d}◄►{dest:03d}"

                outb = str(h.get("commodity_outbound", "ORE"))[:3]
                retc = str(h.get("commodity_return", "ORG"))[:3]
                manif_str = f"{outb}/{retc}"

                escorts = h.get("escort_fighters", 0)
                escort_str = c_red(str(escorts)) if escorts > 0 else c_gray("0")

                profit = h.get("lifetime_profit", 0)
                prof_str = c_green(f"{profit:,}Cr")

                lines.append(f"{h_id:<9} {disp_name:<20} {status_badge:<21} {sec:<5} {route_str:<13} {manif_str:<10} {escort_str:<15} {prof_str:<18}")

        lines.append("-" * 78)
        lines.append(f"{bold(c_white('COMMISSION SPECIALIZED HULL CLASSES:'))}")
        for k, h_cfg in SPECIALIZED_HULLS.items():
            icon = h_cfg.get("icon", "🚚")
            h_name = h_cfg["name"]
            h_holds = h_cfg["holds"]
            h_price = h_cfg["price"]
            h_title = c_gold(f"{h_name} ({k})")
            h_desc = c_gray(h_cfg["description"])
            lines.append(
                f"  {icon} {h_title}: {h_holds} holds, {c_gold(f'{h_price:,} Cr')} — {h_desc}"
            )


        lines.append("-" * 78)
        lines.append(
            f"Commands: {c_gold('[C]ommission')} │ {c_gold('[R]eassign Route')} │ {c_gold('[E]scort Wings')} │ {c_gold('[H]alt/Recall')} │ {c_gold('[S]crap')} │ {c_gold('[V]C Desk')} │ {c_gold('[X] Exit')}"
        )
        return "\n".join(lines)

    @classmethod
    def render_planet_screen(cls, view: Dict[str, Any], planet: Dict[str, Any]) -> str:
        """Renders the BRE/SRE Planetary Command Center."""
        player = view.get("player", {})
        p_id = planet.get("id")
        p_name = planet.get("name")
        owner = planet.get("owner_id")
        is_owner = (owner == player.get("id"))
        citadel_lvl = planet.get("citadel_level", 0)
        citadel_info = CITADEL_CONFIG.get(citadel_lvl, CITADEL_CONFIG[0])

        p_pop = planet.get("population", 0)
        p_treasury = planet.get("treasury", 0)
        p_morale = planet.get("morale", 100)
        max_pop = citadel_info.get("max_population", 2500)
        est_yield = int(p_pop * 0.15 * citadel_info["tax_multiplier"] * (p_morale / 100.0))
        morale_badge = c_green(f"{p_morale}% (Stable)") if p_morale >= 70 else c_red(f"{p_morale}% [FAMINE CRISIS!]")

        lines = [
            f"\n{bold(c_gold('═══════════════ [ PLANETARY COMMAND REDOUBT ] ═══════════════'))}",
            f"Colony: {bold(c_white(p_name))}  │  Sector: {planet.get('sector_id')}",
            f"Sovereignty: {c_cyan('YOU') if is_owner else (c_red(owner) if owner else c_green('UNINHABITED'))}",
            "-" * 72,
            f"Citadel Tier:      {c_white(str(citadel_lvl))} - {bold(citadel_info['name'])} (Pop Cap: {max_pop:,})",
            f"Population:        {c_gold(f'{p_pop:,}')} / {max_pop:,} Colonists (Yield: ~{est_yield} Cr/cycle)",
            f"Colony Morale:     {morale_badge}",
            f"Treasury Vault:    {c_gold(f'{p_treasury:,} Cr')} (Available for collection)",
            f"Planetary Shields: {c_cyan(str(planet.get('shields', 0)))} / {planet.get('max_shields', 200)} MW",
            f"Garrison Fighters: {c_red(str(planet.get('fighters', 0)))} / {citadel_info['max_fighters']} Wings",
            f"Counter-Intel:     {c_magenta(str(planet.get('security_operatives', 0)))} Security Agents",
            f"Mineral Silo:      {c_gold(str(planet.get('ore_silo', 0)))} Ore",
            f"Biosphere Silo:    {c_green(str(planet.get('organics_silo', 0)))} Organics (Food: 1 Org/1,000 Pop/cycle)",
        ]

        civ = planet.get("civilization")
        if civ:
            sigil = civ.get("sigil", "⬡")
            civ_name = civ.get("name", "Unknown")
            clade = civ.get("clade", "hypobiotid")
            meta = civ.get("metabolism", "biotic").upper()
            motto = civ.get("motto", "")
            era = civ.get("era_name", "Progenitor Dawn")
            proj = civ.get("current_project", "None")
            prog = civ.get("project_progress", 0)
            reserves = planet.get("element_reserves", {})
            res_str = ", ".join([f"{k}:{v}" for k, v in reserves.items()]) if reserves else "None"

            lines.append(
                f"Civilization:      {c_cyan(sigil)} {bold(c_white(civ_name))} (Clade: {clade} │ Substrate: {c_gold(meta)})"
            )
            if motto:
                lines.append(f"Motto:             \"{c_gray(motto)}\"")
            lines.append(f"Era & Tech:        Era: {c_gold(era)} │ Tech Level: {c_white(str(civ.get('tech_level', 1)))}")
            lines.append(f"Civic Works:       {c_cyan(proj)} [{_render_bar(prog, 100, length=10)}] {prog}%")
            lines.append(f"Elemental Vault:   {c_gold(res_str)}")

        lines.append("-" * 72)

        if not owner:
            lines.append(
                f"Options:\n"
                f"  {c_gold('[C]laim Planet')}             (Establish colony)\n"
                f"  {c_cyan('[V] Civilization & Elements')} (Taxon, 5-Axis periodic table, and civic works)\n"
                f"  {c_gold('[B]ack to Orbit')}"
            )
        elif is_owner:
            lines.append(
                f"Management:\n"
                f"  {c_gold('[T]ax Collection')}            (Transfer vault credits to ship)\n"
                f"  {c_gold('[I]nvest Population')}          (Spend credits to attract colonists up to cap)\n"
                f"  {c_gold('[S]hield Construction')}        (Build planetary shields: 10 Cr + Ore)\n"
                f"  {c_gold('[F]ighter Bay')}               (Recruit garrison fighters: 60 Cr/ea)\n"
                f"  {c_gold('[U]pgrade Citadel')}           (Advance Citadel tier for higher caps)\n"
                f"  {c_gold('[K] Counter-Intel')}           (Station/Withdraw security operatives)\n"
                f"  {c_cyan('[V] Civilization & Elements')} (Taxon, 5-Axis periodic table, and civic works)\n"
                f"  {c_gold('[D]eposit Cargo')}             (Transfer Ore/Organics from ship to silo)\n"
                f"  {c_gold('[W]ithdraw Cargo')}            (Transfer Ore/Organics from silo to ship)\n"
                f"  {c_gold('[B]ack to Orbit')}"
            )
        else:
            lines.append(
                f"Hostile Colony!\n"
                f"  {c_red('[A]ttack / Invade Planet')}     (Begin orbital bombardment)\n"
                f"  {c_magenta('[E]spionage Black Ops')}        (Deploy field operatives for covert action)\n"
                f"  {c_cyan('[V] Civilization & Elements')} (Scan indigenous taxon, tension & elemental veins)\n"
                f"  {c_gold('[B]ack to Orbit')}"
            )

        return "\n".join(lines)

    @classmethod
    def render_civilization_screen(cls, view: Dict[str, Any], planet: Dict[str, Any]) -> str:
        """Renders the Netstratum Taxon, Metabolic Tension, and Periodic Elements view."""
        player = view.get("player", {})
        civ = planet.get("civilization", {})
        if not civ:
            return c_red(f"No organized civilization recorded on {planet.get('name')}.")

        sigil = civ.get("sigil", "⬡")
        civ_name = civ.get("name", "Unknown")
        clade = civ.get("clade", "hypobiotid")
        meta = civ.get("metabolism", "biotic").upper()
        disp = civ.get("disposition", "empiricist").upper()
        station = civ.get("station", "unseated").upper()
        era = civ.get("era_name", "Progenitor Dawn")
        tech = civ.get("tech_level", 1)
        motto = civ.get("motto", "")
        proj = civ.get("current_project", "None")
        prog = civ.get("project_progress", 0)
        tension = civ.get("tension_vector", {})
        trade_urgency = civ.get("trade_urgency", {})

        deposits = planet.get("element_deposits", {})
        reserves = planet.get("element_reserves", {})
        cargo = player.get("ship", {}).get("cargo", {})
        ship_elems = cargo.get("elements", {})

        line_sep = c_blue("═" * 78)
        lines = [
            f"\n╔{line_sep}╗",
            (
                f"║ {c_cyan('NETSTRATUM CIVILIZATION & PERIODIC TABLE ALMANAC')} "
                f"│ Planet: {bold(c_white(planet.get('name', 'World')))} ║"
            ),
            f"╠{line_sep}╣",
            (
                f"║ Lineage: {bold(c_gold(f'{sigil} {civ_name}')):<24} "
                f"│ Clade: {c_white(clade):<18} "
                f"│ Station: {c_magenta(station):<14} ║"
            ),
            (
                f"║ Substrate: {c_gold(meta):<22} "
                f"│ Disposition: {c_cyan(disp):<12} "
                f"│ Era: {c_gold(era):<18} ║"
            ),
            f"║ Motto: \"{c_gray(motto[:68]):<68}\" ║",
            f"╠{line_sep}╣",
            (
                f"║ {bold(c_cyan('HOMOLOGICAL METABOLIC TENSION (δ = Demand - Supply):'))}{' ' * 27}║"
            ),
        ]

        if not tension or all(v == 0 for v in tension.values()):
            lines.append(f"║   Metabolic Tension: {c_green('● SATISFIED (Surplus directed to civic works & research)')}{' ' * 7}║")
        else:
            t_items = [f"{k}: +{v}" for k, v in tension.items() if v > 0]
            t_str = ", ".join(t_items)
            lines.append(f"║   Metabolic Tension: {c_red(f'▲ DEFICIT: {t_str}')}{' ' * max(1, 55 - len(t_str))}║")

        urgency_items = [f"{k}: {v}" for k, v in trade_urgency.items()]
        if urgency_items:
            urg_str = ", ".join(urgency_items)
            lines.append(f"║   Trade Demand Signal: {c_gold(f'{urg_str}')}{' ' * max(1, 53 - len(urg_str))}║")

        lines.append(f"╠{line_sep}╣")
        lines.append(f"║ {bold(c_cyan('PERIODIC TABLE OF ELEMENTS (5 AXES: LINE, LANE, SHELL, PHASE, SPIN)'))}{' ' * 8}║")
        lines.append(f"║   {'Element':<14} {'Axes (L/G/S/P/X)':<18} {'Binds':<7} {'Refines':<9} {'Reserves':<10} {'Veins':<8} ║")
        lines.append(f"║   {c_gray('-' * 72)} ║")

        # Combine all relevant elements
        all_elem_ids = sorted(list(set(list(deposits.keys()) + list(reserves.keys()) + civ.get("discovered_elements", []))))
        for eid in all_elem_ids:
            elem = PeriodicTable.get_element(eid)
            if elem:
                ename = elem.name[:13]
                axes = f"L{elem.line}/G{elem.lane}/S{elem.shell}/P{elem.phase}/{elem.spin}"
                binds = str(elem.binds)
                refines = f"{int(elem.refines_at * 100)}%"
                res = str(reserves.get(eid, 0))
                dep = str(deposits.get(eid, 0))
                lines.append(
                    f"║   {bold(c_white(ename)):<23} {c_cyan(axes):<27} {binds:<7} {refines:<9} {c_gold(res):<19} {c_gray(dep):<17} ║"
                )

        lines.append(f"╠{line_sep}╣")
        bar = _render_bar(prog, 100, length=12)
        lines.append(
            f"║ Active Civic Work: {c_gold(proj)} [{bar}] {prog}% │ Completed: {len(civ.get('civic_projects', {}))} Works{' ' * 8}║"
        )
        if civ.get("civic_projects"):
            done_works = ", ".join([f"{k} (x{v})" for k, v in civ.get("civic_projects", {}).items()])
            lines.append(f"║   Finished: {c_green(done_works[:66]):<74} ║")

        lines.append(f"╠{line_sep}╣")
        hold_elems_str = ", ".join([f"{k}:{v}" for k, v in ship_elems.items()]) if ship_elems else "Empty"
        lines.append(f"║ Ship Elemental Holds: {c_gold(hold_elems_str):<64} ║")
        lines.append(f"╚{line_sep}╝")
        lines.append(
            f"Options:\n"
            f"  {c_gold('[C]ontribute to Civic Works')} (Invest 50 Cr + 10 Ore -> +30% Progress)\n"
            f"  {c_gold('[L]oad Elements')}           (Transfer mined elements from planetary vault to ship)\n"
            f"  {c_gold('[O]ffload Elements')}        (Transfer elements from ship to planetary vault)\n"
            f"  {c_gold('[B]ack to Planetary Redoubt')}"
        )
        return "\n".join(lines)

    @classmethod
    def render_shipyard_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Federation Stardock Shipyard (Sector 1)."""
        player = view.get("player", {})
        ship = player.get("ship", {})
        cr = player.get("credits", 0)
        debt = player.get("debt", 0)
        turns = player.get("turns_left", 0)
        operatives = player.get("operatives", 0)
        ship_cfg = SHIP_CATALOG.get(ship.get("ship_type"), {})
        max_f = ship_cfg.get("max_fighters", 20)

        debt_str = f" │ Debt: {c_red(f'{debt:,} Cr')}" if debt > 0 else ""
        lines = [
            f"\n{bold(c_cyan('═══════════════ [ FEDERATION NAVAL SHIPYARD & STARDOCK ] ═══════════════'))}",
            f"Location: Sol Central (Sector 1) │ Credits: {c_gold(f'{cr:,} Cr')}{debt_str} │ Turns: {c_gold(str(turns))}",
            f"Current Ship: {c_white(ship.get('ship_type'))} (Shields: {ship.get('shields')}/{ship.get('max_shields')}, Fighters: {ship.get('fighters')}/{max_f}, Agents: {operatives})",
            "-" * 72,
            f"Maintenance & Services:",
            f"  {c_gold('[1]')} Recharge Energy Shields to 100% (3 Cr per MW needed)",
            f"  {c_gold('[2]')} Commission Combat Fighters (45 Cr/ea - Bay Cap: {ship.get('fighters')}/{max_f})",
            f"  {c_gold('[7]')} Federal Bank of Sol (Emergency Relief Loan / Debt Repayment)",
            f"  {c_gold('[8]')} Officer Quarters (Rest & Crew Replenishment: 1,000 Cr -> +50 Turns)",
            f"  {c_gold('[9]')} Intelligence Agency (Recruit Field Operatives: 500 Cr/ea - Ship Agents: {operatives})",
            "-" * 72,
            f"Available Hull Classes:",
        ]

        for idx, (s_name, s_data) in enumerate(SHIP_CATALOG.items(), start=3):
            price_str = f"{s_data['price']:,} Cr" if s_data['price'] > 0 else "Default"
            lines.append(
                f"  {c_gold(f'[{idx}]')} {bold(c_white(s_name)):<26} Price: {c_gold(price_str):<12} "
                f"Holds: {s_data['holds']:<4} Shields: {s_data['max_shields']:<5} Fighters: {s_data['max_fighters']}\n"
                f"      {c_gray(s_data['description'])}"
            )

        lines.append("-" * 72)
        lines.append(f"Select option number, [B]ank, [R]est, or {c_gold('[B]ack to Stardock')}:")
        return "\n".join(lines)

    @classmethod
    def render_nav_computer(cls, start: int, target: int, path: List[int]) -> str:
        """Renders BFS course plotting for the navigation computer."""
        lines = [
            f"\n{bold(c_cyan('═══════════════ [ HYPER-NAV COMPUTER BFS ] ═══════════════'))}",
            f"Current Sector: {start:03d}  │  Destination: {target:03d}",
        ]
        if not path:
            lines.append(c_red("NO VIABLE WARP PATH DETECTED! Sectors are disconnected."))
        else:
            warp_hops = len(path) - 1
            path_str = " -> ".join([c_gold(f"({s:03d})") for s in path])
            lines.append(f"Course plotted: {warp_hops} warp hops required ({warp_hops} turns):")
            lines.append(f"  {path_str}")
        lines.append("-" * 72)
        return "\n".join(lines)

    @classmethod
    def render_trade_routes_menu(cls, view: Dict[str, Any]) -> str:
        """Renders main Trade Route & Arbitrage Command Center menu."""
        player = view.get("player", {})
        sector = view.get("sector", {})
        s_id = sector.get("id", 1)
        credits = player.get("credits", 0)
        turns = player.get("turns_left", 0)
        cargo = player.get("ship", {}).get("cargo", {})
        free_holds = cargo.get("available", 0)

        line_sep = c_blue("═" * 78)
        lines = [
            f"\n╔{line_sep}╗",
            (
                f"║ {bold(c_cyan('HYPER-LANE TRADE ROUTE & ARBITRAGE OPTIMIZER'))} "
                f"│ Sector: {c_gold(f'{s_id:03d}')} │ Free Holds: {c_white(str(free_holds))} ║"
            ),
            (
                f"║ Credits: {c_gold(f'{credits:,} Cr')} │ Turns Remaining: {c_gold(str(turns))} "
                f"│ Engine: {c_green('ONLINE')} ║"
            ),
            f"╠{line_sep}╣",
            f"║  {c_gold('[1]')} All High-Yield Loops (Global scan across all 24+ commodities)       ║",
            f"║  {c_gold('[2]')} Volatiles & Gases (5x Density: H, He-3, C, H2O, Xe)                   ║",
            f"║  {c_gold('[3]')} Structural Metals & Ores (4x Density: Fe, Ti, Si, Ni, Cu, Ore)        ║",
            f"║  {c_gold('[4]')} Fissionables & Exotics (1x Density: U, Pt, SpR, Cryogenite, etc.)     ║",
            f"║  {c_gold('[5]')} Manufactured Components (1x Density: Equipment, M1-M4 Warp Cores)     ║",
            f"║  {c_gold('[6]')} Element-Specific Radar (Targeted corridor scan for specific element)  ║",
            f"║  {c_gold('[7]')} Local High-Yield Departures (Best Exports from Sector {s_id:03d})            ║",
            f"║  {c_gold('[8]')} Colony Supply Corridors (Ore / Organics for Your Outposts)            ║",
            f"║  {c_gold('[9]')} Interstellar Commodity Ticker (High/Low Market Spreads)               ║",
            f"║  {c_gold('[X]')} Return to Main Bridge Prompt                                          ║",
            f"╚{line_sep}╝"
        ]
        return "\n".join(lines)

    @classmethod
    def render_circular_arbitrage(cls, routes: List[Any], current_sec: int, title: Optional[str] = None) -> str:
        """Renders table of circular arbitrage loops."""
        line_sep = c_blue("═" * 78)
        header_title = title if title else "CIRCULAR ARBITRAGE RADAR: TOP CIRCUITS"
        lines = [
            f"\n{bold(c_cyan(f'══════════════ [ {header_title} ] ══════════════'))}",
            "Galaxy-wide 2-way trade circuits between paired ports. Enter route # to autopilot to Sector A:",
            f"╔{line_sep}╗",
        ]
        if not routes:
            lines.append(f"║ {c_red('No profitable trade loops detected within scan range.')}{' ' * 23}║")
        else:
            for idx, r in enumerate(routes, start=1):
                sec = r.security_summary
                if sec == "FEDERATION":
                    sec_badge = c_green("● FED SAFE")
                elif sec == "BORDERLAND":
                    sec_badge = c_gold("▲ BORDERLAND")
                else:
                    sec_badge = c_red("☠ ANARCHY")

                if current_sec == r.sector_a:
                    loc_badge = c_green(" [★ YOU ARE AT START PORT]")
                elif current_sec == r.sector_b:
                    loc_badge = c_gold(" [★ YOU ARE AT RETURN PORT]")
                else:
                    loc_badge = c_cyan(f" [Fly to Sector {r.sector_a:03d} to start]")

                route_title = (
                    f"║ {bold(c_gold(f'[{idx:02d}]'))} Sector {c_gold(f'{r.sector_a:03d}')} ({r.port_a_name[:16]}) "
                    f"◄── {c_cyan(f'{r.warp_hops} Hops ({r.round_trip_turns} Turns)')} ──► "
                    f"Sector {c_gold(f'{r.sector_b:03d}')} ({r.port_b_name[:16]}){loc_badge}"
                )
                lines.append(route_title)

                if r.leg_ab:
                    mult_ab = getattr(r.leg_ab, 'stack_multiplier', 1)
                    mult_tag = f" ({mult_ab}x Bulk)" if mult_ab > 1 else ""
                    lines.append(
                        f"║     ├─ Outbound: Buy {r.leg_ab.trade_units} {r.leg_ab.commodity}{mult_tag} @ {r.leg_ab.buy_price} Cr "
                        f"──► Sell @ {r.leg_ab.sell_price} Cr ({c_green(f'+{r.leg_ab.unit_margin} Cr/ea')} │ {c_gold(f'+{r.leg_ab.est_profit:,} Cr')})"
                    )
                if r.leg_ba:
                    mult_ba = getattr(r.leg_ba, 'stack_multiplier', 1)
                    mult_tag = f" ({mult_ba}x Bulk)" if mult_ba > 1 else ""
                    lines.append(
                        f"║     ├─ Return  : Buy {r.leg_ba.trade_units} {r.leg_ba.commodity}{mult_tag} @ {r.leg_ba.buy_price} Cr "
                        f"──► Sell @ {r.leg_ba.sell_price} Cr ({c_green(f'+{r.leg_ba.unit_margin} Cr/ea')} │ {c_gold(f'+{r.leg_ba.est_profit:,} Cr')})"
                    )

                path_str = "->".join([f"{s:03d}" for s in r.path])
                eff_stars = "★" * min(5, max(1, int(r.efficiency_cr_per_turn // 60)))
                lines.append(
                    f"║     └─ Route Profit: {c_gold(f'+{r.total_profit:,} Cr')} │ "
                    f"Yield: {c_green(f'{r.efficiency_cr_per_turn:.1f} Cr/Turn {eff_stars}')} │ [{sec_badge}]"
                )
                lines.append(f"║        Warp Path: {c_gray(path_str)}")
                if idx < len(routes):
                    lines.append(f"╟{c_gray('─' * 78)}╢")

        lines.append(f"╚{line_sep}╝")
        return "\n".join(lines)

    @classmethod
    def render_local_opportunities(cls, ops: List[Any], current_sec: int) -> str:
        """Renders immediate departure opportunities from current sector."""
        line_sep = c_blue("═" * 78)
        lines = [
            f"\n{bold(c_cyan(f'═══════════ [ HIGH-YIELD EXPORTS FROM SECTOR {current_sec:03d} ] ═══════════'))}",
            "Local port export inventory ranked by profit potential per turn:",
            f"╔{line_sep}╗",
        ]
        if not ops:
            lines.append(f"║ {c_red('No profitable export routes from this sector.')}{' ' * 32}║")
        else:
            for idx, op in enumerate(ops, start=1):
                sec = op.dest_security
                if sec == "FEDERATION":
                    sec_badge = c_green("● FED")
                elif sec == "BORDERLAND":
                    sec_badge = c_gold("▲ BORD")
                else:
                    sec_badge = c_red("☠ ANAR")

                mult = getattr(op, 'stack_multiplier', 1)
                mult_tag = f" ({mult}x Bulk)" if mult > 1 else ""
                units = getattr(op, 'trade_units', 30)

                lines.append(
                    f"║ {bold(c_gold(f'[{idx:02d}]'))} Export {units} {c_cyan(op.commodity)}{mult_tag}: Buy @ {op.buy_price} Cr "
                    f"──► Dest: Sector {c_gold(f'{op.dest_sector:03d}')} ({op.dest_port_name[:18]})"
                )
                lines.append(
                    f"║     Sell @ {op.sell_price} Cr ({c_green(f'+{op.unit_margin} Cr/ea')}) │ "
                    f"Hops: {op.warp_hops} ({op.turns} Turns) │ [{sec_badge}]"
                )
                lines.append(
                    f"║     Net Profit: {c_gold(f'+{op.est_profit:,} Cr')} │ "
                    f"Efficiency: {c_green(f'{op.efficiency_cr_per_turn:.1f} Cr/Turn')} │ "
                    f"Path: {c_gray('->'.join([f'{s:03d}' for s in op.path]))}"
                )
                if idx < len(ops):
                    lines.append(f"╟{c_gray('─' * 78)}╢")

        lines.append(f"╚{line_sep}╝")
        return "\n".join(lines)

    @classmethod
    def render_colony_supply_routes(cls, runs: List[Any]) -> str:
        """Renders supply routes for player-owned colonies."""
        line_sep = c_blue("═" * 78)
        lines = [
            f"\n{bold(c_cyan('═══════════════ [ PLANETARY COLONY SUPPLY CORRIDORS ] ═══════════════'))}",
            "Closest suppliers of Ore (Citadel/Shields) and Organics (Population Growth):",
            f"╔{line_sep}╗",
        ]
        if not runs:
            lines.append(f"║ {c_red('No colonies under your sovereignty or no accessible suppliers.')}{' ' * 13}║")
        else:
            for idx, r in enumerate(runs, start=1):
                sec = r.security_summary
                if sec == "FEDERATION":
                    sec_badge = c_green("● FED")
                elif sec == "BORDERLAND":
                    sec_badge = c_gold("▲ BORD")
                else:
                    sec_badge = c_red("☠ ANAR")

                lines.append(
                    f"║ {bold(c_gold(f'[{idx:02d}]'))} Colony: {c_white(r.planet_name)} (Sector {r.planet_sector:03d}) "
                    f"◄── Target Resource: {c_cyan(r.resource_needed)}"
                )
                lines.append(
                    f"║     Supplier: Sector {c_gold(f'{r.source_sector:03d}')} ({r.source_port_name[:20]}) "
                    f"@ {c_gold(f'{r.buy_price} Cr/ea')} (In Stock: {r.available_stock})"
                )
                lines.append(
                    f"║     Transit: {r.warp_hops} Hops ({r.turn_cost} Turns) │ [{sec_badge}] │ "
                    f"Trajectory: {c_gray('->'.join([f'{s:03d}' for s in r.path]))}"
                )
                if idx < len(runs):
                    lines.append(f"╟{c_gray('─' * 78)}╢")

        lines.append(f"╚{line_sep}╝")
        return "\n".join(lines)

    @classmethod
    def render_galactic_ticker(cls, spreads: List[Any]) -> str:
        """Renders interstellar commodity ticker and highest spreads."""
        line_sep = c_blue("═" * 78)
        lines = [
            f"\n{bold(c_cyan('═════════════ [ INTERSTELLAR COMMODITY MARKET TICKER ] ═════════════'))}",
            "Galactic Best Ask (Lowest Sell Price) vs Best Bid (Highest Buy Price):",
            f"╔{line_sep}╗",
        ]
        for s in spreads:
            lines.append(f"║ Commodity: {bold(c_white(s.commodity))}")
            lines.append(
                f"║   Best Ask: {c_green(f'{s.lowest_sell_price} Cr')} @ Sector {s.lowest_sell_sector:03d} ({s.lowest_sell_port[:22]})"
            )
            lines.append(
                f"║   Best Bid: {c_gold(f'{s.highest_buy_price} Cr')} @ Sector {s.highest_buy_sector:03d} ({s.highest_buy_port[:22]})"
            )
            lines.append(
                f"║   Spread  : {bold(c_green(f'+{s.gross_spread} Cr/unit'))} │ Distance: {s.warp_hops} Hops │ "
                f"Course: {c_gray('->'.join([f'{sec:03d}' for sec in s.path]))}"
            )
            lines.append(f"╟{c_gray('─' * 78)}╢")
        lines[-1] = f"╚{line_sep}╝"
        return "\n".join(lines)

    @classmethod
    def render_stock_market_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Interstellar Securities & Stock Exchange (ISSE) board."""
        market = view.get("market", {})
        companies = market.get("companies", [])
        portfolio = market.get("portfolio", {})
        cycle = view.get("cycle", 0)
        quarter = market.get("fiscal_quarter", 1)
        cycles_left = market.get("cycles_to_dividend", 25)
        player = view.get("player", {})
        cash = player.get("credits", 0)

        # Calculate portfolio value
        total_equity_val = 0
        comp_map = {c["ticker"]: c for c in companies}
        for ticker, shares in portfolio.items():
            if ticker in comp_map:
                total_equity_val += shares * comp_map[ticker]["share_price"]
        net_worth = cash + total_equity_val

        line_sep = c_blue("═" * 78)
        lines = [
            f"\n{bold(c_cyan('══════════════ [ INTERSTELLAR SECURITIES & STOCK EXCHANGE (ISSE) ] ══════════════'))}",
            f"Universal Clock (GST): Cycle {c_white(str(cycle))} │ Financial Quarter: {c_gold(f'Q{quarter}')} │ Next Dividend: in {c_cyan(f'{cycles_left} Cycles')}",
            f"Cash Treasury: {c_gold(f'{cash:,} Cr')} │ Equity Portfolio: {c_green(f'{total_equity_val:,} Cr')} │ Total Net Worth: {bold(c_gold(f'{net_worth:,} Cr'))}",
            f"╔{line_sep}╗",
            f"║ {bold('TICK')} │ {bold('COMPANY NAME / HQ')}               │ {bold('INDUSTRY')}   │ {bold('PRICE')}   │ {bold('3-CYC')} │ {bold('FLOAT / CAP')}      ║",
            f"╠{line_sep}╣",
        ]

        if not companies:
            lines.append(f"║ {c_red('No corporate entities currently listed on the ISSE.')}{' ' * 24}║")
        else:
            for c in companies:
                ticker = c["ticker"]
                name = c["name"][:25]
                sec_id = c["sector_id"]
                planet = c["planet_name"][:12]
                ind = c["industry"][:11]
                price = c["share_price"]
                hist = c.get("price_history", [price])
                if len(hist) >= 2:
                    delta = price - hist[-2]
                    delta_str = c_green(f"+{delta}") if delta > 0 else (c_red(f"{delta}") if delta < 0 else c_gray("="))
                else:
                    delta_str = c_gray("=")

                avail = c.get("available_shares", 0)
                tot = c.get("total_shares", 10000)
                mcap = c.get("market_cap", price * tot)

                line1 = (
                    f"║ {bold(c_gold(f'{ticker:4s}'))} │ {c_white(f'{name:25s}')} │ {c_cyan(f'{ind:11s}')} │ "
                    f"{c_gold(f'{price:5d} Cr')} │ {delta_str:^5s} │ Float: {avail:5d}/{tot:5d} ║"
                )
                level_str = c.get("level_title", "Syndicate")[:20]
                div_pct = int(c.get("dividend_rate", 0.08) * 100)
                line2 = (
                    f"║      └─ HQ: Sec {sec_id:03d} ({planet}) │ Tier {c.get('level', 1)}: {level_str:18s} │ "
                    f"Cap: {c_green(f'{mcap:,} Cr')} │ Div: {c_gold(f'{div_pct}%')} ║"
                )
                lines.append(line1)
                lines.append(line2)
                lines.append(f"╟{c_gray('─' * 78)}╢")
            lines[-1] = f"╠{line_sep}╣"

        # Captain's Portfolio Section
        lines.append(f"║ {bold(c_cyan('CAPTAIN EQUITY HOLDINGS & DIVIDEND YIELDS:'))}{' ' * 36}║")
        if not portfolio:
            lines.append(f"║ {c_gray('You hold 0 equity shares. Buy shares from open market float below.')}{' ' * 13}║")
        else:
            for ticker, shares in portfolio.items():
                comp = comp_map.get(ticker)
                if comp:
                    tot_shares = comp.get("total_shares", 10000)
                    pct_owned = (shares / tot_shares) * 100
                    pos_val = shares * comp["share_price"]
                    est_div = shares * max(1, comp.get("last_dividend", 2))
                    lines.append(
                        f"║  ● {bold(c_gold(f'{ticker}'))} ({comp['name'][:22]}): {c_white(f'{shares:,} Shares')} "
                        f"({c_green(f'{pct_owned:.1f}% stake')}) │ Valuation: {c_gold(f'{pos_val:,} Cr')} │ "
                        f"Est Div: {c_green(f'+{est_div:,} Cr/Qtr')} ║"
                    )

        # Captain's Short Positions Section
        short_positions = market.get("short_positions", {})
        if short_positions:
            lines.append(f"╠{line_sep}╣")
            lines.append(f"║ {bold(c_magenta('ACTIVE SHORT POSITIONS & MARGIN COLLATERAL (BEAR RAIDS):'))}{' ' * 19}║")
            for ticker, pos in short_positions.items():
                comp = comp_map.get(ticker)
                sh_count = pos.get("shares", 0)
                entry_p = pos.get("entry_price", 0)
                cur_p = comp["share_price"] if comp else entry_p
                collat = pos.get("collateral", 0)
                unrealized_pnl = (entry_p - cur_p) * sh_count
                pnl_str = c_green(f"+{unrealized_pnl:,} Cr") if unrealized_pnl >= 0 else c_red(f"{unrealized_pnl:,} Cr")
                lines.append(
                    f"║  ▼ {bold(c_magenta(ticker))} Short: {c_white(f'{sh_count:,} shs')} @ {c_gold(f'{entry_p} Cr')} "
                    f"│ Current: {c_gold(f'{cur_p} Cr')} │ Margin: {c_cyan(f'{collat:,} Cr')} │ Net P&L: {pnl_str} ║"
                )

        lines.append(f"╚{line_sep}╝")
        return "\n".join(lines)

    @classmethod
    def render_freight_board_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Galactic Freight Haulage & Star Courier listings."""
        market = view.get("market", {})
        open_contracts = market.get("open_contracts", [])
        active_contracts = market.get("active_contracts", [])
        curr_sector = view.get("sector", {}).get("id", 1)
        player = view.get("player", {})
        cargo = player.get("ship", {}).get("cargo", {})
        free_holds = cargo.get("available", 0)

        line_sep = c_blue("═" * 78)
        lines = [
            f"\n{bold(c_cyan('═════════════ [ GALACTIC FREIGHT HAULAGE & STAR COURIER BOARD ] ═════════════'))}",
            f"Docked at Sector: {c_gold(f'{curr_sector:03d}')} │ Free Cargo Holds: {c_cyan(str(free_holds))} │ Active Contracts: {c_gold(f'{len(active_contracts)}/3')}",
            f"╔{line_sep}╗",
        ]

        if active_contracts:
            lines.append(f"║ {bold(c_green('ACTIVE IN-TRANSIT MANIFESTS:'))}{' ' * 49}║")
            for c in active_contracts:
                cid = c["id"]
                ticker = c["company_ticker"]
                orig_sec = c["origin_sector"]
                dest_sec = c["destination_sector"]
                dest_name = c["destination_name"][:18]
                comm = c["commodity"]
                amt = c["amount"]
                payout = c["payout_credits"]
                shares = c.get("shares_reward", 0)

                lines.append(
                    f"║  ★ [{bold(c_gold(cid))}] Cargo: {c_cyan(f'{amt} {comm}')} │ Client: {c_white(ticker)} │ "
                    f"Origin: Sec {orig_sec:03d} ──► Dest: Sec {dest_sec:03d} ({dest_name})"
                )
                lines.append(
                    f"║      Bounty: {c_gold(f'+{payout:,} Cr')} + {c_green(f'{shares} Shares of {ticker}')} upon colony delivery."
                )
                lines.append(f"╟{c_gray('─' * 78)}╢")
            if not open_contracts:
                lines[-1] = f"╚{line_sep}╝"
            else:
                lines[-1] = f"╠{line_sep}╣"

        lines.append(f"║ {bold(c_cyan('AVAILABLE FREIGHT CONTRACTS POSTED BY POPULATION ENTERPRISES:'))}{' ' * 16}║")
        if not open_contracts:
            lines.append(f"║ {c_red('No open star freight contracts currently available across the sector net.')}{' ' * 7}║")
        else:
            for idx, c in enumerate(open_contracts, start=1):
                cid = c["id"]
                ticker = c["company_ticker"]
                orig_sec = c["origin_sector"]
                orig_name = c["origin_name"][:16]
                dest_sec = c["destination_sector"]
                dest_name = c["destination_name"][:16]
                comm = c["commodity"]
                amt = c["amount"]
                payout = c["payout_credits"]
                shares = c.get("shares_reward", 0)
                hazard = c.get("hazard_level", "FEDERATION")

                if hazard == "FEDERATION":
                    haz_badge = c_green("● FED")
                elif hazard == "BORDERLAND":
                    haz_badge = c_gold("▲ BORD")
                else:
                    haz_badge = c_red("☠ ANAR")

                can_pickup = (curr_sector == orig_sec)
                pickup_badge = c_green("[PICKUP HERE]") if can_pickup else c_gray(f"[Sec {orig_sec:03d}]")

                lines.append(
                    f"║ {bold(c_gold(f'[{idx:02d}]'))} {bold(cid)} ({ticker}) │ Haul: {c_cyan(f'{amt:2d} {comm}')} │ Route: Sec {orig_sec:03d} ({orig_name}) ──► Sec {dest_sec:03d} ({dest_name})"
                )
                lines.append(
                    f"║     Reward: {c_gold(f'+{payout:,} Cr')} + {c_green(f'{shares:2d} {ticker} Shares')} │ Zone: [{haz_badge}] │ {pickup_badge}"
                )
                if idx < len(open_contracts):
                    lines.append(f"╟{c_gray('─' * 78)}╢")

        lines.append(f"╚{line_sep}╝")
        lines.append(f"{c_gray('NOTE: To accept freight, dock at Origin Sector with free cargo holds. Deliver to destination colony.')}")
        return "\n".join(lines)

    @classmethod
    def render_boardroom_screen(cls, view: Dict[str, Any], target_ticker: str = "") -> str:
        """Renders the ISSE Corporate Boardroom & Executive Governance Terminal."""
        market = view.get("market", {})
        companies = market.get("companies", [])
        portfolio = market.get("portfolio", {})
        player = view.get("player", {})
        player_id = player.get("id", "player_1")

        comp_map = {c["ticker"]: c for c in companies}
        ticker = target_ticker.upper() if target_ticker else ""
        if not ticker or ticker not in comp_map:
            # Pick first company owned, or first listed
            owned = [t for t in portfolio if t in comp_map]
            ticker = owned[0] if owned else (companies[0]["ticker"] if companies else "VOSS")

        comp = comp_map.get(ticker)
        line_sep = c_blue("═" * 78)

        if not comp:
            return f"\n{c_red('No company data found on the ISSE.')}\n"

        name = comp["name"]
        hq_sec = comp["sector_id"]
        hq_planet = comp["planet_name"]
        ind = comp["industry"]
        price = comp["share_price"]
        tot_shares = comp["total_shares"]
        avail_shares = comp["available_shares"]
        treasury = comp["treasury"]
        chairman = comp.get("chairman_id", comp.get("founder_id", "Unknown"))
        is_chairman = (chairman == player_id)

        player_shares = portfolio.get(ticker, 0)
        ownership_pct = (player_shares / tot_shares) * 100 if tot_shares > 0 else 0.0
        float_pct = (avail_shares / tot_shares) * 100 if tot_shares > 0 else 0.0
        insider_shares = max(0, tot_shares - avail_shares - player_shares)
        insider_pct = (insider_shares / tot_shares) * 100 if tot_shares > 0 else 0.0

        if is_chairman:
            status_badge = c_green("★ EXECUTIVE CHAIRMAN (BOARD IN CONTROL) ★")
        elif ownership_pct > 50.0:
            status_badge = c_gold("▲ MAJORITY STAKE (>50%) - TAKEOVER ELIGIBLE ▲")
        elif ownership_pct >= 25.0:
            status_badge = c_cyan("◆ HOSTILE PROXY CHALLENGER (25%-50%) ◆")
        else:
            status_badge = c_gray("○ MINORITY SHAREHOLDER (<25%) ○")

        pill_uses = comp.get("poison_pill_uses", 1)
        pill_status = c_green(f"ARMED ({pill_uses} left)") if pill_uses > 0 else c_red("EXPENDED")
        embargoes = comp.get("embargoed_captains", [])
        embargo_str = ", ".join(embargoes) if embargoes else "None"
        mcap_val = comp.get("market_cap", price * tot_shares)
        spec_div = comp.get("special_dividends_paid", 0)

        trust = comp.get("consumer_trust", 80)
        exec_count = len(comp.get("sales_executives", []))
        pens = comp.get("market_penetration", {})
        if pens:
            top_pens = sorted(pens.items(), key=lambda x: x[1], reverse=True)[:3]
            pen_summary = ", ".join(f"Sec {int(s):03d}: {p:.0f}%" for s, p in top_pens)
        else:
            pen_summary = f"Sec {hq_sec:03d}: 30%"

        lines = [
            f"\n{bold(c_cyan('═════════ [ ISSE CORPORATE BOARDROOM & EXECUTIVE GOVERNANCE ] ═════════'))}",
            f"Target Corporation: {bold(c_gold(f'{name} ({ticker})'))} │ HQ: Sector {hq_sec:03d} ({hq_planet})",
            f"Industry Focus: {c_white(ind)} │ Share Price: {c_gold(f'{price} Cr')} │ Market Cap: {c_green(f'{mcap_val:,} Cr')}",
            f"Governance Status: [{status_badge}]",
            f"Executive Chairman: {bold(c_white(chairman))} {'(YOU)' if is_chairman else ''}",
            f"╔{line_sep}╗",
            f"║ {bold(c_cyan('EQUITY & VOTING POWER BREAKDOWN:'))}{' ' * 45}║",
            f"║  ● Your Stake     : {c_gold(f'{player_shares:,} Shares')} ({c_green(f'{ownership_pct:.1f}%')} voting control)",
            f"║  ● Public Float   : {c_white(f'{avail_shares:,} Shares')} ({c_white(f'{float_pct:.1f}%')} circulating float)",
            f"║  ● Management/Core: {c_white(f'{insider_shares:,} Shares')} ({c_white(f'{insider_pct:.1f}%')} loyalist block)",
            f"║  ● Total Shares   : {tot_shares:,} Shares │ Treasury Balance: {c_gold(f'{treasury:,} Cr')} ║",
            f"╠{line_sep}╣",
            f"║ {bold(c_cyan('ANTI-TAKEOVER DEFENSES & BOARDROOM METRICS:'))}{' ' * 33}║",
            f"║  ● Poison Pill Dilution: [{pill_status}]",
            f"║  ● Active Embargoes    : {c_red(embargo_str)}",
            f"║  ● Special Div Paid    : {c_gold(f'{spec_div:,} Cr')}",
            f"║  ● Consumer Trust      : {c_green(f'{trust}%') if trust >= 60 else c_red(f'{trust}%')} (Brand Reputation)",
            f"║  ● Sales Executives    : {c_cyan(str(exec_count))} stationed agents",
            f"║  ● Market Penetration  : {c_gold(pen_summary)}",
            f"╚{line_sep}╝",
        ]
        return "\n".join(lines)

    @classmethod
    def render_corporate_machine_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Corporate Machine command deck: Executives, Marketing PR, and Trade Council."""
        market = view.get("market", {})
        companies = market.get("companies", [])
        my_execs = market.get("executives", [])
        trade_council = market.get("trade_council", {})
        player = view.get("player", {})
        player_id = player.get("id", "player_1")

        line_sep = c_blue("═" * 78)
        player_credits = player.get("credits", 0)
        lines = [
            f"\n{bold(c_cyan('══════════════ [ THE CORPORATE MACHINE: INDUSTRIAL CONGLOMERATE ] ══════════════'))}",
            f"Universal Clock: Cycle {c_white(str(view.get('cycle', 0)))} │ Liquid Treasury: {c_gold(f'{player_credits:,} Cr')}",
            f"╔{line_sep}╗",
            f"║ {bold(c_cyan('PHASE 1: SALES EXECUTIVES & REGIONAL MARKET PENETRATION'))}{' ' * 23}║",
        ]

        if not my_execs:
            lines.append(f"║ {c_gray('No Sales Executives currently contracted. Hire executives to capture market share.')}{' ' * 1}║")
        else:
            for ex in my_execs:
                eid = ex.get("id", "EXEC-?")
                name = ex.get("name", "Executive")[:18]
                ticker = ex.get("company_ticker", "CORP")
                sec = ex.get("sector_id", 1)
                salary = ex.get("salary", 500)
                lines.append(
                    f"║  ★ [{bold(c_gold(eid))}] {c_white(name)} │ Corp: {bold(c_gold(ticker))} │ "
                    f"Stationed: Sec {sec:03d} │ Salary: {c_gold(f'{salary} Cr/cyc')} ║"
                )

        lines.append(f"╠{line_sep}╣")
        lines.append(f"║ {bold(c_cyan('PHASE 2: MARKETING DEPARTMENTS & PUBLIC RELATIONS CAMPAIGNS'))}{' ' * 19}║")
        controlled = [c for c in companies if c.get("chairman_id") == player_id or c.get("founder_id") == player_id]
        if not controlled:
            lines.append(f"║ {c_gray('You do not chair a corporate board. Take over or float an IPO to access PR.')}{' ' * 1}║")
        else:
            for c in controlled:
                t = c["ticker"]
                trust = c.get("consumer_trust", 80)
                trust_bar = _render_bar(trust, 100, length=10)
                t_color = c_green if trust >= 60 else (c_gold if trust >= 40 else c_red)
                lines.append(
                    f"║  ● {bold(c_gold(t))} PR Trust: {t_color(f'{trust_bar} {trust}%')} │ "
                    f"Positive Campaign: {c_green('+PR / +Share Price')} │ Smear: {c_red('Sabotage Rival')} ║"
                )

        lines.append(f"╠{line_sep}╣")
        lines.append(f"║ {bold(c_cyan('PHASE 3: INTERSTELLAR TRADE COUNCIL & REGULATORY LOBBYING'))}{' ' * 20}║")
        funds = trade_council.get("lobbying_funds", {})
        my_influence = funds.get(player_id, 0)
        active_bills = trade_council.get("active_resolutions", [])

        lines.append(
            f"║  Lobbying Pool Influence: {c_gold(f'{my_influence:,} Credits')} "
            f"(Min 2,500 Cr required to enact Senate bills){' ' * 1}║"
        )
        if not active_bills:
            lines.append(f"║  Active Interstellar Legislation: {c_gray('No active bills currently enacted.')}{' ' * 17}║")
        else:
            for bill in active_bills:
                b_type = bill.get("bill_type", "BILL")
                sponsor = bill.get("sponsor", "Unknown")
                target = bill.get("target", "None")
                dur = bill.get("duration", 0)
                lines.append(
                    f"║   ⚖ [{bold(c_cyan(b_type))}] Sponsor: {c_gold(sponsor)} │ Target: {c_red(target or 'Sector Net')} │ "
                    f"Sunset: in {c_white(str(dur))} cycles ║"
                )

        lines.append(f"╚{line_sep}╝")
        return "\n".join(lines)

    @classmethod
    def render_empire_console(cls, view: Dict[str, Any]) -> str:
        """Renders the Imperial Dominion & Asset Registry Console."""
        player = view.get("player", {})
        planets = view.get("owned_planets", [])
        haulers = view.get("trade_haulers", [])
        credits = player.get("credits", 0)
        cycle = view.get("cycle", 0)

        total_pop = sum(p.get("population", 0) for p in planets)
        total_vault = sum(p.get("treasury", 0) for p in planets)
        total_hauler_profit = sum(h.get("lifetime_profit", 0) for h in haulers)
        total_hauler_trips = sum(h.get("trips_completed", 0) for h in haulers)

        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ IMPERIAL DOMINION & ASSET REGISTRY CONSOLE'))}          {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            (
                f"{bold(c_gold('║'))}  Universal Cycle: {c_white(str(cycle))} │ Sovereign Colonies: {c_gold(str(len(planets)))} "
                f"│ Total Population: {c_green(f'{total_pop:,}')}  {bold(c_gold('║'))}"
            ),
            (
                f"{bold(c_gold('║'))}  Liquid Credits: {c_gold(f'{credits:,} Cr')} │ Uncollected Vault Taxes: {c_green(f'{total_vault:,} Cr')}  {bold(c_gold('║'))}"
            ),
            (
                f"{bold(c_gold('║'))}  Merchant Haulers: {c_cyan(str(len(haulers)))} │ Fleet Lifetime Yield: {c_gold(f'+{total_hauler_profit:,} Cr')} ({total_hauler_trips} runs) {bold(c_gold('║'))}"
            ),
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
        ]

        # Section 1: Sovereign Planetary Colonies
        lines.append(f"\n{bold(c_cyan('──[ SOVEREIGN PLANETARY DOMINIONS & COLONIES ]' + '─' * 33))}")
        if not planets:
            lines.append(f"  {c_gray('No colonized planets under your imperial flag.')}")
            lines.append(f"  {c_gray('Fly to unclaimed worlds (command [P]lanet) to establish planetary outposts.')}")
        else:
            for p in planets:
                p_id = p.get("id", "?")
                p_name = p.get("name", "Planet")
                sec_id = p.get("sector_id", 1)
                sec_name = p.get("sector_name", "Deep Void")
                lvl = p.get("citadel_level", 0)
                cfg = CITADEL_CONFIG.get(lvl, {})
                title = cfg.get("title", "Unfortified")
                pop = p.get("population", 0)
                morale = p.get("morale", 100)
                shld = p.get("shields", 0)
                m_shld = p.get("max_shields", 100)
                fgt = p.get("fighters", 0)
                m_fgt = p.get("max_fighters", 50)
                vault = p.get("treasury", 0)
                ore_s = p.get("ore_stock", 0)
                org_s = p.get("organics_stock", 0)
                eq_s = p.get("equipment_stock", 0)
                tariff = p.get("sector_tariff_pct", 0)

                shld_bar = _render_bar(shld, m_shld, length=6)
                m_color = c_green if morale >= 75 else (c_gold if morale >= 40 else c_red)
                tariff_str = f" │ Tariff: {c_red(f'{tariff}%')}" if tariff > 0 else ""

                lines.append(
                    f"  ★ {bold(c_white(p_name))} [{c_gold(f'Sector {sec_id:03d}')}: {c_cyan(sec_name)}] "
                    f"│ Tier {lvl}: {bold(c_gold(title))}{tariff_str}"
                )
                lines.append(
                    f"    Pop: {c_white(f'{pop:,}')} │ Morale: {m_color(f'{morale}%')} "
                    f"│ Shields: {c_cyan(f'{shld_bar} {shld}/{m_shld}')} │ Fighters: {c_red(f'{fgt}/{m_fgt}')}"
                )
                lines.append(
                    f"    Vault Taxes: {c_green(f'{vault:,} Cr')} │ "
                    f"Silos: Ore:{c_gold(str(ore_s))} Org:{c_green(str(org_s))} Eq:{c_magenta(str(eq_s))}"
                )
                lines.append(c_gray("    " + "─" * 72))

        # Section 2: Automated Merchant Fleet
        lines.append(f"\n{bold(c_cyan('──[ AUTOMATED MERCHANT FLEET & TRADE HAULERS ]' + '─' * 31))}")
        if not haulers:
            lines.append(f"  {c_gray('No automated merchant haulers commissioned.')}")
            lines.append(f"  {c_gray('Commission haulers (Cost: 4,000 Cr) to run autonomous circular trade routes!')}")
        else:
            for h in haulers:
                h_id = h.get("id", "HAUL-?")
                h_name = h.get("name", "Hauler")
                orig = h.get("origin_sector", 1)
                dest = h.get("dest_sector", 30)
                c_out = h.get("commodity_outbound", "EQUIPMENT")
                c_ret = h.get("commodity_return", "ORGANICS")
                cap = h.get("capacity", 50)
                profit = h.get("lifetime_profit", 0)
                trips = h.get("trips_completed", 0)
                active = h.get("active", True)
                status_str = c_green("[ACTIVE YIELD]") if active else c_red("[OFFLINE]")

                lines.append(
                    f"  ► [{bold(c_gold(h_id))}] {bold(c_white(h_name))} {status_str} │ Cap: {c_cyan(f'{cap} Holds')}"
                )
                lines.append(
                    f"    Route: {c_gold(f'Sector {orig:03d}')} ◄──► {c_gold(f'Sector {dest:03d}')} "
                    f"({c_cyan(c_out)} / {c_magenta(c_ret)})"
                )
                lines.append(
                    f"    Trips Completed: {c_white(str(trips))} │ Lifetime Yield: {c_gold(f'+{profit:,} Cr')}"
                )
                lines.append(c_gray("    " + "─" * 72))

        # Section 3: Summary / Actions
        lines.append(f"\n{c_cyan('Dominion Operations:')}")
        lines.append(
            f"  {c_gold('[T]')} Remote Tax Harvest (Harvest all colony vaults)  "
            f"{c_gold('[W]')} Warp Course to Colony"
        )
        lines.append(
            f"  {c_gold('[C]')} Commission Trade Hauler (4,000 Cr)             "
            f"{c_gold('[R]')} Reassign Hauler Route"
        )
        lines.append(
            f"  {c_gold('[D]')} Decommission Trade Hauler (Scrap for 2,000 Cr)  "
            f"{c_gold('[Q]')} Return to Main Dispatch"
        )
        return "\n".join(lines)

    @classmethod
    def render_tech_tree_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Two-Tier Cognitive Economy & Breakthrough Tech Tree."""
        tech_tree = view.get("tech_tree", {})
        unlocked = set(view.get("unlocked_techs", []))
        active_tech = view.get("active_research")
        progress = view.get("research_progress", 0)

        lines = [
            bold(c_cyan("╔══════════════════════════════════════════════════════════════════════════════╗")),
            bold(c_cyan("║            TWO-TIER COGNITIVE ECONOMY & BREAKTHROUGH TECH TREE               ║")),
            bold(c_cyan("╚══════════════════════════════════════════════════════════════════════════════╝")),
            f"  {c_gold('Tier 1 (Rations - Ore & Organics):')} Powers basic biological survival and hull industry.",
            f"  {c_magenta('Tier 2 (Leisure & Exotics):')} Refined elements (Cryogenite, Umbrite, Chitinium,",
            f"  Stelalith, Ferrolattice) fuel Deep Cognition, generating Research Points (RP).\n",
        ]

        if active_tech and active_tech in tech_tree:
            cfg = tech_tree[active_tech]
            cost = cfg.get("cost_research", 100)
            bar = _render_bar(progress, cost, length=18)
            pct = int((progress / cost) * 100) if cost > 0 else 0
            lines.append(f"  {bold(c_cyan('ACTIVE RESEARCH PROJECT:'))} {c_gold(cfg['name'])} ({cfg.get('icon', '⚡')})")
            lines.append(f"    Progress: {c_cyan(bar)} {c_white(f'{progress}/{cost} RP ({pct}%)')}")
            lines.append(f"    Catalyst Element: {c_magenta(cfg.get('cost_element', '').capitalize())}\n")
        else:
            lines.append(f"  {c_gray('ACTIVE RESEARCH: None commissioned. Select a breakthrough project below.')}\n")

        lines.append(bold(c_white("  [ AVAILABLE BREAKTHROUGH TECHNOLOGIES ]")))
        lines.append(c_gray("  " + "─" * 74))

        for idx, (t_key, t_info) in enumerate(tech_tree.items(), 1):
            icon = t_info.get("icon", "★")
            t_name = t_info.get("name", t_key)
            cost_rp = t_info.get("cost_research", 100)
            elem = t_info.get("cost_element", "crystal").capitalize()
            desc = t_info.get("description", "")

            if t_key in unlocked:
                status_tag = c_green("[UNLOCKED / ACTIVE]")
            elif t_key == active_tech:
                status_tag = c_cyan(f"[IN PROGRESS - {progress}/{cost_rp} RP]")
            else:
                status_tag = c_gold(f"[{idx}] COMMISSION ({cost_rp} RP, {elem})")

            lines.append(f"  {c_magenta(icon)} {bold(c_white(t_name))} {status_tag}")
            lines.append(f"     {c_gray(desc)}")
            lines.append(c_gray("  " + "─" * 74))

        return "\n".join(lines)

    @classmethod
    def render_anomaly_screen(cls, view: Dict[str, Any], anomaly: Dict[str, Any]) -> str:
        """Renders interactive anomaly investigation briefing and sensor decoding data."""
        sec_id = anomaly.get("sector_id", 0)
        rew_cr = anomaly.get("reward_credits", 0)
        rew_rp = anomaly.get("reward_research", 0)
        rew_tech = str(anomaly.get("reward_tech", "None"))
        rew_elems = str(anomaly.get("reward_elements", {}))
        target_freq = anomaly.get("puzzle_target", 42)

        lines = [
            bold(c_magenta("╔══════════════════════════════════════════════════════════════════════════════╗")),
            bold(c_magenta("║                    COSMIC ANOMALY INVESTIGATION MATRIX                       ║")),
            bold(c_magenta("╚══════════════════════════════════════════════════════════════════════════════╝")),
            f"  Relic Designation: {bold(c_white(anomaly.get('name', 'Unknown')))} [{c_gold(anomaly.get('id', ''))}]",
            f"  Sector Location  : {c_gold(f'Sector {sec_id:03d}')}",
            f"  Anomaly Type     : {c_cyan(anomaly.get('anomaly_type', '').replace('_', ' '))}",
            f"  Puzzle Protocol  : {c_magenta(anomaly.get('puzzle_type', '').replace('_', ' '))}",
            f"  Status           : {c_green(anomaly.get('status', 'UNDISCOVERED'))}",
            f"  Description      : {c_gray(anomaly.get('description', ''))}\n",
            bold(c_cyan("  [ SENSOR REWARD TELEMETRY ]")),
            f"  • Credits Bounty   : {c_gold(f'+{rew_cr:,} Cr')}",
            f"  • Research Yield   : {c_cyan(f'+{rew_rp} RP')}",
            f"  • Tech Blueprint   : {c_magenta(rew_tech)}",
            f"  • Exotic Elements  : {c_gold(rew_elems)}\n",
            bold(c_white("  [ INVESTIGATION DECODING OPTIONS ]")),
            f"  {c_gold('[1]')} Calibrate Harmonic Frequency (Target: {target_freq})",
            f"  {c_gold('[2]')} Deploy Sensor Computation Probe (1,000 Credits Catalyst)",
            f"  {c_gold('[B]')} Return to Sector Bridge\n",
        ]
        return "\n".join(lines)

    @classmethod
    def render_cartography_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Cartography Lab & Starmap Puzzle Decryption Matrix."""
        cart_info = view.get("cartography", {})
        puzzle = cart_info.get("active_puzzle")
        fragments = cart_info.get("fragments", [])
        unlocked_secrets = cart_info.get("unlocked_secrets", [])
        all_puzzles = cart_info.get("all_puzzles", [])

        lines = []
        p_name = puzzle.get("name", "Starmap Decryption Matrix") if puzzle else "NO ACTIVE MATRIX"
        lines.append(bold(c_cyan("=" * 78)))
        header_text = f"CARTOGRAPHIC DECRYPTION MATRIX: [{p_name.upper()}]"
        lines.append(bold(c_cyan(header_text.center(78))))
        lines.append(bold(c_cyan("=" * 78)))

        if not puzzle:
            lines.append(c_gray("  No active cartographic matrix selected. Use [P] to select a puzzle matrix."))
            lines.append("=" * 78)
            return "\n".join(lines)

        frag_req = puzzle.get("fragments_required", 5)
        frag_applied = puzzle.get("fragments_applied", 0)
        progress = puzzle.get("progress_pct", 0)
        energy_left = puzzle.get("energy_left", 3)
        energy_max = puzzle.get("energy_max", 3)
        status = puzzle.get("status", "UNSOLVED")

        if status == "DECRYPTED":
            status_bar = f"{c_green('[✓ FULLY DECRYPTED]')}"
            meta_str = f"Fragments: [ {frag_applied} / {frag_req} ] │ Decrypted: {c_green('100%')} │ Status: {status_bar}"
        else:
            meta_str = f"Fragments Collected: [ {frag_applied} / {frag_req} ] │ Decryption: {progress}% │ Energy: {energy_left}/{energy_max} Tries"
        lines.append(meta_str.center(78))
        lines.append("-" * 78)

        # 3x3 Grid rendering
        grid_nodes = puzzle.get("grid_nodes", [])
        grid_bridges = puzzle.get("grid_bridges", {})

        def fmt_node(node_dict: Dict[str, Any]) -> str:
            revealed = node_dict.get("is_revealed", False)
            raw_label = node_dict.get("label", "( ? )") if revealed else "( ? )"
            padded = raw_label.center(7)
            if node_dict.get("is_anchor"):
                return bold(c_cyan(padded))
            elif revealed:
                return c_white(padded)
            return c_gray(padded)

        def fmt_h_bridge(r: int, c1: int, c2: int) -> str:
            k1 = f"{r},{c1}-{r},{c2}"
            k2 = f"{r},{c2}-{r},{c1}"
            active = grid_bridges.get(k1, False) or grid_bridges.get(k2, False)
            return c_green(" ─── ") if active else c_red(" ··· ")

        def fmt_v_bridge(r1: int, r2: int, c: int) -> str:
            k1 = f"{r1},{c}-{r2},{c}"
            k2 = f"{r2},{c}-{r1},{c}"
            active = grid_bridges.get(k1, False) or grid_bridges.get(k2, False)
            return c_green("   │   ") if active else c_red("   ·   ")

        instr_lines = [
            "Instructions:",
            "Rotate or bridge the node grid to",
            "align signal vectors with core",
            "vector [001]. Use fragments to",
            "decrypt unknown nodes (?).",
        ]

        if len(grid_nodes) == 3:
            r0 = f"   {fmt_node(grid_nodes[0][0])}{fmt_h_bridge(0, 0, 1)}{fmt_node(grid_nodes[0][1])}{fmt_h_bridge(0, 1, 2)}{fmt_node(grid_nodes[0][2])}"
            v01 = f"   {fmt_v_bridge(0, 1, 0)}     {fmt_v_bridge(0, 1, 1)}     {fmt_v_bridge(0, 1, 2)}"
            r1 = f"   {fmt_node(grid_nodes[1][0])}{fmt_h_bridge(1, 0, 1)}{fmt_node(grid_nodes[1][1])}{fmt_h_bridge(1, 1, 2)}{fmt_node(grid_nodes[1][2])}"
            v12 = f"   {fmt_v_bridge(1, 2, 0)}     {fmt_v_bridge(1, 2, 1)}     {fmt_v_bridge(1, 2, 2)}"
            r2 = f"   {fmt_node(grid_nodes[2][0])}{fmt_h_bridge(2, 0, 1)}{fmt_node(grid_nodes[2][1])}{fmt_h_bridge(2, 1, 2)}{fmt_node(grid_nodes[2][2])}"

            lines.append(f"{r0}         {instr_lines[0]}")
            lines.append(f"{v01}         {instr_lines[1]}")
            lines.append(f"{r1}         {instr_lines[2]}")
            lines.append(f"{v12}         {instr_lines[3]}")
            lines.append(f"{r2}         {instr_lines[4]}")
        lines.append("-" * 78)

        # Sector Vectors & Decryption Telemetry
        lines.append("Sector Vectors & Decryption Telemetry:")
        telemetry_items = []
        for r_idx in range(3):
            for c_idx in range(3):
                if r_idx < len(grid_nodes) and c_idx < len(grid_nodes[r_idx]):
                    node = grid_nodes[r_idx][c_idx]
                    if node.get("is_anchor"):
                        node_name = f"Anchor {node.get('label', '').strip('[] ')}"
                    elif node.get("is_revealed"):
                        node_name = f"Sector {node.get('sector_val', 0):03d}"
                    else:
                        node_name = "Unknown Node"

                    angle = node.get("vector_angle", 0)
                    if angle == 0:
                        align_col = c_green("[▲] 0° ALIGN")
                    elif angle == 90:
                        align_col = c_gold("[►] 90° ROT")
                    elif angle == 180:
                        align_col = c_red("[▼] 180° INV")
                    else:
                        align_col = c_magenta("[◄] 270° MIS")

                    telemetry_items.append((f"• ({r_idx},{c_idx}) {node_name:<12}:", align_col))

        for i in range(5):
            left_lbl, left_val = telemetry_items[i]
            if i + 5 < len(telemetry_items):
                right_lbl, right_val = telemetry_items[i + 5]
                lines.append(f"  {left_lbl} {left_val}   {right_lbl} {right_val}")
            else:
                lines.append(f"  {left_lbl} {left_val}")
        lines.append("-" * 78)

        # Fragments in hold
        lines.append("Fragments in Hold:")
        if fragments:
            for idx, frag in enumerate(fragments, 1):
                rarity = frag.get("rarity", "COMMON")
                if rarity == "LEGENDARY":
                    r_col = c_magenta(rarity)
                elif rarity == "RARE":
                    r_col = c_gold(rarity)
                elif rarity == "UNCOMMON":
                    r_col = c_cyan(rarity)
                else:
                    r_col = c_green(rarity)
                lines.append(f"  [{idx}] {frag.get('name', 'Starmap Fragment')} ({r_col})")
        else:
            lines.append(f"  {c_gray('• No fragments in cargo hold. Acquire via [C]hit, [V] Salvage, or Combat.')}")

        # Unlocked secrets
        lines.append("Unlocked Starmap Secrets:")
        if unlocked_secrets:
            secrets_map = {
                "GHOST_NEXUS": f"  ★ {c_gold('Black-Market Nexus')} [{c_cyan('Sector 105')}] - Link: 078 & 065 (300% Premium)",
                "PRECURSOR_VAULT": f"  ★ {c_gold('Precursor Salvage Vaults')} [{c_cyan('Sector 106')}] - Link: 088 & 092 (Citadel Tier 4)",
                "SMUGGLER_SHORTCUT": f"  ★ {c_gold('Smuggler Void Bypass')} [{c_cyan('Direct Wormhole')}] - Sector 010 ◄──► Sector 070",
            }
            for sec_key in unlocked_secrets:
                if sec_key in secrets_map:
                    lines.append(secrets_map[sec_key])
                else:
                    lines.append(f"  ★ {c_gold(sec_key)} [{c_cyan('Unlocked Secret')}]")
        else:
            lines.append(f"  {c_gray('• None discovered yet. (Decrypt a matrix to unlock secrets / shortcuts)')}")

        # Catalytic Reagents status
        req_reagents = puzzle.get("required_reagents", {})
        if req_reagents:
            app_reagents = puzzle.get("applied_reagents", {})
            is_cat = puzzle.get("is_catalyzed", False)
            cat_status = c_green("[CATALYZED & ENERGIZED]") if is_cat else c_gold("[CATALYSIS LOCKED - Inject via K]")
            lines.append(f"Periodic Catalytic Reagents: {cat_status}")
            r_parts = []
            for r_k, r_v in req_reagents.items():
                cur = app_reagents.get(r_k, 0)
                col = c_green if cur >= r_v else c_gold
                r_parts.append(f"{r_k}: {col(f'{cur}/{r_v}')}")
            lines.append(f"  • Required Elements: [{', '.join(r_parts)}]")
            lines.append("-" * 78)

        # Active Decryption Targets
        if all_puzzles:
            lines.append(bold(c_white("Active Decryption Targets:")))
            for p in all_puzzles:
                marker = c_green("► [ACTIVE]") if p.get("is_active") else c_gray("  [QUEUED]")
                status_str = c_green("DECRYPTED") if p.get("status") == "DECRYPTED" else c_gold(f"{p.get('progress_pct', 0)}% Solved")
                lines.append(f"  {marker} {c_white(p.get('name', ''))} [{p.get('puzzle_id')}] - {status_str}")

        # Orbital Toll Gates
        my_tolls = cart_info.get("toll_gates", [])
        if my_tolls:
            lines.append("-" * 78)
            lines.append("Orbital Toll Gates & Revenue:")
            for tg in my_tolls:
                lines.append(
                    f"  ★ Gate {tg['id']} (Sec {tg['sector_a']:03d}◄─►{tg['sector_b']:03d}) : "
                    f"Toll: {tg['toll_fee']} Cr │ Transits: {tg['total_transits']} │ Rev: +{tg['total_revenue']:,} Cr"
                )

        # Autonomous Survey Probe Fleet
        my_probes = cart_info.get("survey_probes", [])
        if my_probes:
            lines.append("-" * 78)
            lines.append("Autonomous Survey Drones:")
            for sp in my_probes:
                stat_col = c_green if sp['status'] == "SCANNING" else c_red
                lines.append(
                    f"  ► {sp['id']} in Sec {sp['current_sector']:03d} [{stat_col(sp['status'])}] "
                    f"Shields: {sp['shields']}/50 │ Frags Recovered: {sp['fragments_found']}"
                )

        lines.append("=" * 78)
        lines.append(
            f"Commands: {c_gold('[S]')}can Fragment  {c_gold('[R]')}otate Node  {c_gold('[B]')}ridge Vector  {c_gold('[P]')}ick Matrix\n"
            f"          {c_gold('[K]')} Catalyze  {c_gold('[T]')}oll Gate  {c_gold('[D]')}rone Probe  {c_gold('[F]')}orge Chit  {c_gold('[Q]')}uit"
        )
        lines.append("=" * 78)
        return "\n".join(lines)

    @classmethod
    def render_cognitive_console(cls, view: Dict[str, Any]) -> str:
        """
        Renders the Dual-Seat Cognition Engine Console (iae::think).
        Displays the 5 Canonical Ledger Books [Have | Owe], the Divergence Vector,
        Seat ARC spatial peeling status, and crystallized grown_basis invariants.
        Strictly fits within 78-80 terminal columns.
        """
        player = view.get("player", {})
        cycle = view.get("cycle", 0)
        turns = view.get("turns", 0)
        cog = view.get("cognition", {})
        species = cog.get("species") or player.get("species", "human-sol")
        metabolism = cog.get("metabolism") or player.get("metabolism", "biotic")
        books = cog.get("books", {})
        div_data = cog.get("divergence", {})
        grown_basis = cog.get("grown_basis", [])
        active_puzzle = view.get("cartography", {}).get("active_puzzle", {})

        cr_val = player.get("credits", 0)
        cr_text = f"{cr_val:,} Cr"
        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ DUAL-SEAT COGNITION CONSOLE (iae::think)'))}          {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            (
                f"{bold(c_gold('║'))}  Captain: {c_white(player.get('name', 'Captain')[:18]):<18} "
                f"│ Species: {c_green(species):<14} "
                f"│ Mode: {c_magenta(metabolism.upper()):<8}  {bold(c_gold('║'))}"
            ),
            (
                f"{bold(c_gold('║'))}  Cycle: {c_gold(str(cycle)):<6} │ Turns: {c_cyan(str(turns)):<5} "
                f"│ Invariants: {c_gold(str(len(grown_basis))):<4} "
                f"│ Credits: {c_green(f'{cr_text:<13}')} {bold(c_gold('║'))}"
            ),
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
        ]

        # SECTION 1: SEAT 1 - SURVIVE (The 5 Canonical Ledger Books)
        lines.append(f"\n{bold(c_cyan('──[ SEAT 1: SURVIVE │ FIVE CANONICAL LEDGER BOOKS ]' + '─' * 29))}")
        lines.append(
            f"  {bold('BOOK')}         │ {bold('HAVE')}     │ {bold('OWE')}      │ {bold('GAP / RESIDUAL')} │ {bold('EQUILIBRIUM')}"
        )
        lines.append(f"  {'─' * 12}┼{'─' * 9}┼{'─' * 10}┼{'─' * 16}┼{'─' * 18}")

        book_order = ["RATION", "THERMAL", "SECURITY", "MATTER", "LEISURE"]
        for b_name in book_order:
            b_info = books.get(b_name, {})
            is_closed = b_info.get("is_closed", False)
            res = b_info.get("total_residual", 0.0)
            defic = b_info.get("total_deficit", 0.0)

            if is_closed:
                status_str = c_green("CLOSED (Balanced)")
                gap_str = c_green(f"+{res:,.1f}")
            else:
                status_str = c_red("ACUTE DEFICIT")
                gap_str = c_red(f"-{defic:,.1f}")

            entries = b_info.get("entries", {})
            top_coord = next(iter(entries.keys()), "NONE")
            c_have = entries.get(top_coord, {}).get("have", 0.0)
            c_owe = entries.get(top_coord, {}).get("owe", 0.0)

            line_entry = (
                f"  {c_gold(b_name):<20}│ {c_white(f'{c_have:>7.1f}')} │ {c_gray(f'{c_owe:>8.1f}')} │ "
                f"{gap_str:<23}│ {status_str}"
            )
            lines.append(line_entry)

        # SECTION 2: MATERIAL COCHAIN DIVERGENCE TENSOR (div(Delta))
        lines.append(f"\n{bold(c_cyan('──[ MATERIAL COCHAIN DIVERGENCE TENSOR (div(Δ) = Have - Owe) ]' + '─' * 14))}")
        deficits = div_data.get("deficits", {})
        surpluses = div_data.get("surpluses", {})

        def_items = [f"{k}: {c_red(f'-{v:.1f}')}" for k, v in list(deficits.items())[:4]]
        sur_items = [f"{k}: {c_green(f'+{v:.1f}')}" for k, v in list(surpluses.items())[:4]]

        lines.append(f"  Unclosed Deficits: {', '.join(def_items) if def_items else c_green('None (Equilibrium Achieved)')}")
        lines.append(f"  Surplus Reserves : {', '.join(sur_items) if sur_items else c_gray('None')}")

        # SECTION 3: SEAT 2 - ARC (Spatial Navigation & Cartographic Decryption)
        lines.append(f"\n{bold(c_cyan('──[ SEAT 2: ARC │ CARTOGRAPHIC MATRIX & PRECURSOR CIPHERS ]' + '─' * 18))}")
        if active_puzzle:
            p_name = active_puzzle.get("name", "Unknown Anomaly")
            p_stat = active_puzzle.get("status", "LOCKED")
            p_prog = active_puzzle.get("progress_pct", 0)
            p_nodes = active_puzzle.get("grid_nodes", [])
            from xylarium.kernel.cognition import rcf_hash
            p_rcf = rcf_hash(p_nodes)[:16] if p_nodes else "0000000000000000"

            stat_col = c_green("DECRYPTED") if p_stat == "DECRYPTED" else (c_gold("SOLVING") if p_prog > 0 else c_red("LOCKED"))
            lines.append(f"  Active Matrix  : {c_gold(p_name)} [{stat_col}]")
            lines.append(f"  Conjugacy Hash : {c_magenta(f'RCF-{p_rcf}')} │ Decryption: {c_cyan(f'{p_prog}%')}")
        else:
            lines.append(f"  {c_gray('No Precursor anomaly currently locked on cartography sensors.')}")

        # SECTION 4: CRYSTALLIZED INVARIANTS (grown_basis)
        lines.append(f"\n{bold(c_cyan('──[ CRYSTALLIZED INVARIANTS IN GROWN_BASIS (O(1) Recall) ]' + '─' * 19))}")
        if not grown_basis:
            lines.append(f"  {c_gray('Basis empty. As ARC peels spatial matrices, invariants crystallize here.')}")
        else:
            for idx, crystal in enumerate(grown_basis[-4:], 1):
                seat_str = c_cyan(f"[{crystal.get('seat', 'ARC')}]")
                deed_str = c_white(crystal.get("deed", "INVARIANT")[:26])
                coord_str = c_gold(crystal.get("coordinate", "GLOBAL")[:16])
                sig_str = c_gray(crystal.get("certificate", crystal.get("rcf_sig", ""))[:16])
                lines.append(f"  {idx}. {seat_str} {deed_str:<26} │ {coord_str:<16} │ {sig_str}")

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  {bold(c_cyan('Cognition Controls:'))} "
            f"{c_gold('[A]')}utomate Step (iae::think)  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")

        return "\n".join(lines)

    @classmethod
    def render_ideology_screen(cls, view: Dict[str, Any]) -> str:
        ideo = view.get("ideology", {})
        player = view.get("player", {})
        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ SOCIAL THERMODYNAMICS & COHESION LEDGERS'))}        {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            f"{bold(c_gold('║'))}  Entity: {c_white(player.get('name', 'Captain')):<25} "
            f"Active Treaties: {c_green(str(ideo.get('total_treaties', 0))):<28} {bold(c_gold('║'))}",
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
            "",
            bold(c_cyan("COHESION LEDGER METRICS & INTERSTELLAR STANDING:")),
            f"{'-' * 78}",
        ]
        rels = ideo.get("relationships", {})
        if not rels:
            lines.append("  No established bilateral deeds recorded on the ledger.")
        else:
            for entity_id, data in rels.items():
                st = data.get("standing", 0.5)
                st_bar = _render_bar(int(st * 10), 10, length=10)
                lines.append(f"  ► Target: {c_gold(entity_id):<22} Standing: {c_green(f'{st:.2f}')} {st_bar}")
                lines.append(
                    f"    Compassion: {data.get('compassion', 0.5):.2f} │ "
                    f"Resonance: {data.get('resonance', 0.5):.2f} │ "
                    f"Integrity: {data.get('integrity', 0.5):.2f} │ "
                    f"Morality: {data.get('morality', 0.5):.2f}"
                )

        lines.append(f"\n{bold(c_cyan('ACTIVE INTERSTELLAR TREATIES:'))}")
        lines.append(f"{'-' * 78}")
        treaties = ideo.get("active_treaties", [])
        if not treaties:
            lines.append("  No active diplomatic treaties ratified.")
        else:
            for t in treaties:
                lines.append(
                    f"  ★ [{t.get('treaty_type', 'TREATY')}] ID: {t.get('id')} │ "
                    f"Signatories: {t.get('signatory_a')} & {t.get('signatory_b')} │ "
                    f"Tariff Discount: -{t.get('tariff_discount_pct', 15)}%"
                )

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_gold('[P]')}ropose Treaty  "
            f"{c_gold('[S]')}ign Treaty  "
            f"{c_gold('[D]')}ispatch Famine Aid  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_alchemy_screen(cls, view: Dict[str, Any]) -> str:
        alch = view.get("alchemy", {})
        player = view.get("player", {})
        reactor = alch.get("reactor", {})
        heat = reactor.get("heat", 0.0)
        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ PRECURSOR TRANSMUTATION & MATTER BALANCE'))}        {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            f"{bold(c_gold('║'))}  Core Heat: {c_red(f'{heat:.1f} MW'):<18} "
            f"Dissipation Cap: {c_green('20.0 MW'):<16} "
            f"Reactor: {c_cyan('ONLINE'):<18} {bold(c_gold('║'))}",
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
            "",
            bold(c_cyan("CANONICAL PRECURSOR TRANSMUTATION RECIPES:")),
            f"{'-' * 78}",
        ]
        recipes = alch.get("recipes", [])
        if not recipes:
            lines.append("  No transmutation recipes unlocked. Research 'ORBITAL_FOUNDRY' or explore frontier relics.")
        else:
            for r in recipes:
                in_str = ", ".join([f"{k}:{v}" for k, v in r.get("inputs", {}).items()])
                out_str = f"+{r.get('output_qty', 1)} [{r.get('output_element')}]"
                cat_str = f"Cat: {r.get('catalyst')}"
                lines.append(
                    f"  ► {c_gold(r.get('id')):<16} │ {c_white(r.get('name')):<24} │ {c_green(out_str):<12}"
                )
                lines.append(f"    Inputs: {in_str:<24} │ {cat_str:<12} │ Heat: +{r.get('thermal_entropy', 15.0):.1f} MW")

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_gold('[T]')}ransmute Recipe  "
            f"{c_gold('[A]')}ll Recipes  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_astronomy_screen(cls, view: Dict[str, Any]) -> str:
        astro = view.get("astronomy", {})
        sector = view.get("sector", {})
        sec_id = sector.get("id", 1)
        sec_name = sector.get("name", "System")[:28]
        sec_str = f"#{sec_id:03d} {sec_name}"
        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ KEPLERIAN ORBITAL EPHEMERIS & RADAR'))}              {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            f"{bold(c_gold('║'))}  Sector: {c_cyan(sec_str):<35} "
            f"Local Star: {c_gold('Sol Class-G'):<23} {bold(c_gold('║'))}",
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
            "",
        ]
        radar = astro.get("system_map", [])
        if radar:
            lines.append(bold(c_cyan("SYSTEM ASTRODYNAMIC RADAR (☼ Central Star, 1..9 Planets):")))
            for rline in radar:
                lines.append("  " + rline)
            lines.append("")

        lines.append(bold(c_cyan("PLANETARY ORBITAL EPHEMERIS (Keplerian Phase Law):")))
        lines.append(f"{'-' * 78}")
        eph = astro.get("ephemeris", [])
        if not eph:
            lines.append("  No planetary bodies detected orbiting star in current sector.")
        else:
            for p in eph:
                deg_str = f"{p.get('angle_deg', 0.0):.1f}°"
                r_str = f"{p.get('radius_au', 1.0):.2f} AU"
                p_str = f"{p.get('period_cycles', 36)} cyc"
                lines.append(
                    f"  ► {c_gold(p.get('planet_name', 'Planet')[:18]):<18} "
                    f"Radius: {c_white(r_str):<9} "
                    f"Phase: {c_green(deg_str):<8} "
                    f"Period: {c_cyan(p_str):<8} "
                    f"[{p.get('phase_label', 'Active')}]"
                )

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_gold('[W]')}indow Calculation  "
            f"{c_gold('[R]')}efresh Ephemeris  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_senate_screen(cls, view: Dict[str, Any]) -> str:
        sen = view.get("senate", {})
        treasury = sen.get("federal_treasury", 100000)
        curr_cyc = sen.get("current_cycle", 0)
        next_elec = sen.get("next_election_cycle", 60)
        cycles_left = max(0, next_elec - curr_cyc)
        v_weight = sen.get("player_voting_weight", 1.0)
        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan('XYLARIUM BBS │ THE IMPERIAL SENATE & HIGH OFFICES OF STATE'))}        {bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            f"{bold(c_gold('║'))}  Federal Treasury: {c_green(f'{treasury:,} Cr'):<18} "
            f"Next Election: in {c_gold(f'{cycles_left} cycles'):<12} "
            f"Your Votes: {c_cyan(f'{v_weight:.1f}'):<8} {bold(c_gold('║'))}",
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
            "",
            bold(c_cyan("THE FOUR HIGH OFFICES OF THE UNION:")),
            f"{'-' * 78}",
        ]
        offices = sen.get("offices", {})
        for o_key, holder in offices.items():
            inc = holder.get("incumbent_name", "Vacant")
            expires = holder.get("term_expires_cycle", 60)
            lines.append(f"  ★ {c_gold(o_key):<16} : {c_white(inc):<26} (Term ends: Cycle {expires})")

        lines.append(f"\n{bold(c_cyan('SYSTEMIC EDICTS CURRENTLY IN FORCE:'))}")
        lines.append(f"{'-' * 78}")
        edicts = sen.get("active_edicts", [])
        if not edicts:
            lines.append("  No emergency decrees or imperial edicts active.")
        else:
            for ed in edicts:
                lines.append(f"  ► [{c_green(ed.get('edict'))}] {ed.get('description')}")

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_gold('[C]')}ampaign for Office  "
            f"{c_gold('[V]')}ote on Ballot  "
            f"{c_gold('[E]')}nact Imperial Edict  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_surface_screen(cls, view: Dict[str, Any], planet_id: Optional[str] = None) -> str:
        surf = view.get("surface", {})
        planets = surf.get("sector_planets", [])
        if not planets:
            return f"\n{c_red('No planetary bodies present in current sector.')}\n"

        p_data = planets[0]
        if planet_id:
            for p in planets:
                if p.get("id") == planet_id:
                    p_data = p
                    break

        p_name = p_data.get("name", "Planet")
        p_owner = p_data.get("owner_id") or "Unclaimed Frontier"
        garrison = p_data.get("garrison_troops", 0)
        yields = p_data.get("yields", {})
        my_troops = surf.get("player_troops", 0)
        title_str = f"XYLARIUM BBS │ PLANETARY SURFACE & DISTRICT GRID: {p_name[:20]}"
        yield_ore = yields.get("ore", 0.0)
        yield_org = yields.get("organics", 0.0)
        yield_shd = yields.get("shields", 0.0)
        yield_def = yields.get("fortress_defense", 0)

        lines = [
            f"\n{bold(c_gold('╔' + '═' * 76 + '╗'))}",
            f"{bold(c_gold('║'))}  {bold(c_cyan(title_str)):<77}{bold(c_gold('║'))}",
            f"{bold(c_gold('╠' + '═' * 76 + '╣'))}",
            f"{bold(c_gold('║'))}  Owner: {c_white(str(p_owner)[:18]):<18} "
            f"Garrison: {c_green(f'{garrison} div'):<12} "
            f"Your Assault Force: {c_magenta(f'{my_troops} div'):<14} {bold(c_gold('║'))}",
            f"{bold(c_gold('╚' + '═' * 76 + '╝'))}",
            "",
            bold(c_cyan("8x8 DUAL SURFACE TOPOGRAPHY (Terrain & Zoned Districts):")),
        ]
        s_map = p_data.get("map", [])
        for mline in s_map:
            lines.append("  " + mline)

        lines.append("")
        lines.append(
            f"  {bold(c_cyan('Net Production/Tick:'))} "
            f"Ore: {c_green(f'+{yield_ore:.1f}')} │ "
            f"Organics: {c_green(f'+{yield_org:.1f}')} │ "
            f"Shields: {c_cyan(f'+{yield_shd:.1f}')} │ "
            f"Defense: {c_gold(f'+{yield_def}')}"
        )

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_gold('[B]')}uild District  "
            f"{c_gold('[D]')}emolish District  "
            f"{c_gold('[R]')}ecruit Troops  "
            f"{c_gold('[I]')}nvade Planet  "
            f"{c_gold('[Q]')}uit / Return"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_phylogenetic_cladogram(cls, view: Dict[str, Any]) -> str:
        """Renders the comprehensive full-screen ASCII Phylogenetic Cladogram and Canopy Invariants screen."""
        phylo = view.get("phylogeny", {})
        player = view.get("player", {})
        ascii_tree = phylo.get("ascii_cladogram", "")
        eval_data = phylo.get("ascension_eval", {})
        affinities = phylo.get("affinities", {})
        flux_dict = phylo.get("cochain_flux", {})
        cur_node = phylo.get("current_node", {})
        can_ascend = eval_data.get("can_ascend", False)
        best_branch = eval_data.get("best_branch", {})
        chimeric_avail = eval_data.get("chimeric_available", [])

        lines = [
            f"\n{bold(c_gold('╔══════════════════════════════════════════════════════════════════════════════╗'))}",
            f"{bold(c_gold('║                 PHYLOGENETIC ASCENSION CLADOGRAM & CANOPY DAG                ║'))}",
            f"{bold(c_gold('╚══════════════════════════════════════════════════════════════════════════════╝'))}",
        ]

        if ascii_tree:
            lines.append(ascii_tree)
        else:
            lines.append("  [No cladogram telemetry available.]")

        lines.append("")
        if can_ascend and best_branch:
            b_name = best_branch.get("name", "Branch")
            b_tier = best_branch.get("tier", 2)
            b_role = best_branch.get("role", "")
            b_id = best_branch.get("id", "")
            b_aff = int(affinities.get(b_id, 0) * 100)
            lines.append(f"  {bold(c_green(f'▲ COCHAIN INVARIANTS SATISFIED FOR ASCENSION: {b_name} [Tier {b_tier}] ▲'))}")
            lines.append(f"  Role: {c_gold(b_role)} │ Affinity: {b_aff}%")
            lines.append(f"  {bold(c_white('PRESS [A] TO ASCEND AND CRYSTALLIZE THIS BRANCH NOW!'))}")
        elif eval_data.get("unmet_reasons"):
            unmet = "; ".join(eval_data.get("unmet_reasons", []))
            lines.append(f"  {c_gold('Ascension Gate Status:')} {c_red(unmet)}")

        if cur_node.get("canopy_override"):
            c_perk = cur_node.get("canopy_perk_title", "Universe Rewrite")
            c_desc = cur_node.get("canopy_perk_description", "")
            lines.append("")
            lines.append(f"  {bold(c_gold('★ APEX CANOPY OVERRIDE:'))} {bold(c_green(c_perk))}")
            lines.append(f"  Effect: {c_cyan(c_desc)}")
            lines.append(f"  {bold(c_white('PRESS [O] TO TRIGGER CANOPY INVARIANT REWRITE!'))}")

        if chimeric_avail:
            lines.append("")
            lines.append(f"  {bold(c_magenta('LATERAL PRECURSOR CHIMERISM (Cartography Lab Synthesis):'))}")
            for ch in chimeric_avail:
                mats = ", ".join(f"{q} {m}" for m, q in ch.get("chimeric_cost_materials", {}).items())
                ch_name = ch.get("name", "Hybrid")
                ch_tier = ch.get("tier", 3)
                ch_role = ch.get("role", "")
                ch_canopy = ch.get("canopy_perk_title", "None")
                lines.append(f"  ⚡ {bold(c_white(ch_name))} [Tier {ch_tier}] - Cost: {c_gold(mats)}")
                lines.append(f"     Role: {c_gray(ch_role)} │ Canopy: {c_cyan(ch_canopy)}")

        lines.append(f"\n{bold(c_gold('═' * 78))}")
        lines.append(
            f"  Commands: {c_green('[A]scend Branch')}  │  "
            f"{c_gold('[O]verride Canopy')}  │  "
            f"{c_magenta('[G]raft Chimera')}  │  "
            f"{c_white('[Enter / X] Return')}"
        )
        lines.append(f"{bold(c_gold('═' * 78))}")
        return "\n".join(lines)

    @classmethod
    def render_help(cls) -> str:
        """Renders classic BBS door game guide and mechanics."""
        return f"""
{bold(c_gold("══════════════════════ [ XYLARIUM BBS COMMAND GUIDE ] ══════════════════════"))}
{c_cyan("OBJECTIVE:")}
  Amass credits, dominate trade routes, colonize rich planets, defend your
  territory from rival AI captains (Traders, Pirates, MegaCorp Oligarchs),
  and build an interstellar empire across 100 sectors and beyond!

{c_cyan("COMMAND DISPATCH:")}
  {c_gold("[M]ove")}     - Warp to an adjacent sector via wormholes (Cost: 1 Turn).
  {c_gold("[T]rade")}    - Dock at the local port to buy/sell Ore, Organics, Equipment (1 Turn).
  {c_gold("[P]lanet")}   - Orbit and manage planetary colonies: tax, shields, citadels (1 Turn).
  {c_gold("[A]ttack")}   - Engage rival ships or bombard planetary defense grids (2 Turns).
  {c_gold("[S]hipyard")} - Upgrade hulls, recharge shields, purchase fighters (Sector 1 only).
  {c_gold("[C]omputer")} - Plot warp courses, calculate BFS shortest routes, sector scans.
  {c_gold("[O]ptimize")} - Scan galactic arbitrage loops, colony supply runs, and market spreads.
  {c_gold("[E]xchange")} - Interstellar Stock Exchange (ISSE) equities & star freight contracts.
  {c_gold("[F]leet")}    - Automated merchant haulers, VC syndicates & specialized freight.
  {c_gold("[I]mperial")} - Imperial Dominion & Asset Registry console (manage colonies & haulers).
  {c_gold("[G]ov / Cog")}- Dual-Seat Cognition Engine console (SURVIVE & ARC Ledgers).
  {c_gold("[N] Anomaly")} - Research breakthroughs, cognitive metabolism & cosmic anomaly matrix.
  {c_gold("[J]ump")}     - Hyper-Dimensional Jump Drive across charted space & outer clusters.
  {c_gold("[X] Cartography")} - Decrypt starmap fragments to discover ghost sectors & bypasses.
  {c_gold("[R]adio")}    - Broadcast subspace message across universe comm channels.
  {c_gold("[H]elp")}     - Display this tactical manual.
  {c_gold("[Q]uit")}     - Save game state and exit to BBS door prompt.

{c_cyan("DYNAMIC COMMODITY TRADING (TradeWars 2002 Model):")}
  - Ports buy and sell commodities dynamically based on stock and port class.
  - Buying goods depletes port inventory, driving prices UP.
  - Selling goods floods port inventory, driving prices DOWN.
  - Ports replenish and consume goods each game cycle, creating moving arbitrage waves.

{c_cyan("STAR SYSTEMS & NULL SPACE:")}
  - Star systems (ports, worlds) are separated by null space. Firing inside a protected
    system on anyone not wanted is a HOSTILE ACT: Federal warrant + reputation loss.
  - Null space is open ground. SCAN reveals asteroid belts; MINE extracts ore, metals, ices
    and gases (a Mining Barge yields 30/turn). SALVAGE recovers debris from destroyed hulls.
  - SENTRY deploys fighters as a picket that defends you and engages wanted intruders;
    RECALL brings them home. Pirates prowl belts and lanes - escort your miners.
  - Colonies post EXTRACTION work orders for elements their people consume: sign at the
    colony, mine it in nearby null space, deliver it back for pay in local currency.

{c_cyan("ARCHAEOLOGY - DEAD CIVILIZATIONS:")}
  - Civilizations that starve below viability die; their worlds become RUINS and their vaults
    become buried hoards. Ancient precursor ruins also lie beneath some uninhabited worlds.
  - RUINS surveys a site; DIG excavates a stratum (1 Equipment as tools). Deeper strata are older
    and richer but unstable: cave-ins crush finds and damage your ship. SHORE spends extra tools.
  - Finds: ANTIQUITIES (sell at starport curio desks, paid from the port's treasury), TECH RELICS
    (study them for research and breakthroughs, or sell), precious materials, buried hoard money.
  - Provenance: your own world, abandoned systems, or a Federal Antiquities PERMIT (at Sol) make
    finds licensed. Looted pieces only sell on the Anarchy black market, at a discount.
  - Collectors pay more for artifacts far from their culture's homeworld.

{c_cyan("TWO MODES: FLY SHIP & EMPIRE:")}
  - [F]ly Ship mode is the cockpit: warp, trade, fight, scan, dig, deal with locals.
  - [E]mpire mode is your sovereign console: [1] colonies [2] fleets [3] trade routes
    [4] diplomacy, powers & wars [5] treasury. FLEET and STOCK still open those desks by name.

{c_cyan("YOUR LINEAGE (ONE PER UNIVERSE):")}
  - At Lineage Genesis you chose a clade and origin; this universe is bound to that lineage.
  - Each lost flagship decants a backup clone at Sol (CLONE buys more there). Lose a ship with
    no clones left, or lose your home colony with no other world to hold the seat, and the
    lineage ends: its record is sealed in the Library and the Hall of Lineages, and a new
    universe begins. RETIRE ends it by choice.

{c_cyan("THE LIGHT AND THE DARK (ALIGN):")}
  - Every deed moves you along a cosmic axis from Dark (-1) to Light (+1). Freight, charting,
    research, famine aid and protecting locals lean Light; piracy, conquest, looting and
    exploiting natives lean Dark. The universe leans syntropic: a clean quarter drifts you Light.
  - Luminous captains buy on goodwill; Shadowed ones pay friction, wear their hulls, and draw
    warrants. At +0.90 an oath of Light binds you; at -0.90 the Dark does.

{c_cyan("LOCALS & THE PRIME DIRECTIVE (NATIVES, DOCTRINE):")}
  - Many worlds hold non-spacefaring peoples, from the Stone Age to the Orbital age. NATIVES lets
    you observe, contact, trade, uplift, protect (then collect their tithe), or exploit them.
  - The authority here plays a card from the Galactic Policy Deck (ALPHA non-interference, BETA
    observation, GAMMA protectorate, DELTA exploitation, EPSILON conversion) with a sapience
    threshold for contact. The Federation interdicts violators; the Compact and the Imperium
    issue warrants. Uplift too far, too fast, and a people shatters.

{c_cyan("GREAT POWERS:")}
  - The Aurelian Imperium (THR currency) tithes its worlds; Bulk Goliaths haul the tithe and the
    Fortress builds Gothic Battle-Cruisers. Imperial ports gouge xenos; techno-heresy is hunted.
  - The Choir of the Pyre burns its surplus into dogma and crusades. It must expand or purge.

{c_cyan("THE GALACTIC LIBRARY ([L]IBRARY, WRITE):")}
  - Captains' logs, planetary annals, field notes, decrees and manifestos are written as history
    happens. Browse them at any starport; WRITE files your own entry.

{c_cyan("MONEY, CURRENCIES & THE ISSE FX DESK:")}
  - Federation space settles in SOL, the Borderlands in Frontier Scrip (FRN), Anarchy space
    in Void Marks (VOID), Imperial space in Throne Crowns (THR). Ports price and pay in local money; SOL auto-converts on purchase.
  - FX rates float on ISSE liquidity pools: trade flows move them. Type FX to swap.
  - Ports are real balance sheets: an illiquid port can only buy what it can pay for.
  - Manufactures cost more far from Sol; raw materials are cheaper on the frontier.

{c_cyan("PLANETARY COLONIZATION (BRE & SRE Model):")}
  - Found colonies on uninhabited worlds your biology can live on (colony kit required);
    established systems need a charter, indigenous worlds a treaty or an invasion.
  - Build Planetary Shields and Garrison Fighters to repel orbital bombardments.
  - Upgrade your Citadel Tier (Outpost -> Redoubt -> Stronghold -> Imperial Citadel)
    to multiply colonist tax yields and increase defense caps.

{c_cyan("SECURITY ZONES & THE OBSERVATION LAW:")}
  - {c_green("Sectors 001-010 (Federation Core):")} Protected by FedNav. Combat strictly forbidden.
  - {c_gold("Sectors 011-060 (The Borderlands):")} Mixed security. Moderate hazard, steady trade.
  - {c_red("Sectors 061-100 (Deep Void Anarchy):")} Lawless! Precursor relics, high risk and reward!
  - {c_magenta("Sectors 101+ (Procedural Frontier Clusters):")} The Perseus Veil & Cygnus Spiral,
    lazily minted on demand as explorers and Jump Drives cross the frontier!
{"-" * 78}
"""
