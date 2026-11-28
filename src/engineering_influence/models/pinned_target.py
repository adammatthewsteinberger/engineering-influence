# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where one outbound request really goes."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.pinned_target_interface import PinnedTargetInterface


@dataclass(frozen=True, slots=True)
class PinnedTarget(PinnedTargetInterface):
    """An address that was checked, with what is needed to talk to it as the name it was found under.

    ``url`` is the address the request is sent to: the original URL with the **vetted IP address** where
    the host was, so the client never resolves the name again. ``host_header`` is the host (and port)
    the person wrote, sent as the ``Host`` header so the server still sees its own name.
    ``sni_hostname`` is that name without a port, passed to the client so TLS sends it and **checks the
    server's certificate against it**, not against the IP; it is empty when the URL already held an
    address, which is then what the certificate is checked against.
    """

    url: str
    host_header: str
    sni_hostname: str = ""

    def __post_init__(self) -> None:
        """Validate the pinned target's address when it is built."""
        if not self.url or not self.host_header:
            raise ValueError("a pinned target has an address to connect to and a host to ask for")

    def request_headers(self) -> dict[str, str]:
        """The headers that keep the request addressed to the name the person wrote."""
        return {"host": self.host_header}

    def request_extensions(self) -> dict[str, str]:
        """The client extensions that keep the certificate checked against that name."""
        return {"sni_hostname": self.sni_hostname} if self.sni_hostname else {}
