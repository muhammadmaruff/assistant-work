#!/usr/bin/env bash
# Build & jalankan semua service OpenShorts di background
set -euo pipefail
cd /workspaces/openshorts
# Tunggu docker daemon (docker-in-docker) siap
for i in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker compose up -d --build
echo "OpenShorts jalan. Buka tab PORTS -> 5175 (Dashboard). Log: docker compose -f /workspaces/openshorts/docker-compose.yml logs -f"
