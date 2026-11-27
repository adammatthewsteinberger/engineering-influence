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
  --from-literal=EI_API_KEYS='replace-with-a-key-of-at-least-24-characters'
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

## Not in this chart yet

Autoscaling (KEDA for the worker, HPA for the API), Kustomize overlays, object storage (SeaweedFS), logs, metrics,
secrets from OpenBao, and the policy and GitOps objects are later steps in the Kubernetes plan.
