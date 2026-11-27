# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The Kustomize base is the Helm chart's render, and each overlay sets the replicas and namespace it declares.

These run only where helm and kubectl are installed; the rest of the suite does not need them.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "deploy"
HAS_TOOLS = shutil.which("helm") is not None and shutil.which("kubectl") is not None
needs_tools = pytest.mark.skipif(
    not HAS_TOOLS, reason="helm and kubectl are needed to render the manifests"
)


def run(*args: str) -> str:
    return subprocess.run(list(args), check=True, capture_output=True, text=True, cwd=ROOT).stdout


def objects(text: str) -> list[dict[str, Any]]:
    return [doc for doc in yaml.safe_load_all(text) if doc]


def by_kind(docs: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    return {doc["metadata"]["name"]: doc for doc in docs if doc["kind"] == kind}


@needs_tools
def test_the_committed_base_is_the_chart_render_without_hooks() -> None:
    rendered = run(
        "helm",
        "template",
        "ei",
        "deploy/helm/engineering-influence",
        "--set",
        "existingSecret=ei-secrets",
    )
    stripped = subprocess.run(
        ["python3", "deploy/kustomize/strip_hooks.py"],
        input=rendered,
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    committed = (DEPLOY / "kustomize/base/resources.yaml").read_text(encoding="utf-8")
    assert committed == stripped, (
        "deploy/kustomize/base/resources.yaml has drifted; run deploy/kustomize/render-base.sh"
    )


@needs_tools
@pytest.mark.parametrize(
    ("overlay", "namespace", "api", "worker"),
    [("dev", "ei-dev", 1, 1), ("prod", "ei", 3, 2)],
)
def test_an_overlay_sets_its_namespace_replicas_and_image_tag(
    overlay: str, namespace: str, api: int, worker: int
) -> None:
    docs = objects(run("kubectl", "kustomize", f"deploy/kustomize/overlays/{overlay}"))
    deployments = by_kind(docs, "Deployment")
    assert deployments["ei-engineering-influence-api"]["spec"]["replicas"] == api
    assert deployments["ei-engineering-influence-worker"]["spec"]["replicas"] == worker
    assert {doc["metadata"].get("namespace") for doc in docs} == {namespace}
    for deployment in deployments.values():
        image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
        assert image.endswith(":0.1.0"), image


@needs_tools
def test_the_overlays_name_every_object_the_base_names() -> None:
    base = {
        (doc["kind"], doc["metadata"]["name"])
        for doc in objects((DEPLOY / "kustomize/base/resources.yaml").read_text(encoding="utf-8"))
    }
    dev = {
        (doc["kind"], doc["metadata"]["name"])
        for doc in objects(run("kubectl", "kustomize", "deploy/kustomize/overlays/dev"))
    }
    assert base == dev
