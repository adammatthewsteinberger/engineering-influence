#!/bin/sh
# The CLI the way you would use it in a terminal. Run from the repository root:
#
#   uv sync --extra runtime --extra api --extra publishing
#   EI="uv run ei" sh examples/cli/run.sh        # or, with the package installed: sh examples/cli/run.sh
#
# `ei pipeline start` is a local command: it uses in-memory adapters, so it validates and
# plans a pipeline and prints the result, but it does not reach the API, the database or
# the queue. Use the REST API, the SDK or MCP (see ../README.md) to run work on the stack.
set -eu

EI="${EI:-ei}"

echo "== version"
$EI --version

echo "== start a two-stage pipeline (JSON on stdout, ready for jq)"
$EI pipeline start \
  --slug sample-essay \
  --title "A Sample Essay" \
  --postulate "Claims must be supported by evidence." \
  --postulate "Persuasion must not outrun truth." \
  --stage thesis --stage book

echo "== a missing required flag is a usage error (exit 2), not a crash"
set +e
$EI pipeline start --slug only-a-slug 2>/dev/null
echo "exit status: $?"
set -e

echo "== serving fails closed without configuration (exit 2, no traceback)"
set +e
env -i PATH="$PATH" HOME="${HOME:-/tmp}" $EI serve api
echo "exit status: $?"
set -e

echo "== book commands: see what is available"
$EI book --help
