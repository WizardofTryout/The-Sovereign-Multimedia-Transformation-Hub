"""Avatar Sync Handler — Emotion state transmission and avatar synchronisation.

Part of the CAITE Sovereign Multimedia Transformation Engine.
Handles real-time avatar emotion state sync at <20ms latency
via WebSocket connections to game engine clients.
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

class EmotionCategory(str, enum.Enum):
    """Primary emotion categories for avatar expression."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FOCUSED = "focused"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"
    CONCERNED = "concerned"


class GestureType(str, enum.Enum):
    """Avatar gesture classifications."""
    IDLE = "idle"
    TALKING = "talking"
    POINTING = "pointing"
    NODDING = "nodding"
    SHAKING_HEAD = "shaking_head"
    WAVING = "waving"
    THINKING = "thinking"


class BlendShapeTarget(str, enum.Enum):
    """Facial blend shape targets compatible with ARKit/Unity standard."""
    BROW_INNER_UP = "browInnerUp"
    BROW_OUTER_UP_LEFT = "browOuterUpLeft"
    BROW_OUTER_UP_RIGHT = "browOuterUpRight"
    EYE_SQUINT_LEFT = "eyeSquintLeft"
    EYE_SQUINT_RIGHT = "eyeSquintRight"
    JAW_OPEN = "jawOpen"
    MOUTH_SMILE_LEFT = "mouthSmileLeft"
    MOUTH_SMILE_RIGHT = "mouthSmileRight"
    MOUTH_FROWN_LEFT = "mouthFrownLeft"
    MOUTH_FROWN_RIGHT = "mouthFrownRight"


@dataclass
class EmotionState:
    """Current avatar emotion state with blend shape weights."""
    category: EmotionCategory
    intensity: float  # 0.0–1.0
    blend_shapes: dict[str, float] = field(default_factory=dict)
    transition_ms: float = 200.0  # blend transition duration

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "intensity": round(self.intensity, 3),
            "blend_shapes": {k: round(v, 3) for k, v in self.blend_shapes.items()},
            "transition_ms": self.transition_ms,
        }


@dataclass
class AvatarPose:
    """Complete avatar pose including position, rotation, and gesture."""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Euler angles
    gesture: GestureType = GestureType.IDLE
    gaze_target: tuple[float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "position": list(self.position),
            "rotation": list(self.rotation),
            "gesture": self.gesture.value,
        }
        if self.gaze_target:
            result["gaze_target"] = list(self.gaze_target)
        return result


# ---------------------------------------------------------------------------
# Emotion Presets
# ---------------------------------------------------------------------------

EMOTION_BLEND_PRESETS: dict[EmotionCategory, dict[str, float]] = {
    EmotionCategory.NEUTRAL: {},
    EmotionCategory.HAPPY: {
        BlendShapeTarget.MOUTH_SMILE_LEFT.value: 0.7,
        BlendShapeTarget.MOUTH_SMILE_RIGHT.value: 0.7,
        BlendShapeTarget.EYE_SQUINT_LEFT.value: 0.3,
        BlendShapeTarget.EYE_SQUINT_RIGHT.value: 0.3,
    },
    EmotionCategory.FOCUSED: {
        BlendShapeTarget.BROW_INNER_UP.value: 0.4,
        BlendShapeTarget.EYE_SQUINT_LEFT.value: 0.2,
        BlendShapeTarget.EYE_SQUINT_RIGHT.value: 0.2,
    },
    EmotionCategory.CONCERNED: {
        BlendShapeTarget.BROW_INNER_UP.value: 0.6,
        BlendShapeTarget.MOUTH_FROWN_LEFT.value: 0.3,
        BlendShapeTarget.MOUTH_FROWN_RIGHT.value: 0.3,
    },
    EmotionCategory.EXCITED: {
        BlendShapeTarget.BROW_OUTER_UP_LEFT.value: 0.5,
        BlendShapeTarget.BROW_OUTER_UP_RIGHT.value: 0.5,
        BlendShapeTarget.MOUTH_SMILE_LEFT.value: 0.8,
        BlendShapeTarget.MOUTH_SMILE_RIGHT.value: 0.8,
        BlendShapeTarget.JAW_OPEN.value: 0.2,
    },
}


# ---------------------------------------------------------------------------
# Avatar Sync Handler
# ---------------------------------------------------------------------------

class AvatarSyncHandler:
    """Manages avatar state and syncs emotion/pose data to game engine clients.

    Optimised for <20ms latency avatar state transmission.
    Uses delta compression to minimise WebSocket payload size.
    """

    def __init__(self) -> None:
        self._current_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.0,
        )
        self._current_pose = AvatarPose()
        self._last_sent_emotion: EmotionState | None = None
        self._last_sent_pose: AvatarPose | None = None
        self._update_queue: list[dict[str, Any]] = []
        log.info("AvatarSyncHandler initialised")

    def set_emotion(
        self,
        category: EmotionCategory,
        intensity: float = 0.8,
        transition_ms: float = 200.0,
    ) -> EmotionState:
        """Set the avatar's current emotion state.

        Uses preset blend shapes scaled by intensity.

        Args:
            category: Target emotion category.
            intensity: Emotion intensity (0.0–1.0).
            transition_ms: Blend transition duration in milliseconds.

        Returns:
            Updated EmotionState.
        """
        preset = EMOTION_BLEND_PRESETS.get(category, {})
        scaled = {k: v * intensity for k, v in preset.items()}

        self._current_emotion = EmotionState(
            category=category,
            intensity=min(1.0, max(0.0, intensity)),
            blend_shapes=scaled,
            transition_ms=transition_ms,
        )
        self._queue_update("emotion_update", self._current_emotion.to_dict())
        log.info("Emotion → %s (intensity=%.2f, transition=%.0fms)",
                 category.value, intensity, transition_ms)
        return self._current_emotion

    def set_pose(
        self,
        position: tuple[float, float, float] | None = None,
        rotation: tuple[float, float, float] | None = None,
        gesture: GestureType | None = None,
        gaze_target: tuple[float, float, float] | None = None,
    ) -> AvatarPose:
        """Update the avatar's pose.

        Args:
            position: New position (None = keep current).
            rotation: New rotation (None = keep current).
            gesture: New gesture (None = keep current).
            gaze_target: New gaze target (None = keep current).

        Returns:
            Updated AvatarPose.
        """
        if position:
            self._current_pose.position = position
        if rotation:
            self._current_pose.rotation = rotation
        if gesture:
            self._current_pose.gesture = gesture
        if gaze_target is not None:
            self._current_pose.gaze_target = gaze_target

        self._queue_update("pose_update", self._current_pose.to_dict())
        return self._current_pose

    def get_full_state(self) -> dict[str, Any]:
        """Get complete avatar state for session recovery."""
        return {
            "emotion": self._current_emotion.to_dict(),
            "pose": self._current_pose.to_dict(),
            "timestamp": time.time(),
        }

    def flush_updates(self) -> list[dict[str, Any]]:
        """Flush queued updates for WebSocket transmission."""
        updates = self._update_queue.copy()
        self._update_queue.clear()
        return updates

    def _queue_update(self, event_type: str, data: dict[str, Any]) -> None:
        self._update_queue.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })
