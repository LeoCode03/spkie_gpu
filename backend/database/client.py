from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from psycopg_pool import AsyncConnectionPool

from backend.config import settings

_pool: AsyncConnectionPool | None = None


async def init_db() -> None:
    """Inicializa el pool de conexiones y verifica que la BD es accesible."""
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=2,
        max_size=5,
        open=False,
    )
    await _pool.open()
    # Verificar conexión
    async with _pool.connection() as conn:
        await conn.execute("SELECT 1")


async def close_db() -> None:
    """Cierra el pool de conexiones."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Context manager que entrega una conexión del pool."""
    if _pool is None:
        raise RuntimeError("Pool no inicializado. Llamar a init_db() primero.")
    async with _pool.connection() as conn:
        yield conn
