import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def scan_folder(folder_path: str | os.PathLike) -> Dict[str, Any]:
    """
    Recursively scans a user-provided folder using os and pathlib.
    
    Extracts metadata for each file without reading contents, calculating hashes,
    modifying files, or following symlinks.
    
    Handles invalid paths, permission errors, and unreadable files gracefully.

    Returns:
        dict: Structured metadata containing:
            - folder_path: str
            - files: list of dicts with name, path, size (bytes), and extension
            - total_files: int
            - total_size: int (bytes)
            - errors: list of error/warning messages encountered
    """
    result: Dict[str, Any] = {
        "folder_path": str(folder_path) if folder_path is not None else "",
        "files": [],
        "total_files": 0,
        "total_size": 0,
        "errors": []
    }

    if not folder_path:
        result["errors"].append("Folder path was not provided.")
        return result

    try:
        target_path = Path(folder_path).resolve()
    except Exception as e:
        result["errors"].append(f"Invalid folder path format: {e}")
        return result

    if not target_path.exists():
        result["errors"].append(f"Path does not exist: {target_path}")
        return result

    if not target_path.is_dir():
        result["errors"].append(f"Path is not a directory: {target_path}")
        return result

    files_list: List[Dict[str, Any]] = []
    total_size = 0

    def on_walk_error(err: OSError):
        result["errors"].append(f"Access error scanning directory '{err.filename}': {err.strerror}")

    try:
        for root, dirs, files in os.walk(str(target_path), followlinks=False, onerror=on_walk_error):
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    # Do not follow symlinks
                    if os.path.islink(file_path):
                        continue

                    stat_res = os.stat(file_path, follow_symlinks=False)
                    size_bytes = stat_res.st_size
                    _, ext = os.path.splitext(filename)

                    file_entry = {
                        "name": filename,
                        "path": os.path.abspath(file_path),
                        "size": size_bytes,
                        "extension": ext.lower()
                    }
                    files_list.append(file_entry)
                    total_size += size_bytes
                except (PermissionError, OSError) as e:
                    result["errors"].append(f"Could not read metadata for file '{file_path}': {e}")
    except (PermissionError, OSError) as e:
        result["errors"].append(f"Error accessing folder '{target_path}': {e}")

    result["files"] = files_list
    result["total_files"] = len(files_list)
    result["total_size"] = total_size
    return result


def _compute_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 hash in memory-efficient chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_duplicates(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identifies duplicate files from a list of file metadata dictionaries.
    
    Groups candidate files by size, then calculates SHA-256 hashes in memory-efficient
    chunks only for files that share identical sizes. Groups matching files by content hash.
    
    Excludes symlinks, handles unreadable or modified files gracefully, and never modifies
    or deletes any files.
    
    Returns:
        dict:
            - duplicate_groups: list of groups (each with hash, size, count, recoverable_bytes, files)
            - total_duplicate_groups: int
            - total_duplicate_files: int
            - recoverable_bytes: int (potential space recoverable by retaining one copy per group)
            - errors: list of error messages for unreadable or changed files
    """
    result: Dict[str, Any] = {
        "duplicate_groups": [],
        "total_duplicate_groups": 0,
        "total_duplicate_files": 0,
        "recoverable_bytes": 0,
        "errors": []
    }

    if not files or not isinstance(files, list):
        return result

    # 1. Group candidate files by size
    size_groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for f in files:
        if not isinstance(f, dict):
            continue
        path = f.get("path")
        size = f.get("size")
        if path is None or size is None:
            continue
        size_groups[size].append(f)

    duplicate_groups: List[Dict[str, Any]] = []
    total_recoverable_bytes = 0
    total_dup_files_count = 0

    # 2. Only compute hashes for candidate files sharing the exact same size
    for size, candidates in size_groups.items():
        if len(candidates) < 2:
            continue

        hash_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for candidate in candidates:
            file_path = candidate.get("path")
            if not file_path:
                continue

            try:
                # Exclude symlinks
                if os.path.islink(file_path):
                    continue

                # Verify file still exists and size has not altered
                stat_info = os.stat(file_path, follow_symlinks=False)
                if stat_info.st_size != size:
                    result["errors"].append(f"File size changed during scan for '{file_path}'")
                    continue

                file_hash = _compute_sha256(file_path)
                hash_groups[file_hash].append(candidate)
            except (PermissionError, OSError) as e:
                result["errors"].append(f"Could not read/hash file '{file_path}': {e}")

        # 3. Collect groups that have more than 1 file matching the content hash
        for content_hash, matching_files in hash_groups.items():
            count = len(matching_files)
            if count > 1:
                group_recoverable = size * (count - 1)
                duplicate_groups.append({
                    "hash": content_hash,
                    "size": size,
                    "count": count,
                    "recoverable_bytes": group_recoverable,
                    "files": matching_files
                })
                total_recoverable_bytes += group_recoverable
                total_dup_files_count += count

    result["duplicate_groups"] = duplicate_groups
    result["total_duplicate_groups"] = len(duplicate_groups)
    result["total_duplicate_files"] = total_dup_files_count
    result["recoverable_bytes"] = total_recoverable_bytes
    return result
