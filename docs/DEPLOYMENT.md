# Deploying on Kubernetes

The Helm chart in `deploy/helm/engineering-influence/` runs the API, the worker and the schema migration. It does not
deploy Postgres or RabbitMQ: the cluster or an operator provides them, and the chart reads their URLs from one Secret.

## What the chart creates

| Object | Purpose |
|---|---|
| `ServiceAccount` | The pods' identity. The API token is not mounted into any pod. |
| `ConfigMap` | Non-secret settings: `EI_HOST`, `EI_PORT`, `EI_QUEUE_NAME`. |
| `Service` | Cluster-internal access to the API on port 8000. |
| `Deployment` (API) | `ei serve api`, with liveness on `/health/live` and readiness on `/health/ready`. |
| `Deployment` (worker) | `ei serve worker`, which runs the book stages. |
| `Job` (migration) | `ei db upgrade`, run as a Helm hook before each install and upgrade. |

Every pod runs as a non-root user with a read-only root filesystem, all capabilities dropped and `/tmp` on an `emptyDir`.

## The Secret

Create the Secret before installing. It must hold:

- `EI_DATABASE_URL`: a SQLAlchemy URL, for example `postgresql+psycopg://user:pw@postgres:5432/ei`
- `EI_RABBITMQ_URL`: for example `amqp://user:pw@rabbitmq:5672/`
- `EI_API_KEYS`: comma-separated keys, each at least 24 characters
- any model or search keys your run settings name (see [CONFIGURATION.md](CONFIGURATION.md))

```bash
kubectl create secret generic ei-secrets \
  --from-literal=EI_DATABASE_URL='postgresql+psycopg://user:pw@postgres:5432/ei' \
  --from-literal=EI_RABBITMQ_URL='amqp://user:pw@rabbitmq:5672/' \
  --from-literal=EI_API_KEYS='<your-api-key-of-at-least-24-characters>'
```

## Install

```bash
helm install ei deploy/helm/engineering-influence \
  --set existingSecret=ei-secrets \
  --set image.repository=registry.example.com/engineering-influence
```

`image.repository` is a placeholder in the defaults; set it to the registry you push the image to. The image tag
defaults to the chart's `appVersion`.

To build books, the worker needs the TeX image, so set `worker.image.tag` to a `worker-tex` build (see
[WORKER_IMAGE.md](WORKER_IMAGE.md)). The slim worker writes every chapter but fails at `build`.

## Checks

```bash
helm lint deploy/helm/engineering-influence --set existingSecret=ei-secrets
helm template ei deploy/helm/engineering-influence --set existingSecret=ei-secrets
```

The chart's version is `0.1.0`, the same as the package's `__version__`.

## Object storage

By default a run's files stay in Postgres. To keep them in a bucket, set `artifactStore.kind=s3`:

- **Your own S3 service** (AWS S3, or another S3-compatible service): set `artifactStore.bucket`, `artifactStore.region`
  and, for a non-AWS service, `artifactStore.endpointUrl`. The bucket must already exist.
- **SeaweedFS in the namespace**: also set `seaweedfs.enabled=true`. The chart runs one SeaweedFS replica with a
  `seaweedfs.storage` volume, and a post-install Job creates the bucket. The endpoint is then the in-cluster service.
  This is a single replica with one volume: it is not highly available, so use an external service for production.

The S3 credentials are two keys of the same Secret, `EI_S3_ACCESS_KEY_ID` and `EI_S3_SECRET_ACCESS_KEY`, read by the
API, the worker and SeaweedFS's identity file. The image tags in `values.yaml` (`chrislusf/seaweedfs`, `curlimages/curl`,
`busybox`) are pinned to versions you should check against your registry before production.

```bash
helm install ei deploy/helm/engineering-influence \
  --set existingSecret=ei-secrets \
  --set artifactStore.kind=s3 \
  --set seaweedfs.enabled=true
```

SeaweedFS's master, volume and filer ports have no authentication, so the chart adds a NetworkPolicy that lets only the API, the worker and the bucket Job reach its S3 port. It takes effect only on a cluster whose network plugin enforces NetworkPolicy; check your plugin before relying on it.

The command-line book commands and the MCP server still read the database, as the configuration page says.

## Autoscaling

- **The API** scales on CPU with a `HorizontalPodAutoscaler` when `autoscaling.api.enabled=true` (2 to 10 replicas at 70% CPU by default).
- **The worker** scales on its queue depth with KEDA when `autoscaling.keda.enabled=true`. KEDA must already be installed
  in the cluster; the chart creates a `ScaledObject` and a `TriggerAuthentication` that reads `EI_RABBITMQ_URL` from the Secret.
  The worker adds a replica for each `queueLengthPerReplica` (default 10) waiting messages. With KEDA on, the worker's
  `replicas` field is left to KEDA. Use `minReplicaCount: 0` in dev to let the worker scale to nothing, and `1` in production.

```bash
helm install ei deploy/helm/engineering-influence \
  --set existingSecret=ei-secrets \
  --set autoscaling.api.enabled=true \
  --set autoscaling.keda.enabled=true
```

The chart's KEDA objects are checked against the rendered YAML, not against a cluster's CRD schema; run `kubectl apply
--dry-run=server` against your cluster before relying on them.

## Kustomize

Clusters that do not use Helm can apply `deploy/kustomize/overlays/dev` or `overlays/prod`. The base is the chart's
default render, regenerated by `deploy/kustomize/render-base.sh`; a test fails if the committed base drifts from the chart.
Each overlay sets its namespace (`ei-dev` or `ei`), its replica counts and its image tag:

```bash
kubectl apply -k deploy/kustomize/overlays/prod
```

The base expects the `ei-secrets` Secret in the overlay's namespace. The image is a placeholder repository; change the
overlay's `images` entry to yours.

## Not in this chart yet

Logs, metrics, secrets from OpenBao, and the policy and GitOps objects are later steps in the Kubernetes plan. The Loki,
Prometheus and OpenBao pieces are not built as subcharts: the plan's subchart approach needs remote chart downloads, which
this chart does not yet pin.
