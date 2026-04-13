import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from src.automation_server import FfmpegRenderer, create_server


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
        self.storage = FakeStorage()
        self.renderer = FakeRenderer()
        self.server = create_server(
            "127.0.0.1",
            0,
            "test-token",
            storage=self.storage,
            renderer=self.renderer,
        )
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
                "output_prefix": "jobs/job-1/output",
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

        get_status, get_payload = wait_for_job_status(
            self.base_url,
            "job-1",
            target_status="done",
        )

        assert get_status == 200
        assert get_payload["job_id"] == "job-1"
        assert get_payload["status"] == "done"
        assert get_payload["image_keys"] == ["jobs/job-1/images/01.png"]
        assert get_payload["audio_keys"] == ["jobs/job-1/audio/01.mp3"]
        assert get_payload["output_key"] == "jobs/job-1/output/final.mp4"
        assert get_payload["output_url"] == "https://example.test/jobs/job-1/output/final.mp4"

    def test_missing_job_returns_not_found(self):
        try:
            _request("GET", f"{self.base_url}/render-jobs/missing")
        except urllib.error.HTTPError as error:
            assert error.code == 404
            assert json.loads(error.read().decode("utf-8")) == {"error": "not_found"}
        else:
            raise AssertionError("expected not found response")

    def test_render_failure_updates_job_state(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

        self.renderer = FailingRenderer()
        self.server = create_server(
            "127.0.0.1",
            0,
            "test-token",
            storage=self.storage,
            renderer=self.renderer,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

        create_status, _ = _request(
            "POST",
            f"{self.base_url}/render-jobs",
            payload={"job_id": "job-fail", "output_prefix": "jobs/job-fail/output"},
            headers={"X-Automation-Token": "test-token"},
        )

        assert create_status == 202

        _, payload = wait_for_job_status(
            self.base_url,
            "job-fail",
            target_status="failed",
        )
        assert payload["error"] == "render failed"


class FakeStorage:
    def __init__(self):
        self.uploads = {}

    def download_file(self, key, destination):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(f"downloaded:{key}".encode("utf-8"))

    def upload_file(self, source, key, content_type=None):
        self.uploads[key] = {
            "content_type": content_type,
            "bytes": Path(source).read_bytes(),
        }

    def presign_get(self, key, expires_in=3600):
        return f"https://example.test/{key}"


class FakeRenderer:
    def render(self, job, storage, workdir):
        time.sleep(0.05)
        output_key = job["output_prefix"].rstrip("/") + "/final.mp4"
        output_path = Path(workdir) / "final.mp4"
        output_path.write_bytes(b"video-bytes")
        storage.upload_file(output_path, output_key, content_type="video/mp4")
        return {
            "output_key": output_key,
            "output_url": storage.presign_get(output_key),
        }


class FailingRenderer:
    def render(self, job, storage, workdir):
        raise RuntimeError("render failed")


def wait_for_job_status(base_url, job_id, target_status, timeout=3):
    deadline = time.time() + timeout

    while time.time() < deadline:
        status, payload = _request("GET", f"{base_url}/render-jobs/{job_id}")
        if payload.get("status") == target_status:
            return status, payload
        time.sleep(0.05)

    raise AssertionError(f"job {job_id} did not reach {target_status}: {payload}")


def test_compose_final_loops_bgm_until_video_ends(tmp_path):
    renderer = FfmpegRenderer()
    commands = []

    def capture_run(command):
        commands.append(command)

    renderer._run = capture_run

    renderer._compose_final(
        visuals_path=tmp_path / "visuals.mp4",
        output_path=tmp_path / "final.mp4",
        audio_path=tmp_path / "narration.mp3",
        bgm_path=tmp_path / "bgm.mp3",
    )

    command = commands[0]

    bgm_flag_index = command.index("-stream_loop")
    assert command[bgm_flag_index : bgm_flag_index + 4] == [
        "-stream_loop",
        "-1",
        "-i",
        str(tmp_path / "bgm.mp3"),
    ]
    assert any(
        "amix=inputs=2:duration=longest:dropout_transition=2[aout]" in part
        for part in command
    )
