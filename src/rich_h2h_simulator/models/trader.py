from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from rich_h2h_simulator.models.common import AmountComparator, AmountRange, StrictBaseModel


class IdempotencyConfig(StrictBaseModel):
    key_fields: list[str] = Field(default_factory=lambda: ['merchant_id', 'external_id'], min_length=1)
    ttl_sec: int = Field(default=86_400, gt=0)


class CallbackClientConfig(StrictBaseModel):
    timeout_ms: int = Field(default=10_000, gt=0)
    verify_ssl: bool = False
    headers: dict[str, str] = Field(default_factory=lambda: {'Content-Type': 'application/json', 'Accept': 'application/json'})


class TraderDefaultsConfig(StrictBaseModel):
    driver: Literal['standard_h2h'] = 'standard_h2h'
    api_prefix: str = Field(default='/api/h2h', pattern=r'^/.*')
    validate_access_token: bool = True
    validate_merchant_id: bool = True
    selection_strategy: Literal['first_match', 'round_robin', 'random'] = 'first_match'
    idempotency: IdempotencyConfig = Field(default_factory=IdempotencyConfig)
    callback_client: CallbackClientConfig = Field(default_factory=CallbackClientConfig)


class OperationCallbackConfig(StrictBaseModel):
    enabled: bool = False
    after_ms: int = Field(default=0, ge=0)
    payload: dict[str, Any] | None = None

    @model_validator(mode='after')
    def validate_payload(self) -> 'OperationCallbackConfig':
        if self.enabled and self.payload is None:
            raise ValueError('payload is required when callback.enabled=true')
        return self


class OperationBehaviorConfig(StrictBaseModel):
    mode: Literal['success', 'business_reject', 'timeout', 'http_error']
    delay_ms: int = Field(default=0, ge=0)
    status_code: int | None = Field(default=None, ge=100, le=599)
    body: dict[str, Any] | None = None
    callback: OperationCallbackConfig | None = None

    @model_validator(mode='after')
    def defaults(self) -> 'OperationBehaviorConfig':
        if self.mode == 'timeout' and self.status_code is not None:
            raise ValueError('status_code must be omitted for timeout mode')
        if self.mode == 'success' and self.status_code is None:
            self.status_code = 200
        if self.mode == 'business_reject' and self.status_code is None:
            self.status_code = 200
        if self.mode == 'http_error' and self.status_code is None:
            self.status_code = 500
        return self


class ResponseProfileConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    create_order: OperationBehaviorConfig
    cancel_order: OperationBehaviorConfig
    confirm_client: OperationBehaviorConfig
    add_receipt: OperationBehaviorConfig
    open_dispute: OperationBehaviorConfig


class TraderAuthConfig(StrictBaseModel):
    access_token: str = Field(min_length=1)
    merchant_id: UUID
    validate_access_token: bool = True
    validate_merchant_id: bool = True


class RoutingMatchConfig(StrictBaseModel):
    payment_gateway: str | None = None
    payment_detail_type: str | None = None
    amount: AmountComparator | None = None
    is_transgran: bool | None = None
    transgran: bool | None = None

    @model_validator(mode='after')
    def at_least_one_condition(self) -> 'RoutingMatchConfig':
        if all(
            value is None
            for value in (
                self.payment_gateway,
                self.payment_detail_type,
                self.amount,
                self.is_transgran,
                self.transgran,
            )
        ):
            raise ValueError('routing match must contain at least one condition')
        return self


class RoutingRuleConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    match: RoutingMatchConfig
    requisite_pool: list[str] = Field(default_factory=list)
    response_profile_id: str = Field(min_length=1)


class RequisiteConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    payment_gateway: str = Field(min_length=1)
    detail_type: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    initials: str = Field(min_length=1)
    bank_name: str = Field(min_length=1)
    amount_range: AmountRange
    is_transgran: bool = False
    priority: int = 0
    daily_limit: int | None = Field(default=None, ge=0)


class TraderConfigEntry(StrictBaseModel):
    alias: str = Field(min_length=1)
    active: bool = True
    base_path: str = Field(pattern=r'^/.*')
    driver: Literal['standard_h2h'] = 'standard_h2h'
    auth: TraderAuthConfig
    selection_strategy: Literal['first_match', 'round_robin', 'random'] = 'first_match'
    default_response_profile_id: str = Field(min_length=1)
    routing_rules: list[RoutingRuleConfig] = Field(default_factory=list)
    requisites: list[RequisiteConfig] = Field(default_factory=list)


class TraderConfig(StrictBaseModel):
    schema_version: int = Field(default=1, ge=1)
    defaults: TraderDefaultsConfig
    response_profiles: list[ResponseProfileConfig] = Field(default_factory=list)
    traders: list[TraderConfigEntry] = Field(default_factory=list)
