# Made with ❤️ by Vibey.

"""The optional OpenTelemetry collector: off by default, and when on the app sends its traces to it."""

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


def app_endpoint(docs: list[dict[str, Any]]) -> str:
    (config,) = [
        d for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"].endswith("-config")
    ]
    endpoint: str = config["data"]["EI_OTLP_ENDPOINT"]
    return endpoint


@needs_helm
def test_no_collector_is_rendered_by_default() -> None:
    docs = render()
    assert not [d for d in docs if "otel-collector" in d["metadata"]["name"]]


@needs_helm
def test_the_collector_forwards_to_the_endpoint_it_is_given_and_the_app_sends_to_the_collector() -> (
    None
):
    docs = render(
        "otelCollector.enabled=true", "otelCollector.exporter.endpoint=https://traces.example.test"
    )
    (config,) = [
        d
        for d in docs
        if d["kind"] == "ConfigMap" and d["metadata"]["name"].endswith("-otel-collector")
    ]
    assert "https://traces.example.test" in config["data"]["config.yaml"]
    assert app_endpoint(docs) == "http://ei-engineering-influence-otel-collector:4318"


@needs_helm
def test_without_an_endpoint_the_collector_forwards_to_tempo_when_tracing_is_on() -> None:
    docs = render("otelCollector.enabled=true", "tracing.enabled=true")
    (config,) = [
        d
        for d in docs
        if d["kind"] == "ConfigMap" and d["metadata"]["name"].endswith("-otel-collector")
    ]
    assert "http://ei-engineering-influence-tempo:4318" in config["data"]["config.yaml"]


@needs_helm
def test_a_collector_with_nowhere_to_send_refuses_to_render() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        render("otelCollector.enabled=true")


def test_the_cnpg_sample_is_a_cluster_with_the_app_database_and_owner() -> None:
    (cluster,) = [
        doc
        for doc in yaml.safe_load_all(
            (ROOT / "deploy" / "cnpg" / "cluster.yaml").read_text(encoding="utf-8")
        )
        if doc
    ]
    assert cluster["apiVersion"] == "postgresql.cnpg.io/v1" and cluster["kind"] == "Cluster"
    assert cluster["spec"]["bootstrap"]["initdb"] == {"database": "ei", "owner": "ei"}
