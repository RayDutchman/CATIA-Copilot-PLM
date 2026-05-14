#!/bin/bash
# Quick language-only rebuild + Docker image + redeploy.
# Only rebuilds the i18n module and reassembles the EAR.
# Prerequisites: build-backend-full.sh must have been run at least once
#               so other modules are installed in ~/.m2.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "📥 Pulling latest code..."
cd "$REPO_ROOT"
git pull

echo "📦 Building language modules only (docdoku-plm-server-i18n + ear)..."
cd "$REPO_ROOT/docdoku-plm-server"
mvn clean package -DskipTests \
  -pl docdoku-plm-server-i18n,docdoku-plm-server-ear

echo "🐳 Rebuilding Docker image: docdoku/docdoku-plm-server:2.6.2 ..."
docker build \
  --build-arg VERSION=2.6.2 \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-server:2.6.2 \
  .

echo "🚀 Redeploying backend container..."
cd "$REPO_ROOT/docdoku-plm-docker"
docker compose up --force-recreate --no-deps -d back

echo "✅ Done. Monitor startup with: docker compose logs -f back"
