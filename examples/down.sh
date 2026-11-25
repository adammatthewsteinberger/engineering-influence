#!/bin/sh
# Stop the example stack. Pass --volumes to delete the Postgres and RabbitMQ data as well.
set -eu

cd "$(dirname "$0")"
exec docker compose --env-file .env down --remove-orphans "$@"
