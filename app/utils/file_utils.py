"""File system utilities for integrity, hashing, and read-only validation."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class FileFingerprint:
    """Represents the binary fingerprint of a file on disk."""
    path: Path
    file_size_bytes: int
    mtime: float
    sha256: str


def compute_file_sha256(file_path: Path | str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 checksum of a file on disk without loading entire file into RAM.
    
    Args:
        file_path: Path to file.
        chunk_size: Byte size for streaming chunks.
        
    Returns:
        Hexadecimal SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    path = Path(file_path)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_file_fingerprint(file_path: Path | str) -> FileFingerprint:
    """Extracts size, mtime, and SHA-256 hash of a file on disk.
    
    Args:
        file_path: Path to target file.
        
    Returns:
        FileFingerprint instance.
    """
    path = Path(file_path).resolve()
    stat = path.stat()
    sha256 = compute_file_sha256(path)
    return FileFingerprint(
        path=path,
        file_size_bytes=stat.st_size,
        mtime=stat.st_mtime,
        sha256=sha256,
    )


def verify_file_unmodified(before: FileFingerprint, after: FileFingerprint) -> Tuple[bool, str]:
    """Verifies that a file was not written to or modified during an operation.
    
    Args:
        before: Fingerprint taken before operation.
        after: Fingerprint taken after operation.
        
    Returns:
        Tuple of (is_unmodified: bool, detail_message: str).
    """
    if before.sha256 != after.sha256:
        return False, f"File SHA-256 checksum changed: {before.sha256} -> {after.sha256}"
    if before.file_size_bytes != after.file_size_bytes:
        return False, f"File size changed: {before.file_size_bytes} -> {after.file_size_bytes} bytes"
    if before.mtime != after.mtime:
        return False, f"File modification timestamp changed: {before.mtime} -> {after.mtime}"
    return True, "File is strictly unmodified (read-only verified)."
