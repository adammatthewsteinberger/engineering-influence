# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Alert on uncaught exceptions, once per process."""

from typing import ClassVar

from vibey_bootstrap.alerts.dispatcher import install_global_exception_hooks


class ProcessCrashHooks:
    """Install vibey_bootstrap's crash hooks exactly once.

    The library chains onto whatever hook was there before, so installing twice would
    raise every crash alert twice.
    """

    _installed: ClassVar[bool] = False

    def install(self) -> bool:
        """Return True when this call installed the hooks, False when they already were."""
        if ProcessCrashHooks._installed:
            return False
        install_global_exception_hooks()
        ProcessCrashHooks._installed = True
        return True
