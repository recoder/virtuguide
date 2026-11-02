from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from virtuguide.models import Persona, Tour


class LoadError(Exception):
    def __init__(self, path: Path, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path


def _load[M: BaseModel](path: Path, model: type[M]) -> M:
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text())
        return model.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as e:
        raise LoadError(path, str(e)) from e


def load_tour(path: Path) -> Tour:
    return _load(path, Tour)


def load_persona(path: Path) -> Persona:
    return _load(path, Persona)
