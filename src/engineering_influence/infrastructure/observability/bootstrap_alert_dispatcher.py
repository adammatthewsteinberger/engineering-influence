# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Alerts that are logged at once and then handed to vibey_bootstrap for tiering."""

import logging

from vibey_bootstrap.alerts.dispatcher import AlertSeverity, alert_dev_team

from engineering_influence.interfaces.alert_port import AlertPort

_LOGGER = logging.getLogger(__name__)
_LEVELS = {
    AlertSeverity.WARN: logging.WARNING,
    AlertSeverity.ERROR: logging.ERROR,
    AlertSeverity.CRITICAL: logging.CRITICAL,
}


class BootstrapAlertDispatcher(AlertPort):
    """Log every alert immediately, then let vibey_bootstrap dedupe and deliver it.

    vibey_bootstrap sends only CRITICAL alerts at once and holds ERROR and WARN for a
    digest that nothing here drains; with no recipients it records alerts silently. The
    log line is therefore the durable record that log-based alerting can rely on.
    """

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        """Log the alert, then forward it."""
        level = AlertSeverity(severity)
        _LOGGER.log(
            _LEVELS[level],
            "alert: %s",
            subject,
            extra={
                "alert_severity": level.value,
                "dedup_key": dedup_key,
                "alert_context": dict(context),
            },
        )
        alert_dev_team(level, subject, dict(context), dedup_key)
