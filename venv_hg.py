# Always-on задача для PythonAnywhere.
# Запускает Hermes gateway: бот в Telegram/Discord/Slack,
# OpenAI-совместимый прокси на локальном порту.
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

VENV = Path.home() / ".virtualenvs" / "hermes"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
HERMES_HOME.mkdir(parents=True, exist_ok=True)

PY = VENV / "bin" / "python"


def run(cmd, **kw):
    print(f"[venv_hg] >>> {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd, **kw)


def install_hermes():
    if not (VENV / "bin" / "hermes").exists():
        print("[venv_hg] creating venv and installing Hermes", flush=True)
        run(["python3.11", "-m", "venv", str(VENV)])
        run([str(PY), "-m", "pip", "install", "--upgrade", "pip"])
        # Hermes ставится прямо из GitHub, пока PyPI-релиз не догнал.
        run([str(PY), "-m", "pip", "install",
             "git+https://github.com/NousResearch/hermes-agent.git"])

    # Smoke-тест
    try:
        out = subprocess.check_output(
            [str(PY), "-m", "hermes_cli.main", "--version"],
            stderr=subprocess.STDOUT,
        ).decode().strip()
        print(f"[venv_hg] hermes cli ok: {out}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[venv_hg] hermes cli failed: {e.output}", flush=True)
        raise


def load_dotenv():
    env_file = HERMES_HOME / ".env"
    if not env_file.exists():
        env_file.write_text("# Заполни HERMES_HOME/.env на PythonAnywhere "
                            "через Bash-консоль.\n")
        print(f"[venv_hg] created stub {env_file}", flush=True)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def start_proxy():
    # PythonAnywhere пробрасывает наружу только web-приложение.
    # OpenAI-совместимый прокси слушает на 127.0.0.1:8000 — при желании
    # к нему можно обратиться из flask_app.py через внутренний HTTP.
    cmd = [
        str(PY), "-m", "hermes_cli.main", "proxy",
        "--host", "127.0.0.1", "--port", "8000",
    ]
    print(f"[venv_hg] starting proxy: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd, env=os.environ.copy())
    return proc


def watch(proc):
    proc.wait()
    print("[venv_hg] proxy exited; restarting in 5s", flush=True)
    time.sleep(5)


def main():
    install_hermes()
    load_dotenv()
    while True:
        proc = start_proxy()
        try:
            watch(proc)
        except KeyboardInterrupt:
            proc.terminate()
            return 0


if __name__ == "__main__":
    sys.exit(main())