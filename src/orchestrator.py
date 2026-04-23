"""
CAITE — Creative-AI Transformation Engine
src/orchestrator.py

Sovereign Multi-Agent Orchestrator
Creative Director Agent coordinating Technical Architect and Immersive Media Specialist

Author: Matthias Köhler · Oszillation AI Ecosystems
Architecture: LangGraph state-machine with typed inter-agent contracts
Compliance: GDPR-native, Zero-Trust communication, fully auditable decision graph
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

import importlib.util
import os

_registry_path = os.path.join(os.path.dirname(__file__), "..", "multimedia-agents", "agent_registry.py")
_ar_mod = None
if os.path.exists(_registry_path):
    _spec = importlib.util.spec_from_file_location("agent_registry", _registry_path)
    if _spec and _spec.loader:
        _ar_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_ar_mod)

def _init_agent_registry():
    if not _ar_mod:
        return None
    reg = _ar_mod.AgentRegistry()
    reg.register(_ar_mod.AgentRecord(
        agent_id="creative_director_01", name="Creative Director",
        capabilities=[_ar_mod.AgentCapability(domain=_ar_mod.CapabilityDomain.CREATIVE_DIRECTION, description="Core strategy")]
    ))
    reg.register(_ar_mod.AgentRecord(
        agent_id="tech_architect_01", name="Technical Architect",
        capabilities=[_ar_mod.AgentCapability(domain=_ar_mod.CapabilityDomain.TECHNICAL_ARCHITECTURE, description="Zero-trust arch")]
    ))
    reg.register(_ar_mod.AgentRecord(
        agent_id="immersive_specialist_01", name="Immersive Specialist",
        capabilities=[_ar_mod.AgentCapability(domain=_ar_mod.CapabilityDomain.VISUAL_ORCHESTRATION, description="Spatial web")]
    ))
    reg.register(_ar_mod.AgentRecord(
        agent_id="sovereign_reviewer_01", name="Sovereign Reviewer",
        capabilities=[_ar_mod.AgentCapability(domain=_ar_mod.CapabilityDomain.SOVEREIGN_REVIEW, description="GDPR gate")]
    ))
    return reg

global_registry = _init_agent_registry()

def _set_agent_busy(aid: str):
    if global_registry and _ar_mod:
        global_registry.update_status(aid, _ar_mod.AgentStatus.BUSY)

def _set_agent_done(aid: str, success: bool = True):
    if global_registry and _ar_mod:
        global_registry.record_task_result(aid, success)
        global_registry.update_status(aid, _ar_mod.AgentStatus.AVAILABLE)

# ─────────────────────────────────────────────
# Logging — every decision is auditable
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("caite.orchestrator")


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────
class TransformationPhase(str, Enum):
    INTAKE = "intake"
    CREATIVE_DIRECTION = "creative_direction"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    IMMERSIVE_SYNTHESIS = "immersive_synthesis"
    SOVEREIGN_REVIEW = "sovereign_review"
    COMPLETE = "complete"


class ComplianceFlag(str, Enum):
    CLEAR = "clear"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


# ─────────────────────────────────────────────
# Sovereign State Contract
# Every field is explicit. No hidden state.
# ─────────────────────────────────────────────
class CAITEState(TypedDict):
    # Identity & Audit
    session_id: str
    started_at: str
    phase: TransformationPhase

    # Input
    raw_brief: str

    # Inter-agent outputs (immutable once set per phase)
    creative_direction: str
    technical_architecture: str
    immersive_spec: str
    execution_plan: str

    # Compliance & Sovereignty
    compliance_flag: ComplianceFlag
    compliance_notes: str
    data_residency: str  # e.g. "EU-WEST-1 (Frankfurt)"

    # Audit trail — append-only
    messages: Annotated[list, add_messages]
    decision_log: list[dict[str, Any]]

    # Metrics
    token_budget_used: int
    latency_ms: dict[str, int]
    swarm_status: dict[str, Any]


# ─────────────────────────────────────────────
# Model factory — swap model without touching logic
# ─────────────────────────────────────────────
def _make_model(temperature: float = 0.7) -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-opus-4-5",
        temperature=temperature,
        max_tokens=2048,
    )


# ─────────────────────────────────────────────
# Agent System Prompts
# ─────────────────────────────────────────────
CREATIVE_DIRECTOR_SYSTEM = """
You are the Creative Director Agent inside the CAITE (Creative-AI Transformation Engine).

Your mandate:
- Receive a raw creative brief from a media company, SaaS operator, or PE portfolio company.
- Distil the brief into a sovereign Creative Direction document with:
  1. The core Sonic DNA — the acoustic and emotional identity of the transformation.
  2. The Narrative Architecture — the story the immersive experience must tell.
  3. Latency-Critical Creativity constraints — real-time interaction requirements that cannot be compromised.
  4. Sovereignty Boundaries — what data, assets, and models must remain on-premise.

