from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.logging_setup import ChannelLoggerRegistry, log_event
from rich_h2h_simulator.merchant_runner import MerchantRunner, TransportFactory


class RuntimeState:
    def __init__(
        self,
        config_manager: ConfigManager,
        logger_registry: ChannelLoggerRegistry,
        *,
        merchant_transport_factory: TransportFactory | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.logger_registry = logger_registry
        self.merchant_runner = MerchantRunner(
            config_manager,
            logger_registry,
            transport_factory=merchant_transport_factory,
        )
        self._reload_task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        await self.merchant_runner.start()
        await self._start_reloader()
        log_event(self.logger_registry.get('system'), 'runtime_started', await self.get_state_snapshot())

    async def stop(self) -> None:
        if self._reload_task is not None:
            self._reload_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reload_task
        await self.merchant_runner.stop()
        log_event(self.logger_registry.get('system'), 'runtime_stopped', {})

    async def _start_reloader(self) -> None:
        self._reload_task = asyncio.create_task(self._reload_loop(), name='config-auto-reloader')

    async def _reload_loop(self) -> None:
        system_logger = self.logger_registry.get('system')
        while True:
            interval = self.config_manager.bundle.system.service.config_reload_interval_sec
            await asyncio.sleep(interval)
            result = await self.reload_config()
            if result.success and result.changed:
                log_event(system_logger, 'config_reloaded', await self.get_state_snapshot())
            elif not result.success:
                log_event(system_logger, 'config_reload_failed', {'message': result.message})

    def get_health(self) -> dict[str, Any]:
        state = self.config_manager.get_state_snapshot()
        healthy = state['last_reload_error'] is None
        return {
            'status': 'ok' if healthy else 'degraded',
            'service': self.config_manager.bundle.system.service.name,
            'app_started_at': state['app_started_at'],
            'last_reload_success_at': state['last_reload_success_at'],
            'last_reload_error': state['last_reload_error'],
        }

    async def reload_config(self, *, force: bool = False):
        result = self.config_manager.reload(force=force)
        if result.success and result.changed:
            await self.merchant_runner.reconfigure(force=True)
        return result

    async def get_state_snapshot(self) -> dict[str, Any]:
        state = self.config_manager.get_state_snapshot()
        state['merchant_runtime'] = await self.merchant_runner.get_runtime_summary()
        return state
