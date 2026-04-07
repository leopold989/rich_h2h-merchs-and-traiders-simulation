from __future__ import annotations

import asyncio
import random
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import httpx
from fastapi import Request, UploadFile

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.logging_setup import ChannelLoggerRegistry, log_event
from rich_h2h_simulator.models.trader import (
    OperationBehaviorConfig,
    RequisiteConfig,
    ResponseProfileConfig,
    RoutingMatchConfig,
    RoutingRuleConfig,
    TraderConfigEntry,
    TraderDefaultsConfig,
)

TransportFactory = Callable[[str], httpx.AsyncBaseTransport | None]

_CREATE_RE = re.compile(r'^/order$')
_SHOW_BY_ID_RE = re.compile(r'^/order/(?P<order_id>[^/]+)$')
_SHOW_BY_EXTERNAL_RE = re.compile(r'^/order/(?P<merchant_id>[^/]+)/(?P<external_id>[^/]+)$')
_CANCEL_RE = re.compile(r'^/order/(?P<order_id>[^/]+)/cancel$')
_CONFIRM_RE = re.compile(r'^/order/(?P<order_id>[^/]+)/confirm-client$')
_ADD_RECEIPT_RE = re.compile(r'^/order/(?P<order_id>[^/]+)/add-receipt$')
_DISPUTE_RE = re.compile(r'^/order/(?P<order_id>[^/]+)/dispute$')


_OPERATION_PROFILE_ATTR = {
    'cancel': 'cancel_order',
    'confirm_client': 'confirm_client',
    'add_receipt': 'add_receipt',
    'open_dispute': 'open_dispute',
}

@dataclass(slots=True, frozen=True)
class ResolvedTrader:
    defaults: TraderDefaultsConfig
    trader: TraderConfigEntry
    response_profiles: dict[str, ResponseProfileConfig]
    api_root: str


@dataclass(slots=True)
class TraderOrderRecord:
    provider_order_id: str
    trader_alias: str
    merchant_id: str
    external_id: str
    amount: int
    payment_gateway: str | None
    currency: str | None
    payment_detail_type: str | None
    is_transgran: bool
    callback_url: str | None
    response_profile_id: str
    matched_rule_id: str | None
    requisite_id: str | None
    payment_detail: dict[str, Any] | None
    create_mode: str
    create_status_code: int
    create_response_body: dict[str, Any]
    status: str
    sub_status: str | None
    request_payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    cancel_attempts: int = 0
    confirm_attempts: int = 0
    add_receipt_attempts: int = 0
    dispute_attempts: int = 0
    callback_attempts: int = 0
    last_callback_at: datetime | None = None
    last_receipt_excerpt: Any = None
    last_dispute_excerpt: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'provider_order_id': self.provider_order_id,
            'trader_alias': self.trader_alias,
            'merchant_id': self.merchant_id,
            'external_id': self.external_id,
            'amount': self.amount,
            'payment_gateway': self.payment_gateway,
            'currency': self.currency,
            'payment_detail_type': self.payment_detail_type,
            'is_transgran': self.is_transgran,
            'callback_url': self.callback_url,
            'response_profile_id': self.response_profile_id,
            'matched_rule_id': self.matched_rule_id,
            'requisite_id': self.requisite_id,
            'payment_detail': self.payment_detail,
            'create_mode': self.create_mode,
            'create_status_code': self.create_status_code,
            'status': self.status,
            'sub_status': self.sub_status,
            'request_payload': self.request_payload,
            'created_at': _iso(self.created_at),
            'updated_at': _iso(self.updated_at),
            'cancel_attempts': self.cancel_attempts,
            'confirm_attempts': self.confirm_attempts,
            'add_receipt_attempts': self.add_receipt_attempts,
            'dispute_attempts': self.dispute_attempts,
            'callback_attempts': self.callback_attempts,
            'last_callback_at': _iso(self.last_callback_at),
            'last_receipt_excerpt': self.last_receipt_excerpt,
            'last_dispute_excerpt': self.last_dispute_excerpt,
        }