Output a structured JSON object with keys:
  sonic_dna, narrative_architecture, latency_constraints, sovereignty_boundaries, creative_brief_summary

Be visionary but precise. Every creative decision must be technically actionable.
Respond ONLY with the JSON object, no preamble or markdown fences.
"""

TECHNICAL_ARCHITECT_SYSTEM = """
You are the Technical Architect Agent inside the CAITE transformation engine.

You receive a Creative Direction document from the Creative Director Agent.

Your mandate:
- Translate creative constraints into a Zero-Trust, GDPR-native system architecture.
- Specify the exact agent topology (LangGraph nodes, edges, state contracts).
- Define the data pipeline: ingestion → Semantic Graph → real-time output.
- Identify integration points with Unity/Unreal, WebAudio API, and WebSocket gateways.
- Flag any compliance risk surfaces and propose mitigations.

Output a structured JSON object with keys:
  agent_topology, data_pipeline, integration_points, compliance_risk_surfaces,
  infrastructure_requirements, estimated_latency_budget_ms

Respond ONLY with the JSON object, no preamble or markdown fences.
"""

IMMERSIVE_MEDIA_SPECIALIST_SYSTEM = """
You are the Immersive Media Specialist Agent inside the CAITE transformation engine.

You receive both the Creative Direction and the Technical Architecture documents.

