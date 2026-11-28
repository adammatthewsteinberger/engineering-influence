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
KEDA `ScaledObject` for the worker (`autoscaling.keda.enabled`); a NetworkPolicy for the API and the worker
(`networkPolicy.enabled`), which lets the API accept traffic only from the namespaces in `networkPolicy.apiIngressFrom` and
the worker accept none, with DNS and the egress in `networkPolicy.egress` added; and a PodDisruptionBudget for each of them
(`podDisruptionBudget.enabled`), allowing one pod down at a time. Both policy objects are off by default, because a policy
that is too narrow stops the app. The chart has no Ingress or CronJob yet.

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

CI runs these checks on every push (the `kubernetes` job in `.github/workflows/ci.yml`): `helm lint` and a `kubeconform`
validation of the render, once with the defaults and once with every optional object on; `kubectl kustomize` plus the same
validation for the `dev` and `prod` overlays; and a Trivy scan of the image that fails on fixable HIGH and CRITICAL
findings. `kubeconform` skips the CRDs it has no schema for (External Secrets, KEDA), so a typo in those objects is not
caught by CI; check them with `kubectl apply --dry-run=server` against a cluster that has the CRDs.

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
render without a server. The SecretStore authenticates with the token from `bootstrapTokenSecret` unless `openbao.auth` is `kubernetes`. Outside dev,
set `openbao.auth: kubernetes`: the operator then logs in as the chart's ServiceAccount through the OpenBao kubernetes auth
mount `openbao.kubernetes.mountPath` and role `openbao.kubernetes.role`. The platform configures that mount and role in OpenBao,
binding the role to the `ei-engineering-influence` ServiceAccount in the app's namespace. No root token is stored in the cluster.

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

`deploy/argocd/application.yaml` is an Argo CD `Application` that syncs the Helm chart in `deploy/helm/engineering-influence`,
with `values-dev.yaml`, from the `develop` branch of this repository into `ei-dev`. It prunes objects removed from git and
reverts changes made in the cluster (`selfHeal`), so git is the source of truth. Its namespace gets the
`policy.ei/restricted=true` label, which the Kyverno policies match. Install Argo CD (chart `argo-cd` 10.19.1, Argo CD v3.6.3)
and the Application:

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argocd argo/argo-cd --version 10.19.1 -n argocd --create-namespace --wait
kubectl apply -f deploy/argocd/project.yaml
kubectl apply -f deploy/argocd/application.yaml
```

The dev values put Postgres, OpenBao and the object store outside the chart, so they must exist before the first sync:

1. A Postgres and an S3-compatible store for dev, reachable from `ei-dev`. Their addresses go in the `EI_DATABASE_URL`,
   `EI_S3_*` and related keys below.
2. An OpenBao you run, and its address in `openbao.server` in `values-dev.yaml`. The chart refuses to render without it.
   The Application shows a render error until that address is set.
3. The app's values stored once in that OpenBao's KV path `secret/ei`, under the keys in `openbao.keys` (the chart's
   `values.yaml` lists them). The External Secrets Operator copies them into `ei-secrets` in `ei-dev`.

The sync then runs the chart's hooks in Argo CD's `PreSync` phase, in this order: the SecretStore and the ExternalSecret
(weight -10, so `ei-secrets` exists), then the migration Job (weight -5), and only then the Deployments. The migration
runs before the new pods start. `secretsAsPreSync` in `values-dev.yaml` turns the ExternalSecret into a hook; without
it, the chart creates the ExternalSecret as an ordinary resource, as the minikube install expects.

The Application runs in the `engineering-influence` AppProject (`deploy/argocd/project.yaml`), which bounds it: it may
sync only this repository, deploy only into `ei-dev`, create no cluster-scoped objects, and create only the seven kinds the
dev render makes (ConfigMap, Service, ServiceAccount, Deployment, Job, and the External Secrets SecretStore and
ExternalSecret). If the chart gains a kind, add it to the project's `namespaceResourceWhitelist` first, or the sync fails.
Because the sync is automated, `develop` should require reviewed pull requests, since a merge there reaches the cluster.

The `ei-secrets` Secret is created by the External Secrets Operator from OpenBao, never from git. The image is the release
tag `0.1.0rc1` in `values-dev.yaml`, which the registry must allow the cluster to pull. The Kustomize overlays under
`deploy/kustomize/overlays` remain for clusters that do not use Helm; the dev Application no longer syncs them.
## Not in this chart yet

The Loki, Prometheus and OpenBao pieces are not built as subcharts: the plan's subchart approach needs remote chart
downloads, which this chart does not yet pin.
