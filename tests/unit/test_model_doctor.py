# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The doctor checks price, key and transport offline, and probes only when it is given a probe."""

from datetime import date
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_catalog_loader_interface import (
    ModelCatalogLoaderInterface,
)
from engineering_influence.interfaces.model_probe_interface import ModelProbeInterface
from engineering_influence.interfaces.model_profile_loader_interface import (
    ModelProfileLoaderInterface,
)
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_catalog import ModelCatalog
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.interfaces.model_doctor_interface import (
    ModelDoctorInterface,
)
from engineering_influence.services.model_doctor import ModelDoctor

KEY = "sk-test-SECRETSECRET"
TODAY = date(2026, 11, 21)


def descriptor(provider: str, model: str, effective: str) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider, model, "f", 1000, 100, 0, 0, 0, 0, 0, effective, "https://example.test/policy"
    )


class Catalogs(ModelCatalogLoaderInterface):
    def __init__(self, catalog: ModelCatalog | None = None) -> None:
        self.catalog = catalog or ModelCatalog(
            (descriptor("a", "m", "2026-01-01"), descriptor("local", "m", "2026-01-01"))
        )
        self.paths: list[Path] = []

    def load(self, path: Path) -> ModelCatalog:
        self.paths.append(path)
        return self.catalog


class Profiles(ModelProfileLoaderInterface):
    def __init__(self, *profiles: ModelProfile) -> None:
        self.profiles = profiles

    def load(self, path: Path) -> tuple[ModelProfile, ...]:
        return self.profiles


class Secrets(SecretProviderInterface):
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def require(self, name: str) -> str:
        if name not in self.values:
            raise ApplicationError("SECRET_MISSING", f"required secret {name} is not configured")
        return self.values[name]


class Probe(ModelProbeInterface):
    def __init__(self, answer: ModelAvailability | ApplicationError) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str]] = []

    def probe(self, profile: ModelProfile, api_key: str) -> ModelAvailability:
        self.asked.append((profile.name, api_key))
        if isinstance(self.answer, ApplicationError):
            raise self.answer
        return self.answer


HOSTED = ModelProfile("hosted", "anthropic", "a", "m", "https://api.anthropic.com", "AKEY")
LOCAL = ModelProfile("local", "openai_compatible", "local", "m", "http://127.0.0.1:11434")


def doctor(
    *profiles: ModelProfile,
    secrets: dict[str, str] | None = None,
    probe: Probe | None = None,
    catalogs: Catalogs | None = None,
) -> ModelDoctorInterface:
    return ModelDoctor(
        catalogs or Catalogs(), Profiles(*profiles), Secrets(secrets or {}), probe, TODAY
    )


def lines(doc: ModelDoctorInterface) -> list[str]:
    return [f.line() for f in doc.check(Path("c"), Path("p"))]


def test_a_priced_local_profile_passes_everything_without_a_key() -> None:
    assert lines(doctor(LOCAL)) == [
        "ok   local: price: priced, effective 2026-01-01",
        "ok   local: key: none needed",
    ]


def test_a_hosted_profile_with_its_key_passes_and_the_key_is_never_shown() -> None:
    findings = lines(doctor(HOSTED, secrets={"AKEY": KEY}))
    assert findings == [
        "ok   hosted: price: priced, effective 2026-01-01",
        "ok   hosted: key: AKEY is set",
    ]
    assert KEY not in "".join(findings)


def test_a_missing_key_fails_and_names_the_variable() -> None:
    assert "FAIL hosted: key: AKEY is not set" in lines(doctor(HOSTED))


def test_a_model_with_no_price_in_force_today_fails_with_the_catalogs_reason() -> None:
    future = Catalogs(ModelCatalog((descriptor("a", "m", "2027-01-01"),)))
    (price, _key) = lines(doctor(HOSTED, secrets={"AKEY": KEY}, catalogs=future))
    assert price.startswith("FAIL hosted: price: no price for a/m in force on 2026-11-21")


