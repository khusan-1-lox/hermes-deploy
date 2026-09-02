# Hermes Agent — деплой на Render (Docker) и PythonAnywhere

Этот репозиторий — готовый шаблон для развёртывания Hermes Agent в облаке
двумя способами на выбор.

## Содержимое

| Файл | Назначение |
|---|---|
| `Dockerfile` + `start.sh` + `render.yaml` | Деплой на Render Free Tier (Docker web service) |
| `flask_app.py` + `venv_hg.py` + `pa_requirements.txt` | Деплой на PythonAnywhere (web + always-on) |
| `.env.example` | Шаблон переменных окружения |

## Render — путь за 5 минут

1. Открой https://render.com → Sign up with GitHub.
2. New → Blueprint → укажи репозиторий `khusan-1-lox/hermes-deploy`.
3. Render сам прочитает `render.yaml` и поднимет сервис `hermes-agent`
   на плане Free в регионе Oregon.
4. В Dashboard сервиса → Environment → добавь ключи:
   - `OPENROUTER_API_KEY` — бесплатный ключ с https://openrouter.ai/keys
   - `TELEGRAM_BOT_TOKEN` (опционально) — от @BotFather
5. Дождись первого билда (~5–8 минут из-за `pip install -e .`).
6. Открой выданный URL вида `https://hermes-agent-xxxx.onrender.com/v1/models` —
   должен вернуться JSON со списком моделей.

Render Free Tier засыпает после 15 минут простоя. Первый запрос после сна
займёт ~30 секунд на холодный старт. Если нужен always-on — апгрейд до
Starter ($7/мес) или используй PythonAnywhere.

## PythonAnywhere — путь за 10 минут

1. https://www.pythonanywhere.com → Create a Beginner account (бесплатно).
2. Web → Add a new web app → Manual configuration → Python 3.11.
3. Source code: `/home/<user>/hermes-deploy`. WSGI: загрузи `flask_app.py`.
4. Открой Bash-консоль PA и выполни:
   ```bash
   git clone https://github.com/khusan-1-lox/hermes-deploy.git
   cd hermes-deploy
   mkvirtualenv --python=python3.11 hermes
   pip install -r pa_requirements.txt
   ```
5. Заполни `~/.hermes/.env` ключами (см. `.env.example`).
6. Always-On tasks (платная подписка, $5/мес) → Add a new always-on task,
   указав команду:
   ```
   workon hermes && python /home/<user>/hermes-deploy/venv_hg.py
   ```
   Это запустит Hermes gateway, который подхватит токены Telegram/Discord.

На бесплатном аккаунте always-on задач нет, но web-сайт работает — Flask
покажет "Hermes up" и будет принимать healthcheck'и.

## Локальная проверка

```bash
git clone https://github.com/khusan-1-lox/hermes-deploy.git
cd hermes-deploy
docker build -t hermes-agent .
docker run --rm -p 8000:8000 \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  -e HERMES_MODEL=openrouter/deepseek/deepseek-chat-v3.1:free \
  hermes-agent
curl http://localhost:8000/v1/models
```

## Переменные окружения

| Ключ | Зачем |
|---|---|
| `OPENROUTER_API_KEY` | Провайдер (рекомендуется бесплатный) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Альтернативные провайдеры |
| `HERMES_MODEL` | Модель по умолчанию |
| `TELEGRAM_BOT_TOKEN` | Telegram-шлюз |
| `DISCORD_BOT_TOKEN` | Discord-шлюз |
| `SLACK_BOT_TOKEN` | Slack-шлюз |
| `WHATSAPP_TOKEN` | WhatsApp-шлюз |

## Что я не сделаю без тебя

- Зарегистрировать аккаунт на Render / PythonAnywhere.
- Залить туда API-ключи провайдера.
- Оплатить always-on задачу на PythonAnywhere, если нужна.

Регистрация на обоих сервисах делается через GitHub-логин в один клик.