-- Spike GPU — Schema PostgreSQL 17 + pgvector
-- Ejecutado automáticamente al crear el contenedor por primera vez

CREATE EXTENSION IF NOT EXISTS vector;

-- ─── videos ─────────────────────────────────────────────────────────────────
-- Registro principal de cada video procesado
CREATE TABLE IF NOT EXISTS videos (
    id                SERIAL PRIMARY KEY,
    video_id          TEXT NOT NULL UNIQUE,          -- ID de YouTube (ej: dQw4w9WgXcQ)
    url               TEXT NOT NULL,
    title             TEXT,
    description       TEXT,
    tags              TEXT[],
    duration_seconds  INTEGER,
    view_count        BIGINT,
    like_count        BIGINT,
    comment_count     BIGINT,
    published_at      TEXT,
    channel_title     TEXT,
    channel_id        TEXT,
    thumbnail_url     TEXT,
    environment       TEXT NOT NULL DEFAULT 'local', -- 'local' | 'cloud'
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── transcripciones ────────────────────────────────────────────────────────
-- Resultado de faster-whisper por video
CREATE TABLE IF NOT EXISTS transcripciones (
    id          SERIAL PRIMARY KEY,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    word_count  INTEGER,
    language    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── analisis ───────────────────────────────────────────────────────────────
-- Resultado del análisis LLM: transcripción + sentimiento de comentarios
CREATE TABLE IF NOT EXISTS analisis (
    id                        SERIAL PRIMARY KEY,
    video_id                  INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    key_points                JSONB,   -- list[str]
    main_topics               JSONB,   -- list[str]
    tone                      TEXT,
    narrative_structure       TEXT,
    content_gaps              JSONB,   -- list[str]
    improvement_opportunities JSONB,   -- list[str]
    overall_sentiment         TEXT,    -- 'positive' | 'negative' | 'neutral'
    sentiment_score           FLOAT,   -- 0.0 - 1.0
    audience_questions        JSONB,   -- list[str]
    audience_pain_points      JSONB,   -- list[str]
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── guiones ────────────────────────────────────────────────────────────────
-- Guion mejorado + prompts de imagen y video generados por el LLM
CREATE TABLE IF NOT EXISTS guiones (
    id             SERIAL PRIMARY KEY,
    video_id       INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    sections       JSONB,  -- list[ScriptSection]: title, narration_text, duration_seconds, key_message
    image_prompts  JSONB,  -- list[ImagePrompt]: scene_number, description, style_reference, duration_seconds
    video_prompts  JSONB,  -- list[VideoPrompt]: scene_number, motion_type, motion_description, camera_speed
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── tiempos_ejecucion ──────────────────────────────────────────────────────
-- Benchmarking por fase — permite comparar local vs cloud
CREATE TABLE IF NOT EXISTS tiempos_ejecucion (
    id                  SERIAL PRIMARY KEY,
    video_id            INTEGER REFERENCES videos(id) ON DELETE SET NULL,
    fase                TEXT NOT NULL,   -- ej: 'descarga', 'transcripcion', 'analisis_llm'
    duracion_segundos   FLOAT NOT NULL,
    tokens_por_segundo  FLOAT,           -- solo para fases LLM
    environment         TEXT NOT NULL DEFAULT 'local',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Índices ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_videos_video_id ON videos(video_id);
CREATE INDEX IF NOT EXISTS idx_transcripciones_video_id ON transcripciones(video_id);
CREATE INDEX IF NOT EXISTS idx_analisis_video_id ON analisis(video_id);
CREATE INDEX IF NOT EXISTS idx_guiones_video_id ON guiones(video_id);
CREATE INDEX IF NOT EXISTS idx_tiempos_video_id ON tiempos_ejecucion(video_id);
CREATE INDEX IF NOT EXISTS idx_tiempos_environment ON tiempos_ejecucion(environment);
