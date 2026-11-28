# Made with ❤️ by Vibey.

"""The API's and worker's NetworkPolicy and PodDisruptionBudget: off by default, and narrow when on.

These render the chart with helm, so they run only where helm is installed.
"""

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


def render(*sets: str) -> list[dict[str, Any]]:
    command = ["helm", "template", "ei", str(CHART), "--set", "existingSecret=ei-secrets"]
    for item in sets:
        command += ["--set", item]
    result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=ROOT)  # nosec B603
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def of_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc["kind"] == kind]


@needs_helm
def test_neither_policy_is_rendered_by_default() -> None:
    docs = render()
    assert of_kind(docs, "NetworkPolicy") == []
    assert of_kind(docs, "PodDisruptionBudget") == []


@needs_helm
def test_a_pod_disruption_budget_per_component_allows_one_disruption_at_a_time() -> None:
    budgets = of_kind(render("podDisruptionBudget.enabled=true"), "PodDisruptionBudget")
    assert sorted(b["metadata"]["name"] for b in budgets) == [
        "ei-engineering-influence-api",
        "ei-engineering-influence-worker",
    ]
    assert all(
        b["spec"]["maxUnavailable"] == 1 and "minAvailable" not in b["spec"] for b in budgets
    )


@needs_helm
def test_the_api_takes_ingress_only_from_the_namespaces_listed() -> None:
    policies = {
        p["metadata"]["name"]: p
        for p in of_kind(
            render("networkPolicy.enabled=true", "networkPolicy.apiIngressFrom={ingress-nginx}"),
            "NetworkPolicy",
        )
    }
    api = policies["ei-engineering-influence-api"]["spec"]
    assert api["ingress"] == [
        {
            "from": [
                {
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "ingress-nginx"}
                    }
                }
            ],
            "ports": [{"protocol": "TCP", "port": 8000}],
        }
    ]


@needs_helm
def test_the_worker_takes_no_ingress_and_both_may_reach_dns_only_by_default() -> None:
    policies = {
        p["metadata"]["name"]: p
        for p in of_kind(render("networkPolicy.enabled=true"), "NetworkPolicy")
    }
    worker = policies["ei-engineering-influence-worker"]["spec"]
    assert "ingress" not in worker and worker["policyTypes"] == ["Ingress", "Egress"]
    api = policies["ei-engineering-influence-api"]["spec"]
    assert "ingress" not in api  # no namespace listed: no ingress rule, so all ingress is denied
    for spec in (api, worker):
        assert len(spec["egress"]) == 1
        assert spec["egress"][0]["ports"] == [
            {"protocol": "UDP", "port": 53},
            {"protocol": "TCP", "port": 53},
        ]


@needs_helm
def test_extra_egress_is_added_after_dns() -> None:
    policies = of_kind(
        render(
            "networkPolicy.enabled=true",
            "networkPolicy.egress[0].ports[0].protocol=TCP",
            "networkPolicy.egress[0].ports[0].port=5432",
        ),
        "NetworkPolicy",
    )
    for policy in policies:
        assert [{"protocol": "TCP", "port": 5432}] == policy["spec"]["egress"][1]["ports"]


@needs_helm
def test_no_ingress_is_rendered_by_default() -> None:
    assert of_kind(render(), "Ingress") == []


@needs_helm
def test_the_ingress_routes_the_host_to_the_api_under_its_issuers_certificate() -> None:
    (ingress,) = of_kind(
        render(
            "ingress.enabled=true",
            "ingress.host=api.example.test",
            "ingress.issuer=letsencrypt-staging",
        ),
        "Ingress",
    )
    assert ingress["metadata"]["annotations"] == {
        "cert-manager.io/cluster-issuer": "letsencrypt-staging"
    }
    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert ingress["spec"]["tls"] == [{"hosts": ["api.example.test"], "secretName": "ei-api-tls"}]
    (rule,) = ingress["spec"]["rules"]
    assert rule["host"] == "api.example.test"
    assert rule["http"]["paths"][0]["backend"]["service"] == {
        "name": "ei-engineering-influence-api",
        "port": {"name": "http"},
    }


@needs_helm
def test_an_ingress_without_a_host_or_an_issuer_refuses_to_render() -> None:
    for sets in (
        ["ingress.enabled=true", "ingress.issuer=letsencrypt-staging"],
        ["ingress.enabled=true", "ingress.host=api.example.test"],
    ):
        with pytest.raises(subprocess.CalledProcessError):
            render(*sets)
