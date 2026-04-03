from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class MerchantJobRuntime:
    job_id: str
    merchant_alias: str
    template_id: str
    active: bool = True
    started_at: str | None = None
    finished_at: str | None = None
    created_requests: int = 0
    create_success: int = 0
    create_failed: int = 0
    in_flight: int = 0
    last_external_id: str | None = None
    last_order_id: str | None = None
    last_error: str | None = None
    next_run_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'job_id': self.job_id,
            'merchant_alias': self.merchant_alias,
            'template_id': self.template_id,
            'active': self.active,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'created_requests': self.created_requests,
            'create_success': self.create_success,
            'create_failed': self.create_failed,
            'in_flight': self.in_flight,
            'last_external_id': self.last_external_id,
            'last_order_id': self.last_order_id,
            'last_error': self.last_error,
            'next_run_at': self.next_run_at,
        }


@dataclass(slots=True)
class MerchantOrderRuntime:
    internal_id: str
    job_id: str
    merchant_alias: str
    template_id: str
    external_id: str
    created_at: str
    request_payload: dict[str, Any]
    callback_path: str | None = None
    order_id: str | None = None
    provider_order_id: str | None = None
    status: str | None = None
    sub_status: str | None = None
    last_response_status_code: int | None = None
    last_response_body: Any = None
    create_ok: bool = False
    last_error: str | None = None
    callbacks_received: int = 0
    callback_history: list[dict[str, Any]] = field(default_factory=list)
    poll_history: list[dict[str, Any]] = field(default_factory=list)
    actions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'internal_id': self.internal_id,
            'job_id': self.job_id,
            'merchant_alias': self.merchant_alias,
            'template_id': self.template_id,
            'external_id': self.external_id,
            'created_at': self.created_at,
            'callback_path': self.callback_path,
            'order_id': self.order_id,
            'provider_order_id': self.provider_order_id,
            'status': self.status,
            'sub_status': self.sub_status,
            'last_response_status_code': self.last_response_status_code,
            'last_response_body': self.last_response_body,
            'create_ok': self.create_ok,
            'last_error': self.last_error,
            'callbacks_received': self.callbacks_received,
            'callback_history': list(self.callback_history),
            'poll_history': list(self.poll_history),
            'actions': self.actions.copy(),
        }


class MerchantRuntimeStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, MerchantJobRuntime] = {}
        self._orders: dict[str, MerchantOrderRuntime] = {}
        self._order_index_by_order_id: dict[str, str] = {}
        self._order_index_by_external_id: dict[str, str] = {}
        self._callback_paths: dict[str, str] = {}
        self._orphan_callbacks: list[dict[str, Any]] = []

    def reset_job_registry(self, callback_paths: dict[str, str]) -> None:
        self._callback_paths = callback_paths.copy()
        current_job_ids = set(self._jobs)
        if current_job_ids:
            for job in self._jobs.values():
                job.active = False
                job.next_run_at = None

    async def upsert_job(self, job_id: str, merchant_alias: str, template_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                job = MerchantJobRuntime(job_id=job_id, merchant_alias=merchant_alias, template_id=template_id)
                self._jobs[job_id] = job
            job.active = True
            job.merchant_alias = merchant_alias
            job.template_id = template_id
            if job.started_at is None:
                job.started_at = self._now_iso()

    async def mark_job_next_run(self, job_id: str, when_iso: str | None) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.next_run_at = when_iso

    async def mark_job_finished(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.active = False
                job.finished_at = self._now_iso()
                job.next_run_at = None

    async def inc_job_inflight(self, job_id: str, delta: int) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.in_flight = max(0, job.in_flight + delta)

    async def record_create_start(
        self,
        *,
        internal_id: str,
        job_id: str,
        merchant_alias: str,
        template_id: str,
        external_id: str,
        request_payload: dict[str, Any],
        callback_path: str | None,
    ) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.created_requests += 1
            job.last_external_id = external_id
            order = MerchantOrderRuntime(
                internal_id=internal_id,
                job_id=job_id,
                merchant_alias=merchant_alias,
                template_id=template_id,
                external_id=external_id,
                created_at=self._now_iso(),
                request_payload=request_payload,
                callback_path=callback_path,
            )
            self._orders[internal_id] = order
            self._order_index_by_external_id[external_id] = internal_id

    async def record_create_result(
        self,
        internal_id: str,
        *,
        ok: bool,
        status_code: int | None,
        response_body: Any,
        order_id: str | None,
        provider_order_id: str | None,
        status: str | None,
        sub_status: str | None,
        error: str | None,
    ) -> None:
        async with self._lock:
            order = self._orders[internal_id]
            job = self._jobs[order.job_id]
            order.create_ok = ok
            order.last_response_status_code = status_code
            order.last_response_body = response_body
            order.order_id = order_id or order.order_id
            order.provider_order_id = provider_order_id or order.provider_order_id
            order.status = status or order.status
            order.sub_status = sub_status or order.sub_status
            order.last_error = error
            if order.order_id:
                self._order_index_by_order_id[order.order_id] = internal_id
                job.last_order_id = order.order_id
            if ok:
                job.create_success += 1
            else:
                job.create_failed += 1
                job.last_error = error

    async def record_callback(
        self,
        *,
        path: str,
        merchant_alias: str | None,
        body: Any,
        access_token_ok: bool,
        matched_internal_id: str | None,
        headers: dict[str, str],
    ) -> None:
        event = {
            'received_at': self._now_iso(),
            'path': path,
            'merchant_alias': merchant_alias,
            'access_token_ok': access_token_ok,
            'matched_internal_id': matched_internal_id,
            'headers': headers,
            'body': body,
        }
        async with self._lock:
            if matched_internal_id is None:
                self._orphan_callbacks.append(event)
                self._orphan_callbacks = self._orphan_callbacks[-20:]
                return
            order = self._orders.get(matched_internal_id)
            if order is None:
                self._orphan_callbacks.append(event)
                self._orphan_callbacks = self._orphan_callbacks[-20:]
                return
            order.callbacks_received += 1
            order.callback_history.append(event)
            order.callback_history = order.callback_history[-20:]
            self._apply_body_update(order, body)

    async def record_poll_result(
        self,
        internal_id: str,
        *,
        status_code: int | None,
        response_body: Any,
        status: str | None,
        sub_status: str | None,
        error: str | None,
    ) -> None:
        async with self._lock:
            order = self._orders[internal_id]
            if status is not None:
                order.status = status
            if sub_status is not None:
                order.sub_status = sub_status
            if error is not None:
                order.last_error = error
            order.last_response_status_code = status_code or order.last_response_status_code
            order.last_response_body = response_body
            order.poll_history.append(
                {
                    'ts': self._now_iso(),
                    'status_code': status_code,
                    'status': status,
                    'sub_status': sub_status,
                    'error': error,
                    'body': response_body,
                }
            )
            order.poll_history = order.poll_history[-20:]
            extracted_order_id = _extract_order_id(response_body)
            if extracted_order_id and not order.order_id:
                order.order_id = extracted_order_id
                self._order_index_by_order_id[order.order_id] = internal_id

    async def ensure_action_state(self, internal_id: str, action_id: str, action_type: str) -> None:
        async with self._lock:
            order = self._orders[internal_id]
            order.actions.setdefault(
                action_id,
                {
                    'type': action_type,
                    'scheduled_at': self._now_iso(),
                    'started_at': None,
                    'finished_at': None,
                    'status': 'scheduled',
                    'http_status_code': None,
                    'response_body': None,
                    'error': None,
                },
            )

    async def record_action_start(self, internal_id: str, action_id: str) -> None:
        async with self._lock:
            action = self._orders[internal_id].actions[action_id]
            action['status'] = 'running'
            action['started_at'] = self._now_iso()

    async def record_action_result(
        self,
        internal_id: str,
        action_id: str,
        *,
        status: str,
        http_status_code: int | None = None,
        response_body: Any = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            action = self._orders[internal_id].actions[action_id]
            action['status'] = status
            action['http_status_code'] = http_status_code
            action['response_body'] = response_body
            action['error'] = error
            action['finished_at'] = self._now_iso()
            if response_body is not None:
                self._apply_body_update(self._orders[internal_id], response_body)

    async def get_order_snapshot(self, internal_id: str) -> dict[str, Any] | None:
        async with self._lock:
            order = self._orders.get(internal_id)
            return None if order is None else order.as_dict()

    async def summary(self) -> dict[str, Any]:
        async with self._lock:
            jobs = {job_id: job.as_dict() for job_id, job in self._jobs.items()}
            orders = [item.as_dict() for item in self._orders.values()]
            orders_sorted = sorted(orders, key=lambda item: item['created_at'], reverse=True)
            return {
                'callback_paths': self._callback_paths.copy(),
                'jobs': jobs,
                'orders_total': len(self._orders),
                'orders_recent': orders_sorted[:20],
                'orphan_callbacks': list(self._orphan_callbacks),
            }

    async def find_order_match(self, body: Any) -> tuple[str | None, str | None]:
        order_id = _extract_order_id(body)
        external_id = _extract_external_id(body)
        async with self._lock:
            internal_id = None
            if order_id:
                internal_id = self._order_index_by_order_id.get(order_id)
            if internal_id is None and external_id:
                internal_id = self._order_index_by_external_id.get(external_id)
            return internal_id, order_id or external_id

    async def get_order_status(self, internal_id: str) -> str | None:
        async with self._lock:
            order = self._orders.get(internal_id)
            return None if order is None else order.status

    def callback_merchant_alias(self, path: str) -> str | None:
        return self._callback_paths.get(path)

    def _apply_body_update(self, order: MerchantOrderRuntime, body: Any) -> None:
        if not isinstance(body, dict):
            return
        data = body.get('data') if isinstance(body.get('data'), dict) else body
        if isinstance(data, dict):
            order_id = _extract_order_id(body)
            provider_order_id = data.get('provider_order_id') or body.get('provider_order_id')
            status = data.get('status') or body.get('status')
            sub_status = data.get('sub_status') or body.get('sub_status')
            if order_id:
                order.order_id = order_id
                self._order_index_by_order_id[order_id] = order.internal_id
            if provider_order_id:
                order.provider_order_id = provider_order_id
            if status:
                order.status = status
            if sub_status:
                order.sub_status = sub_status

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()


def _extract_order_id(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    data = body.get('data') if isinstance(body.get('data'), dict) else body
    candidates = [
        data.get('order_id') if isinstance(data, dict) else None,
        body.get('order_id'),
        data.get('uuid') if isinstance(data, dict) else None,
        body.get('uuid'),
    ]
    for item in candidates:
        if isinstance(item, str) and item:
            return item
    return None


def _extract_external_id(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    data = body.get('data') if isinstance(body.get('data'), dict) else body
    candidates = [
        data.get('external_id') if isinstance(data, dict) else None,
        body.get('external_id'),
    ]
    for item in candidates:
        if isinstance(item, str) and item:
            return item
    return None
