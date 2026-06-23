"""Blob storage behind a small interface.

Nothing else in the app calls `open()` directly. Today it's the local disk;
swapping in S3 later means writing one more class with these four methods and
changing the `storage` instance at the bottom — callers don't change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from web import settings


class Storage(Protocol):
    def save_upload(self, job_id: str, data: bytes) -> str: ...
    def upload_path(self, job_id: str) -> str: ...
    def save_result(self, job_id: str, name: str, text: str) -> None: ...
    def read_result(self, job_id: str, name: str) -> str: ...
    def result_exists(self, job_id: str, name: str) -> bool: ...


class LocalStorage:
    """Files on local disk under the configured data dir."""

    def __init__(self, upload_dir: Path, review_dir: Path):
        self.upload_dir = upload_dir
        self.review_dir = review_dir

    def save_upload(self, job_id: str, data: bytes) -> str:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        path = self.upload_dir / f"{job_id}.pdf"
        path.write_bytes(data)
        return str(path)

    def upload_path(self, job_id: str) -> str:
        return str(self.upload_dir / f"{job_id}.pdf")

    def _result_file(self, job_id: str, name: str) -> Path:
        return self.review_dir / f"{job_id}.{name}"

    def save_result(self, job_id: str, name: str, text: str) -> None:
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self._result_file(job_id, name).write_text(text, encoding="utf-8")

    def read_result(self, job_id: str, name: str) -> str:
        return self._result_file(job_id, name).read_text(encoding="utf-8")

    def result_exists(self, job_id: str, name: str) -> bool:
        return self._result_file(job_id, name).exists()


storage: Storage = LocalStorage(settings.UPLOAD_DIR, settings.REVIEW_DIR)
