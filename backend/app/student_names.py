"""Teacher-owned name maps, kept outside PostgreSQL."""

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


def name_hash(student_id: str, name: str) -> str:
    return "sha256:" + hashlib.sha256(f"{student_id}:{name}".encode()).hexdigest()


def _path(teacher_id: str) -> Path:
    root = Path(settings.storage_dir) / "student_names"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root / f"{hashlib.sha256(teacher_id.encode()).hexdigest()}.json"


def get_name(teacher_id: str, student_id: str, stored: str) -> str:
    if not stored.startswith("sha256:"):
        return stored  # Existing fixtures; production rows are migrated.
    path = _path(teacher_id)
    names = json.loads(path.read_text()) if path.exists() else {}
    name = names[student_id]
    if name_hash(student_id, name) != stored:
        raise ValueError("student name map does not match database hash")
    return name


@contextmanager
def _locked_map(teacher_id: str):
    path = _path(teacher_id)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield path, json.loads(path.read_text()) if path.exists() else {}
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def save_name(teacher_id: str, student_id: str, name: str | None) -> None:
    with _locked_map(teacher_id) as (path, names):
        if name is None:
            names.pop(student_id, None)
        else:
            names[student_id] = name
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
            os.chmod(tmp.name, 0o600)
            json.dump(names, tmp, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = Path(tmp.name)
        os.replace(temp_path, path)
