import os
import time
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

JUDGE0_URL = os.environ.get("JUDGE0_URL", "https://ce.judge0.com").rstrip("/")
JUDGE0_AUTH_TOKEN = os.environ.get("JUDGE0_AUTH_TOKEN", "")
JAVA_LANGUAGE_ID = 62

MAX_CODE_CHARS = 100_000
MAX_INPUT_CHARS = 20_000
POLL_SECONDS = 0.25
MAX_WAIT_SECONDS = 8

def judge_headers():
    headers = {"Content-Type": "application/json"}
    if JUDGE0_AUTH_TOKEN:
        headers["X-Auth-Token"] = JUDGE0_AUTH_TOKEN
    return headers

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/run")
def run_code():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    stdin = data.get("stdin", "")

    if not isinstance(code, str) or not code.strip():
        return jsonify(error="Please enter Java code."), 400

    if len(code) > MAX_CODE_CHARS:
        return jsonify(error="Code is too large."), 400

    if not isinstance(stdin, str):
        return jsonify(error="Invalid input."), 400

    if len(stdin) > MAX_INPUT_CHARS:
        return jsonify(error="Input is too large."), 400

    payload = {
        "language_id": JAVA_LANGUAGE_ID,
        "source_code": code,
        "stdin": stdin,
        "cpu_time_limit": 2,
        "wall_time_limit": 5,
        "memory_limit": 128000
    }

    try:
        response = requests.post(
            f"{JUDGE0_URL}/submissions?base64_encoded=false&wait=false",
            json=payload,
            headers=judge_headers(),
            timeout=10
        )
        response.raise_for_status()

        token = response.json().get("token")

        if not token:
            return jsonify(
                error="Compiler service did not return a submission token."
            ), 502

        deadline = time.monotonic() + MAX_WAIT_SECONDS

        while time.monotonic() < deadline:
            result = requests.get(
                f"{JUDGE0_URL}/submissions/{token}?base64_encoded=false"
                "&fields=stdout,stderr,compile_output,message,status,time,memory",
                headers=judge_headers(),
                timeout=10
            )

            result.raise_for_status()
            item = result.json()

            status = (item.get("status") or {}).get(
                "description", "Unknown"
            )

            if status not in {"In Queue", "Processing"}:
                output_parts = []

                if item.get("compile_output"):
                    output_parts.append(
                        "COMPILE ERROR\n" + item["compile_output"]
                    )

                if item.get("stdout"):
                    output_parts.append(item["stdout"])

                if item.get("stderr"):
                    output_parts.append(
                        "ERROR\n" + item["stderr"]
                    )

                if item.get("message"):
                    output_parts.append(
                        "MESSAGE\n" + item["message"]
                    )

                output = "\n".join(output_parts).strip()

                if not output:
                    output = f"Status: {status}"

                return jsonify(
                    ok=(status == "Accepted"),
                    status=status,
                    output=output,
                    time=item.get("time"),
                    memory=item.get("memory")
                )

            time.sleep(POLL_SECONDS)

        return jsonify(
            ok=False,
            status="Timed out waiting for compiler service",
            output="The compiler service is busy. Please try again."
        ), 504

    except requests.RequestException as exc:
        return jsonify(
            ok=False,
            status="Compiler service unavailable",
            output=f"Could not reach the compiler service: {exc}"
        ), 502

@app.get("/health")
def health():
    return jsonify(ok=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
