# Hermes Agent — Render Dockerfile
# Образ для Free Tier Render. Поднимает полный стек: CLI, gateway, dashboard.
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HERMES_HOME=/home/hermes/.hermes \
    HERMES_NO_UPDATE_CHECK=1

# Системные зависимости: tmux нужен для TUI, git — для установки Hermes,
# curl/ca-certificates — для инсталлятора и OpenAI-совместимого прокси.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates tmux tini openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Непривилегированный пользователь — Render запускает контейнеры под non-root,
# а Hermes setup лучше делать не от root.
RUN useradd -m -s /bin/bash hermes

USER hermes
WORKDIR /home/hermes

# Сначала ставим сам Hermes CLI, чтобы слой кэшировался.
# Клонируем в /tmp/hermes-src, затем ставим через pip editable —
# так не упираемся в непустой WORKDIR от COPY ниже.
RUN git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-src \
 && pip install --no-build-isolation -e /tmp/hermes-src \
 && rm -rf /tmp/hermes-src/.git

# Конфиги приложения подкладываем ПОСЛЕ установки пакета.
COPY --chown=hermes:hermes start.sh /home/hermes/start.sh
COPY --chown=hermes:hermes .env.example /home/hermes/.env.example
COPY --chown=hermes:hermes README.md /home/hermes/README.md

RUN chmod +x /home/hermes/start.sh

# Render прокидывает порт в $PORT. По умолчанию — 8000 для dashboard/proxy.
EXPOSE 8000

# tini корректно обрабатывает SIGTERM от Render при редеплое/усыплении.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/home/hermes/start.sh"]