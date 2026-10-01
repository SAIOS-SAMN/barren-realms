"""
Xylarium intellect: fluid intelligence a people proves by work, and the crystals it learns with.

Knowledge (knowledge.py) is what a people has stored. Fluid intelligence is what it can do with a problem it has
never seen. Here it is measured the way netstratum's proof of useful work measures it (engine/solver-verify):

  THE FORGE   Each quarter, from the settlement chain's last seal (randomness is a reading of history), a task is
              forged for every people at every rung: a word over the transformation vocabulary at the rung's
              tier and depth, applied to forged grids of the rung's shape - training pairs and a test. Rungs
              mirror netstratum's ladders for rank 2 (planar) and rank 3 (volumetric: the "in and out" axis).

  SOLVING     No search. The coordinate is read off the training pairs (crystal.read / read_stack), and the
              people decompacts it into its own program: the coordinate's address in its chart, the table of
              shortest words over the crystals (generators) it holds. It fails a rung when the coordinate lies
              outside what its crystals can express, or when the work - cells x (frame orbit + address length) -
              exceeds the thought it has this quarter (free labour x leisure x depth of mind: knowledge.effort).

  PROOF       Every claim carries its program and a hash-chained certificate; verifying is replay: re-forge the
              task from the beacon, re-apply the program to every pair and the test, re-chain. Cheap, total.

  THE GAUGE   A people's fluid intelligence is the highest rung it solves at each rank: a vector on orthogonal
              axes - rank (planar or volumetric), breadth (grid shape) and depth (word length).

What it does: every solved task is useful work and mints knowledge (difficulty x scarcity); fluid intelligence
carries a people further along every learning curve (knowledge.mastery) and steadies its judgement - longer
horizons, less noise (decide.py).

CRYSTALS are what a people learns with: every people begins with the quarter turn; reflections come with knowledge
of information, recolouring with biology, the stack operators ("in and out") with energy - discovered at a rate
set by its mastery and its thought. A composite it keeps writing is crystallised into a single generator
(abstraction), shortening its addresses. Crystals spread between neighbours as the knowing teach the less knowing
(Nelson-Phelps catch-up); relics carry the crystals of the dead; a people forgets what too few of its worlds hold,
less where households have the leisure to teach.
"""

import math
import random
import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import KNOWLEDGE_UNIT
from xylarium.kernel import crystal as C
from xylarium.kernel import laws

OPS_PER_UNIT = 1000          # a knowledge unit is a thousand elementary operations of thought
TOP = 8                      # netstratum's ladders run to rung 8
BASE = [C.ROT90]             # every mind can turn a thing around
DISCOVERABLE = {             # crystal -> the domain whose knowledge reveals it
    C.FLIPH: "information", C.FLIPV: "information", C.TRANSPOSE: "information",
    C.RECOLOR: "biology", C.FLIP_STACK: "energy", C.CYCLE_LAYERS: "energy",
    C.HYPER_FLIP: "energy", C.HYPER_CYCLE: "energy",
}
RANK_OF = {C.FLIPH: 2, C.FLIPV: 2, C.TRANSPOSE: 2, C.RECOLOR: 2, C.FLIP_STACK: 3, C.CYCLE_LAYERS: 3,
           C.HYPER_FLIP: 4, C.HYPER_CYCLE: 4}
VOLUMETRIC_WORLDS = ("GAS_GIANT", "OCEANIC")      # peoples born in volumes think in them first
ABSTRACT_AFTER = 3           # a composite written this many times is crystallised into one generator