@dataclass(slots=True)
class TraderStats:
    trader_alias: str
    started_at: datetime
    inbound_requests_total: int = 0
    create_total: int = 0
    success_total: int = 0
    rejected_total: int = 0
    http_error_total: int = 0
    timeout_total: int = 0
    canceled_total: int = 0
    confirm_total: int = 0
    add_receipt_total: int = 0
    dispute_total: int = 0
    callbacks_sent_total: int = 0
    last_error: str | None = None
    status: str = 'starting'

    def to_dict(self) -> dict[str, Any]:
        return {
            'trader_alias': self.trader_alias,
            'started_at': _iso(self.started_at),
            'inbound_requests_total': self.inbound_requests_total,
            'create_total': self.create_total,
            'success_total': self.success_total,
            'rejected_total': self.rejected_total,
            'http_error_total': self.http_error_total,
            'timeout_total': self.timeout_total,
            'canceled_total': self.canceled_total,
            'confirm_total': self.confirm_total,
            'add_receipt_total': self.add_receipt_total,
            'dispute_total': self.dispute_total,
            'callbacks_sent_total': self.callbacks_sent_total,
            'last_error': self.last_error,
            'status': self.status,
        }


@dataclass(slots=True)
class TraderHttpResult:
    status_code: int
    body: dict[str, Any]


