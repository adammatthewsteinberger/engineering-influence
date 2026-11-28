# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The Argo CD Application: it syncs the dev chart and its values, which exist, into ei-dev, under the Kyverno label."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
APPLICATION = ROOT / "deploy" / "argocd" / "application.yaml"


def application() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(APPLICATION.read_text(encoding="utf-8"))
    return loaded


# The kinds `helm template` renders from the chart with values-dev.yaml (checked by hand when it changes).
DEV_RENDERED_KINDS = {
    ("", "ConfigMap"),
    ("", "Service"),
    ("", "ServiceAccount"),
    ("apps", "Deployment"),
    ("batch", "Job"),
    ("external-secrets.io", "ExternalSecret"),
    ("external-secrets.io", "SecretStore"),
    ("networking.k8s.io", "Ingress"),
}


def test_it_is_an_argo_cd_application_in_the_argocd_namespace() -> None:
    app = application()
    assert app["apiVersion"] == "argoproj.io/v1alpha1"
    assert app["kind"] == "Application"
    assert app["metadata"]["namespace"] == "argocd"


def test_it_syncs_a_chart_and_the_dev_values_that_exist_in_this_repository() -> None:
    app = application()
    chart = ROOT / app["spec"]["source"]["path"]
    assert (chart / "Chart.yaml").is_file()
    for values in app["spec"]["source"]["helm"]["valueFiles"]:
        assert (chart / values).is_file(), values


def test_its_destination_is_the_dev_namespace() -> None:
    assert application()["spec"]["destination"]["namespace"] == "ei-dev"


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


def test_the_project_creates_no_cluster_scoped_objects_and_only_the_kinds_the_dev_render_makes() -> (
    None
):
    scoped = project()
    assert scoped["spec"]["clusterResourceWhitelist"] == []
    allowed = {
        (entry["group"], entry["kind"]) for entry in scoped["spec"]["namespaceResourceWhitelist"]
    }
    assert allowed == DEV_RENDERED_KINDS


def test_the_namespace_it_creates_carries_the_label_the_kyverno_policies_match() -> None:
    labels = application()["spec"]["syncPolicy"]["managedNamespaceMetadata"]["labels"]
    assert labels == {"policy.ei/restricted": "true"}
