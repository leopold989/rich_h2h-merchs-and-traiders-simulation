from __future__ import annotations

import asyncio
import json
import mimetypes
import random
import re
from collections import defaultdict
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.logging_setup import ChannelLoggerRegistry, log_event
from rich_h2h_simulator.merchant_runtime import MerchantRuntimeStore
from rich_h2h_simulator.models.bundle import ConfigBundle
from rich_h2h_simulator.models.merchant import (
    MerchantConfigEntry,
    MerchantJobConfig,
    PostActionConfig,
    ReceiptConfig,
    RequestTemplateConfig,
)

TransportFactory = Callable[[str], httpx.AsyncBaseTransport | None]

_DATE_PATTERN = re.compile(r'\{date:([^{}]+)\}')

_ACTION_PATHS = {
    'cancel': ('PATCH', '/order/{order_id}/cancel', 'merchant_cancel_order'),
    'confirm_client': ('PATCH', '/order/{order_id}/confirm-client', 'merchant_confirm_client'),
    'finish': ('PATCH', '/order/{order_id}/finish', 'merchant_finish_order'),
    'add_receipt': ('POST', '/order/{order_id}/add-receipt', 'merchant_add_receipt'),
    'dispute': ('POST', '/order/{order_id}/dispute', 'merchant_open_dispute'),
}


