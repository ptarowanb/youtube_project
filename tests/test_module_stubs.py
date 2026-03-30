from pathlib import Path

import pytest

from src.asset_manager import fetch_assets
from src.job_tracker import JobTracker
from src.scheduler import build_scheduler
from src.subtitle_gen import extract_timestamps
from src.uploader import upload_video
from src.utils.logger import get_logger


def test_future_modules_expose_stable_interfaces(tmp_path: Path):
    logger = get_logger("youtube_automation.test")

    assert logger.name == "youtube_automation.test"
    assert callable(extract_timestamps)
    assert callable(fetch_assets)
    assert callable(build_scheduler)
    assert callable(upload_video)
    assert isinstance(JobTracker(tmp_path / "jobs.db"), JobTracker)


@pytest.mark.parametrize(
    ("callable_obj", "args"),
    [
        (extract_timestamps, (Path("audio.mp3"),)),
        (fetch_assets, ([], {}, Path("assets"))),
        (build_scheduler, tuple()),
        (upload_video, (Path("video.mp4"), {}, {})),
    ],
)
def test_unfinished_modules_fail_with_clear_not_implemented(callable_obj, args):
    with pytest.raises(NotImplementedError):
        callable_obj(*args)


def test_job_tracker_methods_fail_with_not_implemented(tmp_path: Path):
    tracker = JobTracker(tmp_path / "jobs.db")

    with pytest.raises(NotImplementedError):
        tracker.create_job(channel="knowledge", topic="ChatGPT 활용법")

    with pytest.raises(NotImplementedError):
        tracker.update_status("job-1", "SCRIPTING")

    with pytest.raises(NotImplementedError):
        tracker.mark_failed("job-1", "error message")
