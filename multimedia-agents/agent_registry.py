"""Sovereign Agent Registry — Capability map and lifecycle management for CAITE agents.

Part of the CAITE Sovereign Multimedia Transformation Engine.
Provides a centralised registry for all agents, tracking capabilities,
health status, and sovereignty compliance.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain Types
# ---------------------------------------------------------------------------

class AgentStatus(str, enum.Enum):
    """Agent lifecycle status."""
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class CapabilityDomain(str, enum.Enum):
    """Capability domains for agent routing."""
    AUDIO_ANALYSIS = "audio_analysis"
    VISUAL_ORCHESTRATION = "visual_orchestration"
    NARRATIVE_DESIGN = "narrative_design"
    CREATIVE_DIRECTION = "creative_direction"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    SOVEREIGN_REVIEW = "sovereign_review"


@dataclass
class AgentCapability:
    """A single capability offered by an agent."""
    domain: CapabilityDomain
    description: str
    max_concurrency: int = 1
    latency_budget_ms: float = 1000.0
    sovereignty_required: bool = True


@dataclass
class AgentRecord:
    """Registry entry for a single sovereign agent."""
    agent_id: str
    name: str
    capabilities: list[AgentCapability]
    status: AgentStatus = AgentStatus.AVAILABLE
    sovereignty_label: str = "eu-sovereign"
    version: str = "1.0.0"
    last_health_check: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate task success rate."""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "capabilities": [c.domain.value for c in self.capabilities],
            "sovereignty": self.sovereignty_label,
            "version": self.version,
            "success_rate": round(self.success_rate, 3),
            "tasks_completed": self.tasks_completed,
        }


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Centralised registry for sovereign CAITE agents.

    Tracks agent capabilities, health status, and routes tasks
    to the most appropriate agent based on domain and availability.
    All registered agents must operate within the sovereign perimeter.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._health_callbacks: dict[str, Callable[[], bool]] = {}
        log.info("AgentRegistry initialised")

    def register(self, record: AgentRecord) -> None:
        """Register an agent in the sovereign registry.

        Args:
            record: Agent record with capabilities and metadata.

        Raises:
            ValueError: If agent ID is already registered.
        """
        if record.agent_id in self._agents:
            raise ValueError(f"Agent '{record.agent_id}' already registered")
        self._agents[record.agent_id] = record
        log.info("Registered agent '%s' (%s) with %d capabilities",
                 record.name, record.agent_id, len(record.capabilities))

    def deregister(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._health_callbacks.pop(agent_id, None)
            log.info("Deregistered agent '%s'", agent_id)

    def find_by_capability(
        self,
        domain: CapabilityDomain,
        status_filter: AgentStatus | None = AgentStatus.AVAILABLE,
    ) -> list[AgentRecord]:
        """Find agents matching a capability domain.

        Args:
            domain: Required capability domain.
            status_filter: Optional status filter (None = all statuses).

        Returns:
            List of matching agent records, sorted by success rate.
        """
        matches = []
        for agent in self._agents.values():
            if status_filter and agent.status != status_filter:
                continue
            if any(c.domain == domain for c in agent.capabilities):
                matches.append(agent)

        matches.sort(key=lambda a: a.success_rate, reverse=True)
        return matches

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        """Retrieve an agent record by ID."""
        return self._agents.get(agent_id)

    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        """Update an agent's lifecycle status."""
        agent = self._agents.get(agent_id)
        if agent:
            old_status = agent.status
            agent.status = status
            log.info("Agent '%s' status: %s → %s", agent_id, old_status.value, status.value)

    def record_task_result(self, agent_id: str, success: bool) -> None:
        """Record a task completion result for an agent."""
        agent = self._agents.get(agent_id)
        if agent:
            if success:
                agent.tasks_completed += 1
            else:
                agent.tasks_failed += 1

    def run_health_checks(self) -> dict[str, Any]:
        """Execute health checks for all registered agents.

        Returns:
            Health report with per-agent status.
        """
        report: dict[str, Any] = {"timestamp": time.time(), "agents": {}}
        for agent_id, agent in self._agents.items():
            callback = self._health_callbacks.get(agent_id)
            if callback:
                try:
                    healthy = callback()
                    agent.last_health_check = time.time()
                    if not healthy:
                        agent.status = AgentStatus.DEGRADED
                except Exception as exc:
                    log.error("Health check failed for '%s': %s", agent_id, exc)
                    agent.status = AgentStatus.OFFLINE

            report["agents"][agent_id] = {
                "status": agent.status.value,
                "last_check": agent.last_health_check,
                "success_rate": round(agent.success_rate, 3),
            }

        healthy_count = sum(
            1 for a in self._agents.values()
            if a.status == AgentStatus.AVAILABLE
        )
        report["healthy"] = healthy_count
        report["total"] = len(self._agents)
        return report

    def register_health_callback(
        self,
        agent_id: str,
        callback: Callable[[], bool],
    ) -> None:
        """Register a health check callback for an agent."""
        self._health_callbacks[agent_id] = callback

    def get_capability_map(self) -> dict[str, list[str]]:
        """Return a map of capabilities to available agents."""
        cap_map: dict[str, list[str]] = {}
        for agent in self._agents.values():
            for cap in agent.capabilities:
                domain_key = cap.domain.value
                if domain_key not in cap_map:
                    cap_map[domain_key] = []
                cap_map[domain_key].append(agent.agent_id)
        return cap_map

    def get_swarm_status(self) -> dict[str, Any]:
        """Get a summary of the entire agent swarm status."""
        return {
            "total_agents": len(self._agents),
            "by_status": {
                s.value: sum(1 for a in self._agents.values() if a.status == s)
                for s in AgentStatus
            },
            "capability_coverage": list(self.get_capability_map().keys()),
            "agents": [a.to_dict() for a in self._agents.values()],
        }
