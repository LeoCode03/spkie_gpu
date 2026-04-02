# Sesión RunPod — 2026-03-31

## Estado al cerrar la sesión

### Pod
- **ID:** `8j7aeb7ns1c9c4`
- **GPU:** RTX 4090 — 24GB VRAM
- **Estado:** Procesando análisis LLM (chunk 2-3 de 3)

### Progreso del pipeline
| Fase | Estado | Tiempo |
|---|---|---|
| Descarga audio | ✅ Completada (SKIP — archivo local) | — |
| Metadata YouTube | ✅ Completada | — |
| Transcripción Whisper large-v3 | ✅ Completada en CUDA | 195.6s |
| Análisis LLM chunk 1/3 | ✅ Completada | 8m 7s |
| Análisis LLM chunk 2/3 | ⏳ En proceso | ~8 min |
| Análisis LLM chunk 3/3 | ⏳ Pendiente | ~8 min |
| Sentimiento comentarios | ⏳ Pendiente | — |
| Generación guion | ⏳ Pendiente | — |
| Prompts imagen/video | ⏳ Pendiente | — |

### Video analizado
- **Título:** "Por qué AI no está funcionando en tu empresa"
- **Video ID:** `6z2pYdGxfTk`
- **Palabras transcritas:** 4,388
- **Idioma:** Español

### Uso de GPU al cerrar
```
GPU: RTX 4090
VRAM usada: 22,935 MiB / 24,564 MiB
GPU Util: 22%
Potencia: 85W / 450W
Temperatura: 41°C
```

### Distribución del modelo qwen3.5:27b
- 64/65 capas en GPU (13.7 GiB)
- 1 capa en CPU (2.5 GiB) — normal, falta VRAM
- KV Cache en CUDA: 5.7 GiB
- Tiempo de carga del modelo: 48.58 segundos

---

## Cómo cerrar el Pod de forma segura

1. Espera a que el pipeline complete (o Ctrl+C si quieres cancelar)
2. En RunPod panel → tu Pod → **Stop Pod** (detiene GPU, conserva `/workspace`)
3. El modelo `qwen3.5:27b` queda guardado en `/workspace/ollama` — no se pierde

---

## Al volver a iniciar el Pod

```bash
# 1. Reinstalar lo que se borra (container disk)
apt-get update && apt-get install -y ffmpeg postgresql postgresql-contrib postgresql-16-pgvector
curl -fsSL https://ollama.com/install.sh | sh

# 2. Levantar servicios
export OLLAMA_MODELS=/workspace/ollama
ollama serve > /tmp/ollama.log 2>&1 &
pg_ctlcluster 16 main start

# 3. Recrear BD (se pierde con el container disk)
sudo -u postgres psql << 'EOF'
CREATE USER spike_user WITH PASSWORD 'spike_pass';
CREATE DATABASE spike_gpu OWNER spike_user;
\c spike_gpu
CREATE EXTENSION IF NOT EXISTS vector;
EOF
sudo -u postgres psql spike_gpu < /workspace/spike_gpu/backend/database/sql/01_schema.sql

# 4. Lanzar Streamlit
cd /workspace/spike_gpu
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
```

---

## Problemas encontrados y soluciones

| Problema | Solución |
|---|---|
| Docker no disponible en RunPod | Instalar PostgreSQL nativo con apt-get |
| Puerto 8501 no accesible | Agregar en "Expose HTTP ports" ANTES de deployar |
| Modelos Ollama se borran al reiniciar | Guardar en `/workspace/ollama` con `OLLAMA_MODELS=/workspace/ollama` |
| YouTube bloquea descargas desde IPs cloud | Exportar cookies.txt desde navegador y subirlo al Pod |
| `bestaudio[ext=m4a]` no disponible | Cambiar a `bestaudio/best` en downloader.py |
| SKIP_DOWNLOAD no persistía en Streamlit | Usar `session_state` para persistir la decisión |
| ReadTimeout en análisis LLM | Aumentar timeout a 600s, reducir chunks a 1500 palabras |
| VRAM insuficiente para Whisper + Ollama | Ollama carga primero, Whisper hace fallback a CPU automáticamente |

---

## Configuración actual del Pod

```
Container Disk: 30 GB
Volume Disk: 40 GB (persistente en /workspace)
Expose HTTP ports: 8888, 8501
GPU: RTX 4090 — $0.59/hr On-Demand
```

## Archivos clave en el Pod
- `/workspace/spike_gpu/` — proyecto completo
- `/workspace/ollama/` — modelos Ollama (qwen3.5:27b, 17GB)
- `/workspace/spike_gpu/downloads/6z2pYdGxfTk.webm` — audio descargado
- `/workspace/spike_gpu/cookies.txt` — cookies de YouTube
- `/workspace/spike_gpu/backend/.env` — config cloud (SKIP_DOWNLOAD=true)
