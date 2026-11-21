#!/bin/sh
# Starts a throwaway PostgreSQL and RabbitMQ for the integration tests and prints the settings.
#
#   eval "$(sh tests/integration/stack.sh up)"   # start, then export the two URLs
#   uv run pytest -m integration
#   eval "$(sh tests/integration/stack.sh env)"  # export the URLs again from the running stack
#   sh tests/integration/stack.sh down            # remove both containers
#
# Credentials are random and live only in the printed URLs. Ports are chosen by Docker and
# bound to 127.0.0.1. Progress goes to stderr so `eval` sees only the export lines.
set -eu

NAME="${EI_IT_NAME:-ei-it}"

wait_healthy() {
  container="$1"
  for _ in $(seq 1 90); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo missing)"
    [ "$status" = healthy ] && return 0
    sleep 1
  done
  echo "error: $container did not become healthy" >&2
  docker logs --tail 20 "$container" >&2 || true
  return 1
}

host_port() {
  docker port "$1" "$2/tcp" | head -n 1 | sed 's/.*://'
}

container_env() {
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$1" | sed -n "s/^$2=//p"
}

print_exports() {
  pg_password="$(container_env "$NAME-pg" POSTGRES_PASSWORD)"
  mq_password="$(container_env "$NAME-mq" RABBITMQ_DEFAULT_PASS)"
  echo "export EI_TEST_DATABASE_URL='postgresql+psycopg://ei:$pg_password@127.0.0.1:$(host_port "$NAME-pg" 5432)/ei'"
  echo "export EI_TEST_RABBITMQ_URL='amqp://ei:$mq_password@127.0.0.1:$(host_port "$NAME-mq" 5672)/'"
}

case "${1:-}" in
  up)
    docker rm -f "$NAME-pg" "$NAME-mq" >/dev/null 2>&1 || true
    pg_password="$(openssl rand -hex 16)"
    mq_password="$(openssl rand -hex 16)"
    echo "starting postgres and rabbitmq..." >&2
    docker run -d --name "$NAME-pg" \
      -e POSTGRES_USER=ei -e POSTGRES_PASSWORD="$pg_password" -e POSTGRES_DB=ei \
      -p 127.0.0.1::5432 \
      --health-cmd "pg_isready -U ei -d ei" --health-interval 2s --health-retries 45 \
      postgres:18-alpine >/dev/null
    docker run -d --name "$NAME-mq" \
      -e RABBITMQ_DEFAULT_USER=ei -e RABBITMQ_DEFAULT_PASS="$mq_password" \
      -p 127.0.0.1::5672 \
      --health-cmd "rabbitmq-diagnostics -q ping" --health-interval 3s --health-retries 45 \
      rabbitmq:4-alpine >/dev/null
    wait_healthy "$NAME-pg"
    wait_healthy "$NAME-mq"
    print_exports
    ;;
  env)
    print_exports
    ;;
  down)
    docker rm -f "$NAME-pg" "$NAME-mq" >/dev/null 2>&1 || true
    echo "removed $NAME-pg and $NAME-mq" >&2
    ;;
  *)
    echo "usage: sh tests/integration/stack.sh up|env|down" >&2
    exit 2
    ;;
esac
