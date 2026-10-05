"""
Xylarium markets hub: every market the engine keeps, laid out by the ledger behind it.

The engine keeps five ledgers that markets clear against - energy (energy.py), commodities (port goods),
elementals (the periodic table and its fuels, matter.py), equities (the ISSE: firms, solvency, shorts) and FX (the
money pools, prices and inflation). The hub shows them as five tabs with the same five bands, so the eye always
finds the same thing in the same place:

  LEDGER   the galaxy-wide state of this ledger (and whether it balances)
  LOCAL    the market where you stand: this system's worlds, this port, this money
  BRIDGED  the markets beyond it you can reach: allied and aligned grids, nearby ports, the exchange's other pools
  YOURS    what you hold in this ledger
  ACTIONS  the keys that open the desks that trade it

Each band is a pure render function (kernel state -> text), so the layout is testable; the prompt loop only
switches tabs and hands actions to the console's existing desks.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_magenta, c_red, c_white

TABS = [("1", "ENERGY"), ("2", "COMMODITIES"), ("3", "ELEMENTALS"), ("4", "EQUITIES"), ("5", "FX")]
WIDTH = 78


# ---------------------------------------------------------------------- frame
def _band(name: str) -> str:
    return c_cyan(bold(f"  {name:<8}")) + c_gray("─" * (WIDTH - 10))


def _row(*cells: Tuple[Any, ...]) -> str:
    """Fixed-width columns: (text, width[, colour]) - positive width right-aligns (numbers), negative left-aligns.
    Colour is applied after padding, so escape codes never cost a column."""
    out = []
    for cell in cells:
        text, w = str(cell[0]), cell[1]
        cell_s = text[:abs(w)].rjust(w) if w > 0 else text[:abs(w)].ljust(abs(w))
        out.append(cell[2](cell_s) if len(cell) > 2 and cell[2] else cell_s)
    return "    " + " ".join(out)


def _wrap(text: str, colour: Callable[[str], str] = c_gray, indent: str = "    ") -> List[str]:
    """Free text folded to the frame's width."""
    import textwrap
    return [colour(line) for line in textwrap.wrap(text, WIDTH, initial_indent=indent, subsequent_indent=indent + "  ")]


CATEGORY = {"METALS": "metals", "MINERALS": "minerals", "VOLATILES": "volatiles", "EXOTICS": "exotics",
            "MANUFACTURED": "manufactured",
            "LUXURY": "luxuries", "SYNTHETIC": "made from energy", "WASTE": "waste"}


def _n(x: float, digits: int = 0) -> str:
    if x is None:
        return "-"
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f}M"
    if abs(x) >= 1e4:
        return f"{x / 1e3:.1f}k"
    return f"{x:,.{digits}f}"


def _header(kernel: Any, captain: Any, active: str) -> List[str]:
    sec = kernel.sectors.get(captain.sector_id)
    port = getattr(sec, "port", None)
    money = port.currency if port is not None else "-"
    title = f" MARKETS  ·  Sector {captain.sector_id:03d}  ·  {money}  ·  Year {kernel.cycle_count // 100}"
    tabs = []
    for key, name in TABS:
        label = f"[{key}] {name}"
        tabs.append(bold(c_gold(f"▌{label}▐")) if name == active else c_gray(f" {label} "))
    return ["", bold(c_white("═" * WIDTH)), bold(c_white(title)), "  ".join(tabs), bold(c_white("═" * WIDTH))]


def _holder(kernel: Any, captain: Any) -> Optional[str]:
    from xylarium.kernel import knowledge
    return knowledge.holder_of_captain(captain)


