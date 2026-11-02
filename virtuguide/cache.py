import hashlib
import json
from pathlib import Path
from typing import Any


def key(**fields: Any) -> str:
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


class Cache:
    """Plain files: <root>/<stage>/<hash>.<ext> plus <hash>.json sidecar of inputs."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, stage: str, k: str, ext: str) -> Path:
        return self.root / stage / f"{k}.{ext}"

    def has(self, stage: str, k: str, ext: str) -> bool:
        return self.path(stage, k, ext).exists()

    def read(self, stage: str, k: str, ext: str) -> str:
        return self.path(stage, k, ext).read_text()

    def write(self, stage: str, k: str, ext: str, text: str, inputs: dict[str, Any]) -> Path:
        p = self.path(stage, k, ext)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.with_suffix(".json").write_text(json.dumps(inputs, indent=2, sort_keys=True))
        tmp = p.with_suffix(".tmp")
        tmp.write_text(text)
        tmp.replace(p)  # atomic: a half-written file never looks cached
        return p
