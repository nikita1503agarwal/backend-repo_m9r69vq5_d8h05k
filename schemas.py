"""
Database Schemas for SignifyLearn

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name (e.g., Gesture -> "gesture").
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class Gesture(BaseModel):
    """Sign language gesture catalog item"""
    name: str = Field(..., description="Gesture name")
    slug: str = Field(..., description="URL-friendly identifier")
    category: Literal["letters", "numbers", "basic", "emotions", "activity", "other"] = Field(
        "basic", description="Category filter"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field("easy")
    thumbnail: Optional[HttpUrl] = Field(None, description="Preview image URL")
    video_url: Optional[HttpUrl] = Field(None, description="Learning video URL")
    steps: List[str] = Field(default_factory=list, description="Step-by-step explanation")
    examples: List[str] = Field(default_factory=list, description="Usage examples in conversation")
    tags: List[str] = Field(default_factory=list)


class Module(BaseModel):
    """Educational module"""
    title: str
    slug: str
    description: Optional[str] = None
    cover_image: Optional[HttpUrl] = None
    subtopics: List[str] = Field(default_factory=list)
    gesture_slugs: List[str] = Field(default_factory=list, description="Gestures covered in this module")


class QuizQuestion(BaseModel):
    prompt: str
    media_url: Optional[HttpUrl] = None
    options: List[str]
    answer_index: int = Field(ge=0)


class Quiz(BaseModel):
    """Quiz for a module or topic"""
    title: str
    slug: str
    questions: List[QuizQuestion]
    related_module_slug: Optional[str] = None


class Profile(BaseModel):
    """User profile and progress"""
    user_id: str
    name: str
    email: str
    avatar_url: Optional[HttpUrl] = None
    points: int = 0
    level: int = 1
    streak_days: int = 0
    favorite_gesture_slugs: List[str] = Field(default_factory=list)
    completed_module_slugs: List[str] = Field(default_factory=list)


class Accessibility(BaseModel):
    """Accessibility preferences per user"""
    user_id: str
    dark_mode: bool = False
    high_contrast: bool = False
    font_scale: float = Field(1.0, ge=0.85, le=1.6)
    reduce_motion: bool = False
