# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Resolves a URL's host once, checks every address, and fixes the one the request will use."""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget

Resolver = Callable[[str], list[str]]


class PublicHttpsUrlPinner(OutboundUrlPinnerInterface):
    """Closes the gap between checking a name and connecting to it (DNS rebinding).

    A policy that resolves a name when asked, followed by a client that resolves it again when it
    connects, can be answered differently the second time. Here **the name is resolved once**. Each
    address that came back is judged by the injected policy as an address, with no DNS involved, so
    the policy's rules (public addresses only, https only, no credentials in the URL) stay in one place;
    **every** address must pass, as for the policy alone. The first is the one the request is sent to.
    The name is kept for the ``Host`` header and for TLS, so the certificate is still checked against the
    name and not the address.

    A URL that already holds an address is judged as it is, and pinned to itself. Only one address is
    tried: if it is down the request fails rather than falling back to another, which a caller may retry.
    A host that cannot be encoded as a name, or does not resolve, is refused.
    """

    def __init__(
        self, policy: OutboundUrlPolicyInterface, resolver: Resolver | None = None
    ) -> None:
        self._policy = policy
        self._resolve = resolver or self._system_resolve

    def pin(self, url: str) -> PinDecision:
        """The address to connect to, checked once, or the reason the URL may not be used."""
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError:
            return PinDecision.refused("invalid_url")
        host = parts.hostname
        if not host:
            return PinDecision.refused("missing_host")
        if self._is_address(host):
            name, addresses = "", [host]
        else:
            try:
                name = host.encode("idna").decode("ascii")
            except UnicodeError:
                return PinDecision.refused("invalid_host")
            try:
                addresses = list(dict.fromkeys(self._resolve(name)))
            except OSError:
                return PinDecision.refused("unresolvable_host")
            if not addresses:
                return PinDecision.refused("unresolvable_host")
        for address in addresses:
            verdict = self._policy.check(self._with_host(parts, address, port))
            if not verdict.accepted:
                return PinDecision.refused(verdict.reason or "refused")
        return PinDecision.pinned(
            PinnedTarget(
                url=self._with_host(parts, addresses[0], port),
                host_header=self._bracketed(name or host)
                + (f":{port}" if port is not None else ""),
                sni_hostname=name,
            )
        )

    @staticmethod
    def _is_address(host: str) -> bool:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True

    @staticmethod
    def _bracketed(host: str) -> str:
        return f"[{host}]" if ":" in host else host

    def _with_host(self, parts: SplitResult, address: str, port: int | None) -> str:
        """The URL with the address where the host was. A user or password stays, for the policy to refuse."""
        userinfo, at, _ = parts.netloc.rpartition("@")
        netloc = f"{userinfo}{at}{self._bracketed(address)}" + (
            f":{port}" if port is not None else ""
        )
        return urlunsplit(parts._replace(netloc=netloc))

    @staticmethod
    def _system_resolve(host: str) -> list[str]:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        return [str(info[4][0]) for info in infos]
