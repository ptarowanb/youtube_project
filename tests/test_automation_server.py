import json
import threading
import urllib.error
import urllib.request

from src.automation_server import create_server


def _request(method, url, payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)

    for key, value in (headers or {}).items():
        request.add_header(key, value)

    if data is not None:
        request.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


class TestAutomationServer:
    def setup_method(self):
        self.server = create_server("127.0.0.1", 0, "test-token")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def teardown_method(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_health_returns_ok(self):
        status, payload = _request("GET", f"{self.base_url}/health")

        assert status == 200
        assert payload == {"status": "ok"}

    def test_render_jobs_requires_shared_token(self):
        try:
            _request(
                "POST",
                f"{self.base_url}/render-jobs",
                payload={"job_id": "job-1"},
            )
        except urllib.error.HTTPError as error:
            assert error.code == 401
            assert json.loads(error.read().decode("utf-8")) == {
                "error": "unauthorized"
            }
        else:
            raise AssertionError("expected unauthorized response")

    def test_render_job_creation_and_lookup(self):
        create_status, create_payload = _request(
            "POST",
            f"{self.base_url}/render-jobs",
            payload={
                "job_id": "job-1",
                "image_keys": ["jobs/job-1/images/01.png"],
                "audio_keys": ["jobs/job-1/audio/01.mp3"],
            },
            headers={"X-Automation-Token": "test-token"},
        )

        assert create_status == 202
        assert create_payload == {
            "job_id": "job-1",
            "status": "queued",
        }

        get_status, get_payload = _request(
            "GET", f"{self.base_url}/render-jobs/job-1"
        )

        assert get_status == 200
        assert get_payload["job_id"] == "job-1"
        assert get_payload["status"] == "queued"
        assert get_payload["image_keys"] == ["jobs/job-1/images/01.png"]
        assert get_payload["audio_keys"] == ["jobs/job-1/audio/01.mp3"]

    def test_missing_job_returns_not_found(self):
        try:
            _request("GET", f"{self.base_url}/render-jobs/missing")
        except urllib.error.HTTPError as error:
            assert error.code == 404
            assert json.loads(error.read().decode("utf-8")) == {"error": "not_found"}
        else:
            raise AssertionError("expected not found response")
