"""Outbound URL policy: server-side request forgery cases."""

import pytest

from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)

PUBLIC = "93.184.216.34"


def policy_resolving(*addresses: str) -> PublicHttpsUrlPolicy:
    return PublicHttpsUrlPolicy(lambda _: list(addresses))


def test_a_public_https_destination_is_allowed() -> None:
    assert policy_resolving(PUBLIC).check("https://receiver.example.com/events").accepted


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://receiver.example.com/", "scheme_not_https"),
        ("ftp://receiver.example.com/", "scheme_not_https"),
        ("file:///etc/passwd", "scheme_not_https"),
        ("//receiver.example.com/", "scheme_not_https"),
        ("https://user:pw@receiver.example.com/", "credentials_in_url"),
        ("https://user@receiver.example.com/", "credentials_in_url"),
        ("https:///path", "missing_host"),
    ],
)
def test_malformed_or_unsafe_urls_are_refused(url: str, reason: str) -> None:
    verdict = policy_resolving(PUBLIC).check(url)

    assert not verdict.accepted
    assert verdict.reason == reason


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata service
        "100.64.0.1",  # carrier-grade NAT
        "0.0.0.0",
        "::1",
        "fe80::1%en0",
        "fc00::1",
    ],
)
def test_destinations_inside_the_network_are_refused(address: str) -> None:
    verdict = policy_resolving(address).check("https://receiver.example.com/")

    assert verdict.reason == "non_public_address"


def test_one_private_answer_among_public_ones_is_enough_to_refuse() -> None:
    verdict = policy_resolving(PUBLIC, "10.0.0.5").check("https://receiver.example.com/")

    assert verdict.reason == "non_public_address"


def test_a_name_that_does_not_resolve_is_refused() -> None:
    def failing(_: str) -> list[str]:
        raise OSError("no such host")

    assert PublicHttpsUrlPolicy(failing).check("https://nope.invalid/").reason == (
        "unresolvable_host"
    )
    assert policy_resolving().check("https://nope.invalid/").reason == "unresolvable_host"


def test_private_destinations_can_be_allowed_explicitly() -> None:
    policy = PublicHttpsUrlPolicy(lambda _: ["127.0.0.1"], allow_private=True)

    assert policy.check("https://localhost/hook").accepted


def test_the_system_resolver_blocks_loopback_names() -> None:
    assert PublicHttpsUrlPolicy().check("https://localhost/").reason == "non_public_address"
    assert PublicHttpsUrlPolicy().check("https://127.0.0.1/").reason == "non_public_address"