# netstratum's rung ladders: level -> (tier, word length, shape, training pairs)
RUNGS = {
    2: {1: (1, 1, (3, 3), 2), 2: (1, 2, (4, 4), 2), 3: (2, 2, (4, 5), 3), 4: (3, 2, (3, 3), 3),
        5: (3, 3, (4, 4), 3), 6: (3, 4, (4, 4), 3), 7: (3, 5, (4, 5), 3), 8: (3, 6, (5, 5), 3)},
    3: {1: (1, 1, (2, 3, 3), 2), 2: (2, 2, (3, 3, 3), 2), 3: (2, 2, (3, 4, 4), 3), 4: (3, 3, (4, 4, 4), 3),
        5: (3, 3, (5, 4, 5), 3), 6: (3, 4, (5, 4, 5), 3), 7: (3, 5, (5, 5, 5), 3), 8: (3, 6, (5, 5, 5), 3)},
    # rank 4 - the fourth axis: a stack of volumes (beyond netstratum's ladders, on the same progression)
    4: {1: (1, 1, (2, 2, 3, 3), 2), 2: (2, 2, (2, 2, 3, 3), 2), 3: (2, 2, (2, 3, 3, 3), 3), 4: (3, 3, (3, 3, 3, 3), 3),
        5: (3, 3, (3, 3, 3, 4), 3), 6: (3, 4, (3, 3, 4, 4), 3), 7: (3, 5, (3, 4, 4, 4), 3), 8: (3, 6, (4, 4, 4, 4), 3)},
}


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "intellect")


def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


# ---------------------------------------------------------------------- the forge
def beacon(kernel: Any) -> str:
    chain = getattr(kernel, "settlement", None)
    blocks = getattr(chain, "blocks", None) or []
    return blocks[-1]["hash"] if blocks else f"genesis:{getattr(kernel, 'seed', 0)}"


def forge(seed: str, holder: str, rank: int, level: int) -> Dict[str, Any]:
    """A task, deterministic from (beacon, people, rank, level): the same everywhere, different every quarter."""
    tier, word_len, shape, n_train = RUNGS[rank][level]
    rng = random.Random(C.digest(seed, holder, rank, level))
    palette = rng.sample(range(C.HUES), 4)
    frames = list(C.FRAME_OPS)

    def planar_op():
        if tier >= 2 and rng.random() < 0.25:
            cmap = list(range(C.HUES))
            perm = palette[:]
            rng.shuffle(perm)
            for a, b in zip(palette, perm):
                cmap[a] = b
            return (C.RECOLOR, tuple(cmap))
        return rng.choice(frames)

    def grid(rows, cols):
        return tuple(tuple(rng.choice(palette) for _ in range(cols)) for _ in range(rows))

    def make():
        if rank == 4:
            return tuple(tuple(grid(shape[2], shape[3]) for _ in range(shape[1])) for _ in range(shape[0]))
        return tuple(grid(shape[1], shape[2]) for _ in range(shape[0])) if rank == 3 else grid(*shape)

    # a word that comes back to where it started (a flip twice) is no task at all: draw again
    while True:
        word: List[Any] = []
        for _ in range(word_len):
            if rank == 4 and rng.random() < 0.3:
                word.append(rng.choice(C.HYPER_OPS))
            elif rank == 4 and rng.random() < 0.4:
                word.append(("per_volume", rng.choice(C.STACK_OPS)))
            elif rank == 4:
                word.append(("per_volume", ("per_layer", planar_op())))
            elif rank == 3 and rng.random() < 0.4:
                word.append(rng.choice(C.STACK_OPS))
            else:
                op = planar_op()
                word.append(("per_layer", op) if rank == 3 else op)
        train = []
        for _ in range(n_train):
            x = make()
            train.append((x, C.run(word, x)))
        if any(x != y for x, y in train):
            break
    test = make()
    return {"seed": seed, "holder": holder, "rank": rank, "level": level, "train": train, "test": test,
            "expected": C.run(word, test), "id": C.digest(seed, holder, rank, level, train, test)}


def cells(task: Dict[str, Any]) -> int:
    shape = RUNGS[task["rank"]][task["level"]][2]
    return math.prod(shape)


# ---------------------------------------------------------------------- vocabulary
def norm(x: Any) -> Any:
    """Crystals come back from a save as nested lists; they are compared as nested tuples."""
    return tuple(norm(i) for i in x) if isinstance(x, (list, tuple)) else x


def vocabulary(kernel: Any, holder: str) -> List[Any]:
    v = stats(kernel)["vocab"].setdefault(holder, list(BASE))
    return [norm(x) for x in v]


