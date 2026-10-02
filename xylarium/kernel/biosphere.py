"""
Xylarium biosphere: light and land become food, and food becomes people.

Everything here is derived from the world's physics (physics.py) and a handful of biological constants
(config [15]):

  * Light fit. Each metabolism's energy peaks at a flux F* (biotic life at Earth's light, cryogenic life in
    the cold, mineral life on hot rock, umbral life in the dark; plasmic life feeds on a giant's heat, its
    mass). With x = flux / F*, the fit is 4x / (1+x)^2: exactly 1 at the optimum, falling away on both sides.
  * Season. Axial tilt shortens the growing season (1 - tilt/90); a tidally locked world farms only its
    terminator band (half).
  * Carrying capacity K = people-per-Earth-area x tech yield x [surface area x surface chemistry fit x light
    fit x season + enclosed habitat area]. Nothing is looked up by citadel tier except agricultural
    technology; a bigger, better-lit, gentler world feeds more people.
  * Food. Farms produce what the land can yield up to K's needs; consumption is FOOD_PER_THOUSAND per
    thousand people per cycle.
  * Growth is logistic toward K, and never faster than the farms can grow food: r = min(birth rate,
    crop surplus rate x light fit x season). A people can only multiply as fast as its harvests.
    Fractional births are carried exactly from cycle to cycle (nothing is rounded away).
"""

from fractions import Fraction as F
from typing import Any, Dict, Optional

from xylarium.config import (
    BIRTH_RATE,
    CROP_SURPLUS_RATE,
    FOOD_PER_THOUSAND,
    HABITAT_AREA,
    LIGHT_OPTIMUM,
    PEOPLE_PER_EARTH_AREA,
    PLASMIC_MASS_OPTIMUM,
    TECH_YIELD,
)
from xylarium.kernel import physics

_BIRTH = F(BIRTH_RATE)
_CROP = F(CROP_SURPLUS_RATE)
_HAB_AREA = F(HABITAT_AREA)
_TECH = {int(k): F(v) for k, v in TECH_YIELD.items()}
_OPT = {k: F(v) for k, v in LIGHT_OPTIMUM.items()}
_YEAR = physics.CYCLES_PER_STANDARD_YEAR
GIANT_LIVING_BAND = F(1, 20)


def _kernel(kernel: Any = None) -> Any:
    if kernel is not None:
        return kernel
    from xylarium.kernel import ledger
    return ledger.active_kernel()


def metabolism_of(kernel: Any, planet: Any) -> str:
    """The biology of the people who live there: a civilization if one does, else the owner's colonists."""
    civ = getattr(planet, "civilization", None)
    if civ is not None and getattr(civ, "metabolism", None):
        return civ.metabolism
    kept = (getattr(planet, "society", None) or {}).get("people_metab")
    if kept:
        return kept                                    # a people taken by force keeps its biology (occupation.py)
    owner = kernel.captains.get(planet.owner_id) if (kernel is not None and planet.owner_id) else None
    return (getattr(owner, "metabolism", None) if owner is not None else None) or "biotic"


def light_fit(metabolism: str, flux: F, planet: Any, optimum: Optional[F] = None) -> F:
    if metabolism == "plasmic":
        x = physics.body(planet).get("mass", F(1)) / PLASMIC_MASS_OPTIMUM
    else:
        x = flux / (optimum if optimum else _OPT.get(metabolism, F(1)))
    return 4 * x / ((1 + x) ** 2)


def adapt(kernel: Any, civ: Any, planet: Any) -> None:
    """A species is adapted to the world it evolved on: its surface, and the light it was born under."""
    if civ is None or getattr(civ, "light_optimum", None):
        return
    sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
    fl = physics.planet_flux(sec, planet) if sec is not None else F(1)
    civ.home_type = planet.planet_type
    civ.light_optimum = f"{fl.numerator}/{fl.denominator}" if fl > 0 else "1/1"
    g = physics.surface_gravity(planet)
    civ.home_gravity = f"{g.numerator}/{g.denominator}" if g > 0 else "1/1"


def _people(kernel: Any, planet: Any) -> Any:
    """The civilization living on a world (indigenous, great power, or annexed by a captain)."""
    return getattr(planet, "civilization", None)


