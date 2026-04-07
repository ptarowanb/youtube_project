import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock


class JobStore:
    def __init__(self):
        self._jobs = {}
        self._lock = Lock()

    def create(self, payload):
        record = {
            "job_id": payload["job_id"],
            "status": "queued",
            "image_keys": payload.get("image_keys", []),
            "audio_keys": payload.get("audio_keys", []),
            "subtitle_key": payload.get("subtitle_key"),
            "bgm_key": payload.get("bgm_key"),
            "output_prefix": payload.get("output_prefix"),
        }

        with self._lock:
            self._jobs[record["job_id"]] = record

        return record

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)


def _json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def create_handler(job_store, shared_token):
    class AutomationHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            if self.path == "/health":
                _json_response(self, HTTPStatus.OK, {"status": "ok"})
                return

            if self.path.startswith("/render-jobs/"):
                job_id = self.path.removeprefix("/render-jobs/")
                job = job_store.get(job_id)

                if job is None:
                    _json_response(
                        self, HTTPStatus.NOT_FOUND, {"error": "not_found"}
                    )
                    return

                _json_response(self, HTTPStatus.OK, job)
                return

            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/render-jobs":
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return

            if self.headers.get("X-Automation-Token") != shared_token:
                _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")

            if "job_id" not in payload:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "missing_job_id"})
                return

            job = job_store.create(payload)
            _json_response(
                self,
                HTTPStatus.ACCEPTED,
                {
                    "job_id": job["job_id"],
                    "status": job["status"],
                },
            )

    return AutomationHandler


def create_server(host, port, shared_token):
    job_store = JobStore()
    return ThreadingHTTPServer(
        (host, port),
        create_handler(job_store=job_store, shared_token=shared_token),
    )


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    shared_token = os.getenv("AUTOMATION_SHARED_TOKEN", "")

    server = create_server(host, port, shared_token)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
