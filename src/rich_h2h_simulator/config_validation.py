from __future__ import annotations

from pathlib import Path

from rich_h2h_simulator.exceptions import ConfigError
from rich_h2h_simulator.models.bundle import ConfigBundle


class ValidationCollector:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    def extend(self, messages: list[str]) -> None:
        self.errors.extend(messages)

    def raise_if_any(self) -> None:
        if self.errors:
            joined = '\n'.join(f'- {item}' for item in self.errors)
            raise ConfigError(f'Configuration validation failed:\n{joined}')


def validate_bundle(bundle: ConfigBundle) -> None:
    collector = ValidationCollector()
    _validate_merchants(bundle, collector)
    _validate_traders(bundle, collector)
    _validate_paths(bundle, collector)
    collector.raise_if_any()


def _validate_merchants(bundle: ConfigBundle, collector: ValidationCollector) -> None:
    template_ids: set[str] = set()
    for template in bundle.merchant.request_templates:
        if template.id in template_ids:
            collector.add(f'duplicate request_templates.id={template.id}')
        template_ids.add(template.id)
        post_action_ids: set[str] = set()
        for action in template.post_actions:
            if action.id in post_action_ids:
                collector.add(f'duplicate post_actions.id={action.id} inside template {template.id}')
            post_action_ids.add(action.id)

    merchant_aliases: set[str] = set()
    callback_paths: set[str] = set()
    for merchant in bundle.merchant.merchants:
        if merchant.alias in merchant_aliases:
            collector.add(f'duplicate merchants.alias={merchant.alias}')
        merchant_aliases.add(merchant.alias)
        if merchant.callback.path in callback_paths:
            collector.add(f'duplicate merchants.callback.path={merchant.callback.path}')
        callback_paths.add(merchant.callback.path)

    job_ids: set[str] = set()
    for job in bundle.merchant.merchant_jobs:
        if job.id in job_ids:
            collector.add(f'duplicate merchant_jobs.id={job.id}')
        job_ids.add(job.id)
        if job.template_id not in template_ids:
            collector.add(f'merchant_jobs.id={job.id} references unknown template_id={job.template_id}')
        if job.merchant_alias not in merchant_aliases:
            collector.add(f'merchant_jobs.id={job.id} references unknown merchant_alias={job.merchant_alias}')


def _validate_traders(bundle: ConfigBundle, collector: ValidationCollector) -> None:
    profile_ids: set[str] = set()
    for profile in bundle.trader.response_profiles:
        if profile.id in profile_ids:
            collector.add(f'duplicate response_profiles.id={profile.id}')
        profile_ids.add(profile.id)

    trader_aliases: set[str] = set()
    base_paths: set[str] = set()
    for trader in bundle.trader.traders:
        if trader.alias in trader_aliases:
            collector.add(f'duplicate traders.alias={trader.alias}')
        trader_aliases.add(trader.alias)
        if trader.base_path in base_paths:
            collector.add(f'duplicate traders.base_path={trader.base_path}')
        base_paths.add(trader.base_path)
        if trader.default_response_profile_id not in profile_ids:
            collector.add(
                f'trader alias={trader.alias} references unknown default_response_profile_id={trader.default_response_profile_id}'
            )
        requisite_ids = {item.id for item in trader.requisites}
        if len(requisite_ids) != len(trader.requisites):
            collector.add(f'duplicate requisites.id detected inside trader alias={trader.alias}')
        routing_ids: set[str] = set()
        for rule in trader.routing_rules:
            if rule.id in routing_ids:
                collector.add(f'duplicate routing_rules.id={rule.id} inside trader alias={trader.alias}')
            routing_ids.add(rule.id)
            if rule.response_profile_id not in profile_ids:
                collector.add(
                    f'trader alias={trader.alias} routing rule id={rule.id} references unknown '
                    f'response_profile_id={rule.response_profile_id}'
                )
            unknown = [item for item in rule.requisite_pool if item not in requisite_ids]
            if unknown:
                collector.add(
                    f'trader alias={trader.alias} routing rule id={rule.id} references unknown requisites={unknown}'
                )


def _validate_paths(bundle: ConfigBundle, collector: ValidationCollector) -> None:
    fixtures_dir = _resolve(bundle.system_path.parent, bundle.system.paths.fixtures_dir)
    if not fixtures_dir.exists():
        collector.add(f'fixtures_dir does not exist: {fixtures_dir}')
    for template in bundle.merchant.request_templates:
        for action in template.post_actions:
            receipt = action.receipt
            if receipt and receipt.kind == 'file' and receipt.path:
                receipt_path = _resolve(fixtures_dir, receipt.path)
                if not receipt_path.exists():
                    collector.add(
                        f'template id={template.id} action id={action.id} references missing receipt file {receipt_path}'
                    )


def _resolve(base: Path, raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()
