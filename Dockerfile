# Hermes Agent — Render Dockerfile
# Образ для Free Tier Render. Поднимает полный стек: CLI, gateway, dashboard.
#
# Hermes запрещает обычный `pip install` (см. hermes-src/setup.py). Разрешены
# только editable-install, shell installer, Docker-образ или Nix. Используем
# editable, но СТАВИМ ПОД ROOT, чтобы:
#   • бинарь `hermes` ушёл в /usr/local/bin (а не ~/.local/bin),
#   • пакет `hermes_cli` лёг в /usr/local/lib/python3.11/site-packages,
#   • шебанг бинаря указывал на /usr/local/bin/python — стабильный путь.
# Потом переключаемся на непривилегированного hermes — у него нет своего
# site-packages, поэтому import идёт в системный, всё находится.
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HERMES_HOME=/home/hermes/.hermes \
    HERMES_NO_UPDATE_CHECK=1

# Системные зависимости. git нужен для клонирования; tini корректно гасит
# SIGTERM от Render; tmux для TUI на продвинутых сценариях.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates tmux tini openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Клонируем исходники (нужны для editable-install — pip тянет метаданные
# из pyproject.toml + setup.py).
RUN git clone --depth 1 --recurse-submodules \
        https://github.com/NousResearch/hermes-agent.git /opt/hermes-src

# Editable install под ROOT — гарантирует системные пути, которые не зависят
# от пользователя.
#
# ВАЖНО: /opt/hermes-src НЕЛЬЗЯ удалять после установки.
# setuptools editable-install для проектов с [tool.setuptools.packages.find]
# создаёт .pth-файл в site-packages, который на каждом импорте добавляет
# /opt/hermes-src в sys.path. Удалишь — ModuleNotFoundError.
RUN pip install --no-cache-dir -e /opt/hermes-src

# Sanity-check: после установки бинарь должен лежать в /usr/local/bin и
# `hermes --help` должен работать ещё до переключения пользователя.
RUN which hermes && hermes --help >/dev/null && echo "[dockerfile] hermes CLI ok"

# Непривилегированный пользователь — Render запускает контейнеры под non-root.
RUN useradd -m -s /bin/bash hermes \
 && mkdir -p /home/hermes/.hermes \
 && chown -R hermes:hermes /home/hermes

USER hermes
WORKDIR /home/hermes

# Документация и конфиги приложения.
COPY --chown=hermes:hermes start.sh       /home/hermes/start.sh
COPY --chown=hermes:hermes .env.example   /home/hermes/.env.example
COPY --chown=hermes:hermes README.md      /home/hermes/README.md

RUN chmod +x /home/hermes/start.sh

# Render прокидывает порт в $PORT. По умолчанию — 10000 для web service.
EXPOSE 10000

# tini корректно обрабатывает SIGTERM от Render при редеплое/усыплении.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/home/hermes/start.sh"]