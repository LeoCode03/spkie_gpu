"""
backend/api/server.py — Wave 7
FastAPI server para el pipeline Spike GPU.

Endpoints:
  POST /analyze          → ejecuta pipeline completo, retorna PipelineResult
  GET  /health           → estado del servicio y configuración actual
  GET  /timings/{vid_id} → historial de tiempos de un video desde BD

Lifespan: inicializa el pool de BD al arrancar y lo cierra al detener.
"""
from __future__ import annotations

# ── Fix: Windows + Python 3.10 necesita SelectorEventLoop para psycopg_pool ──
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.database.client import close_db, get_connection, init_db
from backend.pipeline import PipelineResult, VideoPipeline


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa el pool de BD al arrancar y lo cierra al detener la app."""
    await init_db()
    print("[api] Pool de BD inicializado.")
    yield
    await close_db()
    print("[api] Pool de BD cerrado.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Spike GPU API",
    description=(
        "Pipeline de análisis de video YouTube: "
        "descarga · transcripción · análisis LLM · generación de guion y prompts."
    ),
    version="7.0.0",
    lifespan=lifespan,
)


# ─── Schemas de request ───────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post(
    "/analyze",
    response_model=PipelineResult,
    summary="Ejecutar pipeline completo",
    description=(
        "Recibe la URL de un video de YouTube, ejecuta el pipeline completo "
        "(descarga → transcripción → análisis → guion → prompts) "
        "y devuelve el PipelineResult con todos los resultados y tiempos."
    ),
)
async def analyze(body: AnalyzeRequest) -> PipelineResult:
    """
    Nota: VideoPipeline.run() gestiona su propio ciclo init_db/close_db
    internamente cuando corre standalone. Para la API, sobrescribimos ese
    comportamiento usando _run_with_shared_pool() que reutiliza el pool
    ya abierto por el lifespan.
    """
    try:
        result = await _run_pipeline_with_shared_pool(body.url)
        print(VideoPipeline.timing_report(result))
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _run_pipeline_with_shared_pool(url: str) -> PipelineResult:
    """
    Ejecuta el pipeline usando el pool compartido del lifespan.
    Evita el doble init_db/close_db que haría VideoPipeline.run().
    """
    import time
    from pathlib import Path

    from backend.config import settings as s
    from backend.core.downloader import download_audio, extract_video_id
    from backend.core.transcriber import transcribe
    from backend.services.analyzer import LLMAnalyzer
    from backend.services.generator import ContentGenerator
    from backend.services.youtube_service import YouTubeService

    timings: dict[str, float] = {}
    youtube_id = extract_video_id(url)

    yt = YouTubeService()
    analyzer = LLMAnalyzer()
    generator = ContentGenerator()

    async with get_connection() as conn:
        t0 = time.perf_counter()
        audio_path, video_db_id = await download_audio(url, s.DOWNLOADS_DIR, conn)
        timings["descarga_audio"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        metadata, comments = await yt.enrich_video_in_db(video_db_id, youtube_id, conn)
        timings["metadata_youtube"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        transcript = await transcribe(audio_path, video_db_id, conn)
        timings["transcripcion"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        analysis = await analyzer.analyze_transcript(transcript, metadata)
        timings["analisis_llm"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        sentiment = await analyzer.analyze_sentiment(comments)
        timings["sentimiento_comentarios"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        script = await generator.generate_script(analysis, sentiment, metadata)
        timings["generacion_guion"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        image_prompts = await generator.generate_image_prompts(script, metadata)
        timings["prompts_imagen"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        video_prompts = await generator.generate_video_prompts(image_prompts, script)
        timings["prompts_video"] = time.perf_counter() - t0

        await analyzer.save_to_db(video_db_id, analysis, sentiment, conn)
        await generator.save_to_db(video_db_id, script, image_prompts, video_prompts, conn)

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


@app.get(
    "/health",
    summary="Health check",
    description="Devuelve el estado del servicio y la configuración activa.",
)
async def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "whisper_model": settings.WHISPER_MODEL,
        "llm_model": settings.OLLAMA_MODEL,
    }


@app.get(
    "/timings/{video_id}",
    summary="Historial de tiempos de un video",
    description=(
        "Devuelve todos los registros de tiempos de ejecución almacenados en BD "
        "para el video_id dado (PK de la tabla videos), ordenados del más reciente "
        "al más antiguo."
    ),
)
async def get_timings(video_id: int) -> list[dict]:
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT fase, duracion_segundos, environment, tokens_por_segundo, created_at
                    FROM tiempos_ejecucion
                    WHERE video_id = %s
                    ORDER BY created_at DESC
                    """,
                    (video_id,),
                )
                rows = await cur.fetchall()

        return [
            {
                "fase": row[0],
                "duracion_segundos": row[1],
                "environment": row[2],
                "tokens_por_segundo": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

