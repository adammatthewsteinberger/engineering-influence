#!/usr/bin/env sh
# Installs the whole stack on a local minikube cluster: the API, the worker, the migration, Postgres, RabbitMQ and
# SeaweedFS, with the image built on this machine. Run after `minikube start` and `docker build -t ei-local:dev .`.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
chart="$here/../helm/engineering-influence"
ns="${NS:-ei}"
rel="${REL:-ei}"
image="${IMAGE:-ei-local:dev}"

minikube image load "$image"
kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns" >/dev/null

# The secrets are generated here and written to a private file, so they are not on the command line or in shell history.
secrets="$(mktemp)"
trap 'rm -f "$secrets"' EXIT
chmod 600 "$secrets"
secret() { python3 -c 'import secrets, sys; print(secrets.token_urlsafe(int(sys.argv[1])))' "$1"; }
pg="$(secret 24)"; mq="$(secret 24)"; key="$(secret 32)"; s3id="ei$(secret 8)"; s3key="$(secret 32)"
host="$rel-engineering-influence"
cat > "$secrets" <<ENV
EI_DATABASE_URL=postgresql+psycopg://ei:$pg@$host-postgres:5432/ei
EI_RABBITMQ_URL=amqp://ei:$mq@$host-rabbitmq:5672/
EI_API_KEYS=$key
EI_POSTGRES_PASSWORD=$pg
EI_RABBITMQ_PASSWORD=$mq
EI_S3_ACCESS_KEY_ID=$s3id
EI_S3_SECRET_ACCESS_KEY=$s3key
ENV
kubectl create secret generic ei-secrets --namespace "$ns" --from-env-file="$secrets" \
  --dry-run=client -o yaml | kubectl apply --namespace "$ns" -f - >/dev/null

helm upgrade --install "$rel" "$chart" --namespace "$ns" \
  --set existingSecret=ei-secrets \
  --set image.repository="${image%%:*}" --set image.tag="${image#*:}" --set image.pullPolicy=Never \
  --set postgres.enabled=true --set rabbitmq.enabled=true \
  --set seaweedfs.enabled=true --set artifactStore.kind=s3 --set artifactStore.bucket=ei-artifacts \
  --set api.replicas=1 --set worker.replicas=1 \
  --wait --timeout 10m

echo "installed. The API key is in the secret: kubectl -n $ns get secret ei-secrets -o jsonpath='{.data.EI_API_KEYS}' | base64 -d"
echo "forward the API with: kubectl -n $ns port-forward svc/$host-api 8000:8000"
