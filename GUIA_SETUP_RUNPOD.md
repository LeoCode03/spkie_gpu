# Guía Setup RunPod — spike_gpu
RTX 5090 (32GB VRAM) · qwen3.5:9b → qwen3.5:27b

---

## Configuración del Pod ANTES de deployar

| Setting | Valor |
|---|---|
| GPU | RTX 5090 |
| Template | RunPod PyTorch 2.x |
| Container Disk | 30 GB |
| Volume Disk | 50 GB |
| Expose HTTP ports | `8888,8501` |
| Expose TCP ports | `22` |

> ⚠️ Agregar el puerto 8501 ANTES de hacer Deploy — no se puede agregar después sin resetear el Pod.

---

## Paso 1 — Abrir terminal

Jupyter Lab → **File → New → Terminal**

---

## Paso 2 — Instalar dependencias del sistema

```bash
apt-get update && apt-get install -y ffmpeg git postgresql postgresql-contrib postgresql-16-pgvector
```

---

## Paso 3 — Instalar Ollama con modelos en /workspace (persistente)

```bash
mkdir -p /workspace/ollama
curl -fsSL https://ollama.com/install.sh | sh
echo 'export OLLAMA_MODELS=/workspace/ollama' >> /root/.bashrc
export OLLAMA_MODELS=/workspace/ollama
ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
ollama pull qwen3.5:9b
```

> Los modelos se guardan en `/workspace/ollama` — persisten entre reinicios del Pod.
> El pull de `qwen3.5:9b` tarda ~3-5 min.

---

## Paso 4 — Configurar PostgreSQL

```bash
pg_ctlcluster 16 main start

sudo -u postgres psql << 'EOF'
CREATE USER spike_user WITH PASSWORD 'spike_pass';
CREATE DATABASE spike_gpu OWNER spike_user;
\c spike_gpu
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

---

## Paso 5 — Clonar proyecto e instalar dependencias

> ⚠️ El repo se llama `spkie_gpu` (typo) — así se clona.

```bash
cd /workspace
git clone https://github.com/LeoCode03/spkie_gpu.git spkie_gpu
cd spkie_gpu
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

---

## Paso 6 — Crear tablas en BD y dar permisos

```bash
sudo -u postgres psql spike_gpu < /workspace/spkie_gpu/backend/database/sql/01_schema.sql

sudo -u postgres psql spike_gpu -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO spike_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO spike_user;"
```

---

## Paso 7 — Crear .env para cloud

```bash
cat > /workspace/spkie_gpu/backend/.env << 'EOF'
DATABASE_URL=postgresql://spike_user:spike_pass@localhost:5432/spike_gpu
YOUTUBE_API_KEY=AIzaSyDskp5HMQFI7D-LfpuYpx0ijB-Mw-nBRb4
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:9b
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
SKIP_DOWNLOAD=true
ENVIRONMENT=cloud
EOF
```

---

## Paso 8 — Lanzar Streamlit

```bash
cd /workspace/spkie_gpu
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
```

Abrir: RunPod panel → Connect → HTTP Services → puerto **8501**

En el sidebar aparece el audio `6z2pYdGxfTk` — selecciónalo → **Analizar Video**

---

## Paso 9 — Prueba 1: qwen3.5:9b

- Espera a que el pipeline complete (~5-10 min)
- Anota los tiempos en la pestaña **⏱️ Tiempos**
- Exporta el ZIP con los resultados

---

## Paso 10 — Cambiar entre modelos

> **Referencia rápida de modelos:**
> - `qwen3.5:9b` — rápido (~30-60s/chunk), bueno para videos cortos (5-15 min)
> - `qwen3.5:27b` — más lento (~3-5 min/chunk), mejor comprensión para videos largos (1hr+)
> - Ambos caben en la RTX 5090 (32GB VRAM) sin spillover a CPU

En otra terminal (File → New → Terminal):

```bash
# Descargar el modelo 27b (tarda ~10-15 min, ~17GB)
export OLLAMA_MODELS=/workspace/ollama
ollama pull qwen3.5:27b

# Verificar cuál modelo está activo
grep OLLAMA_MODEL /workspace/spkie_gpu/backend/.env

# Cambiar a 27b
sed -i 's/OLLAMA_MODEL=qwen3.5:9b/OLLAMA_MODEL=qwen3.5:27b/' /workspace/spkie_gpu/backend/.env

# Cambiar de vuelta a 9b (cuando quieras)
sed -i 's/OLLAMA_MODEL=qwen3.5:27b/OLLAMA_MODEL=qwen3.5:9b/' /workspace/spkie_gpu/backend/.env
```

> **Nota VRAM al cambiar:** Con RTX 5090 ambos modelos caben simultáneamente (~26GB de 32GB). Si hay error de memoria, fuerza la descarga del anterior: `ollama stop qwen3.5:9b`

Reiniciar Streamlit después de cada cambio:

```bash
kill $(pgrep -f streamlit)
cd /workspace/spkie_gpu
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
```

Analiza el mismo video con cada modelo y compara los tiempos en la pestaña **⏱️ Tiempos**.

---

## Paso 11 — Cerrar el Pod de forma segura

1. Exporta el ZIP desde Streamlit → botón **📦 Exportar ZIP**
2. RunPod panel → **Stop Pod** ← usar STOP, no Terminate

> **Stop Pod** conserva `/workspace` (modelos, proyecto, audio).
> **Terminate Pod** borra todo permanentemente.
>
> Lo que se pierde con Stop: apt packages, PostgreSQL, instalación de Ollama.
> Lo que se conserva: modelos en `/workspace/ollama`, proyecto en `/workspace/spkie_gpu`, audio en `/workspace/spkie_gpu/downloads/`.

---

## Al reiniciar el Pod (próximas veces)

Jupyter Lab → File → New → Terminal — pegar todo de una vez:

```bash
# Reinstalar lo que se pierde con el reinicio
apt-get update && apt-get install -y ffmpeg postgresql postgresql-contrib postgresql-16-pgvector
curl -fsSL https://ollama.com/install.sh | sh

# Levantar servicios (modelos ya están en /workspace/ollama)
export OLLAMA_MODELS=/workspace/ollama
ollama serve > /tmp/ollama.log 2>&1 &
pg_ctlcluster 16 main start

# Recrear BD
sudo -u postgres psql << 'EOF'
CREATE USER spike_user WITH PASSWORD 'spike_pass';
CREATE DATABASE spike_gpu OWNER spike_user;
\c spike_gpu
CREATE EXTENSION IF NOT EXISTS vector;
EOF
sudo -u postgres psql spike_gpu < /workspace/spkie_gpu/backend/database/sql/01_schema.sql
sudo -u postgres psql spike_gpu -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO spike_user; GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO spike_user;"

# Lanzar Streamlit
cd /workspace/spkie_gpu
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
```

> Los modelos ya descargados no se vuelven a descargar — están en `/workspace/ollama`.

---

## Notas importantes

- **Repo:** `spkie_gpu` (typo en el nombre — así está en GitHub)
- **SKIP_DOWNLOAD=true** — el audio `6z2pYdGxfTk.webm` ya está en el repo
- **Puerto 5432** — PostgreSQL nativo, sin Docker (RunPod no soporta Docker)
- **Puerto 5433** es solo para local con Docker — en el Pod usar 5432
- **Modelos Ollama persisten** en `/workspace/ollama` entre reinicios
- **PostgreSQL NO persiste** — recrear la BD en cada reinicio
- **Streamlit** requiere `--server.enableCORS false --server.enableXsrfProtection false` para el proxy de RunPod
