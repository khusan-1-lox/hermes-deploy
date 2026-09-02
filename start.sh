#!/usr/bin/env bash
# Hermes на Render: поднимает прокси OpenAI-совместимое API на $PORT,
# плюс стартует gateway в фоне для мессенджеров (если есть токены).
set -euo pipefail

cd /home/hermes

# `hermes` ставится editable в /usr/local/bin под root на этапе сборки —
# он доступен всем пользователям, включая hermes, под которым мы сейчас.
HERMES_BIN="$(command -v hermes || echo 'python -m hermes_cli.main')"
echo "[start] using hermes binary: ${HERMES_BIN}"

# Hermes setup идемпотентен: если конфиг уже есть, повторный setup пропускает шаги.
if [ ! -f "${HERMES_HOME}/config.yaml" ]; then
  echo "[start] first boot — running non-interactive setup"
  ${HERMES_BIN} config set display.interface cli || true
fi

echo "[start] HERMES_HOME=${HERMES_HOME}  PORT=${PORT:-10000}"
echo "[start] starting hermes proxy on :${PORT:-10000}"

# OpenAI-совместимый HTTP-сервер. Render Free Tier даёт PORT=10000.
exec ${HERMES_BIN} proxy --host 0.0.0.0 --port "${PORT:-10000}"