def test_the_latest_price_in_force_is_the_one_reported() -> None:
    catalog = ModelCatalog((descriptor("a", "m", "2026-01-01"), descriptor("a", "m", "2026-06-01")))
    first = lines(doctor(HOSTED, secrets={"AKEY": KEY}, catalogs=Catalogs(catalog)))[0]
    assert first == "ok   hosted: price: priced, effective 2026-06-01"


def test_a_key_over_plain_http_to_another_host_fails_the_transport_check() -> None:
    risky = ModelProfile("r", "openai_compatible", "local", "m", "http://10.0.0.5:8000", "K")
    out = lines(doctor(risky, secrets={"K": KEY}))
    assert (
        "FAIL r: transport: the key would be sent over plain http to 10.0.0.5:8000; use https"
        in out
    )
    assert KEY not in "".join(out)


def test_no_probe_means_no_probe_finding_and_nothing_is_asked() -> None:
    assert not any("probe" in line for line in lines(doctor(HOSTED, LOCAL, secrets={"AKEY": KEY})))


def test_a_probe_asks_each_profile_with_its_key_and_reports_the_answer() -> None:
    probe = Probe(ModelAvailability.AVAILABLE)
    out = lines(doctor(HOSTED, LOCAL, secrets={"AKEY": KEY}, probe=probe))
    assert probe.asked == [("hosted", KEY), ("local", "")]
    assert "ok   hosted: probe: available" in out
    assert "ok   local: probe: available" in out
    assert KEY not in "".join(out)


@pytest.mark.parametrize(
    ("answer", "text"),
    [
        (ModelAvailability.AUTHENTICATION_FAILED, "authentication failed"),
        (ModelAvailability.CREDITS_EXHAUSTED, "credits exhausted"),
        (ModelAvailability.WINDOW_EXHAUSTED, "window exhausted"),
    ],
)
def test_a_blocked_server_fails_the_probe(answer: ModelAvailability, text: str) -> None:
    out = lines(doctor(HOSTED, secrets={"AKEY": KEY}, probe=Probe(answer)))
    assert f"FAIL hosted: probe: {text}" in out


def test_an_unreachable_server_fails_the_probe_with_the_reason() -> None:
    probe = Probe(ApplicationError("MODEL_PROBE_FAILED", "127.0.0.1:1 could not be reached"))
    assert "FAIL local: probe: 127.0.0.1:1 could not be reached" in lines(
        doctor(LOCAL, probe=probe)
    )


def test_a_key_that_would_travel_in_clear_is_never_given_to_the_probe() -> None:
    risky = ModelProfile("r", "openai_compatible", "local", "m", "http://10.0.0.5:8000", "K")
    probe = Probe(ModelAvailability.AVAILABLE)
    out = lines(doctor(risky, secrets={"K": KEY}, probe=probe))
    assert probe.asked == []
    assert "FAIL r: probe: not tried: the key would be sent over plain http" in out
    assert KEY not in "".join(out)


def test_a_missing_key_means_the_probe_is_not_tried() -> None:
    probe = Probe(ModelAvailability.AVAILABLE)
    out = lines(doctor(HOSTED, probe=probe))
    assert probe.asked == []
    assert "FAIL hosted: probe: not tried: the key is missing" in out


def test_unreadable_files_raise_rather_than_report() -> None:
    class Broken(Catalogs):
        def load(self, path: Path) -> ModelCatalog:
            raise ApplicationError("MODEL_CATALOG_INVALID", "bad")

    with pytest.raises(ApplicationError):
        doctor(LOCAL, catalogs=Broken()).check(Path("c"), Path("p"))


def test_the_paths_are_passed_to_the_loaders() -> None:
    catalogs = Catalogs()
    doctor(LOCAL, catalogs=catalogs).check(Path("the-catalog"), Path("p"))
    assert catalogs.paths == [Path("the-catalog")]