def _frame_gens(vocab: List[Any]) -> List[Any]:
    return [g for g in vocab if g in C.FRAME_OPS or (isinstance(g, tuple) and g and g[0] == "composite")]


def _chart(vocab: List[Any]) -> Dict[Tuple[int, int], List[Any]]:
    """The people's chart over its frame crystals, composites included (each a frame element under one name)."""
    gens = _frame_gens(vocab)

    def element(g):
        if isinstance(g, tuple):
            a = C.IDENTITY
            for op in g[1]:
                a = C.compose(a, C.frame_of(op))
            return a
        return C.frame_of(g)
    table: Dict[Tuple[int, int], List[Any]] = {C.IDENTITY: []}
    frontier = [C.IDENTITY]
    while frontier:
        nxt = []
        for a in frontier:
            for g in gens:
                b = C.compose(a, element(g))
                if b not in table:
                    table[b] = table[a] + [g]
                    nxt.append(b)
        frontier = nxt
    return table


def _expand_op(op: Any) -> List[Any]:
    if isinstance(op, tuple) and op and op[0] == "composite":
        return [x for inner in op[1] for x in _expand_op(inner)]
    if isinstance(op, tuple) and op and op[0] in ("per_layer", "per_volume"):
        return [(op[0], x) for x in _expand_op(op[1])]
    return [op]


def expand(program: List[Any]) -> List[Any]:
    """Composites unfold into the ops they name, at any depth of nesting (the replay path speaks only the
    vocabulary itself)."""
    return [x for op in program for x in _expand_op(op)]


def _hyper_chart(vocab: List[Any], n: int) -> Dict[Tuple[int, int], List[Any]]:
    """The fourth axis charted like the third: the people's hyper crystals over n volumes."""
    as_stack = {C.HYPER_FLIP: C.FLIP_STACK, C.HYPER_CYCLE: C.CYCLE_LAYERS}
    back = {v: k for k, v in as_stack.items()}
    table = C.stack_chart([as_stack[g] for g in vocab if g in C.HYPER_OPS], n)
    return {k: [back[w] for w in word] for k, word in table.items()}


def _volumetric(vocab: List[Any], coord, layers: int) -> Optional[List[Any]]:
    """A rank-3 coordinate written in a people's crystals (stack word, then the per-layer frame and colour)."""
    shift, rev, (frame, cmap) = coord
    st = C.stack_chart([g for g in vocab if g in C.STACK_OPS], layers).get((shift, rev))
    fw = _chart(vocab).get(frame)
    if st is None or fw is None:
        return None
    prog = list(st) + [("per_layer", op) for op in fw]
    if tuple(cmap) != tuple(range(C.HUES)):
        if C.RECOLOR not in vocab:
            return None
        prog.append(("per_layer", (C.RECOLOR, tuple(cmap))))
    return prog


def decompact(vocab: List[Any], task: Dict[str, Any]) -> Optional[List[Any]]:
    """The program a people writes for a task: read the coordinate, look up its address in its own chart."""
    recolors = C.RECOLOR in vocab
    if task["rank"] == 4:
        coord = C.read_hyper(task["train"])
        if coord is None:
            return None
        shift, rev, inner = coord
        hw = _hyper_chart(vocab, len(task["test"])).get((shift, rev))
        body = _volumetric(vocab, inner, len(task["test"][0]))
        if hw is None or body is None:
            return None
        return list(hw) + [("per_volume", op) for op in body]
    if task["rank"] == 3:
        coord = C.read_stack(task["train"])
        return None if coord is None else _volumetric(vocab, coord, len(task["test"]))
    coord = C.read(task["train"])
    if coord is None:
        return None
    frame, cmap = coord
    fw = _chart(vocab).get(frame)
    if fw is None:
        return None
    prog = list(fw)
    if tuple(cmap) != tuple(range(C.HUES)):
        if not recolors:
            return None
        prog.append((C.RECOLOR, tuple(cmap)))
    return prog


def work(task: Dict[str, Any], program: List[Any]) -> int:
    """Operations of thought a solve costs: every cell through the frame orbit, and through each op it writes."""
    return cells(task) * (len(C.D4) + len(program))


