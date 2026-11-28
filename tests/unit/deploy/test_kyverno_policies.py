# Made with ❤️ by Vibey.

"""The Kyverno policies: the app's pods must set a memory limit, and the stack's pods are only reported."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
POLICIES = ROOT / "deploy" / "kyverno" / "policies.yaml"


def policies() -> dict[str, dict[str, Any]]:
    docs = [doc for doc in yaml.safe_load_all(POLICIES.read_text(encoding="utf-8")) if doc]
    return {doc["metadata"]["name"]: doc for doc in docs}


def test_the_app_pods_must_set_a_memory_limit_and_are_denied_without_one() -> None:
    policy = policies()["ei-app-memory-limits"]["spec"]
    assert policy["validationActions"] == ["Deny"]
    selector = policy["matchConstraints"]["objectSelector"]["matchExpressions"][0]
    assert selector == {
        "key": "app.kubernetes.io/component",
        "operator": "In",
        "values": ["api", "worker", "migration"],
    }


def test_the_stack_pods_are_only_reported_until_they_set_a_limit() -> None:
    policy = policies()["ei-audit-resources"]["spec"]
    assert policy["validationActions"] == ["Audit"]


def test_release_images_are_verified_against_the_release_workflow_identity_in_audit() -> None:
    policy = policies()["ei-verify-release-images"]
    assert policy["kind"] == "ImageValidatingPolicy"
    assert policy["spec"]["validationActions"] == ["Audit"]
    (identity,) = policy["spec"]["attestors"][0]["cosign"]["keyless"]["identities"]
    assert identity["subject"] == (
        "https://github.com/adammatthewsteinberger/engineering-influence/"
        ".github/workflows/release.yml@refs/heads/main"
    )
