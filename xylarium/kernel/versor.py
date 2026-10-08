"""
Xylarium versor: the conformal geometric algebra Cl(4,1), EXACT - every coefficient a Fraction (field law, operator
ruling 2026-10-08: orbits and spins are sheared exactly; floats never touch orbital mechanics).

A pulse is a versor: BENT is a translator, ROTATED a rotor, TWISTED a screw (a rotor with a translation along its
axis - its PITCH, the translation a full turn carries, is its wavelength), FLIPPED a reflection (an odd versor).
Versors compose by the geometric product; one acts on a point by its sandwich, V X V^-1 (an odd one with its grade
involution: -V X V^-1).

Basis e1 e2 e3 (space), e4 (+1), e5 (-1); a blade is a bitmask. The null directions: n_inf = e4 + e5 and
n_o = (e5 - e4) / 2. A point x embeds as X = x + (x.x / 2) n_inf + n_o. Rotations are exact through rational
directions: a rotor 1 + t e_ij turns by angle 2 atan(t) with rational cos and sin (the Pythagorean rational points),
never through a float angle.
"""

from fractions import Fraction
from typing import Dict, Iterable, Sequence, Tuple

METRIC = (1, 1, 1, 1, -1)          # e1..e4 square to +1, e5 to -1
E1, E2, E3, E4, E5 = 1, 2, 4, 8, 16


def _sign(a: int, b: int) -> int:
    """The sign of reordering blade a times blade b into canonical order (swaps), times the metric of shared axes."""
    s, x = 0, a >> 1
    while x:
        s += bin(x & b).count("1")
        x >>= 1
    sign = -1 if s & 1 else 1
    common = a & b
    for i, m in enumerate(METRIC):
        if common >> i & 1 and m < 0:
            sign = -sign
    return sign


class Mv:
    """A multivector: {blade bitmask: Fraction}, zeros dropped."""
    __slots__ = ("c",)

    def __init__(self, c: Dict[int, Fraction] = None):
        self.c = {b: Fraction(v) for b, v in (c or {}).items() if v != 0}

    @staticmethod
    def scalar(v) -> "Mv":
        return Mv({0: Fraction(v)})

    @staticmethod
    def vector(xs: Sequence) -> "Mv":
        return Mv({1 << i: Fraction(x) for i, x in enumerate(xs)})

    def __add__(self, o: "Mv") -> "Mv":
        out = dict(self.c)
        for b, v in o.c.items():
            out[b] = out.get(b, 0) + v
        return Mv(out)

    def __sub__(self, o: "Mv") -> "Mv":
        return self + o * Mv.scalar(-1)

    def __mul__(self, o: "Mv") -> "Mv":
        """The geometric product."""
        out: Dict[int, Fraction] = {}
        for a, x in self.c.items():
            for b, y in o.c.items():
                out[a ^ b] = out.get(a ^ b, 0) + _sign(a, b) * x * y
        return Mv(out)

    def scale(self, k) -> "Mv":
        return Mv({b: v * Fraction(k) for b, v in self.c.items()})

    def grade(self, k: int) -> "Mv":
        return Mv({b: v for b, v in self.c.items() if bin(b).count("1") == k})

    def reverse(self) -> "Mv":
        return Mv({b: (v if (bin(b).count("1") * (bin(b).count("1") - 1) // 2) % 2 == 0 else -v)
                   for b, v in self.c.items()})

    def involute(self) -> "Mv":
        return Mv({b: (v if bin(b).count("1") % 2 == 0 else -v) for b, v in self.c.items()})

    def odd(self) -> bool:
        return any(bin(b).count("1") % 2 for b in self.c)

    def norm2(self) -> Fraction:
        """V V~ for a versor: a scalar."""
        return (self * self.reverse()).c.get(0, Fraction(0))

    def inverse(self) -> "Mv":
        n = self.norm2()
        if n == 0:
            raise ZeroDivisionError("not a versor")
        return self.reverse().scale(1 / n)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Mv) and self.c == o.c

    def __repr__(self) -> str:
        return "Mv(" + ", ".join(f"{b}:{v}" for b, v in sorted(self.c.items())) + ")"


N_INF = Mv({E4: 1, E5: 1})
N_O = Mv({E4: Fraction(-1, 2), E5: Fraction(1, 2)})


def point(x: Sequence) -> Mv:
    """A point of space, embedded: x + (x.x / 2) n_inf + n_o."""
    v = Mv.vector(list(x))
    xx = sum(Fraction(a) * Fraction(a) for a in x)
    return v + N_INF.scale(xx / 2) + N_O


def unpoint(X: Mv) -> Tuple[Fraction, Fraction, Fraction]:
    """A conformal point back to space (normalized by its n_o weight)."""
    w = -(X * N_INF).c.get(0, Fraction(0))            # X . n_inf = -1 for a normalized point
    if w == 0:
        raise ValueError("not a finite point")
    return tuple(X.c.get(1 << i, Fraction(0)) / w for i in range(3))


def translator(t: Sequence) -> Mv:
    """BEND: a translation by t - exact."""
    return Mv.scalar(1) - (Mv.vector(t) * N_INF).scale(Fraction(1, 2))


def rotor(i: int, j: int, t) -> Mv:
    """ROTATE in the plane of axes i, j by 2 atan(t) - a rational point of the circle, exact (not normalized: the
    sandwich divides by its norm)."""
    return Mv.scalar(1) + Mv({(1 << i) | (1 << j): Fraction(t)})


def reflection(n: Sequence) -> Mv:
    """FLIP: the reflection in the plane through the origin normal to n - an odd versor."""
    return Mv.vector(n)


def screw(i: int, j: int, t, along: Sequence) -> Mv:
    """TWIST: a rotor in the plane (i, j) composed with a translation along its axis."""
    return translator(along) * rotor(i, j, t)


def act(V: Mv, X: Mv) -> Mv:
    """A versor's action on a conformal object: V X V^-1, an odd versor with its grade involution."""
    Y = V * X * V.inverse()
    return Y.scale(-1) if V.odd() else Y


def move(V: Mv, x: Sequence) -> Tuple[Fraction, Fraction, Fraction]:
    """A point of space moved by a versor, exactly."""
    return unpoint(act(V, point(x)))


def compose(vs: Iterable[Mv]) -> Mv:
    out = Mv.scalar(1)
    for v in vs:
        out = v * out
    return out


def torsion(loop: Iterable[Mv]) -> Tuple[Fraction, Fraction, Fraction]:
    """What a loop of pulses fails to close by: the translation it leaves the origin carried through (holonomy) -
    zero for a loop that closes."""
    return move(compose(loop), (0, 0, 0))


def to_wire(V: Mv) -> Dict[str, str]:
    """A versor for the seat wire (Mv, ARG tag 4): every blade's exact coefficient as its Fraction's string."""
    return {str(b): str(v) for b, v in sorted(V.c.items())}


def from_wire(d: Dict[str, str]) -> Mv:
    return Mv({int(b): Fraction(v) for b, v in d.items()})
