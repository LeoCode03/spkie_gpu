"""
run_api.py — Lanzador de la API con fix de event loop para Windows.

Psycopg3 (psycopg_pool) AsyncConnectionPool NO es compatible con el
ProactorEventLoop que usa Python 3.10+ en Windows por defecto.
Este script fuerza WindowsSelectorEventLoopPolicy antes de que uvicorn
cree su event loop.

Uso:
    .\venv\Scripts\python.exe run_api.py
"""
import sys
import asyncio

# CRÍTICO: debe ejecutarse ANTES de importar uvicorn o fastapi
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        loop="asyncio",
    )
