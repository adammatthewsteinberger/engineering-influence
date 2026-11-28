# Running the stack on minikube

This runs the API, the worker, the schema migration, Postgres, RabbitMQ and SeaweedFS on a local minikube cluster, with
the image built on your machine. Nothing leaves the machine.

## Prerequisites

Docker, minikube, kubectl and Helm. Start a cluster with enough memory for the five pods:

```bash
minikube start --driver=docker --cpus=4 --memory=6144
```

## The External Secrets Operator (once per cluster)

The secrets live in OpenBao and reach the app through the External Secrets Operator, which is installed cluster-wide:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets --version 2.15.0 \
  -n external-secrets --create-namespace --set installCRDs=true
```

## Admission policies (optional, Kyverno)

Kyverno, installed cluster-wide, refuses pods in the labelled namespaces that run as root or are privileged, and reports
containers without a memory limit. `deploy/kyverno/policies.yaml` holds them; `up.sh` applies them when Kyverno is present.

```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno --version 3.10.0 -n kyverno --create-namespace
```

Check it refuses a root pod: `kubectl -n ei run roottest --image=busybox:1.37 --restart=Never --command -- sleep 5` is
denied with "pods in this namespace must run as non-root". Only new and updated pods are checked.

## CloudNativePG (optional)

`deploy/cnpg/cluster.yaml` is a two-instance PostgreSQL cluster run by the CloudNativePG operator. Verified on minikube
with operator chart 0.29.2 and a healthy cluster with a primary and a standby:

```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install cnpg cnpg/cloudnative-pg --version 0.29.2 -n cnpg-system --create-namespace
kubectl -n ei apply -f deploy/cnpg/cluster.yaml
kubectl -n ei wait cluster/ei-postgres --for=condition=Ready --timeout=600s
```

The app still uses the chart's own Postgres until its connection string is stored in OpenBao as `EI_DATABASE_URL`.

## Install

From the repository root, build the image and install the chart:

```bash
docker build -t ei-local:dev .
sh deploy/minikube/up.sh
```

`up.sh` loads the image into minikube, generates the passwords and API key into a private file, creates the `ei-secrets`
Secret, installs the chart with the local options, and waits for the migration and the two app rollouts.

Reach the API:

```bash
kubectl -n ei port-forward svc/ei-engineering-influence-api 8000:8000
curl localhost:8000/health/ready
```

The API key is in the synced Secret: `kubectl -n ei get secret ei-secrets -o jsonpath='{.data.EI_API_KEYS}' | base64 -d`.
The values themselves are in OpenBao's `secret/ei` path; OpenBao runs in dev mode here (in memory, with a known root token in `ei-openbao-token`), so
its contents do not survive a restart. Production runs its own OpenBao with storage and unsealing.

Remove the whole stack, its data included, with `sh deploy/minikube/down.sh`.

## Metrics and dashboards

`up.sh` also installs Prometheus and Grafana. Prometheus scrapes the API's `/metrics` with the dedicated metrics key in
the Secret (`EI_METRICS_API_KEY`). That key opens `/metrics` only: the API reads it as `EI_METRICS_API_KEYS`, and refuses it
on every other route; the main key is refused on `/metrics`. Prometheus accepts connections only from Grafana. Open them with:

```bash
kubectl -n ei port-forward svc/ei-engineering-influence-prometheus 9090:9090
kubectl -n ei port-forward svc/ei-engineering-influence-grafana 3000:3000
```

Grafana's user is `admin`, and its password is in the Secret: `kubectl -n ei get secret ei-secrets -o jsonpath='{.data.EI_GRAFANA_ADMIN_PASSWORD}' | base64 -d`.
Its Prometheus and Loki datasources are provisioned. Logs: Alloy reads this namespace's pods through the Kubernetes API and
ships them to Loki, so in Grafana's Explore, pick Loki and query `{namespace="ei"}` (or `{pod=~"ei-engineering-influence-api.*"}`).
Loki accepts connections only from Alloy and Grafana.

## Tracing

`up.sh` sets `tracing.enabled=true`, so Tempo runs too, and the API and the worker send their spans to it. To check that
traces arrive, forward Tempo's query port and search for the API's service:

```bash
kubectl -n ei port-forward svc/ei-engineering-influence-tempo 3200:3200
curl -s "http://127.0.0.1:3200/api/search?tags=service.name%3Dengineering-influence-api&limit=20"
```

Each request appears as a trace named for its route (for example `GET /v1/runs`), with its duration. Health probes and
metric scrapes appear too, since they are requests. Grafana's Tempo data source shows the same traces. A run's phases record
their own spans while the run executes. The settings are in [DEPLOYMENT.md](DEPLOYMENT.md#tracing).

## Traps this setup has hit

- **Reusing an image tag does not update running pods.** After rebuilding, give the image a new tag, for example
  `docker tag ei-local:dev ei-local:fix2`, load that tag into minikube, and upgrade with `--set image.tag=fix2`.
- **Re-running `up.sh` on an existing release generates new passwords,** but Postgres keeps the password it was first
  started with. Run `down.sh` first, or set the password in the database to match the Secret.
- **`helm install --wait` waits on the migration** (a post-install hook that needs the apps ready first), so `up.sh` does not
  use `--wait`.
- **The operator resolves names in its own namespace only:** the SecretStore uses the service's full `<name>.<namespace>.svc` address.
- **A failed migration Job stays listed** after it is fixed; delete the old Jobs before judging the new run.
- **An interrupted `up.sh` leaves a new password in the Secret** while Postgres and RabbitMQ keep the old ones. Either set the password inside the service to match the Secret (`ALTER USER` for Postgres, `rabbitmqctl change_password` for RabbitMQ), or run `down.sh`.
- **`helm upgrade --reuse-values` keeps only the release's old values;** a new block such as `observability` needs its image settings passed again.

## What is not covered here

The local stack runs the API and worker against SeaweedFS for run files. The book build needs the TeX image (see
[WORKER_IMAGE.md](WORKER_IMAGE.md)); the slim image here writes chapters but fails at `build`, as it does elsewhere.
