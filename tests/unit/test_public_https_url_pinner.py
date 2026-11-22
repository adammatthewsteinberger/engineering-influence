# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PublicHttpsUrlPinner: the name is resolved once, every address is checked, and the request goes to the one that was."""

import pytest

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.infrastructure.security.public_https_url_pinner import (
    PublicHttpsUrlPinner,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)

PUBLIC, OTHER = "93.184.216.34", "93.184.216.35"
V6 = "2606:2800:220:1:248:1893:25c8:1946"


class Policy(OutboundUrlPolicyInterface):
    """Refuses the addresses it is told to, with a reason, and remembers every URL it was shown."""

    def __init__(self, refuse: dict[str, str | None] | None = None) -> None:
        self.refuse = refuse or {}
        self.checked: list[str] = []

    def check(self, url: str) -> SecurityVerdict:
        self.checked.append(url)
        for address, reason in self.refuse.items():
            if address in url:
                return SecurityVerdict(accepted=False, reason=reason)
        return SecurityVerdict.accept()


class Resolver:
    def __init__(self, *answers: list[str] | BaseException) -> None:
        self.answers = list(answers)
        self.asked: list[str] = []

    def __call__(self, host: str) -> list[str]:
        self.asked.append(host)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def pinner(
    *answers: list[str] | BaseException, policy: Policy | None = None
) -> tuple[PublicHttpsUrlPinner, Policy, Resolver]:
    made, resolver = policy or Policy(), Resolver(*(answers or ([PUBLIC],)))
    return PublicHttpsUrlPinner(made, resolver), made, resolver


def test_it_is_a_pinner() -> None:
    assert isinstance(pinner()[0], OutboundUrlPinnerInterface)


# ------------------------------------------------------------------------- a name
def test_a_name_is_resolved_once_and_pinned_to_the_address_with_its_name_kept() -> None:
    found, policy, resolver = pinner([PUBLIC])
    decision = found.pin("https://Bees.Example/a/b?x=1#top")
    assert decision.reason == "" and decision.target is not None
    assert decision.target.url == f"https://{PUBLIC}/a/b?x=1#top"
    assert (
        decision.target.host_header == "bees.example"
        and decision.target.sni_hostname == "bees.example"
    )
    assert resolver.asked == ["bees.example"]
    assert policy.checked == [f"https://{PUBLIC}/a/b?x=1#top"]


def test_the_policy_sees_addresses_and_never_the_name() -> None:
    found, policy, _ = pinner([PUBLIC, OTHER])
    found.pin("https://bees.example/x")
    assert policy.checked == [f"https://{PUBLIC}/x", f"https://{OTHER}/x"]


def test_the_port_is_kept_in_the_address_and_in_the_host_header() -> None:
    target = pinner()[0].pin("https://bees.example:8443/x").target
    assert target is not None
    assert target.url == f"https://{PUBLIC}:8443/x" and target.host_header == "bees.example:8443"


def test_every_address_must_pass_and_the_first_one_is_used() -> None:
    found, _, _ = pinner([PUBLIC, OTHER])
    target = found.pin("https://bees.example/x").target
    assert target is not None and target.url == f"https://{PUBLIC}/x"


def test_one_address_the_policy_refuses_refuses_the_name_with_its_reason() -> None:
    found, policy, _ = pinner(
        [PUBLIC, "10.0.0.5"], policy=Policy({"10.0.0.5": "non_public_address"})
    )
    decision = found.pin("https://bees.example/x")
    assert decision.target is None and decision.reason == "non_public_address"
    assert len(policy.checked) == 2


def test_a_refusal_with_no_reason_still_says_something() -> None:
    decision = pinner(policy=Policy({PUBLIC: None}))[0].pin("https://bees.example/x")
    assert decision.target is None and decision.reason == "refused"


def test_the_same_address_twice_is_checked_once() -> None:
    found, policy, _ = pinner([PUBLIC, PUBLIC])
    found.pin("https://bees.example/x")
    assert policy.checked == [f"https://{PUBLIC}/x"]


def test_an_ipv6_address_is_bracketed_in_the_url_and_the_policy_sees_the_same() -> None:
    found, policy, _ = pinner([V6])
    target = found.pin("https://bees.example:8443/x").target
    assert target is not None and target.url == f"https://[{V6}]:8443/x"
    assert (
        policy.checked == [f"https://[{V6}]:8443/x"] and target.host_header == "bees.example:8443"
    )


def test_a_user_and_password_are_left_in_the_url_for_the_policy_to_refuse() -> None:
    found, policy, _ = pinner(policy=Policy({"user": "credentials_in_url"}))
    decision = found.pin("https://user:pw@bees.example/x")
    assert decision.reason == "credentials_in_url"
    assert policy.checked == [f"https://user:pw@{PUBLIC}/x"]


