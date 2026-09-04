import os
import shutil
import subprocess
import tempfile
import threading
import time

from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

MAX_CODE_SIZE = 100_000
MAX_RUNTIME = 10


def send_json(ws, data):
    import json
    ws.send(json.dumps(data))


@sock.route("/run")
def run_java(ws):
    workdir = tempfile.mkdtemp(prefix="codeforge-")

    process = None

    try:
        send_json(ws, {
            "type": "status",
            "message": "Preparing Java..."
        })

        message = ws.receive()

        if not message:
            return

        import json

        request = json.loads(message)
        code = request.get("code", "")

        if not isinstance(code, str):
            send_json(ws, {
                "type": "error",
                "message": "Invalid Java source."
            })
            return

        if not code.strip():
            send_json(ws, {
                "type": "error",
                "message": "Please enter Java code."
            })
            return

        if len(code) > MAX_CODE_SIZE:
            send_json(ws, {
                "type": "error",
                "message": "Java source is too large."
            })
            return

        source_path = os.path.join(workdir, "Main.java")

        with open(source_path, "w", encoding="utf-8") as file:
            file.write(code)

        send_json(ws, {
            "type": "status",
            "message": "Compiling..."
        })

        compile_result = subprocess.run(
            ["javac", "Main.java"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=MAX_RUNTIME
        )

        if compile_result.returncode != 0:
            send_json(ws, {
                "type": "compile_error",
                "output": compile_result.stderr
            })
            return

        send_json(ws, {
            "type": "status",
            "message": "Running..."
        })

        process = subprocess.Popen(
            ["java", "-Xmx128m", "-Xss256k", "Main"],
            cwd=workdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        def read_output():
            try:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        send_json(ws, {
                            "type": "output",
                            "data": line
                        })

                process.stdout.close()

            except Exception:
                pass

        output_thread = threading.Thread(
            target=read_output,
            daemon=True
        )

        output_thread.start()

        start_time = time.time()

        while process.poll() is None:

            if time.time() - start_time > MAX_RUNTIME:
                process.kill()

                send_json(ws, {
                    "type": "error",
                    "message": "Program exceeded the 10 second limit."
                })

                return

            try:
                ws.settimeout(0.2)
                incoming = ws.receive()

                if incoming:
                    data = json.loads(incoming)

                    if data.get("type") == "input":
                        value = data.get("data", "")

                        if process.stdin:
                            process.stdin.write(value + "\n")
                            process.stdin.flush()

            except Exception:
                pass

        return_code = process.returncode

        send_json(ws, {
            "type": "exit",
            "code": return_code
        })

    except subprocess.TimeoutExpired:
        if process:
            process.kill()

        send_json(ws, {
            "type": "error",
            "message": "Compilation or execution timed out."
        })

    except Exception as exc:
        send_json(ws, {
            "type": "error",
            "message": str(exc)
        })

    finally:
        if process and process.poll() is None:
            process.kill()

        shutil.rmtree(workdir, ignore_errors=True)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "CodeForge Java Runner"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))

    from waitress import serve

    serve(
        app,
        host="0.0.0.0",
        port=port
    )
