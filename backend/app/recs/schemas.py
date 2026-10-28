"""Pydantic schemas for recommendation API responses."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.anime import AnimeCard


class ExplanationSchema(BaseModel):
    """Structured explanation attached to every recommendation result."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    shared_genres: list[str] = Field(default_factory=list)
    shared_tags: list[str] = Field(default_factory=list)
    seed_titles: list[str] = Field(default_factory=list)
    quiz_answers: list[str] = Field(default_factory=list)


class RecResult(AnimeCard):
    """A single recommendation result extending AnimeCard with explanation fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: str = ""
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_cosine: float | None = None
    rank_sim: float | None = None
    rank_taste: float | None = None
    quality_score: float | None = None
    final_score: float | None = None
    pre_mmr_rank: int | None = None
    explanation: ExplanationSchema = Field(default_factory=ExplanationSchema)


class QuizAnswerRequest(BaseModel):
    """Request body for POST /api/recs/quiz."""

    answers: dict[str, str]  # {question_id: answer_id}
    n: int = Field(default=10, ge=1, le=50)
    include_mature: bool = Field(default=False, alias="includeMature")

    model_config = ConfigDict(populate_by_name=True)


class QuizResponse(BaseModel):
    """Response for the quiz endpoint."""

    results: list[RecResult]
    quiz_vec_stored: bool = Field(
        default=False,
        alias="quizVecStored",
        description="True if the quiz-derived taste vector was saved to the user profile.",
    )

    model_config = ConfigDict(populate_by_name=True)
