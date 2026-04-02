"""
backend/core/downloader.py — rama api_transcript
Conserva extract_video_id() para parsear URLs y register_video() para insertar
el video en BD. La descarga de audio y Whisper fueron eliminados en esta rama.
"""
import re
import psycopg

from backend.config import settings


# ─── Excepciones ─────────────────────────────────────────────────────────────

class InvalidURLError(Exception):
    """URL inválida o no corresponde a un video de YouTube."""


# ─── Helpers ─────────────────────────────────────────────────────────────────

_YT_ID_RE = re.compile(
    r"""
    (?:
        youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|v/)  # youtube.com
        | youtu\.be/                                           # youtu.be
    )
    ([A-Za-z0-9_\-]{11})                                       # video_id de 11 chars
    """,
    re.VERBOSE,
)


def extract_video_id(url: str) -> str:
    """Extrae el video_id de cualquier formato de URL de YouTube."""
    match = _YT_ID_RE.search(url)
    if not match:
        raise InvalidURLError(
            f"No se pudo extraer el video_id de la URL: {url}\n"
            "Formatos soportados: watch?v=, youtu.be/, shorts/, embed/"
        )
    return match.group(1)


async def register_video(
    conn: psycopg.AsyncConnection,
    video_id: str,
    url: str,
) -> int:
    """
    Registra el video en BD (upsert) y devuelve el video_db_id.
    Reemplaza download_audio() en la rama api_transcript — sin descarga de audio.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id FROM videos WHERE video_id = %s",
            (video_id,),
        )
        row = await cur.fetchone()
        if row:
            return row[0]

        await cur.execute(
            """
            INSERT INTO videos (video_id, url, environment)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (video_id, url, settings.ENVIRONMENT),
        )
        row = await cur.fetchone()
        return row[0]
