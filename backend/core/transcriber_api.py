"""
backend/core/transcriber_api.py — rama api_transcript
Obtiene la transcripción generada por YouTube sin descargar audio ni usar Whisper.
Usa youtube-transcript-api >= 1.0 (pip install youtube-transcript-api).

Cambios de API vs versiones anteriores:
- YouTubeTranscriptApi ahora se instancia: YouTubeTranscriptApi()
- .list_transcripts() → .list()
- .fetch() devuelve FetchedTranscript (iterable de snippets, no lista de dicts)
- Los snippets tienen atributo .text en lugar de clave "text"
"""
from __future__ import annotations

import asyncio
from typing import Optional

import psycopg
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

from backend.core.timer import PhaseTimer


# ─── Cache BD ────────────────────────────────────────────────────────────────

async def _get_cached_transcript(
    conn: psycopg.AsyncConnection,
    video_db_id: int,
) -> Optional[str]:
    """Devuelve la transcripción existente en BD, o None si no existe."""
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT content FROM transcripciones WHERE video_id = %s LIMIT 1",
            (video_db_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else None


# ─── Fetch principal ──────────────────────────────────────────────────────────

async def fetch_transcript(
    youtube_id: str,
    video_db_id: int,
    db_conn: Optional[psycopg.AsyncConnection],
) -> str:
    """
    Obtiene la transcripción de un video de YouTube via youtube-transcript-api.

    Prioridad de idioma: manual ES → manual EN → auto ES → auto EN → cualquiera.
    No descarga audio ni usa GPU — solo consume la transcripción que YouTube
    genera (o que el creador subió manualmente).

    Retorna el texto completo de la transcripción.
    Lanza NoTranscriptFound o TranscriptsDisabled si el video no tiene subtítulos.
    """
    # Cache: si ya existe en BD, devolver directamente
    if db_conn:
        cached = await _get_cached_transcript(db_conn, video_db_id)
        if cached:
            print(f"[transcriber_api] Cache hit (video_db_id={video_db_id})")
            return cached

    timer = PhaseTimer()
    timer.start("transcripcion_api")

    # La API es síncrona — ejecutar en thread pool para no bloquear el event loop
    fetched, language = await asyncio.to_thread(_fetch_sync, youtube_id)

    # FetchedTranscript es iterable de snippets con atributo .text
    text = " ".join(
        snippet.text.strip()
        for snippet in fetched
        if snippet.text.strip()
    )

    duracion = timer.stop()

    word_count = len(text.split())
    tokens_por_segundo = word_count / duracion if duracion > 0 else 0.0

    print(
        f"[transcriber_api] {word_count} palabras | idioma={language} | "
        f"{duracion:.1f}s | {tokens_por_segundo:.1f} palabras/s"
    )

    # Guardar en BD
    if db_conn:
        await db_conn.execute(
            """
            INSERT INTO transcripciones (video_id, content, word_count, language)
            VALUES (%s, %s, %s, %s)
            """,
            (video_db_id, text, word_count, language),
        )
        await timer.save_to_db(video_db_id, db_conn, tokens_por_segundo=tokens_por_segundo)

    return text


# ─── Lógica síncrona ──────────────────────────────────────────────────────────

def _fetch_sync(youtube_id: str):
    """
    Obtiene los datos de transcripción de forma síncrona (v1.x API).
    Prioridad: manual ES → manual EN → auto ES → auto EN → cualquier idioma.
    Devuelve (FetchedTranscript, language_code).
    """
    api = YouTubeTranscriptApi()
    transcript_list = api.list(youtube_id)

    # 1. Transcripción manual (más precisa)
    for lang in ("es", "en"):
        try:
            t = transcript_list.find_manually_created_transcript([lang])
            return t.fetch(), t.language_code
        except Exception:
            pass

    # 2. Transcripción generada automáticamente por YouTube
    for lang in ("es", "en"):
        try:
            t = transcript_list.find_generated_transcript([lang])
            return t.fetch(), t.language_code
        except Exception:
            pass

    # 3. Último recurso: cualquier idioma disponible
    for t in transcript_list:
        try:
            return t.fetch(), t.language_code
        except Exception:
            pass

    raise NoTranscriptFound(
        youtube_id,
        ["es", "en"],
        transcript_list,
    )
