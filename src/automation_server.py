import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self):
        self._jobs = {}
        self._lock = Lock()

    def create(self, payload):
        record = {
            "job_id": payload["job_id"],
            "status": "queued",
            "video_keys": payload.get("video_keys", []),
            "image_keys": payload.get("image_keys", []),
            "audio_keys": payload.get("audio_keys", []),
            "subtitle_key": payload.get("subtitle_key"),
            "bgm_key": payload.get("bgm_key"),
            "output_prefix": payload.get("output_prefix"),
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
            "error": "",
        }

        with self._lock:
            self._jobs[record["job_id"]] = record
            return dict(record)

    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update(self, job_id, **fields):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.update(fields)
            job["updated_at"] = _utcnow()
            return dict(job)


class S3Storage:
    def __init__(self, bucket, region, client=None):
        if not bucket:
            raise ValueError("RENDER_BUCKET is required for automation rendering")

        self.bucket = bucket
        self.region = region

        if client is None:
            import boto3

            client = boto3.client("s3", region_name=region)

        self.client = client

    def download_file(self, key, destination):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))

    def upload_file(self, source, key, content_type=None):
        content_type = content_type or mimetypes.guess_type(str(source))[0]
        extra_args = {}
        if content_type:
            extra_args["ExtraArgs"] = {"ContentType": content_type}

        self.client.upload_file(str(source), self.bucket, key, **extra_args)

    def presign_get(self, key, expires_in=3600):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


class FfmpegRenderer:
    def __init__(self, ffmpeg_bin="ffmpeg", ffprobe_bin="ffprobe", loglevel=None):
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.loglevel = loglevel or os.getenv("FFMPEG_LOGLEVEL", "warning")

    def render(self, job, storage, workdir):
        workdir = Path(workdir)
        inputs_dir = workdir / "inputs"
        segments_dir = workdir / "segments"
        outputs_dir = workdir / "outputs"

        inputs_dir.mkdir(parents=True, exist_ok=True)
        segments_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        video_paths = self._download_many(
            storage, job.get("video_keys", []), inputs_dir / "videos"
        )
        image_paths = self._download_many(
            storage, job.get("image_keys", []), inputs_dir / "images"
        )
        audio_paths = self._download_many(
            storage, job.get("audio_keys", []), inputs_dir / "audio"
        )
        subtitle_path = self._download_optional(
            storage, job.get("subtitle_key"), inputs_dir / "subtitles"
        )
        bgm_path = self._download_optional(storage, job.get("bgm_key"), inputs_dir / "bgm")

        if not video_paths and not image_paths:
            raise ValueError("render job requires at least one video or image input")

        target_duration = self._resolve_target_duration(audio_paths, video_paths)
        segment_paths = []
        normalized_video_durations = []

        for index, video_path in enumerate(video_paths, start=1):
            normalized_path = segments_dir / f"video_{index:02d}.mp4"
            self._normalize_video(video_path, normalized_path)
            segment_paths.append(normalized_path)
            normalized_video_durations.append(self._probe_duration(normalized_path))

        if image_paths:
            consumed_duration = sum(normalized_video_durations)
            remaining_duration = max(target_duration - consumed_duration, 0.0)

            if not segment_paths:
                remaining_duration = target_duration

            segment_duration = max(3.0, remaining_duration / max(len(image_paths), 1))

            for index, image_path in enumerate(image_paths, start=1):
                image_segment_path = segments_dir / f"image_{index:02d}.mp4"
                self._render_image_segment(image_path, image_segment_path, segment_duration)
                segment_paths.append(image_segment_path)

        visuals_path = outputs_dir / "visuals.mp4"
        if len(segment_paths) == 1:
            shutil.copyfile(segment_paths[0], visuals_path)
        else:
            self._concat_segments(segment_paths, visuals_path)

        output_path = outputs_dir / "final.mp4"
        primary_audio_path = audio_paths[0] if audio_paths else None
        self._compose_final(
            visuals_path=visuals_path,
            output_path=output_path,
            audio_path=primary_audio_path,
            bgm_path=bgm_path,
            subtitle_path=subtitle_path,
        )

        output_prefix = (job.get("output_prefix") or f"jobs/{job['job_id']}/output").rstrip("/")
        output_key = f"{output_prefix}/final.mp4"
        storage.upload_file(output_path, output_key, content_type="video/mp4")

        return {
            "output_key": output_key,
            "output_url": storage.presign_get(output_key),
        }

    def _download_many(self, storage, keys, directory):
        paths = []
        for index, key in enumerate(keys or [], start=1):
            suffix = Path(key).suffix or ""
            destination = Path(directory) / f"{index:02d}{suffix}"
            storage.download_file(key, destination)
            paths.append(destination)
        return paths

    def _download_optional(self, storage, key, directory):
        if not key:
            return None
        suffix = Path(key).suffix or ""
        destination = Path(directory) / f"asset{suffix}"
        storage.download_file(key, destination)
        return destination

    def _resolve_target_duration(self, audio_paths, video_paths):
        if audio_paths:
            return max(1.0, self._probe_duration(audio_paths[0]))
        if video_paths:
            return max(3.0, sum(self._probe_duration(path) for path in video_paths))
        return 30.0

    def _normalize_video(self, source, destination):
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-loglevel",
                self.loglevel,
                "-i",
                str(source),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                str(destination),
            ]
        )

    def _render_image_segment(self, source, destination, duration_seconds):
        frames = max(1, int(round(duration_seconds * 30)))
        zoom_filter = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min(zoom+0.0008,1.05)':d={frames}:s=1080x1920:fps=30,"
            "setsar=1"
        )
        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-loglevel",
                self.loglevel,
                "-loop",
                "1",
                "-i",
                str(source),
                "-t",
                f"{duration_seconds:.2f}",
                "-vf",
                zoom_filter,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                str(destination),
            ]
        )

    def _concat_segments(self, segment_paths, destination):
        concat_file = destination.with_suffix(".txt")
        lines = []
        for path in segment_paths:
            escaped_path = path.as_posix().replace("'", "'\\''")
            lines.append(f"file '{escaped_path}'")
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        self._run(
            [
                self.ffmpeg_bin,
                "-y",
                "-loglevel",
                self.loglevel,
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(destination),
            ]
        )

    def _compose_final(self, visuals_path, output_path, audio_path=None, bgm_path=None, subtitle_path=None):
        command = [
            self.ffmpeg_bin,
            "-y",
            "-loglevel",
            self.loglevel,
            "-i",
            str(visuals_path),
        ]

        next_input_index = 1
        audio_input_index = None
        bgm_input_index = None

        if audio_path:
            command.extend(["-i", str(audio_path)])
            audio_input_index = next_input_index
            next_input_index += 1

        if bgm_path:
            command.extend(["-i", str(bgm_path)])
            bgm_input_index = next_input_index
            next_input_index += 1

        filter_complex_parts = []
        if audio_input_index is not None and bgm_input_index is not None:
            filter_complex_parts.extend(
                [
                    f"[{audio_input_index}:a]volume=1.0[narration]",
                    f"[{bgm_input_index}:a]volume=0.12[bgm]",
                    "[narration][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                ]
            )

        if filter_complex_parts:
            command.extend(["-filter_complex", ";".join(filter_complex_parts)])

        if subtitle_path:
            command.extend(["-vf", self._subtitle_filter(subtitle_path)])

        command.extend(["-map", "0:v:0"])

        if filter_complex_parts:
            command.extend(["-map", "[aout]"])
        elif audio_input_index is not None:
            command.extend(["-map", f"{audio_input_index}:a:0"])
        elif bgm_input_index is not None:
            command.extend(["-map", f"{bgm_input_index}:a:0"])
        else:
            command.append("-an")

        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ]
        )

        if audio_input_index is not None or bgm_input_index is not None:
            command.extend(["-c:a", "aac", "-b:a", "192k"])

        command.extend(["-shortest", str(output_path)])
        self._run(command)

    def _subtitle_filter(self, subtitle_path):
        escaped_path = str(subtitle_path).replace("\\", "/")
        escaped_path = escaped_path.replace(":", "\\:")
        escaped_path = escaped_path.replace("'", "\\'")
        escaped_path = escaped_path.replace(",", "\\,")
        escaped_path = escaped_path.replace("[", "\\[")
        escaped_path = escaped_path.replace("]", "\\]")
        return f"subtitles='{escaped_path}'"

    def _probe_duration(self, path):
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    def _run(self, command):
        print(f"[automation] run: {' '.join(command)}", flush=True)
        subprocess.run(command, check=True)


