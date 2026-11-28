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


def test_the_image_glob_matches_tags_digests_and_the_bare_name() -> None:
    import fnmatch

    glob = policies()["ei-verify-release-images"]["spec"]["matchImageReferences"][0]["glob"]
    repository = "ghcr.io/adammatthewsteinberger/engineering-influence"
    for reference in (
        f"{repository}:0.1.0rc3",
        f"{repository}@sha256:54e48dc9bacd60c88b8974ff1f5dd39b3572d3b4eb7ceaf37b09bd9b6ea75bfb",
        repository,
    ):
        assert fnmatch.fnmatchcase(reference, glob), reference


def test_the_signature_check_covers_init_and_ephemeral_containers() -> None:
    expression = policies()["ei-verify-release-images"]["spec"]["validations"][0]["expression"]
    assert "initContainers" in expression and "ephemeralContainers" in expression


def test_the_transparency_log_is_a_sibling_of_keyless_as_the_v1_schema_requires() -> None:
    # Kyverno's v1 ImageValidatingPolicy rejects `ctlog` inside `keyless` (found by a server dry-run on Kyverno 1.20).
    cosign = policies()["ei-verify-release-images"]["spec"]["attestors"][0]["cosign"]
    assert "ctlog" not in cosign["keyless"]
    assert cosign["ctlog"] == {"url": "https://rekor.sigstore.dev"}


def test_an_absent_container_list_falls_back_to_a_list_not_a_map() -> None:
    # `{}` as the fallback makes the ternary mix a list and a map, which the policy's CEL refuses.
    expression = policies()["ei-verify-release-images"]["spec"]["validations"][0]["expression"]
    assert "{}" not in expression
    assert expression.count(": []") == 2
