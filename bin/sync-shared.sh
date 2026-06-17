#!/usr/bin/env bash
# Vendor the shared backend module into each service folder.
#
# backend/_shared/shared is the single source of truth. It is copied into each
# deployable service (backend/<service>/shared) so it ships inside that service's
# own Lambda deployment package — this works identically for LocalStack
# hot-reload (which mounts the service folder) and the AWS function zip.
# A Lambda layer would avoid the copy, but the workshop participant role is not
# granted lambda:PublishLayerVersion. The vendored copies are git-ignored by each
# service's .gitignore; only backend/_shared/shared is tracked.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" > /dev/null 2>&1 || exit 1; pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." > /dev/null 2>&1 || exit 1; pwd -P)"
SOURCE="$PROJECT_ROOT/backend/_shared/shared"

if [ ! -d "$SOURCE" ]; then
    echo "ERROR: shared module not found at $SOURCE"
    exit 1
fi

shopt -s nullglob
for fn in "$PROJECT_ROOT"/backend/*/function.py; do
    svc_dir="$(dirname "$fn")"
    base="$(basename "$svc_dir")"
    case "$base" in _*|.*) continue ;; esac
    rm -rf "$svc_dir/shared"
    cp -r "$SOURCE" "$svc_dir/shared"
    echo "  synced shared -> backend/$base/shared"
done
shopt -u nullglob

echo "Shared module vendored into all services."
