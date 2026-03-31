import asyncio
import io
import json
import sys
import zipfile

# Fix Windows + Python 3.10: psycopg_pool necesita SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st

from backend.config import settings
from backend.pipeline import PipelineResult, VideoPipeline
from backend.services.schemas import (
    AnalysisResult,
    ImagePrompt,
    ScriptResult,
    SentimentResult,
    VideoPrompt,
)

# ─── Configuración de página ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Spike GPU",
    layout="wide",
    page_icon="🎬",
)

# ─── Session state ────────────────────────────────────────────────────────────

for _key, _default in [
    ("result", None),
    ("timings", []),
    ("running", False),
    ("last_error", None),
    ("last_error_exc", None),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configuración")

    # Detectar audios ya descargados en downloads/
    _downloads_dir = settings.DOWNLOADS_DIR
    _audio_exts = (".m4a", ".mp3", ".webm", ".opus")
    _local_files = sorted(
        f for f in _downloads_dir.iterdir()
        if f.suffix in _audio_exts
    ) if _downloads_dir.exists() else []

    if _local_files:
        st.info(f"📂 {len(_local_files)} audio(s) en downloads/")
        _file_options = {f.stem: f"https://www.youtube.com/watch?v={f.stem}" for f in _local_files}
        _selected = st.selectbox(
            "Usar audio local",
            options=["— ingresar URL —"] + list(_file_options.keys()),
        )
        if _selected != "— ingresar URL —":
            url_input = _file_options[_selected]
            settings.SKIP_DOWNLOAD = True
            st.caption(f"✅ Usando `{_selected}{[f for f in _local_files if f.stem == _selected][0].suffix}`")
        else:
            url_input = st.text_input(
                "URL de YouTube",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            settings.SKIP_DOWNLOAD = False
    else:
        url_input = st.text_input(
            "URL de YouTube",
            placeholder="https://www.youtube.com/watch?v=...",
        )

    dry_run = st.checkbox(
        "Modo dry-run",
        help="Omite descarga y transcripción. Requiere audio ya descargado y transcripción en BD.",
    )
    st.divider()

    # Badge de entorno
    env = settings.ENVIRONMENT.upper()
    if env == "LOCAL":
        st.success(f"🖥️ Entorno: **{env}**")
    else:
        st.info(f"☁️ Entorno: **{env}**")
    st.caption(f"Whisper: `{settings.WHISPER_MODEL}` · LLM: `{settings.OLLAMA_MODEL}`")

    # Info del video (después del análisis)
    res = st.session_state.result
    if res:
        meta = res.metadata if hasattr(res, "metadata") else res.get("metadata", {})
        st.divider()
        thumb = meta.get("thumbnail_url", "")
        if thumb:
            st.image(thumb, use_container_width=True)
        st.markdown(f"**{meta.get('title', '')}**")
        st.caption(f"📺 {meta.get('channel_title', '')}")
        c1, c2 = st.columns(2)
        c1.metric("Views", f"{meta.get('view_count', 0):,}")
        c2.metric("Likes", f"{meta.get('like_count', 0):,}")
        dur = meta.get("duration_seconds", 0)
        st.caption(f"⏱️ {dur // 60}m {dur % 60}s · {meta.get('comment_count', 0):,} comentarios")


# ─── Header ──────────────────────────────────────────────────────────────────

st.title("🎬 Spike GPU — Analizador de Video YouTube")
st.caption("Descarga · Transcribe · Analiza · Genera guion + prompts de imagen y video")
st.divider()

# ─── Botón principal ─────────────────────────────────────────────────────────

_, col_btn, _ = st.columns([2, 1, 2])
with col_btn:
    analyze_btn = st.button(
        "🚀 Analizar Video",
        use_container_width=True,
        type="primary",
        disabled=st.session_state.running,
    )


# ─── Manejo de errores ────────────────────────────────────────────────────────

def _show_error(exc: Exception) -> None:
    """Notificación de error con mensaje amigable según el tipo de excepción."""
    from backend.core.downloader import (
        DownloadNetworkError,
        InvalidURLError,
        VideoUnavailableError,
    )

    if isinstance(exc, VideoUnavailableError):
        st.error(
            "❌ **Video no disponible** — El video es privado, fue eliminado "
            "o está geo-restringido."
        )
    elif isinstance(exc, InvalidURLError):
        st.error("❌ **URL inválida** — Verifica que sea una URL de YouTube válida.")
    elif isinstance(exc, DownloadNetworkError):
        st.error(
            "❌ **Error de red** — No se pudo descargar el audio. "
            "Revisa tu conexión a internet."
        )
    elif isinstance(exc, asyncio.TimeoutError):
        st.error(
            "⏱️ **Tiempo agotado** — El pipeline tardó demasiado. "
            "Prueba con un video más corto."
        )
    elif any(word in str(exc).lower() for word in ("connection refused", "psycopg", "pool")):
        st.error(
            "🔌 **Base de datos no disponible** — Verifica que Docker esté corriendo:\n\n"
            "```\ndocker compose up -d\n```"
        )
    elif any(word in str(exc).lower() for word in ("ollama", "connect", "httpx")):
        st.error(
            "🤖 **Ollama no responde** — Verifica que esté corriendo:\n\n"
            "```\nollama serve\n```"
        )
    else:
        st.error(f"**{type(exc).__name__}:** {exc}")

    with st.expander("🔍 Detalles técnicos"):
        st.code(st.session_state.last_error or str(exc), language="python")


# ─── Pipeline ────────────────────────────────────────────────────────────────

# Nota extra por fase para fases que pueden tardar mucho
_PHASE_NOTES: dict[str, str] = {
    "transcripcion": " *(puede tardar varios minutos en CPU)*",
    "analisis_llm":  " *(procesando chunks de texto)*",
}


async def _pipeline(url: str, skip: bool, status, progress_bar) -> PipelineResult:
    """Wrapper sobre VideoPipeline con progreso real en Streamlit."""
    from backend.config import settings as _s
    _s.SKIP_DOWNLOAD = skip

    from backend.pipeline import PHASE_LABELS, TOTAL_PHASES

    def on_phase_start(key: str, num: int, total: int) -> None:
        label = PHASE_LABELS.get(key, key)
        note = _PHASE_NOTES.get(key, "")
        progress_bar.progress((num - 1) / total, text=f"Fase {num}/{total}")
        status.write(f"⏳ **{label}**{note}")

    def on_phase_done(_key: str, duration: float) -> None:
        mins, secs = divmod(int(duration), 60)
        time_str = f"{mins}m {secs:02d}s" if mins else f"{duration:.1f}s"
        status.write(f"  ✅ completado en **{time_str}**")

    pipeline = VideoPipeline()
    result = await pipeline.run(
        url,
        on_phase_start=on_phase_start,
        on_phase_done=on_phase_done,
    )
    progress_bar.progress(1.0, text="✅ Pipeline completado")
    return result


# ─── Ejecución ────────────────────────────────────────────────────────────────

if analyze_btn:
    if not url_input.strip():
        st.warning("Ingresa una URL de YouTube antes de analizar.")
    else:
        st.session_state.running = True
        st.session_state.last_error = None
        st.session_state.last_error_exc = None
        progress_bar = st.progress(0, text="Iniciando pipeline...")
        with st.status("Analizando video...", expanded=True) as status:
            try:
                res = asyncio.run(
                    _pipeline(url_input.strip(), dry_run, status, progress_bar)
                )
                st.session_state.result = res
                st.session_state.timings = list(res.timing_summary.items())
                status.update(label="✅ ¡Análisis completo!", state="complete")
            except Exception as exc:
                import traceback
                st.session_state.last_error_exc = exc
                st.session_state.last_error = traceback.format_exc()
                status.update(label="❌ Error durante el análisis", state="error")
        st.session_state.running = False
        st.rerun()

# Mostrar error persistente (sobrevive al rerun)
if st.session_state.last_error_exc is not None:
    _show_error(st.session_state.last_error_exc)


# ─── Resultados ──────────────────────────────────────────────────────────────

res: PipelineResult | None = st.session_state.result
if res:
    analysis: AnalysisResult = res.analysis
    sentiment: SentimentResult = res.sentiment
    script: ScriptResult = res.script
    image_prompts: list[ImagePrompt] = res.image_prompts
    video_prompts: list[VideoPrompt] = res.video_prompts
    timings: list[tuple[str, float]] = list(res.timing_summary.items())
    transcript: str = res.transcript

    tab_script, tab_images, tab_video, tab_analysis, tab_sentiment, tab_timing = st.tabs([
        "📝 Guion",
        "🖼️ Prompts Imagen",
        "🎬 Prompts Video",
        "🔍 Análisis",
        "💬 Sentimiento",
        "⏱️ Tiempos",
    ])

    # ── Tab: Guion ────────────────────────────────────────────────────────────
    with tab_script:
        st.subheader("Guion mejorado")

        with st.expander(f"🎣 GANCHO — {script.hook_intro.title}", expanded=True):
            st.markdown(script.hook_intro.narration_text)
            st.caption(f"⏱️ {script.hook_intro.duration_seconds}s · Mensaje clave: *{script.hook_intro.key_message}*")

        for i, section in enumerate(script.sections, 1):
            with st.expander(f"📌 {i}. {section.title}"):
                st.markdown(section.narration_text)
                st.caption(f"⏱️ {section.duration_seconds}s · Mensaje clave: *{section.key_message}*")

        with st.expander(f"🎯 CONCLUSIÓN — {script.conclusion_cta.title}"):
            st.markdown(script.conclusion_cta.narration_text)
            st.caption(f"⏱️ {script.conclusion_cta.duration_seconds}s · CTA: *{script.conclusion_cta.key_message}*")

    # ── Tab: Prompts Imagen ───────────────────────────────────────────────────
    with tab_images:
        st.subheader("Prompts de generación de imagen")
        st.caption(f"Estilo visual consistente: *{image_prompts[0].style_reference if image_prompts else '—'}*")
        st.divider()
        for img in image_prompts:
            with st.expander(f"🖼️ Escena {img.scene_number} · {img.duration_seconds}s"):
                st.markdown(f"**Prompt:** {img.description}")
                st.caption(f"Aspect ratio: `{img.aspect_ratio}`")

    # ── Tab: Prompts Video ────────────────────────────────────────────────────
    with tab_video:
        st.subheader("Instrucciones de movimiento de cámara")
        data_rows = [
            {
                "Escena": vp.scene_number,
                "Movimiento": vp.motion_type,
                "Velocidad": vp.camera_speed,
                "Duración (s)": vp.duration_seconds,
                "Descripción": vp.motion_description,
            }
            for vp in video_prompts
        ]
        st.dataframe(data_rows, use_container_width=True)

    # ── Tab: Análisis ─────────────────────────────────────────────────────────
    with tab_analysis:
        st.subheader("Análisis del contenido")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🔑 Puntos clave**")
            for pt in analysis.key_points:
                st.markdown(f"- {pt}")
            st.markdown("**🏷️ Temas principales**")
            for tp in analysis.main_topics:
                st.markdown(f"- {tp}")
        with col2:
            st.markdown("**⚠️ Gaps de contenido**")
            for gap in analysis.content_gaps:
                st.markdown(f"- {gap}")
            st.markdown("**💡 Oportunidades de mejora**")
            for opp in analysis.improvement_opportunities:
                st.markdown(f"- {opp}")

        st.divider()
        st.markdown(f"**🎭 Tono:** {analysis.tone}")
        st.markdown(f"**📐 Estructura narrativa:** {analysis.narrative_structure}")

    # ── Tab: Sentimiento ──────────────────────────────────────────────────────
    with tab_sentiment:
        st.subheader("Sentimiento de comentarios")

        col1, col2 = st.columns([1, 2])
        with col1:
            color = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(
                sentiment.overall_sentiment, "⚪"
            )
            st.metric(
                "Sentimiento general",
                f"{color} {sentiment.overall_sentiment.upper()}",
            )
            st.progress(sentiment.sentiment_score, text=f"Score: {sentiment.sentiment_score:.0%}")
        with col2:
            st.markdown("**❓ Preguntas frecuentes de la audiencia**")
            for q in sentiment.audience_questions:
                st.markdown(f"- {q}")
            st.markdown("**😤 Pain points de la audiencia**")
            for pp in sentiment.audience_pain_points:
                st.markdown(f"- {pp}")

        if sentiment.main_themes_in_comments:
            st.divider()
            st.markdown("**💬 Temas recurrentes en comentarios**")
            for th in sentiment.main_themes_in_comments:
                st.markdown(f"- {th}")

    # ── Tab: Tiempos ──────────────────────────────────────────────────────────
    with tab_timing:
        st.subheader("Benchmark de rendimiento")

        total = sum(d for _, d in timings)
        max_dur = max((d for _, d in timings), default=1)

        for fase, dur in timings:
            mins, secs = divmod(int(dur), 60)
            label = f"**{fase.replace('_', ' ').title()}** — {mins}m {secs:02d}s"
            st.markdown(label)
            st.progress(dur / max_dur)

        st.divider()
        total_min, total_sec = divmod(int(total), 60)
        st.metric("⏱️ Tiempo total", f"{total_min}m {total_sec:02d}s")

        if settings.ENVIRONMENT == "local":
            st.info(
                "📊 Este es tu baseline local. "
                "Despliega en RunPod con `large-v3` + modelo 72B+ para comparar."
            )
        else:
            st.success("☁️ Resultado en GPU cloud.")

    # ── Exportar ZIP ──────────────────────────────────────────────────────────
    st.divider()

    def _build_zip() -> bytes:
        buf = io.BytesIO()

        # Guion en Markdown
        sections_all = [script.hook_intro] + script.sections + [script.conclusion_cta]
        guion_md = "\n\n".join(
            f"## {s.title}\n\n{s.narration_text}\n\n*{s.key_message}* · {s.duration_seconds}s"
            for s in sections_all
        )

        # Tiempos en CSV
        timings_csv = "fase,duracion_segundos,environment\n" + "\n".join(
            f"{fase},{dur:.2f},{settings.ENVIRONMENT}" for fase, dur in timings
        )

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("transcripcion.txt", transcript)
            zf.writestr(
                "analisis.json",
                json.dumps(
                    {
                        "analysis": analysis.model_dump(),
                        "sentiment": sentiment.model_dump(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            zf.writestr("guion.md", guion_md)
            zf.writestr(
                "prompts_imagenes.json",
                json.dumps([p.model_dump() for p in image_prompts], ensure_ascii=False, indent=2),
            )
            zf.writestr(
                "prompts_video.json",
                json.dumps([p.model_dump() for p in video_prompts], ensure_ascii=False, indent=2),
            )
            zf.writestr("tiempos.csv", timings_csv)

        return buf.getvalue()

    video_title = res.metadata.get("title", "video")[:30].replace(" ", "_")
    st.download_button(
        label="📦 Exportar ZIP con todos los resultados",
        data=_build_zip(),
        file_name=f"spike_{video_title}.zip",
        mime="application/zip",
        use_container_width=True,
    )
