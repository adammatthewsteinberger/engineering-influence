#!/usr/bin/env sh
# Removes the local stack and its data. The namespace is deleted, so the Postgres and SeaweedFS volumes go with it.
set -eu
ns="${NS:-ei}"
helm uninstall "${REL:-ei}" --namespace "$ns" || true
kubectl delete namespace "$ns" --ignore-not-found
