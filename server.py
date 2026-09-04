import os
from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

RUNNER_URL = os.environ.get("RUNNER_URL", "")


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def config():
    return {
        "runnerConfigured": bool(RUNNER_URL)
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
