from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    """Return the SHA256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_git_commit(root: Path) -> str:
    """Return the current Git commit SHA, or `unknown` outside a Git checkout."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def q2_q3_core_csv_hashes(root: Path) -> dict[str, str]:
    """Hash every machine-readable Q2/Q3 table included in the release."""
    csv_paths = sorted(
        [
            *list((root / "questions" / "q2" / "artifacts" / "tables").glob("*.csv")),
            *list((root / "questions" / "q3" / "artifacts" / "tables").glob("*.csv")),
        ]
    )
    return {rel_posix(path, root): file_sha256(path) for path in csv_paths}


def write_q2_q3_release_manifest(root: Path, *, config_path: str | Path) -> Path:
    """Write the Q2/Q3 release manifest required by task7."""
    config = root / config_path
    data = root / "data" / "processed" / "golf_shots_clean.csv"
    q2_metadata = root / "questions" / "q2" / "artifacts" / "run_metadata.json"
    q3_metadata = root / "questions" / "q3" / "artifacts" / "run_metadata.json"
    manifest: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": current_git_commit(root),
        "config_path": rel_posix(config, root),
        "config_sha256": file_sha256(config),
        "data_path": rel_posix(data, root),
        "data_sha256": file_sha256(data),
        "q2_run_metadata_path": rel_posix(q2_metadata, root),
        "q2_run_metadata_sha256": file_sha256(q2_metadata),
        "q3_run_metadata_path": rel_posix(q3_metadata, root),
        "q3_run_metadata_sha256": file_sha256(q3_metadata),
        "core_csv_sha256": q2_q3_core_csv_hashes(root),
    }
    output = root / "docs" / "reproducibility" / "q2_q3_release_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return output
