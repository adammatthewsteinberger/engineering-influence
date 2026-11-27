#!/usr/bin/env sh
# Regenerates the Kustomize base from the Helm chart's defaults, so the two stay in step. The migration Job loses
# its Helm hook annotations and its revision suffix, because Kustomize applies it as a plain Job.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
chart="$here/../helm/engineering-influence"
helm template ei "$chart" --set existingSecret=ei-secrets \
  | python3 "$here/strip_hooks.py" > "$here/base/resources.yaml"
echo "wrote $here/base/resources.yaml"
