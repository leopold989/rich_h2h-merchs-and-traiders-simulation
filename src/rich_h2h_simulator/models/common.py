from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)


class StatusBody(StrictBaseModel):
    success: bool = True
    message: str | None = None


class FileResponseBody(StrictBaseModel):
    success: bool = True
    message: str | None = None
    data: dict[str, Any] | None = None


class RotationConfig(StrictBaseModel):
    when: Literal['S', 'M', 'H', 'D', 'midnight', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6'] = 'midnight'
    backup_count: int = Field(default=14, ge=0)
    max_bytes: int = Field(default=0, ge=0)


class PayloadLimits(StrictBaseModel):
    max_body_chars: int = Field(default=10_000, gt=0)
    mask_headers: list[str] = Field(default_factory=lambda: ['Access-Token'])


class AmountRange(StrictBaseModel):
    min: int = Field(ge=0)
    max: int = Field(gt=0)

    @model_validator(mode='after')
    def validate_range(self) -> 'AmountRange':
        if self.max < self.min:
            raise ValueError('max must be greater than or equal to min')
        return self


class AmountComparator(StrictBaseModel):
    gte: int | None = Field(default=None, ge=0)
    lte: int | None = Field(default=None, ge=0)
    gt: int | None = Field(default=None, ge=0)
    lt: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def validate_bounds(self) -> 'AmountComparator':
        if all(value is None for value in (self.gte, self.lte, self.gt, self.lt)):
            raise ValueError('amount comparator must contain at least one boundary')
        lower = self.gt if self.gt is not None else self.gte
        upper = self.lt if self.lt is not None else self.lte
        if lower is not None and upper is not None and lower >= upper:
            raise ValueError('lower boundary must be smaller than upper boundary')
        return self


class ExternalIdPattern(StrictBaseModel):
    pattern: str = Field(min_length=1)