# ---------------------------------------------------------------------- energy
def energy_tab(kernel: Any, captain: Any) -> List[str]:
    from xylarium.kernel import energy, harvest, knowledge, relations, sustenance
    out = [_band("LEDGER")]
    s = energy.summary(kernel)
    bal = energy.residual(kernel)
    out.append(_row(("stored", -7), (_n(s["stored_eu"]), 7), ("EU", -3), ("needs met", -10),
                    (f"{s['mean_sufficiency']:.0%}", 5), ("short worlds", -12), (str(s["short_worlds"]), 3),
                    ("balanced" if bal == 0 else f"off {bal}mEU", -11, c_green if bal == 0 else c_red)))
    src = ", ".join(f"{k} {_n(v)}" for k, v in sorted(s["sources_eu"].items(), key=lambda kv: -kv[1]))
    snk = ", ".join(f"{k} {_n(v)}" for k, v in sorted(s["sinks_eu"].items(), key=lambda kv: -kv[1]))
    out += _wrap(f"in : {src or '-'}")
    out += _wrap(f"out: {snk or '-'}")
    out += _wrap(f"fuel made: hydrogen {s['hydrogen']:,} · antimatter {s['antimatter']:,}")

    out.append(_band("LOCAL"))
    sec = kernel.sectors.get(captain.sector_id)
    worlds = [p for p in (sec.planets if sec else []) if p.population > 0 and not p.natives]
    if not worlds:
        out.append(c_gray("    no peopled world in this system: no grid to trade on"))
    else:
        out.append(c_gray(_row(("world", -16), ("tier", 4), ("need", 7), ("made", 7), ("grid", 7), ("met", 5),
                               ("bid", 7), ("ask", 6), ("works", -9))))
        for p in worlds:
            gen = harvest.generation(kernel, p)
            w = p.society.get("harvest") or {}
            suff = p.society.get("energy_sufficiency")
            works = f"F{w.get('field', 0)} T{w.get('tap', 0)}"
            out.append(_row((p.name, -16), (str(p.citadel_level), 4), (_n(energy.need_eu(p), 1), 7),
                            (_n(sum(gen.values()), 1), 7), (_n(p.society.get("grid_meu", 0) / 1000, 1), 7),
                            ("-" if suff is None else f"{float(suff):.0%}", 5,
                             c_red if (suff is not None and float(suff) < 0.99) else None),
                            (_n(energy.value_short(p), 2), 7), (_n(energy.value_surplus(p), 2), 6), (works, -9)))
        arr = harvest.stats(kernel)["arrays"].get(str(captain.sector_id), {})
        if arr:
            shade = harvest.stats(kernel)["shade"].get(str(captain.sector_id), 0.0)
            owners = ", ".join(f"{sustenance.people_name(kernel, o)} ×{n}" for o, n in arr.items())
            out += _wrap(f"star arrays: {owners}  (shade {shade:.2e})", c_magenta)
        out += _wrap("bid = what a short world loses per EU · ask = what a spare EU makes as fuel · F fields, "
                     "T core bores · local money")

    out.append(_band("BRIDGED"))
    t = s.get("traded_eu", {})
    out.append(_row(("cleared locally", -16), (_n(t.get("local", 0)), 8), ("to allies", -10),
                    (_n(t.get("allied", 0)), 8), ("to aligned", -11), (_n(t.get("aligned", 0)), 8), ("EU", -3)))
    if worlds:
        p0 = max(worlds, key=lambda p: p.population)
        people = sustenance.people_of(p0)
        root = relations.root(kernel, people)
        fam = sum(1 for x in relations.ties(kernel) if relations.root(kernel, x) == root)
        reach = relations._reach_map(kernel, p0)
        out += _wrap(f"{sustenance.people_name(kernel, people)}: family of {fam + 1} under "
                     f"{sustenance.people_name(kernel, root)}; beams reach {len(reach)} systems "
                     f"(loss 1-1/(1+hops)^2)")

    out.append(_band("YOURS"))
    mine = [p for s_ in kernel.sectors.values() for p in s_.planets if p.owner_id == captain.id and p.population > 0]
    if not mine:
        out.append(c_gray("    you govern no world: energy is traded between worlds"))
    for p in mine[:6]:
        suff = p.society.get("energy_sufficiency")
        out.append(_row((p.name, -16), ("need", -5), (_n(energy.need_eu(p), 1), 7), ("met", -4),
                        ("-" if suff is None else f"{float(suff):.0%}", 5)))
    holder = _holder(kernel, captain)
    out.append(c_gray("    your people's designs:"))
    rep_world = mine[0] if mine else (worlds[0] if worlds else None)
    for kind in harvest.KINDS:
        d = harvest.design(kernel, holder, kind, rep_world) if rep_world is not None else None
        out.append(_row((kind, -6), (d["name"] if d else "no material known for a part", -52),
                        (f"{d['eff']:.1%}" if d else "", 7)))
    out.append(_band("ACTIONS"))
    out.append(c_gold("    [P] your planet's works (sunfields, core bores, arrays)") + c_gray("   [Q] back"))
    return out