def test_a_host_that_is_not_ascii_is_resolved_and_verified_as_its_ascii_name() -> None:
    found, _, resolver = pinner()
    target = found.pin("https://bücher.example/x").target
    assert resolver.asked == ["xn--bcher-kva.example"]
    assert target is not None and target.host_header == "xn--bcher-kva.example"
    assert target.sni_hostname == "xn--bcher-kva.example"


def test_a_host_that_cannot_be_a_name_is_refused_before_anything_is_resolved() -> None:
    found, policy, resolver = pinner()
    assert found.pin("https://a..example/x").reason == "invalid_host"
    assert resolver.asked == [] and policy.checked == []


@pytest.mark.parametrize("answer", [OSError("no such host"), []])
def test_a_name_that_does_not_resolve_is_refused(answer: BaseException | list[str]) -> None:
    found, policy, _ = pinner(answer)
    assert found.pin("https://bees.example/x").reason == "unresolvable_host"
    assert policy.checked == []


# ------------------------------------------------------------------- not a name
def test_a_url_that_already_holds_an_address_is_judged_as_it_is_and_pinned_to_itself() -> None:
    found, policy, resolver = pinner()
    target = found.pin(f"https://{PUBLIC}:9000/x?q=1").target
    assert target is not None and target.url == f"https://{PUBLIC}:9000/x?q=1"
    assert target.host_header == f"{PUBLIC}:9000" and target.sni_hostname == ""
    assert resolver.asked == [] and policy.checked == [f"https://{PUBLIC}:9000/x?q=1"]


def test_an_ipv6_address_in_the_url_is_pinned_to_itself_with_its_brackets() -> None:
    found, policy, _ = pinner()
    target = found.pin(f"https://[{V6}]/x").target
    assert target is not None and target.url == f"https://[{V6}]/x"
    assert target.host_header == f"[{V6}]" and policy.checked == [f"https://[{V6}]/x"]


def test_an_address_the_policy_refuses_is_refused_without_resolving_anything() -> None:
    found, _, resolver = pinner(policy=Policy({"10.0.0.5": "non_public_address"}))
    assert found.pin("https://10.0.0.5/x").reason == "non_public_address"
    assert resolver.asked == []


@pytest.mark.parametrize(
    ("url", "reason"),
    [("https:///x", "missing_host"), ("not a url", "missing_host"), ("", "missing_host")],
)
def test_a_url_with_no_host_is_refused_before_anything_is_resolved(url: str, reason: str) -> None:
    found, policy, resolver = pinner()
    assert found.pin(url).reason == reason
    assert resolver.asked == [] and policy.checked == []


@pytest.mark.parametrize("url", ["https://bees.example:99999/x", "https://bees.example:abc/x"])
def test_a_port_that_is_not_a_port_is_refused(url: str) -> None:
    found, policy, resolver = pinner()
    assert found.pin(url).reason == "invalid_url"
    assert resolver.asked == [] and policy.checked == []


# ----------------------------------------------------------------- with the real policy
def real(*answers: list[str] | BaseException) -> PublicHttpsUrlPinner:
    return PublicHttpsUrlPinner(PublicHttpsUrlPolicy(), Resolver(*(answers or ([PUBLIC],))))


def test_with_the_real_policy_a_public_name_is_pinned_and_an_inward_one_is_not() -> None:
    target = real([PUBLIC]).pin("https://bees.example/x").target
    assert target is not None and target.url == f"https://{PUBLIC}/x"
    assert real(["10.0.0.5"]).pin("https://bees.example/x").reason == "non_public_address"
    assert real(["169.254.169.254"]).pin("https://bees.example/x").reason == "non_public_address"
    assert real(["::1"]).pin("https://bees.example/x").reason == "non_public_address"
    assert real(["fe80::1%lo0"]).pin("https://bees.example/x").reason == "non_public_address"


def test_with_the_real_policy_one_inward_address_among_public_ones_refuses_the_name() -> None:
    assert real([PUBLIC, "127.0.0.1"]).pin("https://bees.example/x").reason == "non_public_address"


def test_with_the_real_policy_plain_http_and_credentials_are_still_refused() -> None:
    assert real().pin("http://bees.example/x").reason == "scheme_not_https"
    assert real().pin("https://user:pw@bees.example/x").reason == "credentials_in_url"


def test_a_name_that_resolves_public_and_then_inward_is_pinned_to_the_first_answer_only() -> None:
    resolver = Resolver([PUBLIC], ["10.0.0.5"])
    found = PublicHttpsUrlPinner(PublicHttpsUrlPolicy(), resolver)
    target = found.pin("https://rebind.example/x").target
    assert target is not None and target.url == f"https://{PUBLIC}/x"
    assert resolver.asked == ["rebind.example"] and len(resolver.answers) == 1


def test_the_default_resolver_asks_the_system_and_this_machine_is_not_public() -> None:
    decision = PublicHttpsUrlPinner(PublicHttpsUrlPolicy()).pin("https://localhost/x")
    assert decision.target is None and decision.reason == "non_public_address"
