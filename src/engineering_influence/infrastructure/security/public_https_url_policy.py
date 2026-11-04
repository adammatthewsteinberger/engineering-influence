# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outbound URL policy that blocks server-side request forgery."""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.interfaces.outbound_url_policy_port import OutboundUrlPolicyPort

Resolver = Callable[[str], list[str]]


class PublicHttpsUrlPolicy(OutboundUrlPolicyPort):
    """Allow only https URLs whose every resolved address is publicly routable.

    The check resolves the name when called. A hostile DNS server can answer
    differently when the connection is made later (DNS rebinding), so deployments
    that deliver to untrusted URLs should also egress through a filtering proxy.
    """

    def __init__(self, resolver: Resolver | None = None, allow_private: bool = False) -> None:
        self._resolve = resolver or self._system_resolve
        self._allow_private = allow_private

    def check(self, url: str) -> SecurityVerdict:
        """Reject non-https schemes, embedded credentials, and non-public destinations."""
        parts = urlsplit(url)
        if parts.scheme != "https":
            return SecurityVerdict.reject("scheme_not_https")
        if parts.username is not None or parts.password is not None:
            return SecurityVerdict.reject("credentials_in_url")
        host = parts.hostname
        if not host:
            return SecurityVerdict.reject("missing_host")
        if self._allow_private:
            return SecurityVerdict.accept()
        try:
            addresses = self._resolve(host)
        except OSError:
            return SecurityVerdict.reject("unresolvable_host")
        if not addresses:
            return SecurityVerdict.reject("unresolvable_host")
        if any(
            not ipaddress.ip_address(address.split("%", 1)[0]).is_global for address in addresses
        ):
            return SecurityVerdict.reject("non_public_address")
        return SecurityVerdict.accept()

    @staticmethod
    def _system_resolve(host: str) -> list[str]:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        return [str(info[4][0]) for info in infos]
