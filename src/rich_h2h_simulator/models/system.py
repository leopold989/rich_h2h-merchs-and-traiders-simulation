from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from rich_h2h_simulator.models.common import PayloadLimits, RotationConfig, StrictBaseModel


class ServiceConfig(StrictBaseModel):
    name: str = Field(min_length=1)
    listen_host: str = '0.0.0.0'
    listen_port: int = Field(default=8099, ge=1, le=65535)
    public_base_url: HttpUrl
    timezone: str = 'Europe/Warsaw'
    config_reload_interval_sec: int = Field(default=5, ge=1)


class PlatformConfig(StrictBaseModel):
    base_url: HttpUrl
    verify_ssl: bool = False
    timeout_ms: int = Field(default=10_000, gt=0)
    api_prefix: str = Field(default='/api/h2h', pattern=r'^/.*')


class PathsConfig(StrictBaseModel):
    merchant_config: str = Field(min_length=1)
    trader_config: str = Field(min_length=1)
    fixtures_dir: str = Field(default='./fixtures', min_length=1)
    log_dir: str = Field(default='./logs', min_length=1)


class RedisConfig(StrictBaseModel):
    enabled: bool = False
    url: str = 'redis://redis:6379/0'


class RuntimeConfig(StrictBaseModel):
    state_backend: Literal['memory', 'redis'] = 'memory'
    idempotency_ttl_sec: int = Field(default=86_400, gt=0)
    order_state_ttl_sec: int = Field(default=604_800, gt=0)
    redis: RedisConfig = Field(default_factory=RedisConfig)

    @model_validator(mode='after')
    def validate_backend(self) -> 'RuntimeConfig':
        if self.state_backend == 'redis' and not self.redis.enabled:
            raise ValueError('redis.enabled must be true when state_backend is redis')
        return self


class SafetyConfig(StrictBaseModel):
    enabled: bool = False
    mode: Literal['shared_dev', 'dedicated'] = 'shared_dev'
    max_active_jobs: int = Field(default=10, gt=0)
    max_total_inflight: int = Field(default=20, gt=0)
    max_requests_per_minute_estimate: int = Field(default=300, gt=0)


class LoggingChannels(StrictBaseModel):
    system: str = 'system.log'
    merchant_outbound: str = 'merchant_outbound.log'
    merchant_callbacks: str = 'merchant_callbacks.log'
    trader_inbound: str = 'trader_inbound.log'
    trader_outbound: str = 'trader_outbound.log'


class LoggingConfig(StrictBaseModel):
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    format: Literal['jsonl'] = 'jsonl'
    rotation: RotationConfig = Field(default_factory=RotationConfig)
    channels: LoggingChannels = Field(default_factory=LoggingChannels)
    payload_limits: PayloadLimits = Field(default_factory=PayloadLimits)


class ControlApiConfig(StrictBaseModel):
    enabled: bool = True
    prefix: str = Field(default='/_sim', pattern=r'^/.*')
    read_only_token: str = Field(min_length=1)
    write_token: str = Field(min_length=1)

    @model_validator(mode='after')
    def validate_tokens(self) -> 'ControlApiConfig':
        if self.read_only_token == self.write_token:
            raise ValueError('read_only_token and write_token must differ')
        return self


class SystemConfig(StrictBaseModel):
    schema_version: int = Field(default=1, ge=1)
    service: ServiceConfig
    platform: PlatformConfig
    paths: PathsConfig
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    control_api: ControlApiConfig