# ---------------------------------------------------------------------- proof
def certificate(task: Dict[str, Any], program: List[Any]) -> Dict[str, Any]:
    """Parent-linked chain: the task, each op applied to the test input, the rendered output."""
    head = C.digest("task", task["id"])
    x = task["test"]
    for op in expand(program):
        x = C.run([op], x)
        head = C.digest(head, C.describe(op), x)
    return {"task": task["id"], "seed": task["seed"], "holder": task["holder"], "rank": task["rank"],
            "level": task["level"], "program": _wire(program), "head": head}


def _wire(program: List[Any]) -> List[Any]:
    def one(op):
        if isinstance(op, tuple) and op and op[0] == C.RECOLOR:
            return ["recolor", list(op[1])]
        if isinstance(op, tuple) and op and op[0] in ("per_layer", "per_volume"):
            return [op[0], one(op[1])]
        if isinstance(op, tuple) and op and op[0] == "composite":
            return ["composite", [one(x) for x in op[1]]]
        return op
    return [one(op) for op in program]


def _unwire(program: List[Any]) -> List[Any]:
    def one(op):
        if isinstance(op, list) and op and op[0] == "recolor":
            return (C.RECOLOR, tuple(op[1]))
        if isinstance(op, list) and op and op[0] in ("per_layer", "per_volume"):
            return (op[0], one(op[1]))
        if isinstance(op, list) and op and op[0] == "composite":
            return ("composite", tuple(one(x) for x in op[1]))
        return op
    return [one(op) for op in program]


def verify(cert: Dict[str, Any]) -> bool:
    """Replay, every leg or refuse: re-forge, re-apply to every pair and the test, re-chain. A claim with no path
    is refused (the empty program is the identity and would prove nothing)."""
    program = _unwire(cert.get("program") or [])
    if not program:
        return False
    task = forge(cert["seed"], cert["holder"], cert["rank"], cert["level"])
    if task["id"] != cert["task"]:
        return False
    flat = expand(program)
    if any(C.run(flat, x) != y for x, y in task["train"]) or C.run(flat, task["test"]) != task["expected"]:
        return False
    return certificate(task, program)["head"] == cert["head"]


