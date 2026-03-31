import time
from typing import Optional

import psycopg

from backend.config import settings


class PhaseTimer:
    """
    Mide la duración de una fase del pipeline y la persiste en tiempos_ejecucion.

    Uso:
        timer = PhaseTimer()
        timer.start("transcripcion")
        # ... trabajo ...
        duracion = timer.stop()
        await timer.save_to_db(video_db_id, conn)
    """

    def __init__(self) -> None:
        self._fase: str = ""
        self._start: float = 0.0
        self._duracion: float = 0.0

    def start(self, fase: str) -> None:
        self._fase = fase
        self._start = time.perf_counter()
        self._duracion = 0.0

    def stop(self) -> float:
        """Detiene el timer y devuelve la duración en segundos."""
        self._duracion = time.perf_counter() - self._start
        return self._duracion

    @property
    def duracion(self) -> float:
        return self._duracion

    async def save_to_db(
        self,
        video_id: Optional[int],
        conn: psycopg.AsyncConnection,
        tokens_por_segundo: Optional[float] = None,
    ) -> None:
        """Guarda el tiempo registrado en la tabla tiempos_ejecucion."""
        await conn.execute(
            """
            INSERT INTO tiempos_ejecucion
                (video_id, fase, duracion_segundos, tokens_por_segundo, environment)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (video_id, self._fase, self._duracion, tokens_por_segundo, settings.ENVIRONMENT),
        )
