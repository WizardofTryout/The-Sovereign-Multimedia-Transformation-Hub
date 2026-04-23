"""Narrative Design Agent — Semantic tagging, story graph construction, and adaptive narrative.

Part of the CAITE Sovereign Multimedia Transformation Engine.
This agent enriches the Semantic Graph with contextual intelligence,
builds story graphs for adaptive narratives, and manages narrative coherence.
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

class NarrativeTone(str, enum.Enum):
    """Editorial tone classification."""
    AUTHORITATIVE = "authoritative"
    CONVERSATIONAL = "conversational"
    INVESTIGATIVE = "investigative"
    CELEBRATORY = "celebratory"
    URGENT = "urgent"
    REFLECTIVE = "reflective"


class RelationshipType(str, enum.Enum):
    """Typed relationships in the knowledge graph."""
    IS_PART_OF = "IS_PART_OF"
    REFERENCES = "REFERENCES"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"
    PRECEDES = "PRECEDES"
    FOLLOWS = "FOLLOWS"
    CAUSED_BY = "CAUSED_BY"


@dataclass
class SemanticTag:
    """A semantic label attached to a knowledge graph node."""
    label: str
    category: str
    confidence: float
    source_agent: str = "narrative_design"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "source": self.source_agent,
        }


@dataclass
class NarrativeNode:
    """A node in the story graph representing a narrative beat."""
    node_id: str
    content_summary: str
    tone: NarrativeTone
    entities: list[str] = field(default_factory=list)
    semantic_tags: list[SemanticTag] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    sovereignty_label: str = "eu-sovereign"

    def to_graph_node(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "summary": self.content_summary,
            "tone": self.tone.value,
            "entities": self.entities,
            "tags": [t.to_dict() for t in self.semantic_tags],
            "branches": self.branches,
            "sovereignty": self.sovereignty_label,
        }


@dataclass
class GraphRelationship:
    """A typed, weighted relationship between two graph nodes."""
    source_id: str
    target_id: str
    relationship: RelationshipType
    confidence: float
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relationship.value,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Narrative Design Agent
# ---------------------------------------------------------------------------

class NarrativeDesignAgent:
    """Enriches the Semantic Graph with narrative intelligence.

    Performs topic classification, entity extraction, sentiment mapping,
    and story graph construction — all within the sovereign perimeter.
    """

    def __init__(self, ontology: dict[str, list[str]] | None = None) -> None:
        self._ontology = ontology or self._default_ontology()
        self._story_graph: dict[str, NarrativeNode] = {}
        self._relationships: list[GraphRelationship] = []
        log.info("NarrativeDesignAgent initialised (%d taxonomy categories)",
                 len(self._ontology))

    def tag_content(
        self,
        content: str,
        source_node_id: str | None = None,
    ) -> list[SemanticTag]:
        """Apply semantic tags to content using the domain ontology.

        Args:
            content: Text content to classify.
            source_node_id: Optional graph node ID for provenance.

        Returns:
            List of SemanticTag instances with confidence scores.
        """
        tags: list[SemanticTag] = []
        content_lower = content.lower()

        for category, keywords in self._ontology.items():
            matches = [kw for kw in keywords if kw.lower() in content_lower]
            if matches:
                confidence = min(1.0, len(matches) * 0.3)
                tag = SemanticTag(
                    label=matches[0],
                    category=category,
                    confidence=confidence,
                )
                tags.append(tag)

        log.info("Tagged content → %d semantic tags", len(tags))
        return tags

    def create_narrative_node(
        self,
        content: str,
        tone: NarrativeTone = NarrativeTone.AUTHORITATIVE,
        entities: list[str] | None = None,
    ) -> NarrativeNode:
        """Create a narrative node for the story graph.

        Args:
            content: Narrative content or summary.
            tone: Editorial tone classification.
            entities: Named entities mentioned in the content.

        Returns:
            NarrativeNode registered in the story graph.
        """
        node_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        tags = self.tag_content(content)

        node = NarrativeNode(
            node_id=node_id,
            content_summary=content[:200],
            tone=tone,
            entities=entities or [],
            semantic_tags=tags,
        )
        self._story_graph[node_id] = node
        log.info("Created narrative node %s (tone=%s)", node_id, tone.value)
        return node

    def link_nodes(
        self,
        source: NarrativeNode,
        target: NarrativeNode,
        relationship: RelationshipType,
        confidence: float = 0.8,
        evidence: str = "",
    ) -> GraphRelationship:
        """Create a typed relationship between two narrative nodes.

        Args:
            source: Source narrative node.
            target: Target narrative node.
            relationship: Typed relationship classification.
            confidence: Confidence weight (0.0–1.0).
            evidence: Supporting evidence for the relationship.

        Returns:
            GraphRelationship instance.
        """
        rel = GraphRelationship(
            source_id=source.node_id,
            target_id=target.node_id,
            relationship=relationship,
            confidence=confidence,
            evidence=evidence,
        )
        self._relationships.append(rel)
        source.branches.append(target.node_id)
        log.info("Linked %s → %s (%s, conf=%.2f)",
                 source.node_id, target.node_id, relationship.value, confidence)
        return rel

    def get_story_graph(self) -> dict[str, Any]:
        """Export the current story graph as a serialisable dict."""
        return {
            "nodes": {nid: n.to_graph_node() for nid, n in self._story_graph.items()},
            "relationships": [r.to_dict() for r in self._relationships],
            "node_count": len(self._story_graph),
            "relationship_count": len(self._relationships),
        }

    def validate_coherence(self) -> dict[str, Any]:
        """Check narrative coherence across the story graph.

        Returns:
            Coherence report with warnings for orphaned or contradicting nodes.
        """
        orphans = [nid for nid, n in self._story_graph.items() if not n.branches]
        contradiction_count = sum(
            1 for r in self._relationships
            if r.relationship == RelationshipType.CONTRADICTS
        )

        report = {
            "total_nodes": len(self._story_graph),
            "orphan_nodes": len(orphans),
            "contradictions": contradiction_count,
            "coherent": len(orphans) <= 1 and contradiction_count == 0,
        }
        if not report["coherent"]:
            log.warning("Coherence check failed: %d orphans, %d contradictions",
                        len(orphans), contradiction_count)
        return report

    @staticmethod
    def _default_ontology() -> dict[str, list[str]]:
        """Default domain-specific ontology for multimedia transformation."""
        return {
            "audio": ["spatial audio", "sonic", "acoustic", "frequency", "reverb", "HRTF"],
            "visual": ["rendering", "avatar", "scene", "animation", "lighting", "texture"],
            "narrative": ["story", "dialogue", "character", "plot", "branching", "pacing"],
            "technology": ["WebSocket", "API", "pipeline", "latency", "GPU", "inference"],
            "compliance": ["GDPR", "sovereign", "privacy", "encryption", "audit", "lineage"],
            "business": ["ROI", "revenue", "churn", "EBITDA", "transformation", "PE"],
        }
