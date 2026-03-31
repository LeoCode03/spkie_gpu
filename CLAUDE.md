# Spike GPU — Instrucciones para Claude Code

Spike de viabilidad para procesar videos de YouTube con GPUs cloud (RunPod).
Pipeline: URL → descarga audio → transcripción Whisper → análisis LLM → guion + prompts imagen/video.

## Comandos esenciales

```bash
# Setup inicial (una sola vez)
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt

# Levantar PostgreSQL
docker compose up -d
docker compose down

# Correr la aplicación
streamlit run app.py                                              # UI: http://localhost:8501
uvicorn backend.api.server:app --host 127.0.0.1 --port 8000     # API: http://localhost:8000

# Tests
pytest tests/ -v
pytest tests/test_analyzer.py -v   # test individual

# Verificar BD
docker compose exec postgres psql -U spike_user spike_gpu -c "\dt"
docker compose exec postgres psql -U spike_user spike_gpu \
  -c "SELECT fase, duracion_segundos, environment FROM tiempos_ejecucion ORDER BY created_at DESC LIMIT 20;"

# Modo desarrollo rápido (omite descarga y transcripción, usa cache de BD)
# Setear en backend/.env: SKIP_DOWNLOAD=true
```

## Arquitectura

```
spike_gpu/
├── app.py                      ← Streamlit UI (entry point principal)
├── docker-compose.yml          ← PostgreSQL 17 + pgvector
├── Dockerfile                  ← Para deploy en RunPod (CUDA)
├── Dockerfile.local            ← Para probar Docker sin GPU
├── backend/
│   ├── api/server.py           ← FastAPI: POST /analyze, GET /health
│   ├── pipeline.py             ← Orquestador: llama a todos los servicios en orden
│   ├── core/
│   │   ├── downloader.py       ← yt-dlp: descarga audio m4a
│   │   ├── transcriber.py      ← faster-whisper: audio → texto
│   │   └── timer.py            ← PhaseTimer: mide duración de cada fase
│   ├── services/
│   │   ├── youtube_service.py  ← YouTube API v3: metadata + comentarios
│   │   ├── analyzer.py         ← LLMAnalyzer: análisis de transcripción (chunking 2 pasadas) + sentimiento
│   │   ├── generator.py        ← ContentGenerator: guion + prompts imagen + prompts video
│   │   └── schemas.py          ← Pydantic: AnalysisResult, SentimentResult, ScriptResult, ImagePrompt, VideoPrompt
│   ├── database/
│   │   ├── client.py           ← psycopg3 async pool
│   │   └── sql/01_schema.sql   ← 5 tablas: videos, transcripciones, analisis, guiones, tiempos_ejecucion
│   └── config/settings.py      ← Variables de entorno via python-dotenv
└── tests/
```

## Variables de entorno críticas (backend/.env)

```
DATABASE_URL=postgresql://spike_user:spike_pass@localhost:5433/spike_gpu
YOUTUBE_API_KEY=AIza...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b          # local | qwen2.5:72b en RunPod
WHISPER_MODEL=medium              # local | large-v3 en RunPod
WHISPER_DEVICE=cuda               # cuda | cpu
SKIP_DOWNLOAD=false               # true = usar transcripción cacheada en BD
ENVIRONMENT=local                 # local | cloud (etiqueta los tiempos en BD)
```

## Flujo del pipeline

`VideoPipeline.run(url)` ejecuta en secuencia:
1. `youtube_service.enrich_video_in_db()` — metadata + comentarios
2. `downloader.download_audio()` — audio m4a (omitir si SKIP_DOWNLOAD)
3. `transcriber.transcribe()` — texto (cache si ya existe en BD)
4. `analyzer.analyze_transcript()` — chunking: pasada 1 por chunk → pasada 2 síntesis global
5. `analyzer.analyze_sentiment()` — sentimiento de comentarios
6. `generator.generate_script()` — guion estructurado
7. `generator.generate_image_prompts()` — un prompt por sección (máx 10)
8. `generator.generate_video_prompts()` — movimiento acorde a cada imagen

Cada fase registra su duración en `tiempos_ejecucion` con columna `environment` (local/cloud) para el versus de benchmarking.

## Decisiones de diseño

- **Chunking LLM**: transcripciones largas (~15k tokens/hora de video) se dividen en chunks de 3000 palabras; análisis en 2 pasadas para coherencia
- **Cache de transcripciones**: si el video ya fue procesado, se reutiliza desde BD sin re-descargar ni re-transcribir
- **VAD filter**: `vad_filter=True` en faster-whisper elimina silencios (hasta 30% más rápido)
- **Temperatura por tarea**: análisis=0.1 (determinista), guion=0.7 (creativo), prompts=0.5
- **Sin venv en Docker**: el contenedor es el aislamiento; pip instala directo al Python del contenedor
- **Mismo código local/cloud**: solo `.env` cambia entre entornos

## Praxis Configuration

Praxis Platform:     python-fastapi
Praxis Domain:       software
Praxis Gates:        spec=on, plan=on, review=on, lessons=on
Praxis TestCommand:  pytest tests/ -v
Praxis TestRunner:   pytest
Praxis Language:     python
Praxis SourceRoot:   backend/
Praxis FileExt:      *.py
Praxis IsolationKey: none
