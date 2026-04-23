"""
CAITE — Creative-AI Transformation Engine
multimedia-agents/audio_analysis_agent.py

Audio Analysis Agent — Sonic DNA Extraction & Acoustic Fingerprinting

Responsibilities:
- Ingest raw audio assets (file path or stream URL)
- Extract acoustic fingerprint (spectral centroid, chroma, MFCC, tempo)
- Classify emotional valence and arousal
- Generate Sonic DNA metadata for Semantic Graph ingestion
- All processing within sovereign perimeter — no external API calls for raw audio

Compliance: GDPR Article 25 — data minimisation enforced at extraction layer.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("caite.agents.audio_analysis")


@dataclass
class SonicDNA:
    """Sovereign acoustic fingerprint — the fundamental unit of audio intelligence."""

    asset_id: str
    source_hash: str          # SHA-256 of source file — no raw audio leaves sovereign boundary
    duration_seconds: float
    sample_rate: int

    # Spectral characteristics
    spectral_centroid_mean: float
    spectral_centroid_std: float
    chroma_vector: list[float]    # 12-element pitch class profile
    mfcc_coefficients: list[float]  # 13 MFCCs

    # Temporal characteristics
    tempo_bpm: float
    beat_regularity: float        # 0.0 (free) → 1.0 (metronomic)

    # Semantic classifications
    emotional_valence: float      # -1.0 (negative) → +1.0 (positive)
    emotional_arousal: float      # 0.0 (calm) → 1.0 (excited)
    genre_tags: list[str]
    language_detected: Optional[str] = None
    speaker_count: Optional[int] = None

    # Sovereignty metadata
    data_residency: str = "EU-WEST-1"
    processing_node: str = "sovereign-inference-cluster"
    gdpr_basis: str = "legitimate_interest"

    def to_semantic_graph_node(self) -> dict:
        """Serialise to Semantic Graph node format."""
        return {
            "node_type": "SonicDNA",
            "node_id": self.asset_id,
            "properties": {
                "source_hash": self.source_hash,
                "duration_s": self.duration_seconds,
                "tempo_bpm": self.tempo_bpm,
                "valence": self.emotional_valence,
                "arousal": self.emotional_arousal,
                "genre_tags": self.genre_tags,
                "language": self.language_detected,
                "data_residency": self.data_residency,
            },
            "embedding_hint": self.chroma_vector + self.mfcc_coefficients,
        }


class AudioAnalysisAgent:
    """
    Sovereign audio analysis agent.

    In production: integrates with librosa (local), Whisper (local),
    and a sovereign speaker diarisation model.

    In this reference implementation: demonstrates the full data contract
    and sovereignty enforcement logic. Swap _extract_features() for
    your chosen audio processing backend.
    """

    def __init__(
        self,
        data_residency: str = "EU-WEST-1",
        max_duration_seconds: int = 7200,
    ):
        self.data_residency = data_residency
        self.max_duration_seconds = max_duration_seconds
        log.info("AudioAnalysisAgent initialised | residency=%s", data_residency)

    def analyse(self, asset_path: str | Path) -> SonicDNA:
        """
        Analyse an audio asset and return its Sonic DNA.

        Args:
            asset_path: Local path to the audio file (wav, mp3, flac, aiff).
                        Must be within the sovereign data boundary.

        Returns:
            SonicDNA instance ready for Semantic Graph ingestion.
        """
        path = Path(asset_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio asset not found: {path}")

        log.info("Analysing asset: %s", path.name)

        source_hash = self._hash_file(path)
        asset_id = f"audio:{source_hash[:16]}"

        # In production: replace with librosa.load() + feature extraction
        features = self._extract_features_stub(path)

        dna = SonicDNA(
            asset_id=asset_id,
            source_hash=source_hash,
            duration_seconds=features["duration"],
            sample_rate=features["sample_rate"],
            spectral_centroid_mean=features["spectral_centroid_mean"],
            spectral_centroid_std=features["spectral_centroid_std"],
            chroma_vector=features["chroma"],
            mfcc_coefficients=features["mfcc"],
            tempo_bpm=features["tempo"],
            beat_regularity=features["beat_regularity"],
            emotional_valence=features["valence"],
            emotional_arousal=features["arousal"],
            genre_tags=features["genre_tags"],
            language_detected=features.get("language"),
            speaker_count=features.get("speaker_count"),
            data_residency=self.data_residency,
        )

        log.info(
            "Sonic DNA extracted | asset=%s | valence=%.2f | tempo=%.1f bpm",
            asset_id, dna.emotional_valence, dna.tempo_bpm,
        )
        return dna

    def batch_analyse(self, asset_paths: list[str | Path]) -> list[SonicDNA]:
        """Analyse multiple assets. Returns partial results on individual failures."""
        results = []
        for path in asset_paths:
            try:
                results.append(self.analyse(path))
            except Exception as exc:
                log.error("Failed to analyse %s: %s", path, exc)
        return results

    # ── Private ──────────────────────────────────────────────────────────

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA-256 hash of file content. Raw audio never leaves this hash."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _extract_features_stub(path: Path) -> dict:
        """
        Stub feature extractor.

        PRODUCTION REPLACEMENT:
            import librosa
            y, sr = librosa.load(str(path), sr=None)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1).tolist()
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).mean(axis=1).tolist()
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            # ... etc.
        """
        log.debug("Using stub feature extractor for: %s", path.name)
        return {
            "duration": 180.0,
            "sample_rate": 48000,
            "spectral_centroid_mean": 2400.0,
            "spectral_centroid_std": 380.0,
            "chroma": [0.6, 0.1, 0.4, 0.2, 0.7, 0.3, 0.5, 0.2, 0.4, 0.1, 0.6, 0.3],
            "mfcc": [-200.0, 80.0, -12.0, 18.0, -8.0, 4.0, -2.0, 6.0, -1.0, 3.0, -0.5, 2.0, 1.0],
            "tempo": 92.0,
            "beat_regularity": 0.72,
            "valence": 0.35,
            "arousal": 0.55,
            "genre_tags": ["documentary", "orchestral", "spoken_word"],
            "language": "de",
            "speaker_count": 2,
        }