# ---------------------------------------------------------------------- port goods: commodities and elementals
def _elemental(comm: str) -> bool:
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import chemistry
    return comm in chemistry.TABLE or COMMODITY_CONFIG.get(comm, {}).get("category") == "SYNTHETIC"


def _goods(kernel: Any, captain: Any, elemental: bool) -> List[str]:
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import matter, topology
    from xylarium.kernel.economy import EconomyManager
    out = [_band("LEDGER")]
    census = matter.census(kernel)
    comms = sorted((c for c in COMMODITY_CONFIG if _elemental(c) == elemental
                    and COMMODITY_CONFIG[c].get("category") != "WASTE"),
                   key=lambda c: (COMMODITY_CONFIG[c].get("category", ""), COMMODITY_CONFIG[c].get("name", c)))

    def mined(c: str) -> int:
        rec = census.get(matter.key(c), {})
        return int(rec.get("total", 0)) - int(rec.get("in_ground", 0)) - int(rec.get("belts", 0))
    top = sorted(((c, mined(c)) for c in comms), key=lambda t: -t[1])[:8]
    out += _wrap("above ground: " + ", ".join(f"{c} {_n(v)}" for c, v in top) + "  (the matter ledger balances "
                 "every season: see the audit)")
    if elemental:
        from xylarium.kernel import chemistry
        cs = chemistry.summary(kernel)
        out.append(c_gray(f"    periodic table: {cs.get('discoveries', 0)} discoveries · "
                          f"{cs.get('known_mean', 0)} elements known per people on average"))
    out.append(_band("LOCAL"))
    sec = kernel.sectors.get(captain.sector_id)
    port = getattr(sec, "port", None)
    if port is None:
        out.append(c_gray("    no starport here"))
    else:
        out.append(c_gray(_row(("good", -24), ("bid", 7), ("ask", 7), ("spread", 7), ("stock", 7))))
        last = None
        for c in comms:
            if c not in port.stock:
                continue
            bid, ask = EconomyManager.get_unit_prices(port, c)
            if bid <= 0 and ask <= 0 and port.stock.get(c, 0) <= 0:
                continue
            cat = COMMODITY_CONFIG[c].get("category", "")
            if cat != last:
                out.append(c_magenta(f"    · {CATEGORY.get(cat, cat.lower())}"))
                last = cat
            spread = f"{1 - bid / ask:.0%}" if ask > 0 else "-"
            out.append(_row(("  " + COMMODITY_CONFIG[c].get("name", c), -24), (_n(bid), 7), (_n(ask), 7),
                            (spread, 7), (_n(port.stock.get(c, 0)), 7)))
        out.append(c_gray(f"    prices in {port.currency} · bid = the port pays you · ask = you pay the port"))
    out.append(_band("BRIDGED"))
    near = [s for s in topology.reach(kernel, captain.sector_id, 3) if s != captain.sector_id]
    best: Dict[str, Tuple[int, int, int, int]] = {}
    for sid in near:
        p = kernel.sectors[sid].port if sid in kernel.sectors else None
        if p is None:
            continue
        for c in comms:
            if c not in p.stock:
                continue
            bid, ask = EconomyManager.get_unit_prices(p, c)
            if p.currency != "SOL":                       # compared across monies in SOL
                bid = int(kernel.fx_market.to_sol_value(p.currency, bid))
                ask = int(kernel.fx_market.to_sol_value(p.currency, ask)) if ask > 0 else 0
            b = best.setdefault(c, (0, 0, 10 ** 9, 0))
            if bid > b[0]:
                b = (bid, sid, b[2], b[3])
            if 0 < ask < b[2] and p.stock.get(c, 0) > 0:
                b = (b[0], b[1], ask, sid)
            best[c] = b
    if not best:
        out.append(c_gray("    no starport within 3 jumps"))
    else:
        out.append(c_gray(_row(("good", -24), ("best bid", 9), ("at", 4), ("best ask", 9), ("at", 4))))
        ranked = sorted(best.items(), key=lambda kv: -(kv[1][0] / max(1, kv[1][2]) if kv[1][2] < 10 ** 9 else 0))
        for c, (bid, bs, ask, as_) in ranked[:12]:
            out.append(_row((COMMODITY_CONFIG[c].get("name", c), -24), (_n(bid), 9), (f"{bs:03d}" if bs else "-", 4),
                            (_n(ask) if ask < 10 ** 9 else "-", 9), (f"{as_:03d}" if as_ else "-", 4)))
        out += _wrap("within 3 jumps, in SOL at the exchange's rates; widest gap between a bid and an ask first")
    out.append(_band("YOURS"))
    cg = captain.ship.cargo
    if elemental:
        mine = {e: n for e, n in cg.elements.items() if n}
        fuel = getattr(captain.ship, "fuel", 0)
        from xylarium.kernel import chemistry, propulsion
        known = chemistry.known(kernel, _holder(kernel, captain))
        out.append(_row(("hold", -6), (", ".join(f"{e} {n}" for e, n in mine.items()) or "-", -66)))
        out.append(_row(("drive", -6), (f"{propulsion.drive_of(captain.ship).get('name', '-')} · bunker {fuel}", -66)))
        out += _wrap(f"your people knows {len(known)} elements: {', '.join(known)}")
    else:
        out.append(_row(("hold", -6), (f"ore {cg.ore} · organics {cg.organics} · equipment {cg.equipment} · "
                                       f"free {cg.available_space}", -66)))
    out.append(_band("ACTIONS"))
    out.append(c_gold("    [T] trade here   [O] routes") +
               (c_gold("   [Y] alchemy") if elemental else c_gold("   [F] freight board")) + c_gray("   [Q] back"))
    return out


