"""The only module that touches the filesystem.

Everything goes through here so the local disk can be swapped for S3 later without
changing a single caller. Never open a path under storage/ directly.
"""
import hashlib
import shutil
from pathlib import Path
from typing import BinaryIO

from api.app.config import get_settings


def _root() -> Path:
    root = get_settings().storage_root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve(key: str) -> Path:
    """Resolve a storage key, refusing anything that escapes the root."""
    root = _root().resolve()
    target = (root / key).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"storage key escapes root: {key!r}")
    return target


def put_stream(key: str, stream: BinaryIO, max_bytes: int | None = None) -> tuple[int, str]:
    """Stream to storage while hashing in the same pass.

    Returns (bytes_written, sha256). Hashing during the write means a re-upload of an
    identical file is detected before any parsing compute is spent.
    """
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    with path.open("wb") as fh:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                fh.close()
                path.unlink(missing_ok=True)
                raise ValueError(f"file exceeds {max_bytes} bytes")
            digest.update(chunk)
            fh.write(chunk)
    return total, digest.hexdigest()


def put_bytes(key: str, data: bytes) -> str:
    path = _resolve(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def get_path(key: str) -> Path:
    path = _resolve(key)
    if not path.exists():
        raise FileNotFoundError(key)
    return path


def exists(key: str) -> bool:
    try:
        return _resolve(key).exists()
    except ValueError:
        return False


def delete(key: str) -> None:
    _resolve(key).unlink(missing_ok=True)


def delete_prefix(prefix: str) -> None:
    target = _resolve(prefix)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def health() -> bool:
    try:
        probe = _root() / ".health"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError:
        return False