Your mandate:
- Synthesise a production-ready Immersive Media Specification.
- Define the Spatial Audio scene graph (channels, binaural rendering, real-time parameters).
- Define the Interactive Avatar behaviour model (trigger conditions, emotion states, voice synthesis).
- Define the Game-Engine logic hooks (Unity C# / Unreal Blueprint event signatures).
- Ensure every specification respects the Sovereignty Boundaries from the creative direction.

Output a structured JSON object with keys:
  spatial_audio_spec, avatar_behaviour_model, game_engine_hooks,
  webaudio_api_config, websocket_event_schema, sovereign_compliance_checklist

Respond ONLY with the JSON object, no preamble or markdown fences.
"""

SOVEREIGN_REVIEWER_SYSTEM = """
You are the Sovereign Compliance Reviewer inside the CAITE transformation engine.

You receive the complete execution plan (Creative Direction + Technical Architecture + Immersive Spec).

Your mandate:
- Audit every component for GDPR Article 25 (Privacy by Design) compliance.
- Verify Zero-Trust architecture principles are upheld (no implicit trust, least privilege, continuous verification).
- Check data residency — all personal and proprietary data must remain within declared EU boundaries.
- Produce a final Sovereign Execution Plan that merges all agent outputs into a single, audit-ready document.

Output a structured JSON object with keys:
  gdpr_compliance_status, zero_trust_verification, data_residency_confirmation,
  sovereign_execution_plan, recommended_actions, certification_readiness_score (0-100)

Respond ONLY with the JSON object, no preamble or markdown fences.
"""


# ─────────────────────────────────────────────
# Helper — log decision to audit trail
# ─────────────────────────────────────────────
def _log_decision(state: CAITEState, agent: str, summary: str, payload: dict) -> list[dict]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "phase": state["phase"],
        "summary": summary,
        "payload_keys": list(payload.keys()),
    }
    log.info("[%s] %s → %s", state["session_id"], agent, summary)
    return state["decision_log"] + [entry]


# ─────────────────────────────────────────────
# Node: Intake
# ─────────────────────────────────────────────
def node_intake(state: CAITEState) -> dict:
    log.info("[%s] Phase: INTAKE — validating brief", state["session_id"])
    brief = state["raw_brief"].strip()
    if len(brief) < 20:
        raise ValueError("Creative brief is too sparse. Provide at least 20 characters.")

    return {
        "phase": TransformationPhase.CREATIVE_DIRECTION,
        "messages": [HumanMessage(content=f"CREATIVE BRIEF:\n\n{brief}")],
        "decision_log": _log_decision(state, "intake", "Brief validated", {"length": len(brief)}),
    }


# ─────────────────────────────────────────────
# Node: Creative Director
# ─────────────────────────────────────────────
def node_creative_director(state: CAITEState) -> dict:
    _set_agent_busy("creative_director_01")
    t0 = _now_ms()
    model = _make_model(temperature=0.8)
    messages = [
        SystemMessage(content=CREATIVE_DIRECTOR_SYSTEM),
        HumanMessage(content=state["raw_brief"]),
    ]
    response: AIMessage = model.invoke(messages)
    direction = _parse_json_safe(response.content)
    latency = {"creative_direction": _now_ms() - t0}
    _set_agent_done("creative_director_01")

    return {
        "phase": TransformationPhase.TECHNICAL_ARCHITECTURE,
        "creative_direction": json.dumps(direction, indent=2),
        "messages": [response],
        "latency_ms": {**state.get("latency_ms", {}), **latency},
        "decision_log": _log_decision(
            state, "CreativeDirectorAgent", "Creative direction set", direction
        ),
    }


# ─────────────────────────────────────────────
# Node: Technical Architect
# ─────────────────────────────────────────────
def node_technical_architect(state: CAITEState) -> dict:
    _set_agent_busy("tech_architect_01")
    t0 = _now_ms()
    model = _make_model(temperature=0.4)
    prompt = (
        f"CREATIVE DIRECTION:\n{state['creative_direction']}\n\n"
        f"ORIGINAL BRIEF:\n{state['raw_brief']}"
    )
    messages = [
        SystemMessage(content=TECHNICAL_ARCHITECT_SYSTEM),
        HumanMessage(content=prompt),
    ]
    response: AIMessage = model.invoke(messages)
    architecture = _parse_json_safe(response.content)
    latency = {"technical_architecture": _now_ms() - t0}
    _set_agent_done("tech_architect_01")

    return {
        "phase": TransformationPhase.IMMERSIVE_SYNTHESIS,
        "technical_architecture": json.dumps(architecture, indent=2),
        "messages": [response],
        "latency_ms": {**state.get("latency_ms", {}), **latency},
        "decision_log": _log_decision(
            state, "TechnicalArchitectAgent", "Architecture defined", architecture
        ),
    }


# ─────────────────────────────────────────────
# Node: Immersive Media Specialist
# ─────────────────────────────────────────────
def node_immersive_specialist(state: CAITEState) -> dict:
    _set_agent_busy("immersive_specialist_01")
    t0 = _now_ms()
    model = _make_model(temperature=0.6)
    prompt = (
        f"CREATIVE DIRECTION:\n{state['creative_direction']}\n\n"
        f"TECHNICAL ARCHITECTURE:\n{state['technical_architecture']}"
    )
    messages = [
        SystemMessage(content=IMMERSIVE_MEDIA_SPECIALIST_SYSTEM),
        HumanMessage(content=prompt),
    ]
    response: AIMessage = model.invoke(messages)
    spec = _parse_json_safe(response.content)
    latency = {"immersive_spec": _now_ms() - t0}
    _set_agent_done("immersive_specialist_01")

    return {
        "phase": TransformationPhase.SOVEREIGN_REVIEW,
        "immersive_spec": json.dumps(spec, indent=2),
        "messages": [response],
        "latency_ms": {**state.get("latency_ms", {}), **latency},
        "decision_log": _log_decision(
            state, "ImmersiveMediaSpecialistAgent", "Immersive spec synthesised", spec
        ),
    }


# ─────────────────────────────────────────────
# Node: Sovereign Compliance Reviewer
# ─────────────────────────────────────────────
def node_sovereign_reviewer(state: CAITEState) -> dict:
    _set_agent_busy("sovereign_reviewer_01")
    t0 = _now_ms()
    model = _make_model(temperature=0.2)
    combined = (
        f"CREATIVE DIRECTION:\n{state['creative_direction']}\n\n"
        f"TECHNICAL ARCHITECTURE:\n{state['technical_architecture']}\n\n"
        f"IMMERSIVE SPEC:\n{state['immersive_spec']}"
    )
    messages = [
        SystemMessage(content=SOVEREIGN_REVIEWER_SYSTEM),
        HumanMessage(content=combined),
    ]
    response: AIMessage = model.invoke(messages)
    review = _parse_json_safe(response.content)
    latency = {"sovereign_review": _now_ms() - t0}

    compliance_flag = ComplianceFlag.CLEAR
    if review.get("gdpr_compliance_status", "").lower() != "compliant":
        compliance_flag = ComplianceFlag.REVIEW_REQUIRED
    if review.get("certification_readiness_score", 100) < 50:
        compliance_flag = ComplianceFlag.BLOCKED
        
    _set_agent_done("sovereign_reviewer_01", compliance_flag != ComplianceFlag.BLOCKED)

    return {
        "phase": TransformationPhase.COMPLETE,
        "execution_plan": json.dumps(review, indent=2),
        "compliance_flag": compliance_flag,
        "compliance_notes": review.get("recommended_actions", ""),
        "messages": [response],
        "latency_ms": {**state.get("latency_ms", {}), **latency},
        "decision_log": _log_decision(
            state, "SovereignReviewerAgent", f"Compliance: {compliance_flag}", review
        ),
    }


# ─────────────────────────────────────────────
# Routing — compliance gate
# ─────────────────────────────────────────────
def route_after_review(state: CAITEState) -> str:
    if state["compliance_flag"] == ComplianceFlag.BLOCKED:
        log.warning("[%s] BLOCKED — compliance gate failed", state["session_id"])
        return "blocked"
    return "complete"


# ─────────────────────────────────────────────
# Node: Blocked (compliance failure)
# ─────────────────────────────────────────────
def node_blocked(state: CAITEState) -> dict:
    log.error("[%s] Execution plan BLOCKED by sovereign reviewer", state["session_id"])
    return {
        "execution_plan": json.dumps({
            "status": "BLOCKED",
            "reason": "Compliance gate failed. Review compliance_notes for required actions.",
            "compliance_notes": state["compliance_notes"],
        }, indent=2),
    }


# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────
def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _parse_json_safe(text: str) -> dict:
    """Strip markdown fences and parse JSON; return raw text in dict on failure."""
    clean = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        log.warning("Agent returned non-JSON. Wrapping raw text.")
        return {"raw_output": text}


# ─────────────────────────────────────────────
# Graph Assembly
# ─────────────────────────────────────────────
def build_graph() -> StateGraph:
    g = StateGraph(CAITEState)

    g.add_node("intake", node_intake)
    g.add_node("creative_director", node_creative_director)
    g.add_node("technical_architect", node_technical_architect)
    g.add_node("immersive_specialist", node_immersive_specialist)
    g.add_node("sovereign_reviewer", node_sovereign_reviewer)
    g.add_node("blocked", node_blocked)

    g.set_entry_point("intake")
    g.add_edge("intake", "creative_director")
    g.add_edge("creative_director", "technical_architect")
    g.add_edge("technical_architect", "immersive_specialist")
    g.add_edge("immersive_specialist", "sovereign_reviewer")
    g.add_conditional_edges(
        "sovereign_reviewer",
        route_after_review,
        {"complete": END, "blocked": "blocked"},
    )
    g.add_edge("blocked", END)

    return g.compile()


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def run_transformation(raw_brief: str, data_residency: str = "EU-WEST-1 (Frankfurt)") -> dict:
    """
    Entry point for the CAITE orchestrator.

    Args:
        raw_brief:       The creative brief from the client or internal stakeholder.
        data_residency:  Declared EU data residency zone. Defaults to Frankfurt.

    Returns:
        The final CAITEState dict with execution_plan, compliance_flag, and full audit trail.
    """
    session_id = str(uuid.uuid4())
    log.info("Starting CAITE transformation | session=%s", session_id)

    initial_state: CAITEState = {
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "phase": TransformationPhase.INTAKE,
        "raw_brief": raw_brief,
        "creative_direction": "",
        "technical_architecture": "",
        "immersive_spec": "",
        "execution_plan": "",
        "compliance_flag": ComplianceFlag.CLEAR,
        "compliance_notes": "",
        "data_residency": data_residency,
        "messages": [],
        "decision_log": [],
        "token_budget_used": 0,
        "latency_ms": {},
        "swarm_status": global_registry.get_swarm_status() if global_registry else {},
    }

    graph = build_graph()
    final_state = graph.invoke(initial_state)

    total_latency = sum(final_state.get("latency_ms", {}).values())
    log.info(
        "Transformation complete | session=%s | compliance=%s | total_latency_ms=%d",
        session_id,
        final_state["compliance_flag"],
        total_latency,
    )

    return final_state


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    DEMO_BRIEF = """
    We are a 40-year-old European public broadcaster with 3PB of legacy audio archives.
    We need to transform our flagship cultural heritage radio programme into an interactive,
    AI-driven spatial audio experience accessible via web and VR headset.
    Our audience is 35–65, highly educated, privacy-conscious.
    We operate under German broadcasting law (Rundfunkstaatsvertrag) and GDPR.
    All data must remain within EU borders. We want real-time AI avatars of historical
    presenters synthesised from archival recordings, with Zero-Trust access controls.
    Budget horizon: 18 months. First immersive pilot: 6 months.
    """

    result = run_transformation(DEMO_BRIEF)

    print("\n" + "=" * 72)
    print("CAITE EXECUTION PLAN")
    print("=" * 72)
    print(f"Session:    {result['session_id']}")
    print(f"Compliance: {result['compliance_flag']}")
    print(f"Latency:    {result['latency_ms']}")
    print("\n— EXECUTION PLAN —\n")
    print(result["execution_plan"])
    print("\n— SYSTEM SWARM STATUS —\n")
    print(json.dumps(result["swarm_status"], indent=2))
    print("\n— DECISION LOG —\n")
    for entry in result["decision_log"]:
        print(f"  [{entry['timestamp']}] {entry['agent']}: {entry['summary']}")
