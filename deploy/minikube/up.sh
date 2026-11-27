#!/usr/bin/env sh
# Installs the whole stack on a local minikube cluster: the API, the worker, the migration, Postgres, RabbitMQ,
# SeaweedFS, Prometheus, Grafana, Loki and Alloy, with the image built on this machine. The secrets live in OpenBao
# (dev mode, local only) and the External Secrets Operator copies them into the ei-secrets Secret. Run after
# `minikube start` and `docker build -t ei-local:dev .`.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
chart="$here/../helm/engineering-influence"
ns="${NS:-ei}"
rel="${REL:-ei}"
image="${IMAGE:-ei-local:dev}"

if ! kubectl get crd externalsecrets.external-secrets.io >/dev/null 2>&1; then
  echo "The External Secrets Operator is not installed. Install it first:" >&2
  echo "  helm repo add external-secrets https://charts.external-secrets.io && helm install external-secrets external-secrets/external-secrets --version 2.15.0 -n external-secrets --create-namespace --set installCRDs=true" >&2
  exit 1
fi

minikube image load "$image"
kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns" >/dev/null

# The values are generated here and written to a private file: not on the command line, not in shell history.
values="$(mktemp)"
trap 'rm -f "$values"' EXIT
chmod 600 "$values"
secret() { python3 -c 'import secrets, sys; print(secrets.token_urlsafe(int(sys.argv[1])))' "$1"; }
pg="$(secret 24)"; mq="$(secret 24)"; key="$(secret 32)"; metrics="$(secret 32)"; grafana="$(secret 24)"
s3id="ei$(secret 8)"; s3key="$(secret 32)"
host="$rel-engineering-influence"
cat > "$values" <<ENV
EI_DATABASE_URL=postgresql+psycopg://ei:$pg@$host-postgres:5432/ei
EI_RABBITMQ_URL=amqp://ei:$mq@$host-rabbitmq:5672/
EI_API_KEYS=$key
EI_METRICS_API_KEY=$metrics
EI_GRAFANA_ADMIN_PASSWORD=$grafana
EI_POSTGRES_PASSWORD=$pg
EI_RABBITMQ_PASSWORD=$mq
EI_S3_ACCESS_KEY_ID=$s3id
EI_S3_SECRET_ACCESS_KEY=$s3key
ENV

# The bootstrap token for the dev OpenBao is its own Secret: the operator overwrites ei-secrets.
kubectl -n "$ns" get secret ei-openbao-token >/dev/null 2>&1 || \
  kubectl -n "$ns" create secret generic ei-openbao-token \
    --from-literal=EI_OPENBAO_ROOT_TOKEN="ei-$(secret 24)" >/dev/null

# Two passes. Helm waits for hooks even without --wait, and the migration needs ei-secrets, which needs the values
# stored in OpenBao. So the first pass skips the hooks, and the second, an upgrade, runs the migration once the secret exists.
set_flags="--set existingSecret=ei-secrets \
  --set openbao.enabled=true --set openbao.bootstrapTokenSecret=ei-openbao-token \
  --set image.repository=${image%%:*} --set image.pullPolicy=Never --set image.tag=${image#*:} \
  --set postgres.enabled=true --set rabbitmq.enabled=true --set observability.enabled=true --set logs.enabled=true \
  --set seaweedfs.enabled=true --set artifactStore.kind=s3 --set artifactStore.bucket=ei-artifacts \
  --set api.replicas=1 --set worker.replicas=1"
# shellcheck disable=SC2086
helm upgrade --install "$rel" "$chart" --namespace "$ns" --no-hooks $set_flags

# OpenBao first, then its values, then the operator's sync into ei-secrets. Nothing waits on the migration here: it is a
# post-install hook and the apps cannot be ready before it has run.
kubectl -n "$ns" rollout status "deploy/$rel-engineering-influence-openbao" --timeout=300s
python3 -c 'import json, sys
pairs = dict(line.split("=", 1) for line in open(sys.argv[1]).read().splitlines() if line)
print(json.dumps(pairs))' "$values" \
  | kubectl -n "$ns" exec -i "deploy/$rel-engineering-influence-openbao" -- \
      sh -c 'cat > /tmp/ei.json && BAO_ADDR=http://127.0.0.1:8200 BAO_TOKEN="$EI_OPENBAO_ROOT_TOKEN" bao kv put -mount=secret ei @/tmp/ei.json >/dev/null && rm -f /tmp/ei.json'
kubectl -n "$ns" annotate externalsecret ei-secrets force-sync="$(date +%s)" --overwrite >/dev/null
kubectl -n "$ns" wait --for=condition=Ready externalsecret/ei-secrets --timeout=300s

# shellcheck disable=SC2086
helm upgrade "$rel" "$chart" --namespace "$ns" $set_flags
# Helm waits for the post-upgrade migration hook itself, and deletes its Job once it succeeds.
for deploy in api worker; do
  kubectl -n "$ns" rollout status "deploy/$rel-engineering-influence-$deploy" --timeout=600s
done

echo "installed. The API key is in the synced secret: kubectl -n $ns get secret ei-secrets -o jsonpath='{.data.EI_API_KEYS}' | base64 -d"
echo "forward the API with: kubectl -n $ns port-forward svc/$rel-engineering-influence-api 8000:8000"