def commodities_tab(kernel: Any, captain: Any) -> List[str]:
    return _goods(kernel, captain, elemental=False)


def elementals_tab(kernel: Any, captain: Any) -> List[str]:
    return _goods(kernel, captain, elemental=True)


# ---------------------------------------------------------------------- equities
def equities_tab(kernel: Any, captain: Any) -> List[str]:
    from xylarium.kernel import enterprise, liquidation
    mm = kernel.market_manager
    firms = enterprise.stats(kernel)["firms"]
    ls = liquidation.summary(kernel)
    out = [_band("LEDGER")]
    out.append(_row(("listed", -7), (str(len(mm.companies)), 4), ("distressed", -10), (str(ls["distressed"]), 3),
                    ("wound up", -8), (str(ls["liquidations"]), 4), ("defaults", -8), (str(ls["defaults"]), 3),
                    ("shorts won", -10), (_n(ls["short_pnl_sol"]), 7)))
    out.append(_band("LOCAL"))
    here = [c for c in mm.companies.values() if c.sector_id == captain.sector_id]
    if not here:
        out.append(c_gray("    no company is seated in this system"))

    def line(c: Any) -> str:
        fair = liquidation.fair_price(kernel, c)
        st = liquidation.standing(kernel, c.ticker)
        rec = firms.get(c.ticker)
        what = rec["process"] if rec else "-"
        return _row((c.ticker, -5), (c.name, -24), (_n(c.share_price), 6), (_n(fair, 1), 7), (what, -18),
                    (st, -9, c_red if st == "distressed" else c_green))

    if here:
        out.append(c_gray(_row(("tick", -5), ("company", -24), ("price", 6), ("fair", 7), ("makes", -18),
                               ("standing", -10))))
        out += [line(c) for c in here[:6]]
    out.append(_band("BRIDGED"))
    top = sorted(mm.companies.values(), key=lambda c: -c.share_price * c.total_shares)[:10]
    out.append(c_gray(_row(("tick", -5), ("company", -24), ("price", 6), ("fair", 7), ("makes", -18),
                           ("standing", -10))))
    out += [line(c) for c in top]
    out += _wrap("the ISSE's largest by market value · fair = the greater of estate and going concern, a share")
    out.append(_band("YOURS"))
    port = getattr(captain, "portfolio", {}) or {}
    shorts = getattr(captain, "short_positions", {}) or {}
    loans = getattr(captain, "margin_loans", {}) or {}
    if not (port or shorts or loans):
        out.append(c_gray("    no shares, shorts or margin loans"))
    for t, n in list(port.items())[:8]:
        c = mm.companies.get(t)
        if c is not None:
            out.append(_row((t, -5), (f"{n:,} shares", -14), (f"worth {_n(n * c.share_price)}", -16),
                            (f"margin owed {_n(loans.get(t, 0))}" if loans.get(t) else "", -22)))
    for t, pos in list(shorts.items())[:6]:
        out += _wrap(f"short {t}: {pos['shares']:,} @ {pos['entry_price']} (collateral {_n(pos['collateral'])})", c_magenta)
    out.append(_band("ACTIONS"))
    out.append(c_gold("    [B] buy  [S] sell  [H] short/cover  [R] boardroom  [M] corporate") + c_gray("  [Q] back"))
    return out


