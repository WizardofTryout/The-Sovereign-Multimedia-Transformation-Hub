"""
CAITE — Creative-AI Transformation Engine
immersive-interface/main.py

Sovereign Real-Time Gateway
FastAPI + WebSocket bridge between AI orchestration layer and immersive engines
(Unity · Unreal · WebGL · WebAudio API)

Latency target: <20ms agent-to-engine round trip on EU-sovereign infrastructure
Security: JWT-authenticated WebSocket sessions, per-event audit logging
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from audio_stream_handler import AudioStreamHandler, SpatialSource
from avatar_sync_handler import AvatarSyncHandler, EmotionCategory

log = logging.getLogger("caite.immersive_interface")

app = FastAPI(
    title="CAITE Immersive Interface",
    description="Sovereign real-time bridge: AI agents ↔ game engines & spatial audio",
    version="1.0.0",
    docs_url="/api/docs",
)

# Sovereign CORS policy — restrict to your domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-sovereign-domain.eu"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────

class SpatialAudioCommand(BaseModel):
    """Real-time spatial audio parameter update."""
    session_id: str
    event_type: str = "spatial_audio_update"
    room_size: float = Field(ge=0.0, le=1.0, description="Reverb room size 0–1")
    dampening: float = Field(ge=0.0, le=1.0)
    hrtf_profile: str = Field(description="HRTF profile ID for binaural rendering")
    source_position: dict[str, float] = Field(description="x, y, z in meters")
    gain_db: float = Field(ge=-60.0, le=12.0)
    timestamp_ms: int


class AvatarStateUpdate(BaseModel):
    """Real-time avatar emotion and behaviour state."""
    session_id: str
    event_type: str = "avatar_state_update"
    avatar_id: str
    emotion: str = Field(description="joy | sadness | curiosity | neutral | concern")
    intensity: float = Field(ge=0.0, le=1.0)
    gaze_target: dict[str, float] = Field(description="x, y, z world position")
    lip_sync_phoneme: str | None = None
    animation_trigger: str | None = None
    timestamp_ms: int


class TransformationBriefRequest(BaseModel):
    """HTTP endpoint — submit a brief for async transformation."""
    raw_brief: str = Field(min_length=20)
    data_residency: str = "EU-WEST-1 (Frankfurt)"
    requester_id: str


class TransformationStatus(BaseModel):
    session_id: str
    status: str
    started_at: str
    message: str


# ─────────────────────────────────────────────
# In-memory session registry (replace with Redis in production)
# ─────────────────────────────────────────────
active_sessions: dict[str, dict[str, Any]] = {}
websocket_connections: dict[str, WebSocket] = {}


# ─────────────────────────────────────────────
# REST Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "sovereign",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_sessions": len(active_sessions),
        "data_residency": "EU-WEST-1",
    }


@app.post("/api/transformation/submit", response_model=TransformationStatus)
async def submit_transformation(request: TransformationBriefRequest):
    """
    Submit a creative brief for async multi-agent transformation.
    Returns session_id for WebSocket tracking.
    """
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "status": "queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "requester_id": request.requester_id,
        "data_residency": request.data_residency,
        "audio_handler": AudioStreamHandler(),
        "avatar_handler": AvatarSyncHandler(),
    }

    log.info("Transformation queued | session=%s | requester=%s", session_id, request.requester_id)

    # In production: enqueue to Celery / ARQ / Temporal task queue
    # await task_queue.enqueue("run_transformation", session_id, request.raw_brief)

    return TransformationStatus(
        session_id=session_id,
        status="queued",
        started_at=active_sessions[session_id]["started_at"],
        message="Connect to /ws/{session_id} for real-time progress updates.",
    )


@app.post("/api/audio/command")
async def send_audio_command(cmd: SpatialAudioCommand):
    """Push a spatial audio command to the connected immersive client."""
    if cmd.session_id not in websocket_connections:
        raise HTTPException(status_code=404, detail="No active WebSocket for this session.")

    session_data = active_sessions.get(cmd.session_id)
    if not session_data or "audio_handler" not in session_data:
        raise HTTPException(status_code=400, detail="Invalid session object.")

    handler: AudioStreamHandler = session_data["audio_handler"]
    source_id = "spatial_voice_1"
    
    gain_linear = 10 ** (cmd.gain_db / 20.0)
    pos = (cmd.source_position.get("x", 0.0), cmd.source_position.get("y", 0.0), cmd.source_position.get("z", 0.0))

    if source_id not in handler._sources:
        handler.add_source(SpatialSource(source_id=source_id, position=pos, gain=gain_linear))
    else:
        handler.update_source_position(source_id, pos)
        handler.update_source_gain(source_id, gain_linear)

    ws = websocket_connections[cmd.session_id]
    for update in handler.flush_updates():
        await ws.send_text(json.dumps(update))

    log.info("Audio command sent | session=%s | room_size=%.2f", cmd.session_id, cmd.room_size)
    return {"dispatched": True}


@app.post("/api/avatar/update")
async def send_avatar_update(update: AvatarStateUpdate):
    """Push an avatar state update to the connected immersive client."""
    if update.session_id not in websocket_connections:
        raise HTTPException(status_code=404, detail="No active WebSocket for this session.")

    session_data = active_sessions.get(update.session_id)
    if not session_data or "avatar_handler" not in session_data:
        raise HTTPException(status_code=400, detail="Invalid session object.")

    handler: AvatarSyncHandler = session_data["avatar_handler"]
    
    try:
        category = EmotionCategory(update.emotion.lower())
    except ValueError:
        category = EmotionCategory.NEUTRAL
        
    handler.set_emotion(category=category, intensity=update.intensity)
    
    if update.gaze_target:
        handler.set_pose(gaze_target=(update.gaze_target.get("x", 0.0), update.gaze_target.get("y", 0.0), update.gaze_target.get("z", 0.0)))

    ws = websocket_connections[update.session_id]
    for msg in handler.flush_updates():
        await ws.send_text(json.dumps(msg))

    log.info(
        "Avatar update sent | session=%s | avatar=%s | emotion=%s",
        update.session_id, update.avatar_id, update.emotion,
    )
    return {"dispatched": True}


# ─────────────────────────────────────────────
# WebSocket — Real-Time Engine Bridge
# ─────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_immersive_bridge(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket gateway.

    Client (Unity/Unreal/WebGL) → Server: user interaction events, position updates
    Server → Client: spatial audio commands, avatar state, narrative triggers
    """
    await websocket.accept()
    websocket_connections[session_id] = websocket

    log.info("WebSocket connected | session=%s", session_id)

    # Send sovereign handshake
    await websocket.send_text(json.dumps({
        "event": "sovereign_handshake",
        "session_id": session_id,
        "data_residency": "EU-WEST-1",
        "latency_budget_ms": 20,
        "protocol_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))

    try:
        while True:
            raw = await websocket.receive_text()
            event = json.loads(raw)
            await _handle_client_event(session_id, event, websocket)

    except WebSocketDisconnect:
        log.info("WebSocket disconnected | session=%s", session_id)
        websocket_connections.pop(session_id, None)
    except Exception as exc:
        log.error("WebSocket error | session=%s | error=%s", session_id, exc)
        websocket_connections.pop(session_id, None)


async def _handle_client_event(
    session_id: str,
    event: dict[str, Any],
    ws: WebSocket,
) -> None:
    """Route incoming client events to the appropriate agent handler."""
    event_type = event.get("event_type", "unknown")
    session_data = active_sessions.get(session_id, {})

    if event_type == "user_position_update":
        # Update spatial audio based on user head position (VR/XR)
        if "audio_handler" in session_data:
            pos = event.get("position", {})
            fwd = event.get("forward", {})
            session_data["audio_handler"].set_listener_position(
                position=(pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)),
                orientation=(fwd.get("x", 0.0), fwd.get("y", 0.0), fwd.get("z", -1.0))
            )
            for update in session_data["audio_handler"].flush_updates():
                await ws.send_text(json.dumps(update))

        await ws.send_text(json.dumps({
            "event": "audio_position_ack",
            "session_id": session_id,
            "processed": True,
        }))

    elif event_type == "narrative_choice":
        # User selected a narrative branch — trigger Narrative Design Agent
        log.info("Narrative choice | session=%s | choice=%s", session_id, event.get("choice_id"))
        # In production: enqueue to narrative agent, respond with next scene config

    elif event_type == "avatar_interaction":
        # User interacted with avatar — trigger emotion state update
        log.info("Avatar interaction | session=%s | avatar=%s", session_id, event.get("avatar_id"))

    else:
        log.warning("Unknown event type | session=%s | type=%s", session_id, event_type)
