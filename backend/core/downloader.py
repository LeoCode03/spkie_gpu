import re
from pathlib import Path
from typing import Optional

import yt_dlp
import psycopg

from backend.config import settings
from backend.core.timer import PhaseTimer


# ─── Excepciones ─────────────────────────────────────────────────────────────

class VideoUnavailableError(Exception):
    """Video privado, eliminado o con restricción de edad."""

class InvalidURLError(Exception):
    """URL inválida o no corresponde a un video de YouTube."""

class DownloadNetworkError(Exception):
    """Error de red durante la descarga (reintentable)."""


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


async def _upsert_video(
    conn: psycopg.AsyncConnection,
    video_id: str,
    url: str,
) -> int:
    """Inserta o devuelve el id de BD del video."""
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


async def _update_duration(
    conn: psycopg.AsyncConnection,
    video_db_id: int,
    duration_seconds: Optional[int],
) -> None:
    await conn.execute(
        "UPDATE videos SET duration_seconds = %s WHERE id = %s",
        (duration_seconds, video_db_id),
    )


# ─── Download ────────────────────────────────────────────────────────────────

async def download_audio(
    url: str,
    output_dir: Path,
    db_conn: Optional[psycopg.AsyncConnection],
) -> tuple[Path, int]:
    """
    Descarga solo el audio de un video de YouTube.

    Retorna:
        (ruta_archivo_audio, video_db_id)

    Si settings.SKIP_DOWNLOAD es True, busca el archivo en output_dir y lo
    retorna directamente sin descargar. Útil para desarrollo cuando el audio
    ya fue descargado en una ejecución anterior.
    """
    video_id = extract_video_id(url)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Registrar en BD al inicio (si hay conexión disponible)
    video_db_id: int = -1
    if db_conn:
        video_db_id = await _upsert_video(db_conn, video_id, url)

    # Modo dry-run: devolver archivo existente sin descargar
    if settings.SKIP_DOWNLOAD:
        cached = output_dir / f"{video_id}.m4a"
        if cached.exists():
            return cached, video_db_id
        # Intentar también .mp3 como fallback
        cached_mp3 = output_dir / f"{video_id}.mp3"
        if cached_mp3.exists():
            return cached_mp3, video_db_id
        raise FileNotFoundError(
            f"SKIP_DOWNLOAD=true pero no se encontró {cached} ni {cached_mp3}.\n"
            "Descarga el audio primero con SKIP_DOWNLOAD=false."
        )

    timer = PhaseTimer()
    timer.start("descarga")

    output_template = str(output_dir / f"{video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "ratelimit": 500 * 1024,  # 500 KB/s
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "retries": 3,
        "http_chunk_size": 1024 * 1024,
    }

    duration_seconds: Optional[int] = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                duration_seconds = info.get("duration")

    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc).lower()
        if any(k in msg for k in ("private", "unavailable", "removed", "deleted", "sign in")):
            raise VideoUnavailableError(
                f"El video {video_id} no está disponible (privado, eliminado o requiere login)."
            ) from exc
        if any(k in msg for k in ("network", "connection", "timeout", "http error")):
            raise DownloadNetworkError(
                f"Error de red al descargar {video_id}: {exc}"
            ) from exc
        raise DownloadNetworkError(f"Error de yt-dlp: {exc}") from exc

    duracion = timer.stop()

    # Buscar el archivo descargado (la extensión puede variar)
    audio_path: Optional[Path] = None
    for ext in ("m4a", "mp3", "opus", "webm"):
        candidate = output_dir / f"{video_id}.{ext}"
        if candidate.exists():
            audio_path = candidate
            break

    if audio_path is None:
        raise DownloadNetworkError(
            f"yt-dlp reportó éxito pero no se encontró el archivo de audio para {video_id}."
        )

    # Actualizar duración y guardar tiempo en BD
    if db_conn:
        if duration_seconds:
            await _update_duration(db_conn, video_db_id, duration_seconds)
        await timer.save_to_db(video_db_id, db_conn)

    print(f"[downloader] {video_id} descargado en {duracion:.1f}s → {audio_path.name}")
    return audio_path, video_db_id
