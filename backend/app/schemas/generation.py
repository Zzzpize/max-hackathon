from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Subject = Literal["math", "algebra", "physics", "geometry"]
Difficulty = Literal["easy", "medium", "hard"]


class GeneratedTask(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    index: int = Field(ge=1, strict=True)
    statement: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    difficulty: Difficulty | None = None

    @field_validator("difficulty")
    @classmethod
    def difficulty_must_be_known(cls, value: Difficulty | None) -> Difficulty:
        # Omission is allowed; an explicitly supplied value must be an enum member.
        if value is None:
            raise ValueError("difficulty должен быть easy, medium или hard")
        return value
