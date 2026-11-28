# engineering-influence Helm chart

The chart runs the API and the worker, plus the optional services they use. Each dependency is either in the chart or
provided from outside it, and every choice is one value. The defaults deploy nothing extra and expect a Secret you
create, `existingSecret`, that holds the app's settings. See `docs/DEPLOYMENT.md` for the full install.

## Components and how to swap each

| Need | In the chart | Swap for an external one |
|---|---|---|
| Database (`EI_DATABASE_URL`) | `postgres.enabled` deploys a single Postgres | Leave `postgres.enabled: false`, and put the external URL in the Secret. Any PostgreSQL 14+ works, including a CloudNativePG cluster you run yourself. |
| Queue (`EI_RABBITMQ_URL`) | `rabbitmq.enabled` deploys RabbitMQ | Leave it off, and put the external AMQP URL in the Secret. KEDA scales the worker on that queue. |
| Secrets | `openbao.enabled` with `devMode: true` deploys a single in-memory OpenBao for a local cluster only | `openbao.devMode: false` and `openbao.server` set to your OpenBao. The External Secrets Operator copies the keys in `openbao.keys` into `existingSecret`. Without `openbao.enabled`, you create the Secret yourself. |
| Object store (artifacts) | `seaweedfs.enabled` deploys SeaweedFS with its S3 API, and `artifactStore.kind: s3` points the app at it | Set `artifactStore.endpointUrl` and `artifactStore.bucket` for any S3-compatible store, and its credentials in the Secret. |
| Logs | `logs.enabled` deploys Loki and Grafana Alloy | Leave it off, and ship the JSON logs to your own system. |
| Metrics and dashboards | `observability.enabled` deploys Prometheus and Grafana | Leave it off, and scrape `/metrics` on the API with your own Prometheus. |
| Traces | `tracing.enabled` deploys Tempo and sets `EI_OTLP_ENDPOINT` | Leave it off, and set `EI_OTLP_ENDPOINT` in the config to your OTLP receiver. |
| Ingress and TLS | `ingress.enabled` with `ingress.issuer` names a cert-manager ClusterIssuer | Leave it off, and route to the `ei-…-api` Service with your own ingress or gateway. The ClusterIssuers are in `deploy/cert-manager/`. |
| Autoscaling | `autoscaling.api` (HorizontalPodAutoscaler) and `autoscaling.keda` (KEDA for the worker) | Leave them off and set replica counts. |

Each external service is one URL or one set of keys, so swapping it does not change the application. Anything the chart
creates that you bring from outside is a Secret or a value, never a code change.

## Policies that are off by default

- `networkPolicy.enabled` restricts the API to the namespaces in `networkPolicy.apiIngressFrom` and the worker to none,
  with DNS and the entries in `networkPolicy.egress` allowed. Turn it on only with the egress your database, queue,
  secrets and object store need, or the app cannot start.
- `podDisruptionBudget.enabled` allows one API or worker pod down at a time.

## Pre-install and pre-upgrade hooks

With `secretsAsPreSync: true`, the SecretStore and ExternalSecret are hooks at weight -10, and the migration Job is a
hook at -5 whenever `postgres.enabled` is false. Argo CD runs both as PreSync, so the migration starts after
`existingSecret` exists. With `postgres.enabled` true, the migration is a post-install hook instead, because the database
is created in the same install.
