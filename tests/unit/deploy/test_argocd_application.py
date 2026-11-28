# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The Argo CD Application: it syncs an overlay that exists, into that overlay's namespace, under the Kyverno label."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
APPLICATION = ROOT / "deploy" / "argocd" / "application.yaml"


def application() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(APPLICATION.read_text(encoding="utf-8"))
    return loaded


def overlay_kustomization(app: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / app["spec"]["source"]["path"] / "kustomization.yaml"
    loaded: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded


def test_it_is_an_argo_cd_application_in_the_argocd_namespace() -> None:
    app = application()
    assert app["apiVersion"] == "argoproj.io/v1alpha1"
    assert app["kind"] == "Application"
    assert app["metadata"]["namespace"] == "argocd"


def test_it_syncs_an_overlay_that_exists_in_this_repository() -> None:
    assert (ROOT / application()["spec"]["source"]["path"] / "kustomization.yaml").is_file()


def test_its_destination_is_the_namespace_the_overlay_names() -> None:
    app = application()
    assert app["spec"]["destination"]["namespace"] == overlay_kustomization(app)["namespace"]


def test_it_prunes_and_heals_so_git_is_the_source_of_truth() -> None:
    assert application()["spec"]["syncPolicy"]["automated"] == {"prune": True, "selfHeal": True}


def project() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (ROOT / "deploy" / "argocd" / "project.yaml").read_text(encoding="utf-8")
    )
    return loaded


def test_it_runs_in_a_project_that_bounds_it_to_this_repository_and_namespace() -> None:
    app = application()
    scoped = project()
    assert scoped["kind"] == "AppProject"
    assert app["spec"]["project"] == scoped["metadata"]["name"]
    assert scoped["spec"]["sourceRepos"] == [app["spec"]["source"]["repoURL"]]
    assert scoped["spec"]["destinations"] == [
        {
            "server": app["spec"]["destination"]["server"],
            "namespace": app["spec"]["destination"]["namespace"],
        }
    ]


def test_the_project_creates_no_cluster_scoped_objects_and_only_the_kinds_the_base_renders() -> (
    None
):
    scoped = project()
    assert scoped["spec"]["clusterResourceWhitelist"] == []
    allowed = {
        (entry["group"], entry["kind"]) for entry in scoped["spec"]["namespaceResourceWhitelist"]
    }
    rendered = {
        ("" if doc["apiVersion"] == "v1" else doc["apiVersion"].split("/")[0], doc["kind"])
        for doc in yaml.safe_load_all(
            (ROOT / "deploy/kustomize/base/resources.yaml").read_text(encoding="utf-8")
        )
        if doc
    }
    assert allowed == rendered


def test_the_namespace_it_creates_carries_the_label_the_kyverno_policies_match() -> None:
    labels = application()["spec"]["syncPolicy"]["managedNamespaceMetadata"]["labels"]
    assert labels == {"policy.ei/restricted": "true"}
