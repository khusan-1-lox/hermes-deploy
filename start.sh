#!/usr/bin/env bash
# Hermes на Render: поднимает OpenAI-совместимый HTTP-прокси на $PORT,
# который добавляет OPENROUTER_API_KEY к исходящим запросам.
#
# Используем кастомный прокси (hermes_proxy.py), а не встроенный
# `hermes proxy`, потому что тот работает только с OAuth-провайдерами
# Nous/xAI, а нам нужен произвольный API-ключ.
set -euo pipefail

cd /home/hermes

# Инициализация конфига Hermes (идемпотентна: повторный запуск ничего
# не перезаписывает). Нужна, чтобы gateway/CLI корректно находили config.
HERMES_BIN="$(command -v hermes || echo 'python -m hermes_cli.main')"
if [ ! -f "${HERMES_HOME}/config.yaml" ]; then
  echo "[start] first boot — initialising Hermes config"
  ${HERMES_BIN} config set display.interface cli || true
fi

echo "[start] starting hermes_proxy on :${PORT:-10000} (model=${HERMES_MODEL:-openrouter/auto})"
exec python /home/hermes/hermes_proxy.py