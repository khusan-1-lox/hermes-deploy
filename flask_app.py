# Flask-приложение для бесплатного web-слота PythonAnywhere.
# Показывает "Hermes up" и healthcheck; полноценный dashboard живёт
# в always_on задаче через hermes proxy на отдельном порту.
from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify(
        service="hermes-agent",
        status="ok",
        host=os.environ.get("HERMES_PYTHONANYWHERE_HOST", ""),
        message="Hermes gateway живёт в always_on задаче. См. README.",
    )


@app.route("/healthz")
def healthz():
    return jsonify(status="ok"), 200


@app.route("/v1/models")
def models():
    # Прокси-совместимый endpoint — Render healthcheck на это и опирается.
    return jsonify(
        object="list",
        data=[
            {"id": "hermes", "object": "model", "created": 0, "owned_by": "nous"}
        ],
    )