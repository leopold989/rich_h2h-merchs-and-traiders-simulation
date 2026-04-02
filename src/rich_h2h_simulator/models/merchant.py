from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from rich_h2h_simulator.models.common import ExternalIdPattern, StrictBaseModel


class PollAfterCreateConfig(StrictBaseModel):
    enabled: bool = True
    delay_ms: int = Field(default=2_000, ge=0)
    attempts: int = Field(default=3, ge=0)
    interval_ms: int = Field(default=5_000, ge=0)


class CallbackResponseConfig(StrictBaseModel):
    status_code: int = Field(default=200, ge=100, le=599)
    body: dict[str, Any] = Field(default_factory=lambda: {'success': True, 'message': 'accepted'})


class ExternalIdDefaultsConfig(StrictBaseModel):
    mode: Literal['pattern'] = 'pattern'
    pattern: str = Field(min_length=1)


class MerchantDefaultsConfig(StrictBaseModel):
    request_timeout_ms: int = Field(default=10_000, gt=0)
    poll_after_create: PollAfterCreateConfig = Field(default_factory=PollAfterCreateConfig)
    callback_response: CallbackResponseConfig = Field(default_factory=CallbackResponseConfig)
    external_id: ExternalIdDefaultsConfig


class ReceiptConfig(StrictBaseModel):
    kind: Literal['file', 'url', 'base64']
    path: str | None = None
    url: HttpUrl | None = None
    payload: str | None = None

    @model_validator(mode='after')
    def validate_payload(self) -> 'ReceiptConfig':
        if self.kind == 'file' and not self.path:
            raise ValueError('path is required when kind=file')
        if self.kind == 'url' and not self.url:
            raise ValueError('url is required when kind=url')
        if self.kind == 'base64' and not self.payload:
            raise ValueError('payload is required when kind=base64')
        return self


class TemplateRequestConfig(StrictBaseModel):
    amount: int = Field(gt=0)
    payment_gateway: str | None = None
    currency: str | None = None
    payment_detail_type: str | None = None
    is_transgran: bool = False
    callback_url: HttpUrl | None = None

    @model_validator(mode='after')
    def validate_gateway_currency(self) -> 'TemplateRequestConfig':
        has_gateway = bool(self.payment_gateway)
        has_currency = bool(self.currency)
        if has_gateway and has_currency:
            raise ValueError('payment_gateway and currency are mutually exclusive')
        if not has_gateway and not has_currency:
            raise ValueError('either payment_gateway or currency must be provided')
        return self


class PostActionConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    type: Literal['cancel', 'confirm_client', 'add_receipt', 'dispute', 'finish']
    after_ms: int = Field(ge=0)
    if_order_status_in: list[str] = Field(default_factory=list)
    receipt: ReceiptConfig | None = None

    @model_validator(mode='after')
    def validate_action(self) -> 'PostActionConfig':
        if self.type in {'add_receipt', 'dispute'} and self.receipt is None:
            raise ValueError(f'receipt must be defined for post action type {self.type}')
        return self


class RequestTemplateConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    description: str | None = None
    request: TemplateRequestConfig
    post_actions: list[PostActionConfig] = Field(default_factory=list)


class MerchantTargetConfig(StrictBaseModel):
    base_url: HttpUrl
    api_prefix: str = Field(default='/api/h2h', pattern=r'^/.*')
    verify_ssl: bool = False
    timeout_ms: int = Field(default=10_000, gt=0)


class MerchantCallbackConfig(StrictBaseModel):
    enabled: bool = True
    path: str = Field(pattern=r'^/.*')
    validate_access_token: bool = True
    response_status_code: int = Field(default=200, ge=100, le=599)
    response_body: dict[str, Any] = Field(default_factory=lambda: {'success': True, 'message': 'callback accepted'})


class MerchantConfigEntry(StrictBaseModel):
    alias: str = Field(min_length=1)
    active: bool = True
    merchant_id: UUID
    access_token: str = Field(min_length=1)
    target: MerchantTargetConfig
    callback: MerchantCallbackConfig
    default_headers: dict[str, str] = Field(default_factory=dict)


class JobScheduleConfig(StrictBaseModel):
    start_delay_sec: int = Field(default=0, ge=0)
    interval_sec: int = Field(gt=0)
    requests_total: int = Field(gt=0)
    jitter_sec: int = Field(default=0, ge=0)
    max_inflight: int = Field(default=1, gt=0)


class MerchantJobConfig(StrictBaseModel):
    id: str = Field(min_length=1)
    active: bool = True
    merchant_alias: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    schedule: JobScheduleConfig
    external_id: ExternalIdPattern


class MerchantConfig(StrictBaseModel):
    schema_version: int = Field(default=1, ge=1)
    defaults: MerchantDefaultsConfig
    request_templates: list[RequestTemplateConfig] = Field(default_factory=list)
    merchants: list[MerchantConfigEntry] = Field(default_factory=list)
    merchant_jobs: list[MerchantJobConfig] = Field(default_factory=list)
