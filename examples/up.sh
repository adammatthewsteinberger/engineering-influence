#!/bin/sh
# Start the whole stack (Postgres, RabbitMQ, API, worker) with generated credentials.
#
#   sh examples/up.sh                 # first run creates examples/.env, then builds and starts
#   set -a; . examples/.env; set +a   # export EI_BASE_URL, EI_API_KEY, EI_WEBHOOK_SECRET
#
# Needs Docker with the compose plugin and python3 (only to generate random values).
set -eu

cd "$(dirname "$0")"

if [ -f .env ]; then
  echo "using the existing examples/.env"
else
  secret() { python3 -c 'import secrets; print(secrets.token_hex(24))'; }
  KEY="$(secret)"
  {
    echo "POSTGRES_PASSWORD=$(secret)"
    echo "RABBITMQ_PASSWORD=$(secret)"
    echo "EI_API_KEYS=$KEY"
    echo "# Read by the example scripts, not by the stack:"
    echo "EI_API_KEY=$KEY"
    echo "EI_BASE_URL=http://127.0.0.1:8000"
    echo "EI_WEBHOOK_SECRET=$(secret)"
  } > .env
  chmod 600 .env
  echo "wrote examples/.env with fresh credentials (it is git-ignored)"
fi

docker compose --env-file .env up -d --build --wait

cat <<'EOF'

The stack is up. API: http://127.0.0.1:8000  (health: /health/ready)

  set -a; . examples/.env; set +a
  uv run examples/api/start_pipeline.py

Stop it with: sh examples/down.sh      (add --volumes to delete the data too)
EOF