# ---------------------------------------------------------------------- FX
def fx_tab(kernel: Any, captain: Any) -> List[str]:
    from xylarium.kernel import liquidity, prices
    from xylarium.kernel.ledger import money_supply
    fxm = kernel.fx_market
    pol = kernel.monetary_policy
    supply = {c: b["total"] for c, b in money_supply(kernel).items()}
    out = [_band("LEDGER")]
    out.append(c_gray(_row(("money", -6), ("M/M*", 7), ("prices", 7), ("infl/q", 8), ("policy", 7), ("regime", -12))))
    from xylarium.kernel import regimes
    try:
        rg = regimes.summary(kernel).get("regimes", {})
    except Exception:
        rg = {}
    for cur in ["SOL", *sorted(fxm.pools)]:
        mstar = pol.current.get(cur)
        bank = kernel.banking.banks.get(cur)
        out.append(_row((cur, -6), (f"{supply.get(cur, 0) / mstar:.2f}" if mstar else "-", 7),
                        (f"{prices.level(cur, kernel):.2f}", 7), (f"{prices.inflation(kernel, cur):+.2%}", 8),
                        (f"{getattr(bank, 'policy_rate', 0.0):.2%}" if bank else "-", 7),
                        (str(rg.get(cur, "")) if isinstance(rg, dict) else "", -12)))
    out.append(_band("LOCAL"))
    sec = kernel.sectors.get(captain.sector_id)
    port = getattr(sec, "port", None)
    cur = port.currency if port is not None else None
    st = liquidity.stats(kernel)

    def pool(c: str) -> str:
        return _row((f"SOL/{c}", -9), (f"{fxm.rate(c):.3f}", 8), (f"{fxm.fee(c):.2%}", 7),
                    (_n(2 * fxm.pools[c]['sol']), 8), (f"{st['vol'].get(c, 0.0):.3f}", 6),
                    (str(len([h for h in st['positions'].get(c, {}) if h != liquidity.ISSE])), 4))

    hdr = c_gray(_row(("pool", -9), ("rate", 8), ("fee", 7), ("depth", 8), ("vol", 6), ("LPs", 4)))
    if cur and cur in fxm.pools:
        out.append(hdr)
        out.append(pool(cur))
        route = liquidity.goods_route(kernel, cur)
        out += _wrap(f"the traders' other road (goods at port spreads): {'-' if route is None else f'{route:.1%}'}")
    else:
        out.append(c_gray(f"    this system trades in {cur or 'no money'}: SOL is the numeraire"))
    out.append(_band("BRIDGED"))
    out.append(hdr)
    out += [pool(c) for c in sorted(fxm.pools)]
    for key, p in list(getattr(fxm, "cross_pools", {}).items())[:6]:
        out.append(c_gray(f"    cross {key}: {p['b'] / max(1e-9, p['a']):.3f}"))
    out.append(_band("YOURS"))
    wallet = {c: n for c, n in (captain.fx_wallet or {}).items() if n}
    out.append(_row(("SOL", -6), (_n(captain.credits), 10)))
    for c, n in wallet.items():
        out.append(_row((c, -6), (_n(n), 10), (f"≈ {_n(fxm.to_sol_value(c, n))} SOL", -16)))
    out.append(_band("ACTIONS"))
    out.append(c_gold("    [X] currency desk   [K] central banks") + c_gray("   [Q] back"))
    return out


