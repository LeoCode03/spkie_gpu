"""
backend/pipeline.py — Wave 7
Orquestador central del pipeline de análisis de video YouTube.
"""
from __future__ import annotations

import time
from typing import Callable

from pydantic import BaseModel


# ─── Metadatos de fases ───────────────────────────────────────────────────────

PHASE_LABELS: dict[str, str] = {
    "registro_video":            "📝 Registrando video",
    "metadata_youtube":          "📊 Metadata YouTube",
    "transcripcion_api":         "📄 Transcripción YouTube API",
    "analisis_llm":              "🧠 Análisis LLM",
    "sentimiento_comentarios":   "💬 Sentimiento comentarios",
    "generacion_guion":          "✍️ Generación de guion",
    "prompts_imagen":            "🖼️ Prompts de imagen",
    "prompts_video":             "🎬 Prompts de video",
    "persistencia":              "💾 Guardando en BD",
}

_PHASE_ORDER = list(PHASE_LABELS.keys())
TOTAL_PHASES = len(_PHASE_ORDER)

from backend.config import settings
from backend.core.downloader import extract_video_id, register_video
from backend.core.transcriber_api import fetch_transcript
from backend.database.client import close_db, get_connection, init_db
from backend.services.analyzer import LLMAnalyzer
from backend.services.generator import ContentGenerator
from backend.services.schemas import (
    AnalysisResult,
    ImagePrompt,
    ScriptResult,
    SentimentResult,
    VideoPrompt,
)
from backend.services.youtube_service import YouTubeService


# ─── Schema de resultado ──────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    """Resultado completo de una ejecución del pipeline."""
    video_id: int                          # PK en la tabla videos
    video_youtube_id: str                  # ID de YouTube (11 chars)
    metadata: dict
    transcript: str
    analysis: AnalysisResult
    sentiment: SentimentResult
    script: ScriptResult
    image_prompts: list[ImagePrompt]
    video_prompts: list[VideoPrompt]
    timing_summary: dict[str, float]       # fase → duración en segundos


# ─── Pipeline ────────────────────────────────────────────────────────────────

