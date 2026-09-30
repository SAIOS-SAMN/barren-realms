"""
Orbital Ephemeris & Dynamic Astrodynamics Engine for Xylarium.
Ported from Netstratum 35_ORBIT_DYNAMO_AND_ESTATE and 33_TRADE_FLEET_AND_DESK.
Implements Keplerian discrete planetary orbits, dynamic angular phase tracking,
and D_eff transit window scaling for fuel and turn consumption.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from xylarium.config import (
    ORBIT_MIN_RADIUS_AU,
    ORBIT_MAX_RADIUS_AU,
    ORBIT_CONJUNCTION_TRANSIT_MULT,
    ORBIT_OPPOSITION_TRANSIT_MULT,
)
from xylarium.kernel.models import Planet, ActionResult, ActionType


@dataclass
class OrbitalPosition:
    """Calculated orbital position of a planet at a specific cycle."""
    planet_id: str
    planet_name: str
    radius_au: float
    angle_deg: float
    period_cycles: int
    x: float
    y: float
    phase_label: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "planet_name": self.planet_name,
            "radius_au": round(self.radius_au, 3),
            "angle_deg": round(self.angle_deg, 2),
            "period_cycles": self.period_cycles,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "phase_label": self.phase_label,
        }


@dataclass
class TransitWindow:
    """Astrodynamic transit window evaluation between two planetary bodies."""
    origin_id: str
    target_id: str
    effective_distance_au: float
    transit_multiplier: float
    window_grade: str  # "CHEAP" (Conjunction), "FAIR" (Quadrature), "DEAR" (Opposition)
    delta_angle_deg: float
    cycles_to_next_conjunction: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "target_id": self.target_id,
            "effective_distance_au": round(self.effective_distance_au, 3),
            "transit_multiplier": round(self.transit_multiplier, 3),
            "window_grade": self.window_grade,
            "delta_angle_deg": round(self.delta_angle_deg, 2),
            "cycles_to_next_conjunction": self.cycles_to_next_conjunction,
        }


class AstronomyManager:
    """
    Manages orbital ephemeris, Keplerian mechanics, and transit windows across the universe.
    """

    def __init__(self, cycle_count: int = 0):
        self.cycle_count: int = cycle_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_count": self.cycle_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AstronomyManager":
        return cls(
            cycle_count=data.get("cycle_count", 0),
        )

    def tick(self, planets: List[Planet], sectors: Optional[Dict[int, Any]] = None) -> None:
        """
        Advances the sky one cycle. Worlds with exact physics take their angle from their exact orbital
        phase at this cycle (physics.orbital_phase: no accumulated drift); others step by 360 / period.
        """
        self.cycle_count += 1
        from xylarium.kernel import physics
        for p in planets:
            sec = sectors.get(p.sector_id) if sectors else None
            if sec is not None and getattr(p, "body", None):
                p.orbital_angle = float(physics.orbital_phase(sec, p, self.cycle_count)) * 360.0
                continue
            period = max(1, p.orbital_period)
            p.orbital_angle = (p.orbital_angle + 360.0 / period) % 360.0

    def compute_position(self, planet: Planet) -> OrbitalPosition:
        """Computes Cartesian coordinates and phase label for a planet."""
        r = planet.orbital_radius
        deg = planet.orbital_angle
        rad = math.radians(deg)
        x = r * math.cos(rad)
        y = r * math.sin(rad)

        # Classify quadrant / phase
        if 0.0 <= deg < 90.0:
            phase = "Quadrant I (Ascending)"
        elif 90.0 <= deg < 180.0:
            phase = "Quadrant II (Apastron)"
        elif 180.0 <= deg < 270.0:
            phase = "Quadrant III (Descending)"
        else:
            phase = "Quadrant IV (Periastron)"

        return OrbitalPosition(
            planet_id=planet.id,
            planet_name=planet.name,
            radius_au=r,
            angle_deg=deg,
            period_cycles=planet.orbital_period,
            x=x,
            y=y,
            phase_label=phase,
        )

    def compute_transit_window(self, p1: Planet, p2: Planet) -> TransitWindow:
        """
        Calculates astrodynamic effective distance (D_eff) and transit cost multiplier
        between two worlds based on Keplerian angular separation.
        """
        pos1 = self.compute_position(p1)
        pos2 = self.compute_position(p2)

        # Angular difference normalized to [0.0, 180.0]
        diff = abs(pos1.angle_deg - pos2.angle_deg) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff

        # Law of Cosines on orbital plane
        # D_eff = sqrt(r1^2 + r2^2 - 2*r1*r2*cos(diff))
        rad_diff = math.radians(diff)
        d_sq = (pos1.radius_au ** 2) + (pos2.radius_au ** 2) - (2.0 * pos1.radius_au * pos2.radius_au * math.cos(rad_diff))
        d_eff = math.sqrt(max(0.01, d_sq))

        # Dynamic multiplier interpolation:
        # alpha = 0 (conjunction, closest approach) -> ORBIT_CONJUNCTION_TRANSIT_MULT (0.60x)
        # alpha = 1 (opposition, across star)        -> ORBIT_OPPOSITION_TRANSIT_MULT (1.75x)
        alpha = diff / 180.0
        multiplier = ORBIT_CONJUNCTION_TRANSIT_MULT + alpha * (
            ORBIT_OPPOSITION_TRANSIT_MULT - ORBIT_CONJUNCTION_TRANSIT_MULT
        )

        if alpha < 0.25:
            grade = "CHEAP (Conjunction Window)"
        elif alpha > 0.75:
            grade = "DEAR (Opposition Resistance)"
        else:
            grade = "FAIR (Quadrature Transit)"

        # Calculate cycles until next conjunction
        # Angular velocities: omega = 360 / period
        w1 = 360.0 / max(1, p1.orbital_period)
        w2 = 360.0 / max(1, p2.orbital_period)
        rel_speed = abs(w1 - w2)
        if rel_speed < 0.001:
            cycles_conjunction = 0
        else:
            # Current signed angular distance p1 to p2
            cur_diff = (pos2.angle_deg - pos1.angle_deg) % 360.0
            if cur_diff < 0:
                cur_diff += 360.0
            # If w1 > w2, p1 is catching up to p2
            if w1 > w2:
                cycles_conjunction = int(cur_diff / rel_speed)
            else:
                cycles_conjunction = int((360.0 - cur_diff) / rel_speed)

        return TransitWindow(
            origin_id=p1.id,
            target_id=p2.id,
            effective_distance_au=d_eff,
            transit_multiplier=multiplier,
            window_grade=grade,
            delta_angle_deg=diff,
            cycles_to_next_conjunction=cycles_conjunction,
        )

    def render_ascii_system_map(self, planets: List[Planet], width: int = 35, height: int = 17) -> List[str]:
        """
        Renders a 2D ASCII radar map of planets orbiting the sector's central star.
        """
        grid = [[" " for _ in range(width)] for _ in range(height)]
        cx, cy = width // 2, height // 2

        # Star at center
        grid[cy][cx] = "☼"

        # Max radius for scaling
        max_r = max([p.orbital_radius for p in planets], default=5.0)
        max_r = max(max_r, 1.0)
        scale_x = (cx - 2) / max_r
        scale_y = (cy - 1) / max_r

        # Draw orbital rings for planets
        for idx, p in enumerate(planets):
            pos = self.compute_position(p)
            px = int(cx + pos.x * scale_x)
            py = int(cy - pos.y * scale_y)  # Inverted Y for screen coords

            px = max(0, min(width - 1, px))
            py = max(0, min(height - 1, py))

            # Mark planet with initial or number
            sym = str(idx + 1) if idx < 9 else "@"
            grid[py][px] = sym

        lines = ["+" + "-" * width + "+"]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append("+" + "-" * width + "+")
        return lines
