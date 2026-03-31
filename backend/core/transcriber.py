from pathlib import Path
from typing import Optional

import psycopg

from backend.config import settings
from backend.core.timer import PhaseTimer


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


async def transcribe(
    audio_path: Path,
    video_db_id: int,
    db_conn: Optional[psycopg.AsyncConnection],
) -> str:
    """
    Transcribe el audio a texto usando faster-whisper.

    - Verifica cache en BD antes de transcribir.
    - Si WHISPER_DEVICE=cuda y no hay GPU disponible, hace fallback a cpu+int8.
    - Aplica VAD filter para eliminar silencios (hasta 30% más rápido).

    Retorna el texto completo de la transcripción.
    """
    # Cache: si ya existe transcripción en BD, devolverla directamente
    if db_conn:
        cached = await _get_cached_transcript(db_conn, video_db_id)
        if cached:
            print(f"[transcriber] Transcripción encontrada en cache (video_db_id={video_db_id})")
            return cached

    timer = PhaseTimer()
    timer.start("transcripcion")

    model = _load_model()

    # Transcribir con VAD filter
    segments, info = model.transcribe(
        str(audio_path),
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    # Unir todos los segmentos
    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    language = info.language if hasattr(info, "language") else "unknown"

    duracion = timer.stop()

    # Métricas
    word_count = len(text.split())
    tokens_por_segundo = word_count / duracion if duracion > 0 else 0.0

    print(
        f"[transcriber] {word_count} palabras | idioma={language} | "
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


def _load_model():
    """
    Carga el modelo WhisperModel con fallback automático de CUDA a CPU.
    Se importa faster_whisper aquí para que el módulo sea importable
    incluso si faster_whisper no está instalado aún en desarrollo.
    """
    from faster_whisper import WhisperModel

    device = settings.WHISPER_DEVICE
    compute_type = "float16" if device == "cuda" else "int8"

    try:
        model = WhisperModel(
            settings.WHISPER_MODEL,
            device=device,
            compute_type=compute_type,
        )
        print(f"[transcriber] Modelo {settings.WHISPER_MODEL} cargado en {device} ({compute_type})")
        return model
    except Exception as exc:
        if device == "cuda":
            print(
                f"[transcriber] GPU no disponible ({exc}). "
                "Fallback a CPU con int8."
            )
            model = WhisperModel(
                settings.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
            print(f"[transcriber] Modelo {settings.WHISPER_MODEL} cargado en cpu (int8)")
            return model
        raise
