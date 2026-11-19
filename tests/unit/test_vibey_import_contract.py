# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every vibey symbol this package depends on, checked against the installed vibey-engine.

vibey-engine has restarted its version line once (4.5.0 was removed from PyPI and 0.4.0
published), so the surface we use is listed here in one place. When an upgrade moves or
removes a symbol, this test names it, instead of an import failing somewhere at runtime.
Keep the list in step with the imports under src/ (static imports and `import_module` calls).
"""

from importlib import import_module

import pytest

CONTRACT: dict[str, tuple[str, ...]] = {
    "vibey.application.dto": ("HumanGateRequest",),
    "vibey.application.job_dispatcher": ("JobDispatcher",),
    "vibey.application.worker": ("Park", "Success"),
    "vibey_bootstrap.alerts.dispatcher": (
        "AlertSeverity",
        "alert_dev_team",
        "install_global_exception_hooks",
    ),
    "vibey_bootstrap.auth.webhook": ("WebhookDedup",),
    "vibey_bootstrap.counters": ("bump_counter", "counter_snapshot"),
    "vibey_bootstrap.exceptions": ("ZipBombError",),
    "vibey_bootstrap.failclose": ("ConfigurationError", "require_env"),
    "vibey_bootstrap.fastapi_middleware": ("install_middleware",),
    "vibey_bootstrap.heartbeat": ("start_heartbeat",),
    "vibey_bootstrap.ingress.classifier": ("AttachmentClassifier",),
    "vibey_bootstrap.ingress.zip_safety": ("enforce_zip_safety_limits",),
    "vibey_bootstrap.logging.correlation": (
        "CorrelationFilter",
        "correlation_scope",
        "get_correlation_id",
    ),
    "vibey_bootstrap.logging.jsonformatter": ("JsonLogFormatter",),
    "vibey_bootstrap.logging.masking": ("register_secret_keys",),
    "vibey_bootstrap.logging.noise": ("silence_noisy_loggers",),
    "vibey_bootstrap.path_safety": ("confine_to_root", "sanitize_path_segment"),
    "vibey_bootstrap.ratelimit": ("TokenBucket",),
    "vibey_bootstrap.security": ("compare_secrets",),
    "vibey_bootstrap.tracing.decorators": ("traced", "traced_async"),
    "vibey_bootstrap.tracing.latency": ("latency_snapshot",),
}


@pytest.mark.parametrize(("module", "names"), sorted(CONTRACT.items()))
def test_the_installed_vibey_engine_provides_every_symbol_we_use(
    module: str, names: tuple[str, ...]
) -> None:
    imported = import_module(module)
    missing = [name for name in names if not hasattr(imported, name)]
    assert not missing, f"{module} no longer provides {missing}"
