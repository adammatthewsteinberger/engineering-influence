"""Prometheus text exposition."""

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.contracts.readiness_report import ReadinessReport
from engineering_influence.interaction.api.prometheus_renderer import PrometheusRenderer


def test_counters_are_prefixed_sanitised_and_sorted() -> None:
    text = PrometheusRenderer().render({"webhook.failed": 2, "http.requests": 5}, {}, None)

    assert text == (
        "# TYPE ei_http_requests_total counter\nei_http_requests_total 5\n"
        "# TYPE ei_webhook_failed_total counter\nei_webhook_failed_total 2\n"
    )


def test_latencies_become_a_summary_per_operation() -> None:
    stats = {"count": 3.0, "errors": 1.0, "p50": 0.1, "p95": 0.2, "p99": 0.3, "max": 0.4}

    text = PrometheusRenderer().render({}, {"start.pipeline": stats}, None)

    assert "# TYPE ei_operation_latency_seconds summary" in text
    assert 'ei_operation_latency_seconds{operation="start.pipeline",quantile="0.95"} 0.2' in text
    assert 'ei_operation_latency_seconds_count{operation="start.pipeline"} 3.0' in text
    assert 'ei_operation_errors_total{operation="start.pipeline"} 1.0' in text


def test_missing_statistics_default_to_zero() -> None:
    text = PrometheusRenderer().render({}, {"op": {}}, None)

    assert 'ei_operation_latency_seconds_count{operation="op"} 0' in text
    assert "quantile" not in text


def test_dependency_status_is_a_gauge() -> None:
    report = ReadinessReport(
        ready=False,
        checks=(
            HealthStatus(name="rabbitmq", healthy=False),
            HealthStatus(name="db", healthy=True),
        ),
    )

    text = PrometheusRenderer().render({}, {}, report)

    assert "ei_ready 0" in text
    assert 'ei_dependency_up{name="rabbitmq"} 0' in text
    assert 'ei_dependency_up{name="db"} 1' in text


def test_label_values_cannot_break_the_format() -> None:
    hostile = 'a"b\\c\nd'

    text = PrometheusRenderer().render({}, {hostile: {"count": 1.0}}, None)

    assert 'operation="a\\"b\\\\c\\nd"' in text
    assert all(line.startswith(("#", "ei_")) for line in text.strip().splitlines())


def test_empty_input_is_a_valid_empty_document() -> None:
    assert PrometheusRenderer().render({}, {}, None) == "\n"
