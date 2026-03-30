from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class JobTracker:
    database_path: Path

    def create_job(self, channel: str, topic: str) -> str:
        raise NotImplementedError("Job persistence is planned for a later phase.")

    def update_status(self, job_id: str, status: str) -> None:
        raise NotImplementedError("Job persistence is planned for a later phase.")

    def mark_failed(self, job_id: str, error_message: str) -> None:
        raise NotImplementedError("Job persistence is planned for a later phase.")
