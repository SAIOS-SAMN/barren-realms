"""
Xylarium encounters: whether a world keeps its star among the stars that pass it.

A star passing within a few of a planet's orbital radii unbinds it. How often that happens is the stars' number
density where the system circles, the area a pass must come within, and how fast they move:

    rate = n * pi * (STRIP_RADII * a)^2 * v          survival over t = exp(-rate * t)

Where systems are sparse (the disc near the Sun) almost every world is kept; deep in the bulge a world on a wide
orbit is soon lost; inside the galaxy's nuclear star cluster even a close one is. The galaxy's stars, by component,
as measured:

  disc     0.1 stars per pc^3 at the Sun's radius, scaling with the disc's surface density (fixed thickness);
           40 km/s between stars
  bulge    a Hernquist sphere of 1.5e10 solar masses, scale 0.7 kpc (the Milky Way's bulge and bar); 110 km/s
  nucleus  a Plummer sphere of 2.5e7 solar masses, scale 4 pc (the nuclear star cluster); 100 km/s

(at a mean stellar mass of 0.4 suns, the Kroupa average).
"""

import math

STRIP_RADII = 3.0               # a pass within ~3 orbital radii unbinds a planet (scattering experiments)
MEAN_STAR = 0.4                 # solar masses: the Kroupa mean
DISC_N_R0 = 0.1                 # stars per pc^3 at the Sun's radius
DISC_V = 40.0                   # km/s
BULGE_M, BULGE_A_KPC, BULGE_V = 1.5e10, 0.7, 110.0
NUCLEUS_M, NUCLEUS_A_PC, NUCLEUS_V = 2.5e7, 4.0, 100.0
AU_PC = 4.848e-6
KMS_PC_PER_MYR = 1.0227


def components(r_kpc: float):
    """(number density per pc^3, dispersion km/s) of each component where a system circles."""
    from xylarium.kernel import cosmos
    r_pc = max(0.1, r_kpc * 1000.0)
    disc = DISC_N_R0 * cosmos.density(r_kpc)
    a_pc = BULGE_A_KPC * 1000.0
    bulge = BULGE_M * a_pc / (2 * math.pi * r_pc * (r_pc + a_pc) ** 3) / MEAN_STAR
    nucleus = 3 * NUCLEUS_M / (4 * math.pi * NUCLEUS_A_PC ** 3) * (1 + (r_pc / NUCLEUS_A_PC) ** 2) ** -2.5 / MEAN_STAR
    return [(disc, DISC_V), (bulge, BULGE_V), (nucleus, NUCLEUS_V)]


def rate_per_gyr(a_au: float, r_kpc: float) -> float:
    """How often a pass close enough to unbind a planet at a_au comes, per Gyr."""
    cross = math.pi * (STRIP_RADII * a_au * AU_PC) ** 2          # pc^2
    return sum(n * cross * v * KMS_PC_PER_MYR * 1000.0 for n, v in components(r_kpc))


def survival(a_au: float, r_kpc: float, gyr: float) -> float:
    """The chance a planet at a_au keeps its star for gyr where it circles."""
    return math.exp(-rate_per_gyr(a_au, r_kpc) * max(0.0, gyr))