class MerchantRunner:
    def __init__(
        self,
        config_manager: ConfigManager,
        logger_registry: ChannelLoggerRegistry,
        *,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.logger_registry = logger_registry
        self.transport_factory = transport_factory
        self.state = MerchantRuntimeStore()
        self._job_tasks: dict[str, asyncio.Task[None]] = {}
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._seq_by_job: dict[str, int] = defaultdict(int)
        self._config_fingerprint: str | None = None

    async def start(self) -> None:
        await self.reconfigure(force=True)
        log_event(self.logger_registry.get('system'), 'merchant_runner_started', await self.state.summary())

    async def stop(self) -> None:
        tasks = list(self._job_tasks.values()) + list(self._background_tasks)
        self._job_tasks.clear()
        self._background_tasks.clear()
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        log_event(self.logger_registry.get('system'), 'merchant_runner_stopped', await self.state.summary())

    async def reconfigure(self, *, force: bool = False) -> None:
        bundle = self.config_manager.bundle
        fingerprint = self._build_fingerprint(bundle)
        if not force and fingerprint == self._config_fingerprint:
            return

        callback_paths = {
            merchant.callback.path: merchant.alias
            for merchant in bundle.merchant.merchants
            if merchant.active and merchant.callback.enabled
        }
        self.state.reset_job_registry(callback_paths)

        active_jobs = self._collect_active_jobs(bundle)
        current_job_ids = set(self._job_tasks)
        desired_job_ids = {job.id for job, _, _ in active_jobs}

        for job_id in sorted(current_job_ids - desired_job_ids):
            task = self._job_tasks.pop(job_id)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await self.state.mark_job_finished(job_id)

        for job, merchant, template in active_jobs:
            await self.state.upsert_job(job.id, merchant.alias, template.id)
            if job.id in self._job_tasks:
                continue
            task = asyncio.create_task(self._job_loop(bundle, job, merchant, template), name=f'merchant-job:{job.id}')
            self._job_tasks[job.id] = task

        self._config_fingerprint = fingerprint
        log_event(
            self.logger_registry.get('system'),
            'merchant_runner_reconfigured',
            {
                'active_jobs': sorted(desired_job_ids),
                'callback_paths': callback_paths,
                'fingerprint': fingerprint,
            },
        )

    async def handle_callback(
        self,
        path: str,
        *,
        access_token: str | None,
        body: Any,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any]] | None:
        bundle = self.config_manager.bundle
        merchant = next(
            (item for item in bundle.merchant.merchants if item.active and item.callback.enabled and item.callback.path == path),
            None,
        )
        if merchant is None:
            return None

        access_token_ok = True
        if merchant.callback.validate_access_token:
            access_token_ok = access_token == merchant.access_token
            if not access_token_ok:
                await self.state.record_callback(
                    path=path,
                    merchant_alias=merchant.alias,
                    body=body,
                    access_token_ok=False,
                    matched_internal_id=None,
                    headers=headers,
                )
                raise PermissionError('invalid callback access token')

        matched_internal_id, _ = await self.state.find_order_match(body)
        await self.state.record_callback(
            path=path,
            merchant_alias=merchant.alias,
            body=body,
            access_token_ok=access_token_ok,
            matched_internal_id=matched_internal_id,
            headers=headers,
        )
        log_event(
            self.logger_registry.get('merchant_callbacks'),
            'merchant_callback_received',
            {
                'path': path,
                'merchant_alias': merchant.alias,
                'access_token_ok': access_token_ok,
                'matched_internal_id': matched_internal_id,
                'headers': self._sanitize_headers(headers),
                'body': self._sanitize_body(body),
            },
        )
        return merchant.callback.response_status_code, merchant.callback.response_body

    async def get_runtime_summary(self) -> dict[str, Any]:
        return await self.state.summary()

    async def _job_loop(
        self,
        bundle: ConfigBundle,
        job: MerchantJobConfig,
        merchant: MerchantConfigEntry,
        template: RequestTemplateConfig,
    ) -> None:
        schedule = job.schedule
        try:
            if schedule.start_delay_sec > 0:
                await self.state.mark_job_next_run(job.id, self._future_iso(seconds=schedule.start_delay_sec))
                await asyncio.sleep(schedule.start_delay_sec)
            semaphore = asyncio.Semaphore(schedule.max_inflight)
            running: set[asyncio.Task[None]] = set()
            for idx in range(schedule.requests_total):
                await semaphore.acquire()
                task = asyncio.create_task(
                    self._run_create_once(bundle, job, merchant, template, semaphore),
                    name=f'job:{job.id}:request:{idx + 1}',
                )
                running.add(task)
                task.add_done_callback(running.discard)
                if idx >= schedule.requests_total - 1:
                    continue
                delay = schedule.interval_sec
                if schedule.jitter_sec > 0:
                    delay += random.uniform(0, schedule.jitter_sec)
                await self.state.mark_job_next_run(job.id, self._future_iso(seconds=delay))
                await asyncio.sleep(delay)
            if running:
                await asyncio.gather(*running)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            await self.state.mark_job_finished(job.id)
            log_event(
                self.logger_registry.get('system'),
                'merchant_job_failed',
                {'job_id': job.id, 'merchant_alias': merchant.alias, 'template_id': template.id, 'error': str(exc)},
            )
            return
        await self.state.mark_job_finished(job.id)

    async def _run_create_once(
        self,
        bundle: ConfigBundle,
        job: MerchantJobConfig,
        merchant: MerchantConfigEntry,
        template: RequestTemplateConfig,
        semaphore: asyncio.Semaphore,
    ) -> None:
        await self.state.inc_job_inflight(job.id, 1)
        try:
            self._seq_by_job[job.id] += 1
            sequence = self._seq_by_job[job.id]
            external_id = self._render_external_id(job.id, merchant.alias, template.id, sequence, job.external_id.pattern)
            callback_url = None
            if template.request.callback_url:
                callback_url = str(template.request.callback_url)
            elif merchant.callback.enabled:
                callback_url = self._make_callback_url(bundle, merchant.callback.path)

            payload = template.request.model_dump(mode='json', exclude_none=True)
            payload.update(
                {
                    'external_id': external_id,
                    'merchant_id': str(merchant.merchant_id),
                }
            )
            if callback_url:
                payload['callback_url'] = callback_url

            internal_id = f'{job.id}:{sequence}'
            await self.state.record_create_start(
                internal_id=internal_id,
                job_id=job.id,
                merchant_alias=merchant.alias,
                template_id=template.id,
                external_id=external_id,
                request_payload=payload,
                callback_path=merchant.callback.path if merchant.callback.enabled else None,
            )
            response = await self._request_json(
                merchant=merchant,
                method='POST',
                path='/order',
                json_body=payload,
                event='merchant_create_order',
            )
            body = response.get('json')
            parsed = self._extract_order_metadata(body)
            await self.state.record_create_result(
                internal_id,
                ok=response['ok'],
                status_code=response['status_code'],
                response_body=body,
                order_id=parsed['order_id'],
                provider_order_id=parsed['provider_order_id'],
                status=parsed['status'],
                sub_status=parsed['sub_status'],
                error=response.get('error'),
            )
            if response['ok']:
                self._track_task(
                    asyncio.create_task(
                        self._run_post_create_flow(bundle, merchant, template, internal_id),
                        name=f'merchant-post-create:{internal_id}',
                    )
                )
        finally:
            await self.state.inc_job_inflight(job.id, -1)
            semaphore.release()

    async def _run_post_create_flow(
        self,
        bundle: ConfigBundle,
        merchant: MerchantConfigEntry,
        template: RequestTemplateConfig,
        internal_id: str,
    ) -> None:
        poll_cfg = bundle.merchant.defaults.poll_after_create
        if poll_cfg.enabled:
            self._track_task(
                asyncio.create_task(
                    self._poll_after_create(bundle, merchant, internal_id),
                    name=f'merchant-poll:{internal_id}',
                )
            )
        for action in template.post_actions:
            if not action.active:
                continue
            await self.state.ensure_action_state(internal_id, action.id, action.type)
            self._track_task(
                asyncio.create_task(
                    self._run_post_action(bundle, merchant, internal_id, action),
                    name=f'merchant-action:{internal_id}:{action.id}',
                )
            )

    async def _poll_after_create(
        self,
        bundle: ConfigBundle,
        merchant: MerchantConfigEntry,
        internal_id: str,
    ) -> None:
        poll_cfg = bundle.merchant.defaults.poll_after_create
        if poll_cfg.delay_ms > 0:
            await asyncio.sleep(poll_cfg.delay_ms / 1000)
        for attempt in range(poll_cfg.attempts):
            response = await self._fetch_order_state(bundle, merchant, internal_id)
            body = response.get('json')
            parsed = self._extract_order_metadata(body)
            await self.state.record_poll_result(
                internal_id,
                status_code=response['status_code'],
                response_body=body,
                status=parsed['status'],
                sub_status=parsed['sub_status'],
                error=response.get('error'),
            )
            if attempt >= poll_cfg.attempts - 1:
                break
            if poll_cfg.interval_ms > 0:
                await asyncio.sleep(poll_cfg.interval_ms / 1000)

    async def _run_post_action(
        self,
        bundle: ConfigBundle,
        merchant: MerchantConfigEntry,
        internal_id: str,
        action: PostActionConfig,
    ) -> None:
        if action.after_ms > 0:
            await asyncio.sleep(action.after_ms / 1000)

        current_status = await self.state.get_order_status(internal_id)
        if current_status is None and action.if_order_status_in:
            await self._fetch_and_record_order(bundle, merchant, internal_id)
            current_status = await self.state.get_order_status(internal_id)
        if action.if_order_status_in and current_status not in set(action.if_order_status_in):
            await self.state.record_action_result(
                internal_id,
                action.id,
                status='skipped',
                error=f'status {current_status!r} not in allowed set {action.if_order_status_in}',
            )
            return

        order_id = await self._ensure_order_id(bundle, merchant, internal_id)
        if order_id is None:
            await self.state.record_action_result(
                internal_id,
                action.id,
                status='failed',
                error='unable to resolve order_id for action execution',
            )
            return

        await self.state.record_action_start(internal_id, action.id)
        method, path_template, event_name = _ACTION_PATHS[action.type]
        path = path_template.format(order_id=order_id)
        files = None
        form = None
        if action.type in {'add_receipt', 'dispute'}:
            if action.receipt is None:
                await self.state.record_action_result(
                    internal_id,
                    action.id,
                    status='failed',
                    error='receipt configuration is required for action',
                )
                return
            form, files = await self._build_receipt_payload(bundle, action.receipt)

        response = await self._request_json(
            merchant=merchant,
            method=method,
            path=path,
            form_body=form,
            files=files,
            event=event_name,
        )
        status_name = 'done' if response['ok'] else 'failed'
        await self.state.record_action_result(
            internal_id,
            action.id,
            status=status_name,
            http_status_code=response['status_code'],
            response_body=response['json'],
            error=response['error'],
        )

    async def _fetch_and_record_order(self, bundle: ConfigBundle, merchant: MerchantConfigEntry, internal_id: str) -> None:
        response = await self._fetch_order_state(bundle, merchant, internal_id)
        body = response.get('json')
        parsed = self._extract_order_metadata(body)
        await self.state.record_poll_result(
            internal_id,
            status_code=response['status_code'],
            response_body=body,
            status=parsed['status'],
            sub_status=parsed['sub_status'],
            error=response.get('error'),
        )

    async def _fetch_order_state(
        self,
        bundle: ConfigBundle,
        merchant: MerchantConfigEntry,
        internal_id: str,
    ) -> dict[str, Any]:
        snapshot = await self.state.get_order_snapshot(internal_id)
        assert snapshot is not None
        if snapshot['order_id']:
            path = f"/order/{snapshot['order_id']}"
        else:
            path = f"/order/{merchant.merchant_id}/{snapshot['external_id']}"
        return await self._request_json(
            merchant=merchant,
            method='GET',
            path=path,
            event='merchant_get_order',
        )

    async def _ensure_order_id(
        self,
        bundle: ConfigBundle,
        merchant: MerchantConfigEntry,
        internal_id: str,
    ) -> str | None:
        snapshot = await self.state.get_order_snapshot(internal_id)
        if snapshot is None:
            return None
        if snapshot['order_id']:
            return snapshot['order_id']
        await self._fetch_and_record_order(bundle, merchant, internal_id)
        snapshot = await self.state.get_order_snapshot(internal_id)
        if snapshot is None:
            return None
        return snapshot['order_id']

    async def _build_receipt_payload(
        self,
        bundle: ConfigBundle,
        receipt: ReceiptConfig,
    ) -> tuple[dict[str, Any] | None, dict[str, tuple[str, bytes, str]] | None]:
        if receipt.kind == 'file' and receipt.path:
            file_path = self._resolve_fixture_path(bundle, receipt.path)
            content = file_path.read_bytes()
            mime_type, _ = mimetypes.guess_type(file_path.name)
            return None, {'receipt': (file_path.name, content, mime_type or 'application/octet-stream')}
        if receipt.kind == 'base64' and receipt.payload:
            return {'receipt': receipt.payload}, None
        if receipt.kind == 'url' and receipt.url is not None:
            content, filename, mime_type = await self._download_receipt(str(receipt.url))
            return None, {'receipt': (filename, content, mime_type)}
        raise ValueError('unsupported receipt configuration')

    async def _download_receipt(self, url: str) -> tuple[bytes, str, str]:
        filename = Path(urlparse(url).path).name or f'receipt-{uuid4().hex}.bin'
        mime_type, _ = mimetypes.guess_type(filename)
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content, filename, mime_type or 'application/octet-stream'

    async def _request_json(
        self,
        *,
        merchant: MerchantConfigEntry,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        event: str,
    ) -> dict[str, Any]:
        url = self._build_target_url(merchant, path)
        headers = {
            'Accept': 'application/json',
            'Access-Token': merchant.access_token,
            **merchant.default_headers,
        }
        if json_body is not None:
            headers['Content-Type'] = 'application/json'
        timeout_ms = merchant.target.timeout_ms or self.config_manager.bundle.merchant.defaults.request_timeout_ms
        transport = self.transport_factory(str(merchant.target.base_url)) if self.transport_factory else None
        start = datetime.now(UTC)
        response_payload: dict[str, Any] = {
            'ok': False,
            'status_code': None,
            'json': None,
            'error': None,
        }
        async with httpx.AsyncClient(
            verify=merchant.target.verify_ssl,
            timeout=timeout_ms / 1000,
            transport=transport,
        ) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_body,
                    data=form_body,
                    files=files,
                )
                response_payload['status_code'] = response.status_code
                try:
                    response_payload['json'] = response.json()
                except json.JSONDecodeError:
                    response_payload['json'] = {'raw_body': response.text}
                success_flag = None
                if isinstance(response_payload['json'], dict) and 'success' in response_payload['json']:
                    success_flag = bool(response_payload['json']['success'])
                response_payload['ok'] = response.is_success and success_flag is not False
                if not response_payload['ok']:
                    if success_flag is False:
                        response_payload['error'] = str(response_payload['json'].get('message') or 'application error')
                    else:
                        response_payload['error'] = f'HTTP {response.status_code}'
            except Exception as exc:  # noqa: BLE001
                response_payload['error'] = str(exc)
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        log_event(
            self.logger_registry.get('merchant_outbound'),
            event,
            {
                'merchant_alias': merchant.alias,
                'request': {
                    'method': method,
                    'url': url,
                    'headers': self._sanitize_headers(headers),
                    'json': self._sanitize_body(json_body),
                    'form': self._sanitize_body(form_body),
                    'files': list((files or {}).keys()),
                },
                'response': {
                    'ok': response_payload['ok'],
                    'status_code': response_payload['status_code'],
                    'body': self._sanitize_body(response_payload['json']),
                    'error': response_payload['error'],
                    'duration_ms': duration_ms,
                },
            },
        )
        return response_payload

    def _collect_active_jobs(
        self,
        bundle: ConfigBundle,
    ) -> list[tuple[MerchantJobConfig, MerchantConfigEntry, RequestTemplateConfig]]:
        merchants = {item.alias: item for item in bundle.merchant.merchants if item.active}
        templates = {item.id: item for item in bundle.merchant.request_templates if item.active}
        jobs: list[tuple[MerchantJobConfig, MerchantConfigEntry, RequestTemplateConfig]] = []
        for job in bundle.merchant.merchant_jobs:
            if not job.active:
                continue
            merchant = merchants.get(job.merchant_alias)
            template = templates.get(job.template_id)
            if merchant is None or template is None:
                continue
            jobs.append((job, merchant, template))
        return jobs

    def _build_fingerprint(self, bundle: ConfigBundle) -> str:
        digests = self.config_manager.get_state_snapshot()['digests']
        return f"{digests['system']}:{digests['merchant']}"

    def _build_target_url(self, merchant: MerchantConfigEntry, path: str) -> str:
        base = str(merchant.target.base_url).rstrip('/')
        prefix = merchant.target.api_prefix.rstrip('/')
        return f'{base}{prefix}{path}'

    def _make_callback_url(self, bundle: ConfigBundle, path: str) -> str:
        return f"{str(bundle.system.service.public_base_url).rstrip('/')}{path}"

    def _render_external_id(
        self,
        job_id: str,
        merchant_alias: str,
        template_id: str,
        sequence: int,
        pattern: str,
    ) -> str:
        now = datetime.now(UTC)
        rendered = pattern
        rendered = rendered.replace('{merchant_alias}', merchant_alias)
        rendered = rendered.replace('{template_id}', template_id)
        rendered = rendered.replace('{job_id}', job_id)
        rendered = rendered.replace('{seq}', str(sequence))
        rendered = rendered.replace('{uuid}', uuid4().hex)
        rendered = _DATE_PATTERN.sub(lambda match: now.strftime(match.group(1)), rendered)
        return rendered

    def _future_iso(self, *, seconds: float) -> str:
        return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()

    def _resolve_fixture_path(self, bundle: ConfigBundle, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        base = bundle.system_path.parent / bundle.system.paths.fixtures_dir
        return (base / raw_path).resolve()

    def _extract_order_metadata(self, body: Any) -> dict[str, str | None]:
        if not isinstance(body, dict):
            return {
                'order_id': None,
                'provider_order_id': None,
                'status': None,
                'sub_status': None,
            }
        data = body.get('data') if isinstance(body.get('data'), dict) else body
        if not isinstance(data, dict):
            data = body
        return {
            'order_id': _first_string(data.get('order_id'), body.get('order_id'), data.get('uuid'), body.get('uuid')),
            'provider_order_id': _first_string(data.get('provider_order_id'), body.get('provider_order_id')),
            'status': _first_string(data.get('status'), body.get('status')),
            'sub_status': _first_string(data.get('sub_status'), body.get('sub_status')),
        }

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        masked = {item.lower() for item in self.config_manager.bundle.system.logging.payload_limits.mask_headers}
        result: dict[str, str] = {}
        for key, value in headers.items():
            result[key] = '***masked***' if key.lower() in masked else value
        return result

    def _sanitize_body(self, body: Any) -> Any:
        limit = self.config_manager.bundle.system.logging.payload_limits.max_body_chars
        if body is None:
            return None
        text = json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else str(body)
        if len(text) <= limit:
            return body
        return {'truncated': True, 'preview': text[:limit], 'total_chars': len(text)}

    def _track_task(self, task: asyncio.Task[Any]) -> None:
        self._background_tasks.add(task)

        def _cleanup(done: asyncio.Task[Any]) -> None:
            self._background_tasks.discard(done)

        task.add_done_callback(_cleanup)


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None
