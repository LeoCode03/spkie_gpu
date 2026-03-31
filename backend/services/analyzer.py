import json
import re
from typing import Optional

import httpx
import psycopg

from backend.config import settings
from backend.core.timer import PhaseTimer
from backend.services.schemas import AnalysisResult, SentimentResult


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _chunk_transcript(text: str, max_words: int = 3000) -> list[str]:
    """
    Divide la transcripción en chunks de máximo max_words palabras,
    respetando límites de oraciones para no cortar a mitad de idea.
    """
    # Separar en oraciones por . ? ! seguido de espacio o fin de string
    sentences = re.split(r"(?<=[.?!])\s+", text.strip())

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current_words + sentence_words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = sentence_words
        else:
            current.append(sentence)
            current_words += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [text]


def _extract_json(raw: str) -> dict:
    """
    Extrae el primer objeto JSON del texto de respuesta del LLM.
    Maneja casos donde Ollama envuelve el JSON en bloques markdown.
    """
    # Intentar parsear directamente
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Buscar bloque ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Buscar primer { ... } en el texto
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No se pudo extraer JSON de la respuesta del LLM:\n{raw[:300]}")


# ─── Cliente Ollama ───────────────────────────────────────────────────────────

async def _ollama_chat(
    messages: list[dict],
    temperature: float = 0.1,
) -> str:
    """Llamada al endpoint /api/chat de Ollama. Retorna el content del mensaje."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


# ─── Analizador ──────────────────────────────────────────────────────────────

class LLMAnalyzer:

    # ── Análisis de transcripción ─────────────────────────────────────────────

    async def analyze_transcript(
        self,
        transcript: str,
        metadata: dict,
    ) -> AnalysisResult:
        """
        Analiza la transcripción en dos pasadas:
        1. Analiza cada chunk individualmente → extrae puntos clave por segmento
        2. Sintetiza todos los resultados en un AnalysisResult global
        """
        timer = PhaseTimer()
        timer.start("analisis_transcripcion")

        chunks = _chunk_transcript(transcript, max_words=3000)
        total_words = len(transcript.split())

        print(f"[analyzer] Transcripción: {total_words} palabras en {len(chunks)} chunk(s)")

        # ── Pasada 1: análisis por chunk ──────────────────────────────────────
        chunk_results: list[dict] = []
        for i, chunk in enumerate(chunks, 1):
            print(f"[analyzer] Chunk {i}/{len(chunks)} ({len(chunk.split())} palabras)...")
            raw = await _ollama_chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un analista de contenido experto en YouTube. "
                            "Analiza el fragmento de transcripción y responde SOLO con JSON válido, "
                            "sin texto adicional."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analiza este fragmento de la transcripción del video "
                            f"'{metadata.get('title', 'desconocido')}':\n\n{chunk}\n\n"
                            "Responde con este JSON exacto:\n"
                            "{\n"
                            '  "chunk_key_points": ["punto 1", "punto 2"],\n'
                            '  "chunk_topics": ["tema 1", "tema 2"],\n'
                            '  "chunk_tone": "informativo|educativo|entretenimiento|motivacional|crítico"\n'
                            "}"
                        ),
                    },
                ],
                temperature=0.1,
            )
            try:
                chunk_results.append(_extract_json(raw))
            except ValueError:
                chunk_results.append({"chunk_key_points": [], "chunk_topics": [], "chunk_tone": "neutral"})

        # ── Pasada 2: síntesis global ─────────────────────────────────────────
        print(f"[analyzer] Sintetizando {len(chunk_results)} chunk(s)...")

        all_points = [p for r in chunk_results for p in r.get("chunk_key_points", [])]
        all_topics = [t for r in chunk_results for t in r.get("chunk_topics", [])]
        all_tones = [r.get("chunk_tone", "") for r in chunk_results]

        raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de contenido experto en YouTube. "
                        "Sintetiza el análisis de múltiples fragmentos de un video. "
                        "Responde SOLO con JSON válido, sin texto adicional."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Video: '{metadata.get('title', '')}' | "
                        f"{metadata.get('view_count', 0):,} views\n\n"
                        f"Puntos clave por fragmento: {json.dumps(all_points, ensure_ascii=False)}\n"
                        f"Temas por fragmento: {json.dumps(all_topics, ensure_ascii=False)}\n"
                        f"Tonos por fragmento: {all_tones}\n\n"
                        "Genera el análisis global con este JSON exacto:\n"
                        "{\n"
                        '  "key_points": ["los 5-8 puntos más importantes del video"],\n'
                        '  "main_topics": ["los 3-5 temas principales"],\n'
                        '  "tone": "tono predominante del video en una frase",\n'
                        '  "narrative_structure": "descripción de cómo está estructurada la narrativa",\n'
                        '  "content_gaps": ["tema o aspecto importante que el video NO cubre"],\n'
                        '  "improvement_opportunities": ["mejoras concretas que haría el video mejor"]\n'
                        "}"
                    ),
                },
            ],
            temperature=0.1,
        )

        duracion = timer.stop()
        tokens_por_segundo = total_words / duracion if duracion > 0 else 0.0
        print(f"[analyzer] Análisis completado en {duracion:.1f}s ({tokens_por_segundo:.1f} palabras/s)")

        data = _extract_json(raw)
        return AnalysisResult.model_validate(data)

    # ── Análisis de sentimiento ───────────────────────────────────────────────

    async def analyze_sentiment(
        self,
        comments: list[dict],
    ) -> SentimentResult:
        """
        Analiza el sentimiento general de los comentarios del video.
        Si no hay comentarios, devuelve resultado neutral por defecto.
        """
        if not comments:
            return SentimentResult()

        timer = PhaseTimer()
        timer.start("analisis_sentimiento")

        # Formatear comentarios como texto numerado (máx 50 para no saturar el contexto)
        sample = comments[:50]
        formatted = "\n".join(
            f"{i + 1}. {c['text'][:200]}" for i, c in enumerate(sample)
        )

        raw = await _ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de sentimiento experto en audiencias de YouTube. "
                        "Analiza los comentarios y responde SOLO con JSON válido, sin texto adicional."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Analiza estos {len(sample)} comentarios de YouTube:\n\n"
                        f"{formatted}\n\n"
                        "Responde con este JSON exacto:\n"
                        "{\n"
                        '  "overall_sentiment": "positive|negative|neutral",\n'
                        '  "sentiment_score": 0.0,\n'
                        '  "main_themes_in_comments": ["tema recurrente 1", "tema recurrente 2"],\n'
                        '  "audience_questions": ["pregunta frecuente de la audiencia"],\n'
                        '  "audience_pain_points": ["problema o frustración de la audiencia"]\n'
                        "}\n"
                        "sentiment_score: 0.0=muy negativo, 0.5=neutro, 1.0=muy positivo"
                    ),
                },
            ],
            temperature=0.1,
        )

        duracion = timer.stop()
        print(f"[analyzer] Sentimiento completado en {duracion:.1f}s")

        data = _extract_json(raw)
        return SentimentResult.model_validate(data)

    # ── Persistencia ──────────────────────────────────────────────────────────

    async def save_to_db(
        self,
        video_db_id: int,
        analysis: AnalysisResult,
        sentiment: SentimentResult,
        db_conn: psycopg.AsyncConnection,
    ) -> None:
        """Guarda análisis y sentimiento en la tabla 'analisis'."""
        await db_conn.execute(
            """
            INSERT INTO analisis (
                video_id, key_points, main_topics, tone, narrative_structure,
                content_gaps, improvement_opportunities,
                overall_sentiment, sentiment_score,
                audience_questions, audience_pain_points
            ) VALUES (
                %s, %s::jsonb, %s::jsonb, %s, %s,
                %s::jsonb, %s::jsonb,
                %s, %s,
                %s::jsonb, %s::jsonb
            )
            """,
            (
                video_db_id,
                json.dumps(analysis.key_points, ensure_ascii=False),
                json.dumps(analysis.main_topics, ensure_ascii=False),
                analysis.tone,
                analysis.narrative_structure,
                json.dumps(analysis.content_gaps, ensure_ascii=False),
                json.dumps(analysis.improvement_opportunities, ensure_ascii=False),
                sentiment.overall_sentiment,
                sentiment.sentiment_score,
                json.dumps(sentiment.audience_questions, ensure_ascii=False),
                json.dumps(sentiment.audience_pain_points, ensure_ascii=False),
            ),
        )
