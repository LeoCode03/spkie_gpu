from typing import Literal
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    key_points: list[str] = Field(default_factory=list)
    main_topics: list[str] = Field(default_factory=list)
    tone: str = ""
    narrative_structure: str = ""
    content_gaps: list[str] = Field(default_factory=list)
    improvement_opportunities: list[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    overall_sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    sentiment_score: float = Field(default=0.5, ge=0.0, le=1.0)
    main_themes_in_comments: list[str] = Field(default_factory=list)
    audience_questions: list[str] = Field(default_factory=list)
    audience_pain_points: list[str] = Field(default_factory=list)


class ScriptSection(BaseModel):
    title: str = ""
    narration_text: str = ""
    duration_seconds: int = 0
    key_message: str = ""


class ScriptResult(BaseModel):
    hook_intro: ScriptSection = Field(default_factory=ScriptSection)
    sections: list[ScriptSection] = Field(default_factory=list)
    conclusion_cta: ScriptSection = Field(default_factory=ScriptSection)


class ImagePrompt(BaseModel):
    scene_number: int = 0
    description: str = ""
    style_reference: str = ""
    duration_seconds: int = 0
    aspect_ratio: str = "16:9"


class VideoPrompt(BaseModel):
    scene_number: int = 0
    motion_type: Literal[
        "zoom-in", "zoom-out", "pan-left", "pan-right",
        "static", "tilt-up", "tilt-down"
    ] = "static"
    motion_description: str = ""
    duration_seconds: int = 0
    camera_speed: Literal["slow", "medium", "fast"] = "medium"
