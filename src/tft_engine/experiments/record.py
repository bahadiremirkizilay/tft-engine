"""Experiment records: one JSON object per line (JSONL), append-only.

A record holds everything needed to rerun an experiment and check that it
gives the same result: name, config, config hash, seed, data version, code
version (git commit) and metrics. Fields that legitimately differ between
runs (timestamps, run id, environment) are kept but never compared.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Fields that must match for two runs to count as the same result.
REPRODUCIBLE_FIELDS = ("name", "config", "config_hash", "seed", "data_version", "metrics")


def canonical_json(obj: Any) -> str:
    """JSON with sorted keys and no whitespace, so equal configs hash equally."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(config).encode()).hexdigest()[:16]


def git_commit(cwd: Path | None = None) -> str | None:
    """Current commit hash, with a ``-dirty`` suffix if there are local changes."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{commit}-dirty" if dirty else commit


def environment_info() -> dict[str, str]:
    import numpy

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": numpy.__version__,
    }


@dataclass
class ExperimentRecord:
    name: str
    config: dict[str, Any]
    seed: int
    metrics: dict[str, Any]
    data_version: str = "none"
    config_hash: str = ""
    git_commit: str | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    duration_s: float = 0.0
    environment: dict[str, str] = field(default_factory=environment_info)

    def __post_init__(self) -> None:
        if not self.config_hash:
            self.config_hash = config_hash(self.config)

    def reproducible_view(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: d[k] for k in REPRODUCIBLE_FIELDS}

    def to_json(self) -> str:
        return canonical_json(asdict(self))

    def append_to(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(self.to_json() + "\n")


def load_records(path: Path) -> list[ExperimentRecord]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(ExperimentRecord(**json.loads(line)))
    return records
