"""Audio Stream Handler — WebAudio spatial audio parameter streaming.

Part of the CAITE Sovereign Multimedia Transformation Engine.
Handles real-time spatial audio parameter streaming to WebAudio API clients
via WebSocket connections.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain Types
# ---------------------------------------------------------------------------

class SpatialModel(str, enum.Enum):
    """Spatial audio rendering model."""
    HRTF = "HRTF"
    EQUAL_POWER = "equalpower"


class ReverbPreset(str, enum.Enum):
    """Convolution reverb room presets."""
    STUDIO = "studio"
    CONCERT_HALL = "concert_hall"
    CATHEDRAL = "cathedral"
    OUTDOOR = "outdoor"
    INTIMATE = "intimate"
    BROADCAST = "broadcast"


@dataclass
class SpatialSource:
    """A positioned audio source in 3D space."""
    source_id: str
    position: tuple[float, float, float]  # x, y, z in metres
    gain: float = 1.0
    spatial_model: SpatialModel = SpatialModel.HRTF
    cone_inner_angle: float = 360.0
    cone_outer_angle: float = 360.0
    cone_outer_gain: float = 0.0
    max_distance: float = 100.0
    rolloff_factor: float = 1.0

    def to_webaudio_params(self) -> dict[str, Any]:
        """Convert to WebAudio PannerNode parameter dict."""
        return {
            "source_id": self.source_id,
            "positionX": self.position[0],
            "positionY": self.position[1],
            "positionZ": self.position[2],
            "gain": self.gain,
            "panningModel": self.spatial_model.value,
            "coneInnerAngle": self.cone_inner_angle,
            "coneOuterAngle": self.cone_outer_angle,
            "coneOuterGain": self.cone_outer_gain,
            "maxDistance": self.max_distance,
            "rolloffFactor": self.rolloff_factor,
        }


@dataclass
class RoomEnvironment:
    """Room environment parameters for convolution reverb."""
    preset: ReverbPreset
    room_size: tuple[float, float, float] = (10.0, 3.0, 8.0)  # w, h, d
    reverb_wet: float = 0.3
    reverb_dry: float = 0.7
    high_frequency_damping: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset": self.preset.value,
            "room_size": list(self.room_size),
            "reverb_wet": self.reverb_wet,
            "reverb_dry": self.reverb_dry,
            "hf_damping": self.high_frequency_damping,
        }


# ---------------------------------------------------------------------------
# Audio Stream Handler
# ---------------------------------------------------------------------------

class AudioStreamHandler:
    """Manages spatial audio sources and streams parameters to WebAudio clients.

    All audio processing metadata stays within the sovereign perimeter.
    Only rendering parameters (positions, gains, room configs) are
    transmitted to the client-side WebAudio API.
    """

    def __init__(self, default_room: ReverbPreset = ReverbPreset.STUDIO) -> None:
        self._sources: dict[str, SpatialSource] = {}
        self._room = RoomEnvironment(preset=default_room)
        self._listener_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._listener_orientation: tuple[float, float, float] = (0.0, 0.0, -1.0)
        self._update_queue: list[dict[str, Any]] = []
        log.info("AudioStreamHandler initialised (room=%s)", default_room.value)

    def add_source(self, source: SpatialSource) -> None:
        """Register a spatial audio source."""
        self._sources[source.source_id] = source
        self._queue_update("source_add", source.to_webaudio_params())
        log.info("Added audio source '%s' at (%.1f, %.1f, %.1f)",
                 source.source_id, *source.position)

    def update_source_position(
        self,
        source_id: str,
        position: tuple[float, float, float],
    ) -> None:
        """Update the position of an existing audio source."""
        source = self._sources.get(source_id)
        if source:
            source.position = position
            self._queue_update("source_move", {
                "source_id": source_id,
                "positionX": position[0],
                "positionY": position[1],
                "positionZ": position[2],
            })

    def update_source_gain(self, source_id: str, gain: float) -> None:
        """Update the gain of a spatial audio source."""
        source = self._sources.get(source_id)
        if source:
            source.gain = max(0.0, min(1.0, gain))
            self._queue_update("source_gain", {
                "source_id": source_id,
                "gain": source.gain,
            })

    def set_room(self, room: RoomEnvironment) -> None:
        """Update the room environment."""
        self._room = room
        self._queue_update("room_update", room.to_dict())
        log.info("Room environment updated: %s", room.preset.value)

    def set_listener_position(
        self,
        position: tuple[float, float, float],
        orientation: tuple[float, float, float] | None = None,
    ) -> None:
        """Update the listener position and optional orientation."""
        self._listener_position = position
        if orientation:
            self._listener_orientation = orientation
        self._queue_update("listener_update", {
            "positionX": position[0],
            "positionY": position[1],
            "positionZ": position[2],
            "forwardX": self._listener_orientation[0],
            "forwardY": self._listener_orientation[1],
            "forwardZ": self._listener_orientation[2],
        })

    def flush_updates(self) -> list[dict[str, Any]]:
        """Flush queued updates for WebSocket transmission.

        Returns:
            List of update messages ready for JSON serialisation.
        """
        updates = self._update_queue.copy()
        self._update_queue.clear()
        return updates

    def get_scene_state(self) -> dict[str, Any]:
        """Get the complete audio scene state for session recovery."""
        return {
            "sources": {sid: s.to_webaudio_params() for sid, s in self._sources.items()},
            "room": self._room.to_dict(),
            "listener": {
                "position": list(self._listener_position),
                "orientation": list(self._listener_orientation),
            },
            "source_count": len(self._sources),
            "timestamp": time.time(),
        }

    def remove_source(self, source_id: str) -> None:
        """Remove a spatial audio source."""
        if source_id in self._sources:
            del self._sources[source_id]
            self._queue_update("source_remove", {"source_id": source_id})

    def _queue_update(self, event_type: str, data: dict[str, Any]) -> None:
        """Queue an update for batch transmission."""
        self._update_queue.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })
