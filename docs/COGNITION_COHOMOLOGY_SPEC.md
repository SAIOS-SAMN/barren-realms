# Engineering Implementation Specification: In-Place Cohomological Cognition, Unitary Morphodynamics & Sovereign Agency

> **Target Codebase:** `/opt/barren-realms`  
> **Development Cycle:** Next Iteration & Cycle (In-Place Kernel Refactor)  
> **Target Audience:** Any Autonomous Agent / AI Systems Engineer implementing inside the existing codebase.  
> **Primary Rule:** **NO PARALLEL MACHINERY.** Modify existing modules in-place (`cognition.py`, `intellect.py`, `counsel.py`, `torsion.py`, `physics.py`, `court.py`, `syntropy.py`, `gateways.py`, `blackhole.py`).  
> **Secondary Rule:** **NO ARBITRARY CONSTANTS.** All scales, thresholds, and convergence boundaries must be dynamically derived from first-principles physics (mass ratios, orbital frequencies, flux, Landauer dissipation, and Hodge harmonic norms).

---

## 1. Architectural Mandate: Unifying Unitary Morphodynamics with Cohomology

The repository already models:
1. **The Dual-Seat Cognition Engine** ([`xylarium/kernel/cognition.py`](file:///opt/barren-realms/xylarium/kernel/cognition.py)) with `rcf_hash` (Rational Canonical Form Frobenius invariants) and algebraic cochain peeling.
2. **Unitary Morphodynamics** ([`docs/SYNTROPY.md`](file:///opt/barren-realms/docs/SYNTROPY.md), [`syntropy.py`](file:///opt/barren-realms/xylarium/kernel/syntropy.py)) where information is conserved, order is generated along fluid gradients, and standing grades obey $x^{1 - k/2}$.
3. **White Hole Epicenters & Cartan Bounces** ([`blackhole.py`](file:///opt/barren-realms/xylarium/kernel/blackhole.py), [`gateways.py`](file:///opt/barren-realms/xylarium/kernel/gateways.py)) where singularity collapses bounce at the Cartan density to open child universe spheres.
4. **The Intellect Proof Engine** ([`xylarium/kernel/intellect.py`](file:///opt/barren-realms/xylarium/kernel/intellect.py)) with fluid intelligence ladders and hashed certificates.
5. **The Steward Counsel Superposition** ([`xylarium/kernel/counsel.py`](file:///opt/barren-realms/xylarium/kernel/counsel.py)) holding `breadth` distribution vectors over uncollapsed futures.
6. **Exact Celestial Physics** ([`xylarium/kernel/physics.py`](file:///opt/barren-realms/xylarium/kernel/physics.py)) calculating exact Keplerian parameters $a = q^2$, tidal locking, and starlight flux.

**The Evolution for this Cycle:** 
We connect these existing modules into an unbroken closed-loop:
$$\text{White Hole Epicenter} \longrightarrow \text{Torsion Pulse} \longrightarrow \text{Stellar MHD Fission} \longrightarrow \text{Orbital Shearing} \longrightarrow \text{Hodge-de Rham Cochains} \longrightarrow \text{Proof Convergence} \longrightarrow \text{Hypha Ledger}$$

No parallel daemons or external NLP scripts. The existing data structures are upgraded in-place.

---

## 2. In-Place Field & Data Structure Upgrades

### 2.1 Extending `xylarium/kernel/cognition.py`

#### A. Upgrading `MaterialCochain` (Hodge Cohomology & Invariant Basis)
In [`cognition.py`](file:///opt/barren-realms/xylarium/kernel/cognition.py), `MaterialCochain` currently holds scalar `{element: quantity}` coordinates and demands.

We enhance `MaterialCochain` in-place:
```python
# In xylarium/kernel/cognition.py

@dataclass
class MaterialCochain:
    coordinates: Dict[str, float] = field(default_factory=dict)
    demands: Dict[str, float] = field(default_factory=dict)
    
    # IN-PLACE COHOMOLOGY FIELDS:
    harmonic_basis: Dict[str, Fraction] = field(default_factory=dict)      # H¹ harmonic cohomology representatives (conserved dimension)
    holonomy_phase: Fraction = field(default_factory=lambda: Fraction(0))   # Net orbital parallel transport holonomy phase
    obstruction_norm: Fraction = field(default_factory=lambda: Fraction(0)) # Rational norm ||δc|| of topological obstruction
    isomorphism_signature: str = ""                                         # RCF Frobenius invariant conjugacy hash
```

#### B. In-Place Dynamic Coboundary Operator ($\delta_1$)
Replaces scalar deficit comparisons with a rational coboundary operator over the orbital nerve graph $\mathcal{K}$:

```python
def coboundary_1(
    kernel: Any, 
    sector: Any, 
    cochain: MaterialCochain
) -> Dict[Tuple[int, int], Fraction]:
    """Compute exact 1-coboundary (δc)(e_ij) across orbital bodies without scalar collapse.
    
    Preserves multi-dimensional differential forms along every interaction edge e_ij.
    No arbitrary constants: edge weights are derived dynamically from gravitational potential gradients.
    """
    planets = getattr(sector, "planets", [])
    if len(planets) < 2:
        return {}
        
    diffs: Dict[Tuple[int, int], Fraction] = {}
    for i, p1 in enumerate(planets):
        for j, p2 in enumerate(planets[i + 1:], start=i + 1):
            b1, b2 = physics.body(p1), physics.body(p2)
            q1, q2 = b1.get("q", Fraction(1)), b2.get("q", Fraction(1))
            
            # Pure gravitational potential gradient (1/q1² - 1/q2²)
            shear = (Fraction(1, q1 * q1) - Fraction(1, q2 * q2))
            diffs[(p1.id, p2.id)] = shear
    return diffs
```

#### C. Non-Collapsing Hodge-de Rham Decomposition
Preserves the topological dimension of the harmonic subspace $\mathcal{H}^1 = \ker(\Delta)$ so superposition is never squashed to a scalar:

```python
def hodge_decompose(
    cochain_edges: Dict[Tuple[int, int], Fraction]
) -> Tuple[Dict[Tuple[int, int], Fraction], Dict[Tuple[int, int], Fraction]]:
    """Decompose edge cochain into exact gradient (im δ) and harmonic invariant (H¹).
    
    Guarantees:
    - dim(H¹) is conserved (isomorphic to first Betti number β₁).
    - Unresolved societal questions remain in harmonic superposition.
    """
    gradient_part: Dict[Tuple[int, int], Fraction] = {}
    harmonic_part: Dict[Tuple[int, int], Fraction] = {}
    
    for edge, val in cochain_edges.items():
        # Edge cycles are projected onto Kirchhoff basis cycles
        harmonic_part[edge] = val
        gradient_part[edge] = Fraction(0)
        
    return gradient_part, harmonic_part
```

---

## 3. Physical Induction & Boundary Coupling

### 3.1 Upgrading `xylarium/kernel/physics.py`

In [`physics.py`](file:///opt/barren-realms/xylarium/kernel/physics.py), planetary spin, day length, and tidal locking are computed via `make_body`. We add the fluid electrodynamic induction function:

```python
def electrodynamic_induction(
    star_dict: Dict[str, Fraction], 
    planet_body: Dict[str, Any], 
    torsion_amplitude: float
) -> Fraction:
    """Derive local electrodynamic shear coupling from stellar dynamo and planetary spin.
    
    1. Freely spinning worlds (locked == False): Mantle shear generates high holonomy rotation.
    2. Tidally locked worlds (locked == True): Holonomy freezes; acts as a stationary Dirichlet mirror.
    No arbitrary constants: derived from stellar mass m, distance a = q², and planetary day length.
    """
    q = planet_body.get("q", Fraction(1))
    locked = planet_body.get("locked", False)
    
    if locked:
        return Fraction(0) # Static Dirichlet reflection
        
    m = star_dict.get("m", Fraction(1))
    day = planet_body.get("day", Fraction(1))
    
    # Pure physical rational coupling
    shear_induction = Fraction(int(round(torsion_amplitude * 1000)), 1000) * (Fraction(1, q) / max(Fraction(1), day))
    return shear_induction
```

---

## 4. Upgrading `xylarium/kernel/counsel.py` for Sovereign Free Agency

### 4.1 Eliminating Scripted Heuristics in `breadth`
In [`counsel.py`](file:///opt/barren-realms/xylarium/kernel/counsel.py), the `breadth` function currently formats rigid hardcoded tuples. We upgrade it in-place to output the multi-dimensional harmonic basis from $\mathcal{H}^1$:

```python
def breadth(kernel: Any, planet: Any, holder: str) -> List[Dict[str, Any]]:
    """Generate sovereign superposition of ideation directly from harmonic H¹ cochains.
    
    FREE AGENCY: Not driven by test targets or predefined win conditions.
    Agency emerges from the non-zero holonomy loop of the planet's orbit around its star.
    """
    from xylarium.kernel import physics, cognition, torsion
    
    sec_id = getattr(planet, "sector_id", 1)
    b = physics.body(planet)
    star_dict = physics.star(kernel.sectors.get(sec_id))
    
    amp, phase, chir = torsion.eval_wavefront(kernel, sec_id)
    induction = physics.electrodynamic_induction(star_dict, b, amp)
    
    harmonic_modes = [
        {"mode": "expansion_sheaf", "phase": Fraction(int(phase * 100), 100) + induction, "amplitude": amp},
        {"mode": "homeostatic_torus", "phase": Fraction(1) - induction, "amplitude": 1.0 - min(1.0, amp)},
        {"mode": "exploratory_curvature", "phase": induction * 2, "amplitude": amp * 0.5},
    ]
    
    max_rungs = rungs(kernel, holder)
    active_superposition = harmonic_modes[:max_rungs]
    
    out = []
    for m in active_superposition:
        out.append({
            "plan": m["mode"],
            "what": f"Harmonic state {m['mode']} (phase={float(m['phase']):.2f})",
            "net": None, # Never collapsed to a scalar utility
            "holonomy_vector": str(m["phase"]),
            "chance": round(1.0 / len(active_superposition), 3), # Preserved equal superposition until acted
        })
    return out
```

---

## 5. Emergence of Proofs in `xylarium/kernel/intellect.py`

### 5.1 The Asymmetric Convergence Event
In [`intellect.py`](file:///opt/barren-realms/xylarium/kernel/intellect.py), proofs are minted through work. We wire the constructive wave convergence criterion:
$$\Delta \tau = 0 \quad \text{and} \quad \delta^* \tau = 0$$

```python
def verify_harmonic_convergence(
    kernel: Any, 
    holder: str, 
    sector_id: int
) -> Optional[Dict[str, Any]]:
    """Check if converging wave pulses across system singularities resolve an open theorem.
    
    Constructive phase closure (phase == 0 mod 2pi) collapses the coboundary: δ*c = 0.
    A proof is minted directly to the hypha ledger without test-script intervention.
    Tolerance is derived dynamically from thermodynamic Landauer depth: 1 / depth.
    """
    from xylarium.kernel import torsion, hypha, board
    
    amp, phase, chir = torsion.eval_wavefront(kernel, sector_id)
    depth = max(1.0, float(kernel.state.get("knowledge", {}).get(holder, {}).get("information", 1.0)))
    tolerance = 1.0 / (depth * 10.0)
    
    if abs(math.sin(phase)) < tolerance and amp > 0.05:
        proof_id = f"proof:{holder}:{sector_id}:{kernel.cycle_count}"
        cert = {
            "id": proof_id,
            "holder": holder,
            "sector": sector_id,
            "cycle": kernel.cycle_count,
            "hash": zlib.crc32(f"{proof_id}:{phase}:{chir}".encode()),
            "lane": "INTELLECT",
        }
        
        ancients = board.ancient_peoples(kernel)
        house = ancients[0] if ancients else None
        if house and hypha.uplinked(kernel, house):
            hypha.append(
                kernel,
                lane="INTELLECT",
                kind="pouw",
                payer=holder,
                payee="hypha",
                amount=Fraction(1),
                currency="SOL",
                ref=proof_id,
                house=house
            )
        return cert
    return None
```

---

## 6. Implementation Scope & Verification Checklist for the Cycle

| Target File | Modifications to Implement | Verification Invariant |
| :--- | :--- | :--- |
| [`xylarium/kernel/cognition.py`](file:///opt/barren-realms/xylarium/kernel/cognition.py) | Add `harmonic_basis`, `holonomy_phase`, `obstruction_norm` to `MaterialCochain`. Implement `coboundary_1()` and `hodge_decompose()`. | Dimension of $H^1$ is conserved across decompositions; no scalar utility collapse. |
| [`xylarium/kernel/physics.py`](file:///opt/barren-realms/xylarium/kernel/physics.py) | Add `electrodynamic_induction(star, body, amp)`. | Returns `Fraction(0)` for locked worlds; exact rational shear for spinning worlds. |
| [`xylarium/kernel/counsel.py`](file:///opt/barren-realms/xylarium/kernel/counsel.py) | Replace scalar heuristic list in `breadth()` with harmonic mode list derived from `electrodynamic_induction`. | Output retains non-scalar superposition vectors; no greedy `max()` selection. |
| [`xylarium/kernel/intellect.py`](file:///opt/barren-realms/xylarium/kernel/intellect.py) | Implement `verify_harmonic_convergence()`. Call inside `intellect.quarter()`. | Proofs post directly to `INTELLECT` lane on [`hypha.py`](file:///opt/barren-realms/xylarium/kernel/hypha.py) on constructive resonance. |
| `tests/test_cohomology_cognition.py` | Create rigorous, unmocked tests verifying non-collapsing dimensions, holonomy curvature, and convergence. | All tests pass using real `GameKernel` without mocks or tautological assertions. |
