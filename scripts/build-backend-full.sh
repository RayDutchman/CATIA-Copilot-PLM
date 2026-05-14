#!/bin/bash
# Full backend build + Docker image + redeploy.
# Use this on the FIRST build, or after any non-language code changes.
# After this completes, use build-i18n.sh for subsequent language-only updates.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "📥 Pulling latest code..."
cd "$REPO_ROOT"
git pull

echo "📦 Full Maven build (first run ~5-15 min, subsequent runs use cache)..."
cd "$REPO_ROOT/docdoku-plm-server"
mvn clean install -DskipTests

echo "🐳 Building Docker image: docdoku/docdoku-plm-server:2.6.2 ..."
docker build \
  --build-arg VERSION=2.6.2 \
  -f docker/Dockerfile \
  -t docdoku/docdoku-plm-server:2.6.2 \
  .

echo "🚀 Redeploying backend container..."
cd "$REPO_ROOT/docdoku-plm-docker"
docker compose up --force-recreate --no-deps -d back

echo "✅ Done. Monitor startup with: docker compose logs -f back"