# ---------------------------------------------------------------------- the quarter
def _peoples(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """Each people's thought this quarter (knowledge.effort over its worlds) and its worlds."""
    from xylarium.kernel import knowledge
    out: Dict[str, Dict[str, Any]] = {}
    years = _quarter() / 100.0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            h = knowledge.holder_of_planet(p)
            if not h:
                continue
            rec = out.setdefault(h, {"effort": 0.0, "worlds": [], "lux": 0.0, "aptitude": []})
            from xylarium.kernel import genome
            rec["aptitude"].append(genome.aptitude_factor(p))
            rec["effort"] += knowledge.effort(kernel, p) * years
            rec["worlds"].append(p)
            rec["lux"] = max(rec["lux"], float(p.society.get("lux_access", 0.0) or 0.0))
    return out


def gauge(kernel: Any, holder: str) -> Dict[str, int]:
    return stats(kernel)["gauge"].get(holder, {"2": 0, "3": 0, "4": 0})


def fluid(kernel: Any, holder: Optional[str]) -> float:
    """A people's fluid intelligence as a share of the ladders' height, 0 .. 1."""
    if not holder or kernel is None or not hasattr(kernel, "state") or "intellect" not in kernel.state:
        return 0.0
    g = gauge(kernel, holder)
    return (g.get("2", 0) + g.get("3", 0) + g.get("4", 0)) / (3.0 * TOP)


def _attempt(kernel: Any, holder: str, budget: float, seed: str) -> Tuple[Dict[str, int], List[Dict[str, Any]], float]:
    vocab = vocabulary(kernel, holder)
    reached = {"2": 0, "3": 0, "4": 0}
    proofs = []
    minted = 0.0
    st = stats(kernel)
    for rank in (2, 3, 4):
        for level in range(1, TOP + 1):
            task = forge(seed, holder, rank, level)
            program = decompact(vocab, task)
            if not program:
                break
            cost = work(task, program)
            if cost > budget:
                break
            # the coordinate fits every training pair by construction; a misread (pairs too symmetric to pin it)
            # shows on the test - then the work proves nothing. Full replay (verify) is for anyone checking later.
            if C.run(expand(program), task["test"]) != task["expected"]:
                break
            cert = certificate(task, program)
            budget -= cost
            reached[str(rank)] = level
            proofs.append(cert)
            # useful work mints knowledge: difficulty x scarcity (fewer peoples at this rung, the rarer the feat)
            peers = sum(1 for g in st["gauge"].values() if g.get(str(rank), 0) >= level)
            minted += (level / TOP) / (1 + peers)
            _remember(kernel, holder, program)
    return reached, proofs, minted


def _remember(kernel: Any, holder: str, program: List[Any]) -> None:
    """Abstraction: a composite the people keeps writing becomes one crystal (library learning, no search)."""
    frames = [op for op in program if op in C.FRAME_OPS]
    if len(frames) < 2:
        return
    key = "|".join(str(x) for x in frames)
    use = stats(kernel)["usage"].setdefault(holder, {})
    use[key] = use.get(key, 0) + 1
    if use[key] == ABSTRACT_AFTER:
        comp = ("composite", tuple(frames))
        v = stats(kernel)["vocab"].setdefault(holder, list(BASE))
        if comp not in {norm(x) for x in v}:
            v.append(comp)
            stats(kernel)["stats"]["abstractions"] += 1


def _learn(kernel: Any, holder: str, rec: Dict[str, Any], neighbours: List[str]) -> None:
    """Discovery from the people's own knowledge, teaching from the more knowing, forgetting what too few hold."""
    from xylarium.kernel import knowledge
    st = stats(kernel)
    v = st["vocab"].setdefault(holder, list(BASE))
    held = {norm(x) for x in v}
    stocks = knowledge.stocks(kernel, holder)
    rng = _rng("crystals", holder, kernel.cycle_count)
    thought = 1.0 - math.exp(-rec["effort"])
    # a people thinks first in the dimensions it was born into: volume-dwellers find the stack, surface-dwellers
    # the mirror (its most populous world is its home)
    home = max(rec["worlds"], key=lambda p: p.population) if rec["worlds"] else None
    native = 3 if (home is not None and home.planet_type in VOLUMETRIC_WORLDS) else 2
    for crystal, domain in DISCOVERABLE.items():
        if crystal in held:
            continue
        rank = RANK_OF.get(crystal, 2)
        if rank == 4 and not all(s in held for s in C.STACK_OPS):
            continue                                  # a fourth axis cannot be conceived before the third
        chance = laws.mastery(stocks.get(domain, 0.0), KNOWLEDGE_UNIT) * thought * (2.0 if rank == native else 1.0)
        if rank == 4:
            chance *= laws.mastery(stocks.get("information", 0.0), KNOWLEDGE_UNIT)   # it takes both
        if rng.random() < chance:
            v.append(crystal)
            held.add(crystal)
            st["stats"]["discovered"] += 1
    me = fluid(kernel, holder)
    for other in neighbours:                      # the knowing teach the less knowing, at the gap between them
        gap = fluid(kernel, other) - me
        if gap <= 0:
            continue
        for crystal in vocabulary(kernel, other):
            if not grounded(crystal, held):
                continue                              # what cannot yet be understood cannot be taught
            if crystal not in held and rng.random() < gap:
                v.append(crystal)
                held.add(crystal)
                st["stats"]["taught"] += 1
    # forgetting: knowledge's own depreciation, spread over the worlds that hold it, less where households teach
    years = _quarter() / 100.0
    forgetful = sum(rec.get("aptitude") or [1.0]) / max(1, len(rec.get("aptitude") or [1.0]))   # heritable
    lose = (1.0 - (1.0 - laws.KNOWLEDGE_DEPRECIATION) ** years) * (1.0 - rec["lux"]) / max(1, len(rec["worlds"])) \
        * forgetful
    keep = []
    for crystal in v:
        if norm(crystal) not in BASE and rng.random() < lose:
            st["stats"]["forgotten"] += 1
            continue
        keep.append(crystal)
    st["vocab"][holder] = keep


def _neighbours(kernel: Any, peoples: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Peoples whose worlds share a system or a lane."""
    from xylarium.kernel import topology
    by_sector: Dict[int, set] = {}
    for h, rec in peoples.items():
        for p in rec["worlds"]:
            by_sector.setdefault(p.sector_id, set()).add(h)
    out: Dict[str, List[str]] = {}
    for h, rec in peoples.items():
        near = set()
        for p in rec["worlds"]:
            for sid in topology.reach(kernel, p.sector_id, 1):
                near |= by_sector.get(sid, set())
        near.discard(h)
        out[h] = sorted(near)
    return out


def grounded(crystal: Any, held: set) -> bool:
    """A fourth axis cannot be understood - discovered, taught or read from a relic - before the third."""
    return RANK_OF.get(crystal, 2) < 4 or all(s in held for s in C.STACK_OPS)


def relic_crystal(kernel: Any, holder: str, relic_id: str) -> Optional[Any]:
    """A relic carries the crystal its makers last wrote: a discoverable one, by the relic's own hash - legible
    only to a people with the foundations to read it."""
    choices = sorted(DISCOVERABLE, key=str)
    crystal = choices[zlib.crc32(str(relic_id).encode()) % len(choices)]
    v = stats(kernel)["vocab"].setdefault(holder, list(BASE))
    held = {norm(x) for x in v}
    if crystal in held or not grounded(crystal, held):
        return None
    v.append(crystal)
    stats(kernel)["stats"]["from_relics"] += 1
    return crystal


def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import knowledge
    st = stats(kernel)
    peoples = _peoples(kernel)
    seed = beacon(kernel)
    near = _neighbours(kernel, peoples)
    for holder, rec in peoples.items():
        _learn(kernel, holder, rec, near.get(holder, []))
    for holder, rec in peoples.items():
        budget = rec["effort"] * OPS_PER_UNIT
        reached, proofs, minted = _attempt(kernel, holder, budget, seed)
        st["gauge"][holder] = reached
        st["proofs"][holder] = proofs[-2:]               # the hardest planar and volumetric feats, for anyone to check
        if minted > 0:
            knowledge.learn(kernel, holder, "information", minted, "useful_work")
        st["stats"]["solved"] += len(proofs)
    for gone in [h for h in st["gauge"] if h not in peoples]:      # a people that is no more proves nothing
        st["gauge"].pop(gone, None)
        st["proofs"].pop(gone, None)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    g = st["gauge"]
    top = sorted(g.items(), key=lambda kv: -sum(kv[1].get(r, 0) for r in ("2", "3", "4")))[:5]
    by_kind: Dict[str, List[float]] = {}
    for h in g:
        by_kind.setdefault(h.partition(":")[0], []).append(fluid(kernel, h))
    vocab_sizes = [len(v) for v in st["vocab"].values()]
    return {"peoples": len(g), "top": {h: v for h, v in top},
            "mean_fluid": {k: round(sum(v) / len(v), 3) for k, v in by_kind.items()},
            "volumetric_peoples": sum(1 for v in g.values() if v.get("3", 0) > 0),
            "fourth_axis_proven": sum(1 for v in g.values() if v.get("4", 0) > 0),
            "interdimensional_peoples": sum(1 for h in st["vocab"] if any(norm(c) in C.HYPER_OPS
                                                                            for c in st["vocab"][h])),
            "vocab_mean": round(sum(vocab_sizes) / len(vocab_sizes), 2) if vocab_sizes else 0,
            **st["stats"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="intellect",
    state=lambda: {"vocab": {}, "gauge": {}, "proofs": {}, "usage": {},
                   "stats": {"solved": 0, "discovered": 0, "taught": 0, "forgotten": 0, "abstractions": 0,
                             "from_relics": 0}},
    season=quarter,
    summary=summary,
))
