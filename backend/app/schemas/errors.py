"""Error response schemas matching FastAPI and HTTPException responses."""

from typing import Any

from pydantic import BaseModel


class ValidationErrorItem(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any = None
    ctx: dict[str, Any] | None = None


class ApiErrorResponse(BaseModel):
    detail: str | list[ValidationErrorItem]
    code: str | None = None
