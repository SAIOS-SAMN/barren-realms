"""
Event dispatch and subspace radio transmission bus for Xylarium.
"""

from typing import List, Callable, Optional, Dict, Any
from collections import deque
from xylarium.kernel.models import RadioMessage


class EventBus:
    """Decoupled event queue and radio transceiver system."""

    def __init__(self, max_radio_history: int = 50):
        self._radio_history: deque[RadioMessage] = deque(maxlen=max_radio_history)
        self._event_listeners: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register an external listener (e.g. WebSocket streamer or client HUD)."""
        self._event_listeners.append(listener)

    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcasts an event to all subscribers."""
        payload = {"event": event_type, "data": data}
        for listener in self._event_listeners:
            try:
                listener(payload)
            except Exception:
                pass

    def broadcast_radio(
        self,
        sender: str,
        text: str,
        channel: str = "COMM-1",
        sector_id: Optional[int] = None
    ) -> RadioMessage:
        """Emit a subspace radio transmission."""
        msg = RadioMessage(
            sender=sender,
            text=text,
            channel=channel,
            sector_id=sector_id
        )
        self._radio_history.append(msg)
        self.emit_event("RADIO_TRANSMISSION", msg.to_dict())
        return msg

    def get_recent_radio(self, limit: int = 6) -> List[RadioMessage]:
        """Returns the most recent radio messages."""
        return list(self._radio_history)[-limit:]