class VideoPipeline:
    """
    Orquesta las 9 fases del pipeline completo:
    descarga → metadata → transcripción → análisis → sentimiento
    → guion → prompts imagen → prompts video → persistencia
    """

    def __init__(self) -> None:
        self._yt = YouTubeService()
        self._analyzer = LLMAnalyzer()
        self._generator = ContentGenerator()

    # ── Pipeline principal ────────────────────────────────────────────────────

    async def run(
        self,
        url: str,
        on_phase_start: Callable[[str, int, int], None] | None = None,
        on_phase_done: Callable[[str, float], None] | None = None,
    ) -> PipelineResult:
        """
        Ejecuta el pipeline completo para la URL dada.

        on_phase_start(key, phase_num, total) — llamado justo antes de cada fase.
        on_phase_done(key, duration_seconds)  — llamado justo después.
        """
        timings: dict[str, float] = {}
        youtube_id = extract_video_id(url)

        def _start(key: str) -> float:
            idx = _PHASE_ORDER.index(key) + 1
            if on_phase_start:
                on_phase_start(key, idx, TOTAL_PHASES)
            return time.perf_counter()

        def _done(key: str, t0: float) -> None:
            dur = time.perf_counter() - t0
            timings[key] = dur
            if on_phase_done:
                on_phase_done(key, dur)

        await init_db()
        try:
            async with get_connection() as conn:
                # 1 · Registro del video en BD ────────────────────────────────
                t0 = _start("registro_video")
                video_db_id = await register_video(conn, youtube_id, url)
                _done("registro_video", t0)

                # 2 · Metadata de YouTube (enrich actualiza la fila en BD) ─────
                t0 = _start("metadata_youtube")
                metadata, comments = await self._yt.enrich_video_in_db(
                    video_db_id=video_db_id,
                    video_id=youtube_id,
                    db_conn=conn,
                )
                _done("metadata_youtube", t0)

                # 3 · Transcripción vía YouTube API (usa cache si ya existe) ──
                t0 = _start("transcripcion_api")
                transcript = await fetch_transcript(youtube_id, video_db_id, conn)
                _done("transcripcion_api", t0)

                # 4 · Análisis de transcripción (2 pasadas internas) ───────────
                t0 = _start("analisis_llm")
                analysis = await self._analyzer.analyze_transcript(transcript, metadata)
                _done("analisis_llm", t0)

                # 5 · Sentimiento de comentarios ───────────────────────────────
                t0 = _start("sentimiento_comentarios")
                sentiment = await self._analyzer.analyze_sentiment(comments)
                _done("sentimiento_comentarios", t0)

                # 6 · Generación de guion ──────────────────────────────────────
                t0 = _start("generacion_guion")
                script = await self._generator.generate_script(analysis, sentiment, metadata)
                _done("generacion_guion", t0)

                # 7 · Prompts de imagen ────────────────────────────────────────
                t0 = _start("prompts_imagen")
                image_prompts = await self._generator.generate_image_prompts(script, metadata)
                _done("prompts_imagen", t0)

                # 8 · Prompts de movimiento de cámara ──────────────────────────
                t0 = _start("prompts_video")
                video_prompts = await self._generator.generate_video_prompts(image_prompts, script)
                _done("prompts_video", t0)

                # 9 · Persistencia en BD ───────────────────────────────────────
                t0 = _start("persistencia")
                await self._analyzer.save_to_db(video_db_id, analysis, sentiment, conn)
                await self._generator.save_to_db(
                    video_db_id, script, image_prompts, video_prompts, conn
                )
                _done("persistencia", t0)

        finally:
            await close_db()

        return PipelineResult(
            video_id=video_db_id,
            video_youtube_id=youtube_id,
            metadata=metadata,
            transcript=transcript,
            analysis=analysis,
            sentiment=sentiment,
            script=script,
            image_prompts=image_prompts,
            video_prompts=video_prompts,
            timing_summary=timings,
        )

    # ── Reporte de tiempos ────────────────────────────────────────────────────

    @staticmethod
    def timing_report(result: PipelineResult) -> str:
        """
        Genera una tabla ASCII con los tiempos de cada fase del pipeline.

        ┌─────────────────────────┬──────────────┐
        │ Fase                    │ Tiempo       │
        ├─────────────────────────┼──────────────┤
        │ Descarga audio          │  X m XX s    │
        │ ...                     │  ...         │
        ├─────────────────────────┼──────────────┤
        │ TOTAL                   │  X m XX s    │
        │ Entorno                 │  LOCAL       │
        └─────────────────────────┴──────────────┘
        """
        # Etiquetas legibles para cada fase (en el orden canónico)
        phase_labels: list[tuple[str, str]] = [
            ("registro_video",           "Registro video"),
            ("transcripcion_api",        "Transcripción API"),
            ("metadata_youtube",         "Metadata YouTube"),
            ("analisis_llm",             "Análisis LLM"),
            ("sentimiento_comentarios",  "Sentimiento comentarios"),
            ("generacion_guion",         "Generación guion"),
            ("prompts_imagen",           "Prompts imagen"),
            ("prompts_video",            "Prompts video"),
        ]

        def _fmt(seconds: float) -> str:
            mins, secs = divmod(int(seconds), 60)
            return f"{mins} m {secs:02d} s"

        col_fase = 25
        col_tiempo = 12
        sep_top   = f"┌{'─' * (col_fase + 2)}┬{'─' * (col_tiempo + 2)}┐"
        sep_head  = f"├{'─' * (col_fase + 2)}┼{'─' * (col_tiempo + 2)}┤"
        sep_bot   = f"└{'─' * (col_fase + 2)}┴{'─' * (col_tiempo + 2)}┘"

        def row(label: str, value: str) -> str:
            return f"│ {label:<{col_fase}} │ {value:>{col_tiempo}} │"

        lines: list[str] = [
            sep_top,
            row("Fase", "Tiempo"),
            sep_head,
        ]

        total = 0.0
        for key, label in phase_labels:
            dur = result.timing_summary.get(key, 0.0)
            total += dur
            lines.append(row(label, _fmt(dur)))

        # Añadir fases no cubiertas por phase_labels (por si se agregan más)
        known_keys = {k for k, _ in phase_labels}
        for key, dur in result.timing_summary.items():
            if key not in known_keys:
                total += dur
                lines.append(row(key.replace("_", " ").title(), _fmt(dur)))

        lines.append(sep_head)
        lines.append(row("TOTAL", _fmt(total)))
        lines.append(row("Entorno", settings.ENVIRONMENT.upper()))
        lines.append(sep_bot)

        return "\n".join(lines)
