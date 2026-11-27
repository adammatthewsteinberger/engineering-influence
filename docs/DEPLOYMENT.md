# Deploying on Kubernetes

The Helm chart in `deploy/helm/engineering-influence/` runs the API, the worker and the schema migration. Postgres and
RabbitMQ come from the cluster or an operator, or the chart can run them in-cluster (`postgres.enabled`,
`rabbitmq.enabled`). Either way the chart reads their URLs from one Secret. The objects below are the core ones; the
optional ones are listed after the table.

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

Optional objects, each behind its own value: the in-cluster Postgres and RabbitMQ (`postgres.enabled`, `rabbitmq.enabled`);
SeaweedFS for run files (`seaweedfs.enabled`, with its NetworkPolicy and bucket Job); OpenBao and the External Secrets
objects that copy its values into `existingSecret` (`openbao.enabled`); Prometheus, Grafana and the Loki and Alloy log
stack (`observability.enabled`, `logs.enabled`), with NetworkPolicies on Prometheus and Loki; Tempo for traces
(`tracing.enabled`, with its NetworkPolicy); a HorizontalPodAutoscaler for the API (`autoscaling.api.enabled`); and a
KEDA `ScaledObject` for the worker (`autoscaling.keda.enabled`). The chart has no Ingress, PodDisruptionBudget or
CronJob yet.

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

## Secrets from OpenBao

`openbao.enabled=true` syncs the app's values from OpenBao into `existingSecret`, through the External Secrets Operator
(which must be installed, with its CRDs). `openbao.devMode=true` (the default) deploys one in-memory OpenBao with a root
token from `openbao.bootstrapTokenSecret`: a local cluster only, and its data does not survive a restart. In production,
set `openbao.devMode=false` and `openbao.server` to an OpenBao you run; the chart then deploys no OpenBao and refuses to
render without a server. The SecretStore still authenticates with a token from `bootstrapTokenSecret`, so a scoped
auth method (Kubernetes or AppRole) is the next step before production use.

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

## Tracing

`tracing.enabled=true` runs Tempo in the namespace and points the API and the worker at it. Each API request becomes a
span, from the FastAPI instrumentation, and each run phase becomes a `run_phase` span carrying its artifact type, so a slow
request or a slow phase can be found in Grafana's Tempo data source. The apps read one setting, `EI_OTLP_ENDPOINT`: the chart
sets it to Tempo's OTLP/HTTP receiver, `http://<release>-engineering-influence-tempo:4318`. With the setting empty, nothing
is exported.

Tempo keeps traces on its volume (`tracing.tempo.storage`, default `5Gi`) and runs as one replica, so it suits a local
cluster or a trial, not a production store. It has no authentication: its NetworkPolicy admits spans only from the API and
the worker, and queries only from Grafana. Grafana's Tempo data source appears only with `observability.enabled=true`.

```bash
helm upgrade --install ei deploy/helm/engineering-influence \
  --set existingSecret=ei-secrets \
  --set observability.enabled=true \
  --set tracing.enabled=true
```

## Kustomize

Clusters that do not use Helm can apply `deploy/kustomize/overlays/dev` or `overlays/prod`. The base is the chart's
default render, regenerated by `deploy/kustomize/render-base.sh`; a test fails if the committed base drifts from the chart.
Each overlay sets its namespace (`ei-dev` or `ei`), its replica counts and its image tag:

```bash
kubectl apply -k deploy/kustomize/overlays/prod
```

The base expects the `ei-secrets` Secret in the overlay's namespace. The image is a placeholder repository; change the
overlay's `images` entry to yours.

## GitOps with Argo CD

`deploy/argocd/application.yaml` is an Argo CD `Application` that syncs `deploy/kustomize/overlays/dev` from the `develop`
branch of this repository into `ei-dev`. It prunes objects removed from git and reverts changes made in the cluster
(`selfHeal`), so git is the source of truth. Its namespace gets the `policy.ei/restricted=true` label, which the Kyverno
policies match. Install Argo CD (chart `argo-cd` 10.19.1, Argo CD v3.6.3) and the Application:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argocd argo/argo-cd --version 10.19.1 -n argocd --create-namespace --wait
kubectl apply -f deploy/argocd/project.yaml
kubectl apply -f deploy/argocd/application.yaml
```

The Application runs in the `engineering-influence` AppProject (`deploy/argocd/project.yaml`), which bounds it: it may
sync only this repository, deploy only into `ei-dev`, create no cluster-scoped objects, and create only the five kinds
the dev overlay renders (ConfigMap, Service, ServiceAccount, Deployment, Job). If the overlay gains a kind, add it to the
project's `namespaceResourceWhitelist` first, or the sync fails. Because the sync is automated, `develop` should require
reviewed pull requests, since a merge there reaches the cluster.

Argo CD does not create the `ei-secrets` Secret, because the values never live in git. Create it in `ei-dev` (for
example through the External Secrets Operator, as in [MINIKUBE.md](MINIKUBE.md)) before the pods can start. The overlay's
image is a placeholder registry path that must be pullable from the cluster, and the Application's sync status is
`Synced` only when git and the cluster agree.

To try a local image without changing git, override it on the live Application only, for example
`kubectl -n argocd patch application engineering-influence-dev --type merge -p '{"spec":{"source":{"kustomize":{"images":["ghcr.io/adammatthewsteinberger/engineering-influence=ei-local:tracing1"]}}}}'`.
Because `selfHeal` is on, Argo CD then reports the Deployments `OutOfSync` and restores the git image. A local override
therefore needs the image pushed to the registry the overlay names, or the change belongs in git.

## Not in this chart yet

The Loki, Prometheus and OpenBao pieces are not built as subcharts: the plan's subchart approach needs remote chart
downloads, which this chart does not yet pin.