RENDER: Dict[str, Callable[[Any, Any], List[str]]] = {"ENERGY": energy_tab, "COMMODITIES": commodities_tab,
                                                     "ELEMENTALS": elementals_tab, "EQUITIES": equities_tab,
                                                     "FX": fx_tab}


def render_markets(kernel: Any, captain: Any, tab: str = "ENERGY") -> str:
    return "\n".join(_header(kernel, captain, tab) + RENDER[tab](kernel, captain))


# ---------------------------------------------------------------------- the loop
def prompt_markets(cli: Any) -> None:
    tab = "ENERGY"
    by_key = dict(TABS)
    while True:
        captain = cli.kernel.captains[cli.player_id]
        print(render_markets(cli.kernel, captain, tab))
        try:
            cmd = input(c_gold("  Tab [1-5] or action > ")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            return
        if cmd in ("", "Q", "BACK", "EXIT"):
            return
        if cmd in by_key:
            tab = by_key[cmd]
            continue
        view = cli.kernel.get_player_view(cli.player_id)
        desks = {
            ("COMMODITIES", "T"): lambda: cli._prompt_trade(view), ("ELEMENTALS", "T"): lambda: cli._prompt_trade(view),
            ("COMMODITIES", "O"): lambda: cli._prompt_trade_routes(view),
            ("ELEMENTALS", "O"): lambda: cli._prompt_trade_routes(view),
            ("COMMODITIES", "F"): lambda: cli._prompt_freight_board(view),
            ("ELEMENTALS", "Y"): lambda: cli._prompt_alchemy(view),
            ("EQUITIES", "B"): lambda: cli._prompt_stock_buy(view), ("EQUITIES", "S"): lambda: cli._prompt_stock_sell(view),
            ("EQUITIES", "H"): lambda: cli._prompt_stock_short_cover(view),
            ("EQUITIES", "R"): lambda: cli._prompt_boardroom(view),
            ("EQUITIES", "M"): lambda: cli._prompt_corporate_machine(view),
            ("FX", "X"): lambda: cli._prompt_fx_desk(view), ("FX", "K"): cli._show_banking,
            ("ENERGY", "P"): lambda: cli._prompt_planet(view),
        }
        act = desks.get((tab, cmd[:1]))
        if act is None:
            print(c_red(f"  '{cmd}' is not an action on the {tab} tab."))
            continue
        act()
