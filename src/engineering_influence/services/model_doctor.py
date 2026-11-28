# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Check that a deployment's model profiles are ready, without calling any model."""

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_catalog_loader_interface import (
    ModelCatalogLoaderInterface,
)
from engineering_influence.interfaces.model_probe_interface import ModelProbeInterface
from engineering_influence.interfaces.model_profile_loader_interface import (
    ModelProfileLoaderInterface,
)
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_catalog import ModelCatalog
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.services.interfaces.model_doctor_interface import (
    ModelDoctorInterface,
)


class ModelDoctor(ModelDoctorInterface):
    """Per profile: is it priced today, is its key present, and would the key travel safely.

    These checks read two files and the environment and touch no network. A ``probe`` is optional:
    given one, each profile whose key is in place also gets a request to its server's model list.
    Nothing here asks a model to complete anything, so nothing here can bill. A finding never
    holds a key, only whether one was found.
    """

    def __init__(
        self,
        catalogs: ModelCatalogLoaderInterface,
        profiles: ModelProfileLoaderInterface,
        secrets: SecretProviderInterface,
        probe: ModelProbeInterface | None,
        today: date,
    ) -> None:
        """Remember the catalogs, profiles, secrets and the optional probe each profile is checked with."""
        self._catalogs = catalogs
        self._profiles = profiles
        self._secrets = secrets
        self._probe = probe
        self._today = today

    def check(self, catalog_path: Path, profiles_path: Path) -> tuple[DoctorFinding, ...]:
        """Load both files, then check every profile in the order the file lists them."""
        catalog = self._catalogs.load(catalog_path)
        findings: list[DoctorFinding] = []
        for profile in self._profiles.load(profiles_path):
            findings.append(self._price(catalog, profile))
            key_finding, key = self._key(profile)
            findings.append(key_finding)
            if profile.sends_key_in_clear():
                host = urlsplit(profile.base_url).netloc
                findings.append(
                    DoctorFinding(
                        profile.name,
                        "transport",
                        False,
                        f"the key would be sent over plain http to {host}; use https",
                    )
                )
            if self._probe is not None:
                findings.append(self._probed(self._probe, profile, key))
        return tuple(findings)

    def _price(self, catalog: ModelCatalog, profile: ModelProfile) -> DoctorFinding:
        try:
            descriptor = catalog.descriptor(profile.provider, profile.model, self._today)
        except ApplicationError as error:
            return DoctorFinding(profile.name, "price", False, error.message)
        return DoctorFinding(
            profile.name, "price", True, f"priced, effective {descriptor.price_effective}"
        )

    def _key(self, profile: ModelProfile) -> tuple[DoctorFinding, str | None]:
        if not profile.requires_key():
            return DoctorFinding(profile.name, "key", True, "none needed"), ""
        try:
            key = self._secrets.require(profile.api_key_env)
        except ApplicationError:
            return (
                DoctorFinding(profile.name, "key", False, f"{profile.api_key_env} is not set"),
                None,
            )
        return DoctorFinding(profile.name, "key", True, f"{profile.api_key_env} is set"), key

    @staticmethod
    def _probed(
        probe: ModelProbeInterface, profile: ModelProfile, key: str | None
    ) -> DoctorFinding:
        if key is None:
            return DoctorFinding(profile.name, "probe", False, "not tried: the key is missing")
        if profile.sends_key_in_clear():
            return DoctorFinding(
                profile.name, "probe", False, "not tried: the key would be sent over plain http"
            )
        try:
            availability = probe.probe(profile, key)
        except ApplicationError as error:
            return DoctorFinding(profile.name, "probe", False, error.message)
        return DoctorFinding(
            profile.name,
            "probe",
            availability is ModelAvailability.AVAILABLE,
            availability.value.replace("_", " "),
        )
