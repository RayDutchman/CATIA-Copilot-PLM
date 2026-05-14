#!/bin/bash
# Step 0: Build the private base image (docdoku/docdoku-plm-server-base:2.6.2)
# Only needs to run once; re-run only if you cleared Docker image cache.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔨 Building base image: docdoku/docdoku-plm-server-base:2.6.2 ..."
docker build \
  -f "$REPO_ROOT/docdoku-plm-server/docker/payara/Dockerfile" \
  -t docdoku/docdoku-plm-server-base:2.6.2 \
  "$REPO_ROOT/docdoku-plm-server/docker/payara/"

echo "✅ Base image built successfully."
