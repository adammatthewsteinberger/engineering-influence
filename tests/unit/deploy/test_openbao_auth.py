# Made with ❤️ by Vibey.

"""The operator's login to OpenBao: the dev root token by default, or the chart's ServiceAccount outside dev."""

import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CHART = ROOT / "deploy" / "helm" / "engineering-influence"
needs_helm = pytest.mark.skipif(
    shutil.which("helm") is None, reason="helm is needed to render the chart"
)


def secret_store(*sets: str) -> dict[str, Any]:
    command = ["helm", "template", "ei", str(CHART), "--set", "existingSecret=ei-secrets"]
    for item in sets:
        command += ["--set", item]
    result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=ROOT)  # nosec B603
    (store,) = [
        doc for doc in yaml.safe_load_all(result.stdout) if doc and doc["kind"] == "SecretStore"
    ]
    auth: dict[str, Any] = store["spec"]["provider"]["vault"]["auth"]
    return auth


@needs_helm
def test_the_root_token_is_the_default_for_dev() -> None:
    auth = secret_store("openbao.enabled=true", "openbao.bootstrapTokenSecret=ei-openbao-token")
    assert auth == {"tokenSecretRef": {"name": "ei-openbao-token", "key": "EI_OPENBAO_ROOT_TOKEN"}}


@needs_helm
def test_kubernetes_auth_logs_in_as_the_charts_service_account_with_no_stored_token() -> None:
    auth = secret_store(
        "openbao.enabled=true",
        "openbao.devMode=false",
        "openbao.server=https://bao.example.test",
        "openbao.auth=kubernetes",
    )
    assert auth == {
        "kubernetes": {
            "mountPath": "kubernetes",
            "role": "engineering-influence",
            "serviceAccountRef": {"name": "ei-engineering-influence"},
        }
    }
