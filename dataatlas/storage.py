"""Workspace-scoped local Bronze file storage with safe, atomic writes."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class StoredBronzeFile:
    uri: str
    byte_count: int
    sha256: str


class LocalFileStorage:
    """Stores original upload bytes below ``<data_home>/lake/bronze``."""

    def __init__(self, data_home: Path):
        self.root = (data_home / "lake").resolve()

    def _target(self, workspace_id: str, dataset_id: str, version_id: str | None = None) -> Path:
        version_id = version_id or dataset_id
        if not ID_PATTERN.fullmatch(workspace_id) or not ID_PATTERN.fullmatch(dataset_id) or not ID_PATTERN.fullmatch(version_id):
            raise ValueError("Invalid workspace or dataset identifier.")
        target = (self.root / "bronze" / workspace_id / dataset_id / f"{version_id}.csv").resolve()
        if self.root not in target.parents:
            raise ValueError("Storage path escaped the configured data directory.")
        return target

    def write_bronze_csv(self, workspace_id: str, dataset_id: str, raw: bytes,
                         version_id: str | None = None) -> StoredBronzeFile:
        target = self._target(workspace_id, dataset_id, version_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        fd, temp_path = tempfile.mkstemp(prefix=".upload-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
        except Exception:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise
        return StoredBronzeFile(target.relative_to(self.root).as_posix(), len(raw), digest)

    def delete(self, workspace_id: str, dataset_id: str, version_id: str | None = None) -> None:
        target = self._target(workspace_id, dataset_id, version_id)
        try:
            target.unlink()
        except FileNotFoundError:
            pass

    def read(self, uri: str) -> bytes:
        target = (self.root / uri).resolve()
        if self.root not in target.parents or not target.is_file():
            raise FileNotFoundError("Stored dataset file was not found.")
        return target.read_bytes()