class TraderRunner:
    def __init__(
        self,
        config_manager: ConfigManager,
        logger_registry: ChannelLoggerRegistry,
        *,
        callback_transport_factory: TransportFactory | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.logger_registry = logger_registry
        self.callback_transport_factory = callback_transport_factory
        self._trader_digest: str | None = None
        self._resolved_by_alias: dict[str, ResolvedTrader] = {}
        self._resolved_prefixes: list[tuple[str, ResolvedTrader]] = []
        self._stats_by_alias: dict[str, TraderStats] = {}
        self._orders_by_id: dict[str, TraderOrderRecord] = {}
        self._orders_by_external: dict[tuple[str, str, str], str] = {}
        self._round_robin_counters: dict[tuple[str, str], int] = {}
        self._requisite_usage: dict[tuple[str, str, str], int] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def start(self) -> None:
        await self.reconfigure(force=True)
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name='trader-cleanup')
        log_event(self.logger_registry.get('system'), 'trader_runner_started', await self.get_runtime_summary())

    async def stop(self) -> None:
        tasks = list(self._background_tasks)
        if self._cleanup_task is not None:
            tasks.append(self._cleanup_task)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._background_tasks.clear()
        log_event(self.logger_registry.get('system'), 'trader_runner_stopped', await self.get_runtime_summary())

    async def reconfigure(self, *, force: bool = False) -> None:
        digest = self.config_manager.get_state_snapshot()['digests']['trader']
        if not force and digest == self._trader_digest:
            return
        self._trader_digest = digest
        bundle = self.config_manager.bundle
        profiles = {profile.id: profile for profile in bundle.trader.response_profiles if profile.active}
        self._resolved_by_alias.clear()
        self._resolved_prefixes.clear()
        now = datetime.now(UTC)
        for trader in bundle.trader.traders:
            if not trader.active:
                continue
            api_root = f"{trader.base_path.rstrip('/')}{bundle.trader.defaults.api_prefix}"
            resolved = ResolvedTrader(
                defaults=bundle.trader.defaults,
                trader=trader,
                response_profiles=profiles,
                api_root=api_root,
            )
            self._resolved_by_alias[trader.alias] = resolved
            self._resolved_prefixes.append((api_root, resolved))
            stats = self._stats_by_alias.get(trader.alias)
            if stats is None:
                self._stats_by_alias[trader.alias] = TraderStats(trader_alias=trader.alias, started_at=now, status='ready')
            else:
                stats.status = 'ready'
        active_aliases = set(self._resolved_by_alias)
        for alias, stats in self._stats_by_alias.items():
            if alias not in active_aliases:
                stats.status = 'inactive'
        self._resolved_prefixes.sort(key=lambda item: len(item[0]), reverse=True)
        log_event(
            self.logger_registry.get('system'),
            'trader_runner_reconfigured',
            {
                'active_traders': sorted(active_aliases),
                'prefixes': [prefix for prefix, _ in self._resolved_prefixes],
            },
        )

    def matches_path(self, path: str) -> bool:
        return any(path == prefix or path.startswith(prefix + '/') for prefix, _ in self._resolved_prefixes)

    async def handle_request(self, method: str, path: str, headers: dict[str, str], request: Request) -> TraderHttpResult | None:
        resolved, subpath = self._resolve_path(path)
        if resolved is None:
            return None
        stats = self._stats_by_alias[resolved.trader.alias]
        stats.inbound_requests_total += 1
        log_event(
            self.logger_registry.get('trader_inbound'),
            'trader_request_received',
            {
                'trader_alias': resolved.trader.alias,
                'method': method,
                'path': path,
                'subpath': subpath,
            },
        )

        if method == 'POST' and _CREATE_RE.fullmatch(subpath):
            return await self._handle_create_order(resolved, headers, request, path)
        if method == 'GET':
            matched = _SHOW_BY_ID_RE.fullmatch(subpath)
            if matched:
                return self._handle_show_by_id(resolved, headers, matched.group('order_id'), path)
            matched = _SHOW_BY_EXTERNAL_RE.fullmatch(subpath)
            if matched:
                return self._handle_show_by_external(
                    resolved,
                    headers,
                    matched.group('merchant_id'),
                    matched.group('external_id'),
                    path,
                )
        if method == 'PATCH':
            matched = _CANCEL_RE.fullmatch(subpath)
            if matched:
                return await self._handle_operation(
                    resolved,
                    headers,
                    matched.group('order_id'),
                    path,
                    operation='cancel',
                )
            matched = _CONFIRM_RE.fullmatch(subpath)
            if matched:
                return await self._handle_operation(
                    resolved,
                    headers,
                    matched.group('order_id'),
                    path,
                    operation='confirm_client',
                )
        if method == 'POST':
            matched = _ADD_RECEIPT_RE.fullmatch(subpath)
            if matched:
                return await self._handle_operation(
                    resolved,
                    headers,
                    matched.group('order_id'),
                    path,
                    operation='add_receipt',
                    request=request,
                )
            matched = _DISPUTE_RE.fullmatch(subpath)
            if matched:
                return await self._handle_operation(
                    resolved,
                    headers,
                    matched.group('order_id'),
                    path,
                    operation='open_dispute',
                    request=request,
                )
        return TraderHttpResult(status_code=404, body={'success': False, 'message': 'unknown trader endpoint'})

    async def get_runtime_summary(self) -> dict[str, Any]:
        return {
            'active_traders': sorted(self._resolved_by_alias),
            'orders_count': len(self._orders_by_id),
            'background_tasks': len(self._background_tasks),
            'traders': {alias: stats.to_dict() for alias, stats in self._stats_by_alias.items()},
            'orders': {order_id: record.to_dict() for order_id, record in self._orders_by_id.items()},
        }

    def _resolve_path(self, path: str) -> tuple[ResolvedTrader | None, str]:
        for prefix, resolved in self._resolved_prefixes:
            if path == prefix:
                return resolved, '/'
            if path.startswith(prefix + '/'):
                return resolved, path[len(prefix) :]
        return None, ''

    async def _handle_create_order(
        self,
        resolved: ResolvedTrader,
        headers: dict[str, str],
        request: Request,
        path: str,
    ) -> TraderHttpResult:
        auth_error = self._authorize(resolved, headers)
        if auth_error is not None:
            return auth_error
        try:
            payload = await self._read_payload(request)
        except ValueError as exc:
            return TraderHttpResult(status_code=400, body={'success': False, 'message': str(exc)})
        if not isinstance(payload, dict):
            return TraderHttpResult(status_code=400, body={'success': False, 'message': 'request body must be object'})
        error = self._validate_create_payload(payload)
        if error is not None:
            return error

        merchant_id = str(payload['merchant_id'])
        if resolved.trader.auth.validate_merchant_id and merchant_id != str(resolved.trader.auth.merchant_id):
            return TraderHttpResult(status_code=403, body={'success': False, 'message': 'invalid merchant_id'})

        external_id = str(payload['external_id'])
        idempotency_key = (resolved.trader.alias, merchant_id, external_id)
        existing_order_id = self._orders_by_external.get(idempotency_key)
        if existing_order_id is not None:
            existing = self._orders_by_id[existing_order_id]
            self._log_response(path, resolved.trader.alias, existing.create_status_code, existing.create_response_body)
            return TraderHttpResult(status_code=existing.create_status_code, body=existing.create_response_body)

        amount = int(payload['amount'])
        payment_gateway = _optional_str(payload.get('payment_gateway'))
        currency = _optional_str(payload.get('currency'))
        payment_detail_type = _optional_str(payload.get('payment_detail_type'))
        is_transgran = _extract_transgran(payload)
        callback_url = _optional_str(payload.get('callback_url'))

        matched_rule = self._match_rule(resolved, payload)
        profile_id = matched_rule.response_profile_id if matched_rule else resolved.trader.default_response_profile_id
        profile = resolved.response_profiles[profile_id]
        behavior = profile.create_order
        stats = self._stats_by_alias[resolved.trader.alias]
        stats.create_total += 1

        candidates = self._select_candidate_requisites(
            resolved,
            matched_rule,
            amount=amount,
            payment_gateway=payment_gateway,
            payment_detail_type=payment_detail_type,
            is_transgran=is_transgran,
        )
        selected = self._pick_requisite(resolved, matched_rule, candidates)

        if behavior.delay_ms > 0:
            await asyncio.sleep(behavior.delay_ms / 1000)

        if behavior.mode == 'success' and selected is None:
            # В конфиге могли выбрать success profile, но по факту не осталось подходящих реквизитов.
            body = {'success': False, 'message': 'No requisites available'}
            record = self._new_order_record(
                resolved=resolved,
                merchant_id=merchant_id,
                external_id=external_id,
                amount=amount,
                payment_gateway=payment_gateway,
                currency=currency,
                payment_detail_type=payment_detail_type,
                is_transgran=is_transgran,
                callback_url=callback_url,
                response_profile_id=profile_id,
                matched_rule_id=matched_rule.id if matched_rule else None,
                requisite=None,
                create_mode='business_reject',
                create_status_code=200,
                create_response_body=body,
                status='failed',
                sub_status='no_requisites',
                request_payload=payload,
            )
            self._store_order(record)
            stats.rejected_total += 1
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, 200, body)
            return TraderHttpResult(status_code=200, body=body)

        if behavior.mode == 'success':
            record = self._new_order_record(
                resolved=resolved,
                merchant_id=merchant_id,
                external_id=external_id,
                amount=amount,
                payment_gateway=payment_gateway or (selected.payment_gateway if selected else None),
                currency=currency,
                payment_detail_type=payment_detail_type or (selected.detail_type if selected else None),
                is_transgran=is_transgran,
                callback_url=callback_url,
                response_profile_id=profile_id,
                matched_rule_id=matched_rule.id if matched_rule else None,
                requisite=selected,
                create_mode='success',
                create_status_code=behavior.status_code or 200,
                create_response_body={},
                status='pending',
                sub_status='requisites_assigned',
                request_payload=payload,
            )
            body = behavior.body or _build_order_body(record)
            record.create_response_body = body
            self._store_order(record)
            self._mark_requisite_usage(record)
            stats.success_total += 1
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, record.create_status_code, body)
            return TraderHttpResult(status_code=record.create_status_code, body=body)

        if behavior.mode == 'business_reject':
            body = behavior.body or {'success': False, 'message': 'No requisites available'}
            record = self._new_order_record(
                resolved=resolved,
                merchant_id=merchant_id,
                external_id=external_id,
                amount=amount,
                payment_gateway=payment_gateway,
                currency=currency,
                payment_detail_type=payment_detail_type,
                is_transgran=is_transgran,
                callback_url=callback_url,
                response_profile_id=profile_id,
                matched_rule_id=matched_rule.id if matched_rule else None,
                requisite=selected,
                create_mode='business_reject',
                create_status_code=behavior.status_code or 200,
                create_response_body=body,
                status='failed',
                sub_status='no_requisites',
                request_payload=payload,
            )
            self._store_order(record)
            stats.rejected_total += 1
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, record.create_status_code, body)
            return TraderHttpResult(status_code=record.create_status_code, body=body)

        if behavior.mode == 'http_error':
            body = behavior.body or {'success': False, 'message': 'Simulated provider error'}
            record = self._new_order_record(
                resolved=resolved,
                merchant_id=merchant_id,
                external_id=external_id,
                amount=amount,
                payment_gateway=payment_gateway,
                currency=currency,
                payment_detail_type=payment_detail_type,
                is_transgran=is_transgran,
                callback_url=callback_url,
                response_profile_id=profile_id,
                matched_rule_id=matched_rule.id if matched_rule else None,
                requisite=None,
                create_mode='http_error',
                create_status_code=behavior.status_code or 500,
                create_response_body=body,
                status='failed',
                sub_status='http_error',
                request_payload=payload,
            )
            self._store_order(record)
            stats.http_error_total += 1
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, record.create_status_code, body)
            return TraderHttpResult(status_code=record.create_status_code, body=body)

        body = {'success': False, 'message': 'Simulated provider timeout'}
        record = self._new_order_record(
            resolved=resolved,
            merchant_id=merchant_id,
            external_id=external_id,
            amount=amount,
            payment_gateway=payment_gateway,
            currency=currency,
            payment_detail_type=payment_detail_type,
            is_transgran=is_transgran,
            callback_url=callback_url,
            response_profile_id=profile_id,
            matched_rule_id=matched_rule.id if matched_rule else None,
            requisite=None,
            create_mode='timeout',
            create_status_code=504,
            create_response_body=body,
            status='failed',
            sub_status='timeout',
            request_payload=payload,
        )
        self._store_order(record)
        stats.timeout_total += 1
        await self._maybe_schedule_callback(record, behavior)
        self._log_response(path, resolved.trader.alias, 504, body)
        return TraderHttpResult(status_code=504, body=body)

    def _handle_show_by_id(
        self,
        resolved: ResolvedTrader,
        headers: dict[str, str],
        order_id: str,
        path: str,
    ) -> TraderHttpResult:
        auth_error = self._authorize(resolved, headers)
        if auth_error is not None:
            return auth_error
        record = self._orders_by_id.get(order_id)
        if record is None or record.trader_alias != resolved.trader.alias:
            return TraderHttpResult(status_code=404, body={'success': False, 'message': 'order not found'})
        body = _build_order_body(record)
        self._log_response(path, resolved.trader.alias, 200, body)
        return TraderHttpResult(status_code=200, body=body)

    def _handle_show_by_external(
        self,
        resolved: ResolvedTrader,
        headers: dict[str, str],
        merchant_id: str,
        external_id: str,
        path: str,
    ) -> TraderHttpResult:
        auth_error = self._authorize(resolved, headers)
        if auth_error is not None:
            return auth_error
        if resolved.trader.auth.validate_merchant_id and merchant_id != str(resolved.trader.auth.merchant_id):
            return TraderHttpResult(status_code=403, body={'success': False, 'message': 'invalid merchant_id'})
        order_id = self._orders_by_external.get((resolved.trader.alias, merchant_id, external_id))
        if order_id is None:
            return TraderHttpResult(status_code=404, body={'success': False, 'message': 'order not found'})
        body = _build_order_body(self._orders_by_id[order_id])
        self._log_response(path, resolved.trader.alias, 200, body)
        return TraderHttpResult(status_code=200, body=body)

    async def _handle_operation(
        self,
        resolved: ResolvedTrader,
        headers: dict[str, str],
        order_id: str,
        path: str,
        *,
        operation: str,
        request: Request | None = None,
    ) -> TraderHttpResult:
        auth_error = self._authorize(resolved, headers)
        if auth_error is not None:
            return auth_error
        record = self._orders_by_id.get(order_id)
        if record is None or record.trader_alias != resolved.trader.alias:
            return TraderHttpResult(status_code=404, body={'success': False, 'message': 'order not found'})
        profile = resolved.response_profiles[record.response_profile_id]
        behavior = getattr(profile, _OPERATION_PROFILE_ATTR[operation])

        payload: Any = None
        if request is not None:
            try:
                payload = await self._read_payload(request)
            except ValueError as exc:
                return TraderHttpResult(status_code=400, body={'success': False, 'message': str(exc)})

        if behavior.delay_ms > 0:
            await asyncio.sleep(behavior.delay_ms / 1000)

        stats = self._stats_by_alias[resolved.trader.alias]
        record.updated_at = datetime.now(UTC)
        if operation == 'cancel':
            record.cancel_attempts += 1
        elif operation == 'confirm_client':
            record.confirm_attempts += 1
        elif operation == 'add_receipt':
            record.add_receipt_attempts += 1
            record.last_receipt_excerpt = _excerpt_payload(payload)
        elif operation == 'open_dispute':
            record.dispute_attempts += 1
            record.last_dispute_excerpt = _excerpt_payload(payload)

        if behavior.mode == 'success':
            if operation == 'cancel':
                record.status = 'failed'
                record.sub_status = 'canceled'
                stats.canceled_total += 1
            elif operation == 'confirm_client':
                record.status = 'pending'
                record.sub_status = 'confirmed_by_client'
                stats.confirm_total += 1
            elif operation == 'add_receipt':
                record.status = 'pending'
                record.sub_status = 'receipt_attached'
                stats.add_receipt_total += 1
            elif operation == 'open_dispute':
                record.status = 'pending'
                record.sub_status = 'in_dispute'
                stats.dispute_total += 1
            body = behavior.body or _build_order_body(record)
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, behavior.status_code or 200, body)
            return TraderHttpResult(status_code=behavior.status_code or 200, body=body)

        if behavior.mode == 'business_reject':
            body = behavior.body or {'success': False, 'message': f'{operation} rejected'}
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, behavior.status_code or 200, body)
            return TraderHttpResult(status_code=behavior.status_code or 200, body=body)

        if behavior.mode == 'http_error':
            body = behavior.body or {'success': False, 'message': 'Simulated provider error'}
            stats.http_error_total += 1
            await self._maybe_schedule_callback(record, behavior)
            self._log_response(path, resolved.trader.alias, behavior.status_code or 500, body)
            return TraderHttpResult(status_code=behavior.status_code or 500, body=body)

        body = {'success': False, 'message': 'Simulated provider timeout'}
        stats.timeout_total += 1
        await self._maybe_schedule_callback(record, behavior)
        self._log_response(path, resolved.trader.alias, 504, body)
        return TraderHttpResult(status_code=504, body=body)

    async def _maybe_schedule_callback(self, record: TraderOrderRecord, behavior: OperationBehaviorConfig) -> None:
        callback = behavior.callback
        if callback is None or not callback.enabled or record.callback_url is None:
            return
        payload = self._prepare_callback_payload(record, callback.payload or {})
        task = asyncio.create_task(
            self._send_callback(record, payload, after_ms=callback.after_ms),
            name=f'trader-callback:{record.trader_alias}:{record.provider_order_id}:{record.callback_attempts + 1}',
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _prepare_callback_payload(self, record: TraderOrderRecord, configured_payload: dict[str, Any]) -> dict[str, Any]:
        base = {
            'success': True,
            'data': {
                'order_id': record.provider_order_id,
                'provider_order_id': record.provider_order_id,
                'external_id': record.external_id,
                'merchant_id': record.merchant_id,
                'status': record.status,
                'sub_status': record.sub_status,
                'payment_detail': record.payment_detail,
                'method': record.payment_gateway,
                'payment_gateway': record.payment_gateway,
                'payment_gateway_code': record.payment_gateway,
            },
        }
        return _deep_merge(base, configured_payload)

    async def _send_callback(self, record: TraderOrderRecord, payload: dict[str, Any], *, after_ms: int) -> None:
        if after_ms > 0:
            await asyncio.sleep(after_ms / 1000)
        callback_cfg = self.config_manager.bundle.trader.defaults.callback_client
        headers = dict(callback_cfg.headers)
        headers.setdefault('Content-Type', 'application/json')
        transport = self.callback_transport_factory(record.callback_url) if self.callback_transport_factory else None
        record.callback_attempts += 1
        record.last_callback_at = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(
                timeout=callback_cfg.timeout_ms / 1000,
                verify=callback_cfg.verify_ssl,
                transport=transport,
                follow_redirects=True,
            ) as client:
                response = await client.post(record.callback_url, json=payload, headers=headers)
            self._stats_by_alias[record.trader_alias].callbacks_sent_total += 1
            self._log_callback_sent(record, payload, response.status_code)
        except Exception as exc:  # noqa: BLE001
            self._stats_by_alias[record.trader_alias].last_error = str(exc)
            log_event(
                self.logger_registry.get('trader_outbound'),
                'trader_callback_failed',
                {
                    'trader_alias': record.trader_alias,
                    'provider_order_id': record.provider_order_id,
                    'callback_url': record.callback_url,
                    'error': str(exc),
                    'payload': payload,
                },
            )

    def _log_callback_sent(self, record: TraderOrderRecord, payload: dict[str, Any], status_code: int) -> None:
        log_event(
            self.logger_registry.get('trader_outbound'),
            'trader_callback_sent',
            {
                'trader_alias': record.trader_alias,
                'provider_order_id': record.provider_order_id,
                'callback_url': record.callback_url,
                'status_code': status_code,
                'payload': payload,
            },
        )

    def _new_order_record(
        self,
        *,
        resolved: ResolvedTrader,
        merchant_id: str,
        external_id: str,
        amount: int,
        payment_gateway: str | None,
        currency: str | None,
        payment_detail_type: str | None,
        is_transgran: bool,
        callback_url: str | None,
        response_profile_id: str,
        matched_rule_id: str | None,
        requisite: RequisiteConfig | None,
        create_mode: str,
        create_status_code: int,
        create_response_body: dict[str, Any],
        status: str,
        sub_status: str | None,
        request_payload: dict[str, Any],
    ) -> TraderOrderRecord:
        now = datetime.now(UTC)
        return TraderOrderRecord(
            provider_order_id=str(uuid4()),
            trader_alias=resolved.trader.alias,
            merchant_id=merchant_id,
            external_id=external_id,
            amount=amount,
            payment_gateway=payment_gateway,
            currency=currency,
            payment_detail_type=payment_detail_type,
            is_transgran=is_transgran,
            callback_url=callback_url,
            response_profile_id=response_profile_id,
            matched_rule_id=matched_rule_id,
            requisite_id=requisite.id if requisite else None,
            payment_detail=_payment_detail_payload(requisite) if requisite else None,
            create_mode=create_mode,
            create_status_code=create_status_code,
            create_response_body=create_response_body,
            status=status,
            sub_status=sub_status,
            request_payload=request_payload,
            created_at=now,
            updated_at=now,
        )

    def _authorize(self, resolved: ResolvedTrader, headers: dict[str, str]) -> TraderHttpResult | None:
        validate_token = resolved.trader.auth.validate_access_token and resolved.defaults.validate_access_token
        if not validate_token:
            return None
        token = headers.get('Access-Token') or headers.get('access-token')
        if token is None:
            return TraderHttpResult(status_code=401, body={'success': False, 'message': 'missing Access-Token header'})
        if token != resolved.trader.auth.access_token:
            return TraderHttpResult(status_code=403, body={'success': False, 'message': 'invalid Access-Token'})
        return None

    def _validate_create_payload(self, payload: dict[str, Any]) -> TraderHttpResult | None:
        missing = [field for field in ('external_id', 'amount', 'merchant_id') if field not in payload]
        if missing:
            return TraderHttpResult(status_code=422, body={'success': False, 'message': f'missing required fields: {missing}'})
        if payload.get('payment_gateway') and payload.get('currency'):
            return TraderHttpResult(
                status_code=422,
                body={'success': False, 'message': 'payment_gateway and currency are mutually exclusive'},
            )
        return None

    async def _read_payload(self, request: Request) -> Any:
        content_type = request.headers.get('content-type', '').lower()
        if 'application/json' in content_type:
            try:
                return await request.json()
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f'invalid JSON body: {exc}') from exc
        if 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
            form = await request.form()
            return _normalize_form(form)
        raw = await request.body()
        if not raw:
            return {}
        try:
            return raw.decode('utf-8')
        except Exception:  # noqa: BLE001
            return {'raw_body': raw.hex()}

    def _match_rule(self, resolved: ResolvedTrader, payload: dict[str, Any]) -> RoutingRuleConfig | None:
        for rule in resolved.trader.routing_rules:
            if not rule.active:
                continue
            if self._rule_matches(rule.match, payload):
                return rule
        return None

    def _rule_matches(self, match: RoutingMatchConfig, payload: dict[str, Any]) -> bool:
        if match.payment_gateway is not None and _optional_str(payload.get('payment_gateway')) != match.payment_gateway:
            return False
        if match.payment_detail_type is not None and _optional_str(payload.get('payment_detail_type')) != match.payment_detail_type:
            return False
        amount = int(payload.get('amount', 0))
        if match.amount is not None:
            if match.amount.gte is not None and amount < match.amount.gte:
                return False
            if match.amount.lte is not None and amount > match.amount.lte:
                return False
            if match.amount.gt is not None and amount <= match.amount.gt:
                return False
            if match.amount.lt is not None and amount >= match.amount.lt:
                return False
        is_transgran = _extract_transgran(payload)
        if match.is_transgran is not None and match.is_transgran != is_transgran:
            return False
        if match.transgran is not None and match.transgran != is_transgran:
            return False
        return True

    def _select_candidate_requisites(
        self,
        resolved: ResolvedTrader,
        matched_rule: RoutingRuleConfig | None,
        *,
        amount: int,
        payment_gateway: str | None,
        payment_detail_type: str | None,
        is_transgran: bool,
    ) -> list[RequisiteConfig]:
        requisites = [requisite for requisite in resolved.trader.requisites if requisite.active]
        if matched_rule is not None and matched_rule.requisite_pool:
            allowed = set(matched_rule.requisite_pool)
            requisites = [requisite for requisite in requisites if requisite.id in allowed]
        today = date.today().isoformat()
        filtered: list[RequisiteConfig] = []
        for requisite in requisites:
            if payment_gateway is not None and requisite.payment_gateway != payment_gateway:
                continue
            if payment_detail_type is not None and requisite.detail_type != payment_detail_type:
                continue
            if requisite.is_transgran != is_transgran:
                continue
            if amount < requisite.amount_range.min or amount > requisite.amount_range.max:
                continue
            if requisite.daily_limit is not None:
                used = self._requisite_usage.get((resolved.trader.alias, requisite.id, today), 0)
                if used >= requisite.daily_limit:
                    continue
            filtered.append(requisite)
        filtered.sort(key=lambda requisite: (-requisite.priority, requisite.id))
        return filtered

    def _pick_requisite(
        self,
        resolved: ResolvedTrader,
        matched_rule: RoutingRuleConfig | None,
        candidates: list[RequisiteConfig],
    ) -> RequisiteConfig | None:
        if not candidates:
            return None
        strategy = resolved.trader.selection_strategy or resolved.defaults.selection_strategy
        if strategy == 'first_match':
            return candidates[0]
        if strategy == 'random':
            return random.choice(candidates)
        scope = matched_rule.id if matched_rule is not None else '__default__'
        counter_key = (resolved.trader.alias, scope)
        idx = self._round_robin_counters.get(counter_key, 0) % len(candidates)
        self._round_robin_counters[counter_key] = idx + 1
        return candidates[idx]

    def _store_order(self, record: TraderOrderRecord) -> None:
        self._orders_by_id[record.provider_order_id] = record
        self._orders_by_external[(record.trader_alias, record.merchant_id, record.external_id)] = record.provider_order_id

    def _mark_requisite_usage(self, record: TraderOrderRecord) -> None:
        if record.requisite_id is None:
            return
        usage_key = (record.trader_alias, record.requisite_id, date.today().isoformat())
        self._requisite_usage[usage_key] = self._requisite_usage.get(usage_key, 0) + 1

    async def _cleanup_loop(self) -> None:
        while True:
            ttl = self.config_manager.bundle.system.runtime.order_state_ttl_sec
            await asyncio.sleep(max(1, min(ttl, 60)))
            cutoff = datetime.now(UTC) - timedelta(seconds=ttl)
            stale = [order_id for order_id, record in self._orders_by_id.items() if record.updated_at < cutoff]
            for order_id in stale:
                record = self._orders_by_id.pop(order_id)
                self._orders_by_external.pop((record.trader_alias, record.merchant_id, record.external_id), None)
            if stale:
                log_event(
                    self.logger_registry.get('system'),
                    'trader_cleanup_removed_orders',
                    {'removed_orders': stale, 'remaining_orders': len(self._orders_by_id)},
                )

    def _log_response(self, path: str, trader_alias: str, status_code: int, body: dict[str, Any]) -> None:
        log_event(
            self.logger_registry.get('trader_outbound'),
            'trader_response_sent',
            {
                'trader_alias': trader_alias,
                'path': path,
                'status_code': status_code,
                'body': body,
            },
        )


