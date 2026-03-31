import json

import httpx
import psycopg

from backend.config import settings
from backend.core.timer import PhaseTimer
from backend.services.analyzer import _extract_json, _ollama_chat
from backend.services.schemas import (
    AnalysisResult,
    ImagePrompt,
    ScriptResult,
    ScriptSection,
    SentimentResult,
    VideoPrompt,
)

# Tipos de movimiento válidos (para fallback si el LLM devuelve algo inválido)
_VALID_MOTIONS = {"zoom-in", "zoom-out", "pan-left", "pan-right", "static", "tilt-up", "tilt-down"}
_VALID_SPEEDS = {"slow", "medium", "fast"}


def _distribute_duration(total_seconds: int, num_sections: int) -> tuple[int, int, int]:
    """
    Distribuye la duración total entre hook (30s), secciones centrales y conclusión (30s).
    Retorna (hook_secs, secs_por_seccion, conclusion_secs).
    """
    if total_seconds <= 0:
        total_seconds = num_sections * 60 + 60  # estimado si no se conoce
    hook = 30
    conclusion = 30
    remaining = max(total_seconds - hook - conclusion, num_sections * 20)
    per_section = remaining // num_sections if num_sections else 60
    return hook, per_section, conclusion


class ContentGenerator:

    # ── Guion ────────────────────────────────────────────────────────────────

    async def generate_script(
        self,
        analysis: AnalysisResult,
        sentiment: SentimentResult,
        metadata: dict,
    ) -> ScriptResult:
        """
        Genera un guion mejorado estructurado en gancho + secciones + CTA.
        Incorpora las oportunidades de mejora del análisis y los pain points
        del sentimiento para crear contenido más relevante que el original.
        """
        timer = PhaseTimer()
        timer.start("generacion_guion")

        total_seconds = metadata.get("duration_seconds", 0)
        title = metadata.get("title", "el video")

        raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un guionista experto en YouTube con 10 años de experiencia "
                        "creando videos virales. Tu especialidad es transformar contenido "
                        "existente en versiones mejoradas y más atractivas para la audiencia. "
                        "Responde SOLO con JSON válido, sin texto adicional."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Crea un guion mejorado inspirado en: '{title}'\n\n"
                        f"Temas principales: {analysis.main_topics}\n"
                        f"Puntos clave del original: {analysis.key_points[:5]}\n"
                        f"Oportunidades de mejora: {analysis.improvement_opportunities}\n"
                        f"Problemas de la audiencia: {sentiment.audience_pain_points}\n"
                        f"Preguntas de la audiencia: {sentiment.audience_questions}\n"
                        f"Duración objetivo: {total_seconds} segundos\n\n"
                        "Genera un guion con esta estructura JSON exacta:\n"
                        "{\n"
                        '  "hook_intro": {\n'
                        '    "title": "nombre del gancho",\n'
                        '    "narration_text": "texto de narración del gancho (máx 3 oraciones, debe enganchar en 5 segundos)",\n'
                        '    "key_message": "mensaje clave del gancho"\n'
                        "  },\n"
                        '  "sections": [\n'
                        "    {\n"
                        '      "title": "nombre de la sección",\n'
                        '      "narration_text": "texto de narración completo de la sección",\n'
                        '      "key_message": "mensaje clave de esta sección"\n'
                        "    }\n"
                        "  ],\n"
                        '  "conclusion_cta": {\n'
                        '    "title": "Conclusión y llamada a la acción",\n'
                        '    "narration_text": "texto de cierre con CTA claro",\n'
                        '    "key_message": "mensaje final"\n'
                        "  }\n"
                        "}\n"
                        "Incluye entre 5 y 8 secciones de desarrollo. "
                        "El guion debe ser MEJOR que el original: más claro, más atractivo, "
                        "respondiendo las dudas de la audiencia y cubriendo los gaps identificados."
                    ),
                },
            ],
            temperature=0.7,
        )

        duracion = timer.stop()
        print(f"[generator] Guion generado en {duracion:.1f}s")

        data = _extract_json(raw)

        # Construir ScriptResult asignando duration_seconds
        num_sections = len(data.get("sections", []))
        hook_secs, per_sec, conclusion_secs = _distribute_duration(
            total_seconds, max(num_sections, 1)
        )

        hook = ScriptSection(
            title=data.get("hook_intro", {}).get("title", "Gancho"),
            narration_text=data.get("hook_intro", {}).get("narration_text", ""),
            duration_seconds=hook_secs,
            key_message=data.get("hook_intro", {}).get("key_message", ""),
        )

        sections = [
            ScriptSection(
                title=s.get("title", f"Sección {i + 1}"),
                narration_text=s.get("narration_text", ""),
                duration_seconds=per_sec,
                key_message=s.get("key_message", ""),
            )
            for i, s in enumerate(data.get("sections", []))
        ]

        conclusion = ScriptSection(
            title=data.get("conclusion_cta", {}).get("title", "Conclusión"),
            narration_text=data.get("conclusion_cta", {}).get("narration_text", ""),
            duration_seconds=conclusion_secs,
            key_message=data.get("conclusion_cta", {}).get("key_message", ""),
        )

        return ScriptResult(hook_intro=hook, sections=sections, conclusion_cta=conclusion)

    # ── Prompts de imagen ────────────────────────────────────────────────────

    async def generate_image_prompts(
        self,
        script: ScriptResult,
        metadata: dict,
    ) -> list[ImagePrompt]:
        """
        Genera un prompt de imagen por sección del guion (máximo 10).
        El style_reference es idéntico en todas las imágenes para coherencia visual.
        Los prompts se generan en inglés para máxima compatibilidad con generadores.
        """
        timer = PhaseTimer()
        timer.start("generacion_prompts_imagen")

        # Todas las secciones en orden: hook + desarrollo + conclusión
        all_sections = [script.hook_intro] + script.sections + [script.conclusion_cta]
        all_sections = all_sections[:10]  # máximo 10 imágenes

        title = metadata.get("title", "the video")
        topics = ", ".join(metadata.get("main_topics", [])) if metadata.get("main_topics") else title

        # Paso 1: definir el style_reference consistente para todo el video
        style_raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cinematography expert for YouTube videos. "
                        "Define a consistent visual style for all video frames. "
                        "Respond ONLY with valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Video topic: '{title}'\n"
                        f"Main themes: {topics}\n\n"
                        "Define a cinematic visual style that will be consistent across ALL scenes. "
                        'Respond with this exact JSON:\n{"style_reference": "one sentence '
                        "describing the visual style: lighting, color palette, camera style, mood. "
                        'Example: cinematic 4K, warm golden hour lighting, shallow depth of field, '
                        'documentary style, natural colors, professional photography"}'
                    ),
                },
            ],
            temperature=0.3,
        )

        try:
            style_data = _extract_json(style_raw)
            style_reference = style_data.get("style_reference", "cinematic 4K, professional photography, natural lighting, sharp focus")
        except ValueError:
            style_reference = "cinematic 4K, professional photography, natural lighting, sharp focus"

        print(f"[generator] Estilo visual: {style_reference[:80]}...")

        # Paso 2: generar descripciones de imagen para cada sección
        sections_summary = "\n".join(
            f"{i + 1}. [{s.title}]: {s.narration_text[:150]}"
            for i, s in enumerate(all_sections)
        )

        images_raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a visual director for YouTube videos. "
                        "Create detailed image generation prompts for each scene. "
                        "All prompts must be in English. "
                        "Respond ONLY with valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Create one image prompt per scene for this YouTube video about: '{title}'\n\n"
                        f"Scenes:\n{sections_summary}\n\n"
                        f"Visual style for ALL scenes: {style_reference}\n\n"
                        "Respond with this exact JSON:\n"
                        '{"images": [\n'
                        '  {"scene_number": 1, "description": "detailed English prompt for image generation, '
                        "include subject, action, environment, lighting, composition\"}\n"
                        "]}"
                    ),
                },
            ],
            temperature=0.5,
        )

        duracion = timer.stop()
        print(f"[generator] Prompts de imagen generados en {duracion:.1f}s")

        try:
            images_data = _extract_json(images_raw)
            raw_images = images_data.get("images", [])
        except ValueError:
            raw_images = []

        prompts: list[ImagePrompt] = []
        for i, section in enumerate(all_sections):
            raw_img = raw_images[i] if i < len(raw_images) else {}
            prompts.append(
                ImagePrompt(
                    scene_number=i + 1,
                    description=raw_img.get("description", f"Scene {i + 1}: {section.title}"),
                    style_reference=style_reference,
                    duration_seconds=section.duration_seconds,
                    aspect_ratio="16:9",
                )
            )

        return prompts

    # ── Prompts de video ─────────────────────────────────────────────────────

    async def generate_video_prompts(
        self,
        image_prompts: list[ImagePrompt],
        script: ScriptResult,
    ) -> list[VideoPrompt]:
        """
        Genera instrucciones de movimiento de cámara para cada imagen.
        El tipo de movimiento se elige según el contenido narrado:
        - Acción/energía → zoom-in, pan rápido
        - Explicativo/reflexivo → static, tilt-up lento
        """
        timer = PhaseTimer()
        timer.start("generacion_prompts_video")

        all_sections = [script.hook_intro] + script.sections + [script.conclusion_cta]

        scenes_summary = "\n".join(
            f"{i + 1}. Scene: {ip.description[:100]} | Narration: {all_sections[i].narration_text[:100] if i < len(all_sections) else ''}"
            for i, ip in enumerate(image_prompts)
        )

        raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a video motion director. "
                        "Assign camera movements to each scene based on its content and energy. "
                        "Rules: action/energetic content → zoom-in or fast pan. "
                        "Reflective/explanatory content → static or slow tilt-up. "
                        "Respond ONLY with valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Assign camera motion to each scene:\n{scenes_summary}\n\n"
                        "Valid motion_type values: zoom-in, zoom-out, pan-left, pan-right, static, tilt-up, tilt-down\n"
                        "Valid camera_speed values: slow, medium, fast\n\n"
                        "Respond with this exact JSON:\n"
                        '{"motions": [\n'
                        '  {\n'
                        '    "scene_number": 1,\n'
                        '    "motion_type": "zoom-in",\n'
                        '    "motion_description": "specific description of the movement",\n'
                        '    "camera_speed": "medium"\n'
                        "  }\n"
                        "]}"
                    ),
                },
            ],
            temperature=0.5,
        )

        duracion = timer.stop()
        print(f"[generator] Prompts de video generados en {duracion:.1f}s")

        try:
            data = _extract_json(raw)
            raw_motions = data.get("motions", [])
        except ValueError:
            raw_motions = []

        prompts: list[VideoPrompt] = []
        for i, img in enumerate(image_prompts):
            raw_m = raw_motions[i] if i < len(raw_motions) else {}
            motion = raw_m.get("motion_type", "static")
            speed = raw_m.get("camera_speed", "medium")

            # Validar y hacer fallback si el LLM devolvió un valor inválido
            if motion not in _VALID_MOTIONS:
                motion = "static"
            if speed not in _VALID_SPEEDS:
                speed = "medium"

            prompts.append(
                VideoPrompt(
                    scene_number=img.scene_number,
                    motion_type=motion,
                    motion_description=raw_m.get("motion_description", ""),
                    duration_seconds=img.duration_seconds,
                    camera_speed=speed,
                )
            )

        return prompts

    # ── Persistencia ─────────────────────────────────────────────────────────

    async def save_to_db(
        self,
        video_db_id: int,
        script: ScriptResult,
        image_prompts: list[ImagePrompt],
        video_prompts: list[VideoPrompt],
        db_conn: psycopg.AsyncConnection,
    ) -> None:
        """Guarda guion, prompts de imagen y video en la tabla 'guiones'."""
        # Aplanar el guion a una lista ordenada: [hook, ...secciones, conclusión]
        all_sections = [script.hook_intro] + script.sections + [script.conclusion_cta]
        sections_data = [s.model_dump() for s in all_sections]

        await db_conn.execute(
            """
            INSERT INTO guiones (video_id, sections, image_prompts, video_prompts)
            VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb)
            """,
            (
                video_db_id,
                json.dumps(sections_data, ensure_ascii=False),
                json.dumps([p.model_dump() for p in image_prompts], ensure_ascii=False),
                json.dumps([p.model_dump() for p in video_prompts], ensure_ascii=False),
            ),
        )
