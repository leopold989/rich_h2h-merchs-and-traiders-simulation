from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from rich_h2h_simulator.config_loader import ReloadResult
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
        return runtime.config_manager.get_state_snapshot()

    @router.post(f'{control_prefix}/reload')
    async def reload_config(
        request: Request,
        token: str | None = Header(default=None, alias='X-Control-Token'),
    ) -> dict:
        runtime: RuntimeState = request.app.state.runtime
        _authorize(runtime, token, write=True)
        result: ReloadResult = runtime.config_manager.reload(force=True)
        status_name = 'ok' if result.success else 'error'
        return {
            'status': status_name,
            'message': result.message,
            'changed': result.changed,
            'attempted_at': result.attempted_at.isoformat(),
        }

    return router


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
