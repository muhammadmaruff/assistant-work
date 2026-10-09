#!/usr/bin/env bash
# Clone OpenShorts ke /workspaces/openshorts dan siapkan .env
set -euo pipefail
DIR=/workspaces/openshorts
if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 https://github.com/mutonby/openshorts.git "$DIR"
fi
cd "$DIR"
[ -f .env ] || cp .env.example .env
# Vite hanya mengizinkan host openshorts.app; tambahkan domain port-forward Codespaces
grep -q "app.github.dev" dashboard/vite.config.js || \
  sed -i "s/allowedHosts: \[/allowedHosts: [\n      '.app.github.dev',/" dashboard/vite.config.js
