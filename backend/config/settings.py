from pathlib import Path
from dotenv import load_dotenv
import os

# Cargar .env desde backend/.env (relativo al directorio de trabajo del proceso)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


def _bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


# Base de datos
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://spike_user:spike_pass@localhost:5432/spike_gpu",
)

# YouTube API
YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

# Ollama (LLM local)
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Whisper
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")

# Control de desarrollo
SKIP_DOWNLOAD: bool = _bool(os.getenv("SKIP_DOWNLOAD", "false"))

# Entorno — etiqueta los tiempos en BD para el versus local vs cloud
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

# Directorio de descargas de audio
DOWNLOADS_DIR: Path = Path(__file__).parent.parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)
