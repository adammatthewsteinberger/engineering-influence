# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Pinning over real TLS: the connection goes to the vetted address and the certificate is still checked against the name."""

import datetime
import ssl
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.research.html_text_extractor import HtmlTextExtractor
from engineering_influence.infrastructure.research.http_source_fetcher import HttpSourceFetcher
from engineering_influence.infrastructure.security.public_https_url_pinner import (
    PublicHttpsUrlPinner,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.infrastructure.tools.http_mcp_transport import HttpMcpTransport


def certificate(directory: Path, name: str) -> tuple[Path, Path]:
    """A self-signed certificate that is valid for name and nothing else."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / f"{name}.pem", directory / f"{name}.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


class Seen:
    def __init__(self) -> None:
        self.hosts: list[str] = []
        self.names: list[str | None] = []


@contextmanager
def tls_server(cert_path: Path, key_path: Path) -> Iterator[tuple[int, Seen]]:
    seen = Seen()

    class Handler(BaseHTTPRequestHandler):
        def _reply(self) -> None:
            seen.hosts.append(self.headers["Host"])
            length = int(self.headers.get("content-length") or 0)
            if length:
                self.rfile.read(length)
            body = (
                b'{"jsonrpc":"2.0","id":1,"result":{}}' if self.command == "POST" else b"<p>hi</p>"
            )
            kind = "application/json" if self.command == "POST" else "text/html"
            self.send_response(200)
            self.send_header("content-type", kind)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _reply

        def log_message(self, format: str, *args: object) -> None:
            return

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    context.sni_callback = lambda sock, name, ctx: seen.names.append(name)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def client_trusting(cert_path: Path) -> httpx.Client:
    return httpx.Client(verify=ssl.create_default_context(cafile=str(cert_path)), timeout=5.0)


def pinner() -> PublicHttpsUrlPinner:
    """Resolves every name to this machine, which the policy is told to allow for the test."""
    return PublicHttpsUrlPinner(
        PublicHttpsUrlPolicy(allow_private=True), lambda host: ["127.0.0.1"]
    )


def test_fetch_url_connects_to_the_pinned_address_and_verifies_the_certificate_for_the_name(
    tmp_path: Path,
) -> None:
    cert, key = certificate(tmp_path, "bees.test")
    with tls_server(cert, key) as (port, seen):
        fetch = HttpSourceFetcher(client_trusting(cert), pinner(), HtmlTextExtractor())
        page = fetch.fetch(f"https://bees.test:{port}/x")
    assert page.text == "hi" and page.url == f"https://bees.test:{port}/x"
    assert seen.hosts == [f"bees.test:{port}"] and seen.names == ["bees.test"]


def test_fetch_url_refuses_a_server_whose_certificate_is_not_for_the_name_that_was_asked_for(
    tmp_path: Path,
) -> None:
    cert, key = certificate(tmp_path, "someone-else.test")
    with tls_server(cert, key) as (port, seen):
        fetch = HttpSourceFetcher(client_trusting(cert), pinner(), HtmlTextExtractor())
        with pytest.raises(
            TransientStageError, match="bees.test could not be reached: ConnectError"
        ):
            fetch.fetch(f"https://bees.test:{port}/x")
    assert seen.hosts == []


def test_the_mcp_transport_connects_to_the_pinned_address_and_verifies_the_certificate_for_the_name(
    tmp_path: Path,
) -> None:
    cert, key = certificate(tmp_path, "mcp.test")
    with tls_server(cert, key) as (port, seen):
        transport = HttpMcpTransport(
            client_trusting(cert), f"https://mcp.test:{port}/mcp", pinner()
        )
        transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        reply = transport.receive(1.0)
        transport.close()
    assert reply == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert seen.hosts == [f"mcp.test:{port}"] and set(seen.names) == {"mcp.test"}


def test_the_mcp_transport_refuses_a_server_whose_certificate_is_not_for_the_name(
    tmp_path: Path,
) -> None:
    cert, key = certificate(tmp_path, "someone-else.test")
    with tls_server(cert, key) as (port, seen):
        transport = HttpMcpTransport(
            client_trusting(cert), f"https://mcp.test:{port}/mcp", pinner()
        )
        with pytest.raises(
            TransientStageError, match="mcp.test could not be reached: ConnectError"
        ):
            transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        transport.close()
    assert seen.hosts == []


def test_an_address_the_real_policy_refuses_is_never_dialled_even_when_a_server_is_listening(
    tmp_path: Path,
) -> None:
    cert, key = certificate(tmp_path, "mcp.test")
    strict = PublicHttpsUrlPinner(PublicHttpsUrlPolicy(), lambda host: ["127.0.0.1"])
    with tls_server(cert, key) as (port, seen):
        transport = HttpMcpTransport(client_trusting(cert), f"https://mcp.test:{port}/mcp", strict)
        with pytest.raises(ApplicationError, match="mcp.test refused: non_public_address"):
            transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        transport.close()
    assert seen.hosts == [] and seen.names == []