class BackgroundRenderProcessor:
    def __init__(self, job_store, storage, renderer):
        self.job_store = job_store
        self.storage = storage
        self.renderer = renderer

    def submit(self, job_id):
        thread = Thread(target=self._process, args=(job_id,), daemon=True)
        thread.start()

    def _process(self, job_id):
        job = self.job_store.get(job_id)
        if job is None:
            return

        print(f"[automation] start job {job_id}", flush=True)
        self.job_store.update(job_id, status="processing", error="")

        try:
            with tempfile.TemporaryDirectory(prefix=f"{job_id}_") as workdir:
                result = self.renderer.render(job, self.storage, workdir)
            self.job_store.update(job_id, status="done", error="", **result)
            print(f"[automation] job {job_id} done", flush=True)
        except Exception as error:
            self.job_store.update(job_id, status="failed", error=str(error))
            print(f"[automation] job {job_id} failed: {error}", flush=True)


def _json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def create_handler(job_store, shared_token, render_processor):
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
            render_processor.submit(job["job_id"])
            _json_response(
                self,
                HTTPStatus.ACCEPTED,
                {
                    "job_id": job["job_id"],
                    "status": job["status"],
                },
            )

    return AutomationHandler


def create_server(host, port, shared_token, storage=None, renderer=None, job_store=None):
    job_store = job_store or JobStore()
    storage = storage or S3Storage(
        bucket=os.getenv("RENDER_BUCKET"),
        region=os.getenv("AWS_REGION", "ap-northeast-2"),
    )
    renderer = renderer or FfmpegRenderer()
    render_processor = BackgroundRenderProcessor(job_store, storage, renderer)

    return ThreadingHTTPServer(
        (host, port),
        create_handler(
            job_store=job_store,
            shared_token=shared_token,
            render_processor=render_processor,
        ),
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
