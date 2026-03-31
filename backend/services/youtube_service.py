import asyncio
import re
from typing import Optional

import psycopg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.core.timer import PhaseTimer


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_iso8601_duration(duration: str) -> int:
    """
    Convierte duración ISO 8601 a segundos totales.
    Ejemplos: PT1H2M3S → 3723 | PT30M → 1800 | PT45S → 45
    """
    match = re.match(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration or "",
    )
    if not match:
        return 0
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _pick_thumbnail(thumbnails: dict) -> str:
    """Devuelve la URL del thumbnail de mayor resolución disponible."""
    for quality in ("maxresdefault", "standard", "high", "medium", "default"):
        if quality in thumbnails:
            return thumbnails[quality]["url"]
    return ""


# ─── Servicio ────────────────────────────────────────────────────────────────

class YouTubeService:
    """
    Wrapper sobre YouTube Data API v3.

    La librería googleapiclient es síncrona, por lo que todas las llamadas
    HTTP se ejecutan en un thread separado via asyncio.to_thread para no
    bloquear el event loop.
    """

    def __init__(self) -> None:
        if not settings.YOUTUBE_API_KEY:
            raise ValueError(
                "YOUTUBE_API_KEY no está configurada en backend/.env"
            )
        # El cliente se construye de forma lazy (primera llamada) para no
        # bloquear la importación del módulo
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = build(
                "youtube", "v3",
                developerKey=settings.YOUTUBE_API_KEY,
                cache_discovery=False,
            )
        return self._client

    # ─── Metadata ────────────────────────────────────────────────────────────

    async def get_video_metadata(self, video_id: str) -> dict:
        """
        Obtiene metadata completa del video via YouTube API v3.

        Retorna dict con: title, description, tags, duration_seconds,
        view_count, like_count, comment_count, published_at,
        channel_title, channel_id, thumbnail_url.
        """
        def _fetch():
            return (
                self._get_client()
                .videos()
                .list(
                    part="snippet,contentDetails,statistics",
                    id=video_id,
                )
                .execute()
            )

        response = await asyncio.to_thread(_fetch)

        items = response.get("items", [])
        if not items:
            raise ValueError(f"Video '{video_id}' no encontrado en YouTube API.")

        item = items[0]
        snippet = item.get("snippet", {})
        details = item.get("contentDetails", {})
        stats = item.get("statistics", {})

        return {
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "duration_seconds": _parse_iso8601_duration(details.get("duration", "")),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "published_at": snippet.get("publishedAt", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "thumbnail_url": _pick_thumbnail(snippet.get("thumbnails", {})),
        }

    # ─── Comentarios ─────────────────────────────────────────────────────────

    async def get_comments(
        self,
        video_id: str,
        max_results: int = 100,
    ) -> list[dict]:
        """
        Obtiene los comentarios más relevantes del video.

        Devuelve lista de dicts con: author, text, like_count, published_at.
        Si los comentarios están desactivados, devuelve lista vacía silenciosamente.
        """
        def _fetch():
            return (
                self._get_client()
                .commentThreads()
                .list(
                    part="snippet",
                    videoId=video_id,
                    order="relevance",
                    maxResults=min(max_results, 100),
                    textFormat="plainText",
                )
                .execute()
            )

        try:
            response = await asyncio.to_thread(_fetch)
        except HttpError as exc:
            # 403 commentsDisabled o 400 son comunes — no es un error crítico
            if exc.resp.status in (400, 403):
                return []
            raise

        comments = []
        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "author": top.get("authorDisplayName", ""),
                "text": top.get("textDisplay", ""),
                "like_count": int(top.get("likeCount", 0)),
                "published_at": top.get("publishedAt", ""),
            })

        return comments

    # ─── Enrich en BD ────────────────────────────────────────────────────────

    async def enrich_video_in_db(
        self,
        video_db_id: int,
        video_id: str,
        db_conn: psycopg.AsyncConnection,
    ) -> tuple[dict, list[dict]]:
        """
        Obtiene metadata + comentarios del video y actualiza la fila en BD.

        Retorna (metadata, comments) para que el pipeline los use directamente
        sin necesidad de releerlos desde la BD.
        """
        timer = PhaseTimer()
        timer.start("metadata_youtube")

        metadata, comments = await asyncio.gather(
            self.get_video_metadata(video_id),
            self.get_comments(video_id),
        )

        await db_conn.execute(
            """
            UPDATE videos SET
                title          = %s,
                description    = %s,
                tags           = %s,
                duration_seconds = %s,
                view_count     = %s,
                like_count     = %s,
                comment_count  = %s,
                published_at   = %s,
                channel_title  = %s,
                channel_id     = %s,
                thumbnail_url  = %s
            WHERE id = %s
            """,
            (
                metadata["title"],
                metadata["description"],
                metadata["tags"],          # psycopg3 convierte list → text[]
                metadata["duration_seconds"],
                metadata["view_count"],
                metadata["like_count"],
                metadata["comment_count"],
                metadata["published_at"],
                metadata["channel_title"],
                metadata["channel_id"],
                metadata["thumbnail_url"],
                video_db_id,
            ),
        )

        timer.stop()
        await timer.save_to_db(video_db_id, db_conn)

        print(
            f"[youtube] '{metadata['title']}' | "
            f"{metadata['view_count']:,} views | "
            f"{len(comments)} comentarios"
        )

        return metadata, comments
