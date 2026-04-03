from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from rich_h2h_simulator.runtime import RuntimeState


def build_router(control_prefix: str = "/_sim") -> APIRouter:
    router = APIRouter()

    @router.get('/health')
    async def health(request: Request) -> dict:
        runtime: RuntimeState = request.app.state.runtime
        return runtime.get_health()

    @router.get(f'{control_prefix}/config')
    async def get_config(
        request: Request,
        token: str | None = Header(default=None, alias='X-Control-Token'),
    ) -> dict:
        runtime: RuntimeState = request.app.state.runtime
        _authorize(runtime, token, write=False)
        return runtime.config_manager.public_bundle

    @router.get(f'{control_prefix}/state')
    async def get_state(
        request: Request,
        token: str | None = Header(default=None, alias='X-Control-Token'),
    ) -> dict:
        runtime: RuntimeState = request.app.state.runtime
        _authorize(runtime, token, write=False)
        return await runtime.get_state_snapshot()

    @router.post(f'{control_prefix}/reload')
    async def reload_config(
        request: Request,
        token: str | None = Header(default=None, alias='X-Control-Token'),
    ) -> dict:
        runtime: RuntimeState = request.app.state.runtime
        _authorize(runtime, token, write=True)
        result = await runtime.reload_config(force=True)
        status_name = 'ok' if result.success else 'error'
        return {
            'status': status_name,
            'message': result.message,
            'changed': result.changed,
            'attempted_at': result.attempted_at.isoformat(),
        }

    @router.post('/{full_path:path}')
    async def merchant_callback_catch_all(
        request: Request,
        full_path: str,
        access_token: str | None = Header(default=None, alias='Access-Token'),
    ) -> Response:
        runtime: RuntimeState = request.app.state.runtime
        path = '/' + full_path
        try:
            body = await _read_request_body(request)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        headers = {key: value for key, value in request.headers.items()}
        try:
            callback_response = await runtime.merchant_runner.handle_callback(
                path,
                access_token=access_token,
                body=body,
                headers=headers,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        if callback_response is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='route not found')
        status_code, response_body = callback_response
        return Response(
            content=json.dumps(response_body, ensure_ascii=False),
            status_code=status_code,
            media_type='application/json',
        )

    return router


async def _read_request_body(request: Request) -> Any:
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        return await request.json()
    body = await request.body()
    if not body:
        return {}
    try:
        return json.loads(body.decode('utf-8'))
    except Exception:  # noqa: BLE001
        return {'raw_body': body.decode('utf-8', errors='replace')}


def _authorize(runtime: RuntimeState, token: str | None, *, write: bool) -> None:
    control = runtime.config_manager.bundle.system.control_api
    if not control.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='control api disabled')
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='missing X-Control-Token header')
    valid_tokens = {control.write_token}
    if not write:
        valid_tokens.add(control.read_only_token)
    if token not in valid_tokens:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='invalid control token')
