# Running the stack on minikube

This runs the API, the worker, the schema migration, Postgres, RabbitMQ and SeaweedFS on a local minikube cluster, with
the image built on your machine. Nothing leaves the machine.

## Prerequisites

Docker, minikube, kubectl and Helm. Start a cluster with enough memory for the five pods:

```bash
minikube start --driver=docker --cpus=4 --memory=6144
```

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

The API key is in the Secret: `kubectl -n ei get secret ei-secrets -o jsonpath='{.data.EI_API_KEYS}' | base64 -d`.

Remove the whole stack, its data included, with `sh deploy/minikube/down.sh`.

## Traps this setup has hit

- **Reusing an image tag does not update running pods.** After rebuilding, give the image a new tag, for example
  `docker tag ei-local:dev ei-local:fix2`, load that tag into minikube, and upgrade with `--set image.tag=fix2`.
- **Re-running `up.sh` on an existing release generates new passwords,** but Postgres keeps the password it was first
  started with. Run `down.sh` first, or set the password in the database to match the Secret.
- **`helm install --wait` waits on the migration** (a post-install hook that needs the apps ready first), so `up.sh` does not
  use `--wait`.
- **A failed migration Job stays listed** after it is fixed; delete the old Jobs before judging the new run.

## What is not covered here

The local stack runs the API and worker against SeaweedFS for run files. The book build needs the TeX image (see
[WORKER_IMAGE.md](WORKER_IMAGE.md)); the slim image here writes chapters but fails at `build`, as it does elsewhere.
