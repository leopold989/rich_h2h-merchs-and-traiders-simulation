from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from rich_h2h_simulator.models.system import LoggingChannels, LoggingConfig

CHANNEL_PREFIX = 'rich_h2h_simulator'


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            'ts': datetime.fromtimestamp(record.created, UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if hasattr(record, 'event'):
            payload['event'] = getattr(record, 'event')
        if hasattr(record, 'payload'):
            payload['payload'] = getattr(record, 'payload')
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ChannelLoggerRegistry:
    def __init__(self, loggers: dict[str, logging.Logger], log_dir: Path):
        self.loggers = loggers
        self.log_dir = log_dir

    def get(self, channel: str) -> logging.Logger:
        return self.loggers[channel]



def setup_logging(config: LoggingConfig, log_dir: Path) -> ChannelLoggerRegistry:
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = JsonLineFormatter()
    channels: LoggingChannels = config.channels
    loggers: dict[str, logging.Logger] = {}
    channel_map = channels.model_dump(mode='json')
    for channel, filename in channel_map.items():
        logger_name = f'{CHANNEL_PREFIX}.{channel}'
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(getattr(logging, config.level))
        logger.propagate = False
        handler = _build_handler(log_dir / filename, config)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        loggers[channel] = logger
    return ChannelLoggerRegistry(loggers, log_dir)



def _build_handler(path: Path, config: LoggingConfig):
    if config.rotation.max_bytes > 0:
        return RotatingFileHandler(
            filename=path,
            maxBytes=config.rotation.max_bytes,
            backupCount=config.rotation.backup_count,
            encoding='utf-8',
        )
    return TimedRotatingFileHandler(
        filename=path,
        when=config.rotation.when,
        backupCount=config.rotation.backup_count,
        encoding='utf-8',
    )


def log_event(logger: logging.Logger, event: str, payload: dict[str, Any] | None = None, level: int = logging.INFO) -> None:
    logger.log(level, event, extra={'event': event, 'payload': payload or {}})