def _build_order_body(record: TraderOrderRecord) -> dict[str, Any]:
    data = {
        'order_id': record.provider_order_id,
        'provider_order_id': record.provider_order_id,
        'external_id': record.external_id,
        'merchant_id': record.merchant_id,
        'amount': record.amount,
        'status': record.status,
        'sub_status': record.sub_status,
        'payment_detail': record.payment_detail,
        'method': record.payment_gateway,
        'payment_gateway': record.payment_gateway,
        'payment_gateway_code': record.payment_gateway,
        'callback_url': record.callback_url,
        'created_at': int(record.created_at.timestamp()),
        'current_server_time': int(datetime.now(UTC).timestamp()),
    }
    return {'success': True, 'data': data}


def _payment_detail_payload(requisite: RequisiteConfig | None) -> dict[str, Any] | None:
    if requisite is None:
        return None
    return {
        'detail_type': requisite.detail_type,
        'detail': requisite.detail,
        'initials': requisite.initials,
        'bank_name': requisite.bank_name,
    }


def _extract_transgran(payload: dict[str, Any]) -> bool:
    if 'is_transgran' in payload:
        return bool(payload['is_transgran'])
    if 'transgran' in payload:
        return bool(payload['transgran'])
    return False


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_form(form: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in form.multi_items():
        if isinstance(value, UploadFile):
            normalized[key] = {
                'filename': value.filename,
                'content_type': value.content_type,
            }
        else:
            normalized[key] = value
    return normalized


def _excerpt_payload(payload: Any) -> Any:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    return str(payload)[:512]
