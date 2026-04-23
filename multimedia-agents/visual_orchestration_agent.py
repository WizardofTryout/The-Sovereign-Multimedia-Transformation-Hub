"""Visual Orchestration Agent — Asset classification and real-time rendering coordination.

Part of the CAITE Sovereign Multimedia Transformation Engine.
This agent classifies visual assets, composes scenes, and coordinates
rendering output for Unity, Unreal Engine, and WebGL targets.
"""

from __future__ import annotations

import enum
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain Types
# ---------------------------------------------------------------------------

class RenderTarget(str, enum.Enum):
    """Supported rendering targets."""
    WEBGL = "webgl"
    UNITY = "unity"
    UNREAL = "unreal"


class AssetCategory(str, enum.Enum):
    """Visual asset classification categories."""
    BACKGROUND = "background"
    CHARACTER = "character"
    UI_ELEMENT = "ui_element"
    PARTICLE_EFFECT = "particle_effect"
    LIGHTING = "lighting"
    PROP = "prop"


class EmotionState(str, enum.Enum):
    """Avatar emotion states for real-time synthesis."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    FOCUSED = "focused"
    CONCERNED = "concerned"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"


@dataclass
class VisualAsset:
    """Classified visual asset ready for scene composition."""
    asset_id: str
    category: AssetCategory
    semantic_tags: list[str]
    render_targets: list[RenderTarget]
    resolution: tuple[int, int] = (1920, 1080)
    frame_budget_ms: float = 16.0
    sovereignty_label: str = "eu-sovereign"

    def to_scene_node(self) -> dict[str, Any]:
        """Convert to scene graph node representation."""
        return {
            "id": self.asset_id,
            "category": self.category.value,
            "tags": self.semantic_tags,
            "targets": [t.value for t in self.render_targets],
            "resolution": list(self.resolution),
            "frame_budget_ms": self.frame_budget_ms,
            "sovereignty": self.sovereignty_label,
        }


@dataclass
class SceneComposition:
    """A composed scene ready for rendering."""
    scene_id: str
    target: RenderTarget
    assets: list[VisualAsset] = field(default_factory=list)
    avatar_state: EmotionState = EmotionState.NEUTRAL
    lighting_preset: str = "default"
    camera_position: tuple[float, float, float] = (0.0, 0.0, 5.0)

    @property
    def total_draw_calls(self) -> int:
        """Estimate draw call count for performance budgeting."""
        return len(self.assets) + (2 if self.avatar_state != EmotionState.NEUTRAL else 1)


# ---------------------------------------------------------------------------
# Visual Orchestration Agent
# ---------------------------------------------------------------------------

class VisualOrchestrationAgent:
    """Classifies visual assets and composes scenes for real-time rendering.

    This agent operates within the sovereign perimeter — all asset
    classification and scene composition happens on controlled infrastructure.
    No visual data is transmitted to external services.
    """

    def __init__(self, default_target: RenderTarget = RenderTarget.WEBGL) -> None:
        self._default_target = default_target
        self._asset_cache: dict[str, VisualAsset] = {}
        log.info("VisualOrchestrationAgent initialised (target=%s)", default_target.value)

    def classify_asset(
        self,
        asset_path: str,
        semantic_tags: list[str] | None = None,
    ) -> VisualAsset:
        """Classify a visual asset and register it in the sovereign cache.

        Args:
            asset_path: Path to the asset file within the sovereign perimeter.
            semantic_tags: Optional semantic labels from the knowledge graph.

        Returns:
            Classified VisualAsset instance.
        """
        asset_id = self._hash_path(asset_path)
        if asset_id in self._asset_cache:
            log.debug("Cache hit for asset %s", asset_id[:12])
            return self._asset_cache[asset_id]

        category = self._infer_category(asset_path, semantic_tags or [])
        asset = VisualAsset(
            asset_id=asset_id,
            category=category,
            semantic_tags=semantic_tags or [],
            render_targets=[self._default_target],
        )
        self._asset_cache[asset_id] = asset
        log.info("Classified asset %s → %s", asset_id[:12], category.value)
        return asset

    def compose_scene(
        self,
        assets: list[VisualAsset],
        avatar_emotion: EmotionState = EmotionState.NEUTRAL,
        target: RenderTarget | None = None,
    ) -> SceneComposition:
        """Compose a scene from classified assets.

        Args:
            assets: Visual assets to include in the scene.
            avatar_emotion: Current avatar emotion state.
            target: Rendering target override.

        Returns:
            SceneComposition ready for the rendering pipeline.
        """
        scene = SceneComposition(
            scene_id=self._generate_scene_id(assets),
            target=target or self._default_target,
            assets=assets,
            avatar_state=avatar_emotion,
        )
        log.info(
            "Composed scene %s: %d assets, %d est. draw calls",
            scene.scene_id[:12],
            len(assets),
            scene.total_draw_calls,
        )
        return scene

    def validate_performance(self, scene: SceneComposition) -> dict[str, Any]:
        """Validate scene against performance budget.

        Returns:
            Performance report with warnings if budget exceeded.
        """
        total_budget_ms = min(a.frame_budget_ms for a in scene.assets) if scene.assets else 16.0
        estimated_ms = scene.total_draw_calls * 0.5  # simplified estimate
        within_budget = estimated_ms <= total_budget_ms

        report = {
            "scene_id": scene.scene_id,
            "target": scene.target.value,
            "draw_calls": scene.total_draw_calls,
            "estimated_ms": round(estimated_ms, 2),
            "budget_ms": total_budget_ms,
            "within_budget": within_budget,
        }
        if not within_budget:
            log.warning("Scene %s exceeds frame budget: %.1fms > %.1fms",
                        scene.scene_id[:12], estimated_ms, total_budget_ms)
        return report

    # -- internal helpers --------------------------------------------------

    @staticmethod
    def _hash_path(path: str) -> str:
        return hashlib.sha256(path.encode()).hexdigest()

    @staticmethod
    def _generate_scene_id(assets: list[VisualAsset]) -> str:
        combined = "|".join(sorted(a.asset_id for a in assets))
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def _infer_category(path: str, tags: list[str]) -> AssetCategory:
        """Rule-based category inference from path and semantic tags."""
        lower_path = path.lower()
        tag_set = {t.lower() for t in tags}

        if "background" in tag_set or "bg" in lower_path:
            return AssetCategory.BACKGROUND
        if "character" in tag_set or "avatar" in lower_path:
            return AssetCategory.CHARACTER
        if "ui" in tag_set or "hud" in lower_path:
            return AssetCategory.UI_ELEMENT
        if "particle" in tag_set or "fx" in lower_path:
            return AssetCategory.PARTICLE_EFFECT
        if "light" in tag_set or "lighting" in lower_path:
            return AssetCategory.LIGHTING
        return AssetCategory.PROP