def season(planet: Any) -> F:
    b = physics.body(planet)
    if b.get("locked"):
        return F(1, 2)
    return 1 - F(int(b.get("tilt", 0)), 90)


def _surface_fit(metabolism: str, planet_type: str) -> F:
    from xylarium.kernel.universe import habitability
    return F(str(habitability(metabolism, planet_type)))


def land(kernel: Any, planet: Any, metabolism: Optional[str] = None) -> Dict[str, F]:
    """The world's natural capacity for a people of ``metabolism`` (independent of technology)."""
    kernel = _kernel(kernel)
    metab = metabolism or metabolism_of(kernel, planet)
    sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
    fl = physics.planet_flux(sec, planet) if sec is not None else F(1)
    civ = _people(kernel, planet) if metabolism is None else None
    if civ is not None and not getattr(civ, "light_optimum", None):
        adapt(kernel, civ, planet)             # first sight of a people is its homeworld (genesis, first flight)
    optimum = F(civ.light_optimum) if (civ is not None and civ.light_optimum) else None
    from xylarium.kernel import genome
    if metabolism is None and metab != "plasmic":
        # the people's genome tunes its light (optimum x e^light) and widens it (tolerance, at constant area)
        optimum = (optimum if optimum else _OPT.get(metab, F(1))) * genome.fraction(genome.optimum_factor(planet))
        x = float(fl / optimum) if optimum else 1.0
        fit = genome.fraction(genome.tuned_fit(float(light_fit(metab, fl, planet, optimum)), x,
                                               genome.value(planet, "tolerance")))
    else:
        fit = light_fit(metab, fl, planet, optimum)
    chemistry = F(1) if (civ is not None and civ.home_type == planet.planet_type) else _surface_fit(metab, planet.planet_type)
    if metabolism is None and chemistry < 1:
        chemistry = genome.fraction(genome.adapted_chemistry(float(chemistry), planet))   # a people adapts
    if (getattr(planet, "society", None) or {}).get("terraform"):
        from xylarium.kernel import terraform                  # ... or its world is made over (terraform.py)
        chemistry = genome.fraction(terraform.reshape(float(chemistry), metab, planet))
    area = physics.surface_area(planet)
    if physics.body(planet).get("giant"):
        area = area * GIANT_LIVING_BAND        # life on a giant lives in a band of its clouds
    return {"area": area, "chemistry": chemistry, "light": fit, "season": season(planet)}


MICRO = 1_000_000          # growth and food rates are carried as integer millionths (exact, bounded)


def _profile(kernel: Any, planet: Any, citadel: Optional[int] = None, habitats: Optional[int] = None,
             metabolism: Optional[str] = None) -> Dict[str, int]:
    """K and the world's growth rate (per cycle, in millionths), cached until the world or its people change."""
    kernel = _kernel(kernel)
    tier = planet.citadel_level if citadel is None else citadel
    habs = getattr(planet, "habitats", 0) if habitats is None else habitats
    metab = metabolism or metabolism_of(kernel, planet)
    civ = getattr(planet, "civilization", None)
    tailings = (getattr(planet, "element_deposits", {}) or {}).get("TAILINGS", 0)
    from xylarium.kernel import genome
    from xylarium.kernel import cosmos
    key = (tier, habs, metab, planet.planet_type, str(getattr(planet, "body", None)), planet.owner_id,
           cosmos.lum(planet.sector_id),
           getattr(civ, "light_optimum", None), tailings // 500,
           round(genome.value(planet, "light"), 3), round(genome.value(planet, "tolerance"), 3),
           round(genome.value(planet, "chemistry"), 3), str((getattr(planet, "society", None) or {}).get("terraform")),
           round(genome.value(planet, "birth"), 3), round(genome.value(planet, "temperature"), 3),
           getattr(civ, "clade", None))
    if citadel is None and habitats is None and metabolism is None and kernel is not None \
            and hasattr(kernel, "caches"):
        from xylarium.kernel import cache
        return cache.stamped(kernel, "k_profile", planet.id, key, lambda: _reckon(kernel, planet, None, tier, habs))
    return _reckon(kernel, planet, metabolism, tier, habs)


def _reckon(kernel: Any, planet: Any, metabolism: Optional[str], tier: int, habs: int) -> Dict[str, int]:
    ld = land(kernel, planet, metabolism)
    if metabolism is not None:                             # a body not yet living here (a design, a forecast)
        from xylarium.config import METABOLISM_STRATEGY
        sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
        nf = metabolic_factor(metabolism, METABOLISM_STRATEGY.get(metabolism, "K"),     # bred for this world
                              home_flux=float(physics.planet_flux(sec, planet)) if sec is not None else None,
                              home_gravity=float(physics.surface_gravity(planet)))
    else:
        nf = need_factor(planet, kernel)
    natural = ld["area"] * ld["chemistry"] * ld["light"] * ld["season"]
    from xylarium.kernel.geology import pollution_factor
    k = int(PEOPLE_PER_EARTH_AREA * _TECH.get(tier, _TECH[max(_TECH)]) * (natural + _HAB_AREA * habs)
            * pollution_factor(planet) / F(nf).limit_denominator(10 ** 6))              # Damuth's law
    food = _CROP * ld["light"] * ld["season"]
    rate = min(_BIRTH, food) if k > 0 else F(0)
    prof = {"k": k, "food_rate_micro": int(food * MICRO), "rate_micro_per_cycle": int(rate * MICRO / _YEAR),
            "birth_micro_per_cycle": int(_BIRTH * MICRO / _YEAR) if k > 0 else 0,
            "food_micro_per_cycle": int(food * MICRO / _YEAR) if k > 0 else 0}
    return prof


def carrying_capacity(kernel: Any, planet: Any, citadel: Optional[int] = None, habitats: Optional[int] = None,
                      metabolism: Optional[str] = None) -> int:
    """K: how many people this world can feed at its technology - less what a stripped atmosphere no longer
    shelters (harvest.py: a stalled dynamo lets the stars' wind take the air)."""
    k = _profile(kernel, planet, citadel, habitats, metabolism)["k"]
    soc = getattr(planet, "society", None) or {}
    air = float(soc.get("atmosphere", 1.0))
    way = float(soc.get("way_k", 1.0))                 # foragers live a link up the food chain (ways.py)
    sun = float(soc.get("star_k", 1.0))                # a star ageing past its main sequence (cosmos.py)
    if air >= 1.0 and way >= 1.0 and sun >= 1.0:
        return k
    return int(k * min(1.0, air) * min(1.0, way) * max(0.0, min(1.0, sun)))


def food_rate(kernel: Any, planet: Any) -> F:
    """Per standard year: how fast this world's farms can add food (the crops' own threshold)."""
    return F(_profile(kernel, planet)["food_rate_micro"], MICRO)


def growth_rate(kernel: Any, planet: Any) -> F:
    """A people multiplies no faster than its farms can feed the newcomers (per standard year)."""
    return F(_profile(kernel, planet)["rate_micro_per_cycle"] * _YEAR, MICRO)


def harvest(kernel: Any, planet: Any, k: int) -> int:
    """Organics the farms bring in this cycle: the land's yield, up to what K people would eat.
    Farmers feed themselves and a quarter more, up to the land; the fraction of a unit is carried."""
    fed = min(planet.population * 5 // 4, k)
    total = int(fed * FOOD_PER_THOUSAND * need_factor(planet, kernel)) + int(getattr(planet, "harvest_carry", 0) or 0)
    planet.harvest_carry = total % 1000
    return total // 1000


# ---------------------------------------------------------------------- what a body burns (metabolic theory)
GRAVITY_MASS_POWER = 3.0        # square-cube: a skeleton's stress ~ M^(1/3) g, so the bodies a world bears ~ g^-3


def metabolic_factor(metabolism: str, strat: str, birth: float = 1.0, temperature: float = 1.0,
                     home_flux: Optional[float] = None, home_gravity: Optional[float] = None) -> float:
    """A body's need, per head, over a K-strategist carbon body's on Earth under the Sun (Brown et al. 2004, the
    metabolic theory of ecology): B ~ M^(3/4) x the kinetic pace of its chemistry at its body's temperature.

      temperature  its homeworld's: the light it evolved under - its star's luminosity over its orbit squared -
                   at radiative equilibrium (Stefan-Boltzmann); plasmic minds run in ionised hydrogen. Pace ~ sqrt T.
      mass         from its homeworld's gravity (square-cube: the bodies a world supports scale as g^-3 - a light
                   world grows large, hungry bodies; a heavy one small, frugal ones; a plasmic body has no frame to
                   bear) and its life history (a generation ~ M^(1/4): r-strategists are small, K large;
                   fertility.CEILING x its heritable birth factor).

    The land holds inversely many such bodies (Damuth's law): a world's yield is the same food, divided by size."""
    from xylarium.kernel import fertility, laws
    c = fertility.CEILING.get(strat, fertility.CEILING["K"]) * max(1e-6, birth)
    mass = (fertility.CEILING["K"] / c) ** 4
    if metabolism == "plasmic":
        t = laws.T_PLASMA * temperature
    else:
        t = laws.stefan_boltzmann_temperature(home_flux if home_flux else float(_OPT.get(metabolism, F(1)))) \
            * temperature
        mass *= max(1e-3, home_gravity if home_gravity else 1.0) ** -GRAVITY_MASS_POWER
    return mass ** 0.75 * laws.thermal_speed(t)


def home_flux(planet: Any) -> Optional[float]:
    """The light this world's people evolved under (its homeworld's), if known."""
    civ = getattr(planet, "civilization", None)
    return float(F(civ.light_optimum)) if civ is not None and getattr(civ, "light_optimum", None) else None


def cognition_of(kernel: Any, planet: Any) -> dict:
    """This world's people's minds (laws.cognition) at its own homeworld's temperature, as its genome tunes them."""
    from xylarium.kernel import genome, laws
    return laws.cognition(metabolism_of(_kernel(kernel), planet), genome.temperature_factor(planet), home_flux(planet))


def need_factor(planet: Any, kernel: Any = None) -> float:
    """This world's people's metabolic factor (its species, as its genome has drifted)."""
    from xylarium.kernel import fertility, genome
    kernel = _kernel(kernel)
    civ = getattr(planet, "civilization", None)
    flux = float(F(civ.light_optimum)) if civ is not None and getattr(civ, "light_optimum", None) else None
    grav = float(F(civ.home_gravity)) if civ is not None and getattr(civ, "home_gravity", None) else None
    return metabolic_factor(metabolism_of(kernel, planet), fertility.strategy(kernel, planet),
                            genome.birth_factor(planet), genome.temperature_factor(planet), flux, grav)


def consumption(planet: Any) -> int:
    from xylarium.kernel.fertility import food_factor
    return max(1, int(planet.population * FOOD_PER_THOUSAND * food_factor(planet) * need_factor(planet)) // 1000)


def meal(planet: Any) -> int:
    """What the world eats this cycle: its exact need, the fraction of a unit carried - as its harvest carries its
    own (a band of 845 eats 0.845 units a cycle, not a whole one it cannot grow)."""
    from xylarium.kernel.fertility import food_factor
    soc = planet.society
    total = int(planet.population * FOOD_PER_THOUSAND * food_factor(planet) * need_factor(planet)) \
        + int(soc.get("meal_carry", 0) or 0)
    soc["meal_carry"] = total % 1000
    return total // 1000


def births(kernel: Any, planet: Any, ceiling: int) -> int:
    """
    Logistic growth this cycle toward min(1, f) x ``ceiling``, where f is the people's fertility relative to
    replacement (fertility.py): a people below replacement settles under what the land could carry (and
    shrinks toward it if above - never faster than r of its number), a fertile one grows up to f times faster,
    never faster than its farms can add food. The fraction of a person is carried (in millionths).
    """
    p = planet.population
    if p <= 0 or ceiling <= 0:
        return 0
    prof = _profile(kernel, planet)
    f = float((getattr(planet, "society", None) or {}).get("fertility", 1.0))
    speed = max(1.0, f)
    from xylarium.kernel import genome
    speed *= genome.birth_factor(planet)                 # its natural increase is heritable
    r = min(int(prof.get("birth_micro_per_cycle", prof["rate_micro_per_cycle"]) * speed),
            prof.get("food_micro_per_cycle", prof["rate_micro_per_cycle"]))
    target = max(1, int(ceiling * min(1.0, f)))
    carry = int(getattr(planet, "growth_carry", None) or 0)
    micro = r * p * (target - p) // max(target, p) + carry    # floor division: exact in millionths
    whole = micro // MICRO if micro >= 0 else -((-micro) // MICRO)
    planet.growth_carry = str(micro - whole * MICRO)
    return whole
