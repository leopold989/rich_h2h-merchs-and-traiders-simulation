from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from rich_h2h_simulator.api import build_router
from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.logging_setup import log_event, setup_logging
from rich_h2h_simulator.merchant_runner import TransportFactory
from rich_h2h_simulator.runtime import RuntimeState
from rich_h2h_simulator.trader_runner import TransportFactory as TraderTransportFactory


def create_app(
    system_config_path: str | Path | None = None,
    *,
    merchant_transport_factory: TransportFactory | None = None,
    trader_callback_transport_factory: TraderTransportFactory | None = None,
) -> FastAPI:
    system_path = Path(system_config_path or 'config/system.json').resolve()
    config_manager = ConfigManager(system_path)
    log_dir = (config_manager.bundle.system_path.parent / config_manager.bundle.system.paths.log_dir).resolve()
    logger_registry = setup_logging(config_manager.bundle.system.logging, log_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = RuntimeState(
            config_manager,
            logger_registry,
            merchant_transport_factory=merchant_transport_factory,
            trader_callback_transport_factory=trader_callback_transport_factory,
        )
        app.state.runtime = runtime
        log_event(logger_registry.get('system'), 'app_starting', {'system_config': str(system_path)})
        await runtime.start()
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(
        title='Rich H2H Simulator',
        version='0.6.0',
        docs_url='/docs',
        redoc_url='/redoc',
        lifespan=lifespan,
    )
    app.include_router(build_router(config_manager.bundle.system.control_api.prefix))
    return app
