#!/usr/bin/env bash
# Hermes на Render: поднимает прокси OpenAI-совместимое API на $PORT,
# плюс стартует gateway в фоне для мессенджеров (если есть токены).
set -euo pipefail

cd /home/hermes

# Render Free Tier засыпает после 15 минут idle. Hermes setup идемпотентен —
# если config уже есть, повторный setup просто пропустит шаги.
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  echo "[start] first boot — running non-interactive setup"
  hermes config set display.interface cli || true
fi

echo "[start] HERMES_HOME=$HERMES_HOME  PORT=${PORT:-8000}"
echo "[start] starting hermes proxy on :${PORT:-8000}"

# OpenAI-совместимый HTTP-сервер. Render даёт PORT; тащим его сюда.
exec hermes proxy --host 0.0.0.0 --port "${PORT:-8000}"