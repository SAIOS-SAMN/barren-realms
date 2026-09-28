"""
JSON Persistence engine for Xylarium game saves.
"""

import json
import os
from typing import Optional
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Sector, Captain, RadioMessage


class StatePersistence:
    """Serializes and deserializes the entire GameKernel to and from JSON."""

    @staticmethod
    def save_to_file(kernel: GameKernel, filepath: str) -> bool:
        """Serializes current universe and state to a JSON file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            data = {
                "seed": kernel.seed,
                "cycle_count": kernel.cycle_count,
                "sectors": {s_id: sec.to_dict() for s_id, sec in kernel.sectors.items()},
                "captains": {c_id: cap.to_dict() for c_id, cap in kernel.captains.items()},
                "radio": [m.to_dict() for m in kernel.event_bus.get_recent_radio(50)],
                "logs": list(kernel.action_logs),
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

    @staticmethod
    def load_from_file(filepath: str) -> Optional[GameKernel]:
        """Loads and reconstructs a GameKernel instance from a JSON file."""
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            kernel = GameKernel.__new__(GameKernel)
            kernel.seed = data.get("seed", 42)
            kernel.cycle_count = data.get("cycle_count", 0)
            kernel.sectors = {
                int(s_id): Sector.from_dict(sec_data)
                for s_id, sec_data in data["sectors"].items()
            }
            kernel.captains = {
                c_id: Captain.from_dict(cap_data)
                for c_id, cap_data in data["captains"].items()
            }
            from xylarium.kernel.events import EventBus
            from collections import deque
            kernel.event_bus = EventBus()
            for r_data in data.get("radio", []):
                kernel.event_bus.broadcast_radio(
                    sender=r_data["sender"],
                    text=r_data["text"],
                    channel=r_data.get("channel", "COMM-1"),
                    sector_id=r_data.get("sector_id")
                )
            kernel.action_logs = deque(data.get("logs", []), maxlen=20)
            return kernel
        except Exception as e:
            print(f"Error loading game state: {e}")
            return None
