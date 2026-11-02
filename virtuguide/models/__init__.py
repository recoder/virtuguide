from collections import deque
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["walk", "drive", "bike", "transit"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- persona ---


class Length(Strict):
    words: int = Field(gt=0)
    tolerance: float = Field(default=0.2, ge=0, lt=1)


class BridgeLength(Strict):
    words: int = Field(gt=0)


class PersonaContent(Strict):
    prompt: str
    audience: str
    length: Length
    bridge_length: BridgeLength


class Voice(Strict):
    engine: str
    voice: str


class PersonaTTS(Strict):
    style: str
    speed: float = Field(gt=0)
    voices: list[Voice] = Field(min_length=1)


class Persona(Strict):
    id: str
    name: str
    language: str
    content: PersonaContent
    tts: PersonaTTS


# --- tour ---


class Geo(Strict):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius: float = Field(gt=0)


class EdgeSpec(Strict):
    to: str
    label: str | None = None
    minutes: float | None = Field(default=None, ge=0)
    mode: Mode | None = None
    optional: bool = False


class Node(Strict):
    title: str
    topic: str
    geo: Geo | None = None
    notes: str | None = None
    optional: bool = False
    next: list[EdgeSpec]


class Defaults(Strict):
    mode: Mode = "walk"


class Edge(Strict):
    """Flattened edge; mode resolved against tour defaults."""

    from_: str
    to: str
    label: str | None
    minutes: float | None
    mode: Mode
    optional: bool


class Tour(Strict):
    id: str
    title: str
    start: str
    defaults: Defaults = Defaults()
    nodes: dict[str, Node] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_graph(self) -> "Tour":
        errors = []
        if self.start not in self.nodes:
            errors.append(f"start {self.start!r} is not a node")
        dangling = [f"{n}->{e.to}" for n, node in self.nodes.items() for e in node.next
                    if e.to not in self.nodes]
        if dangling:
            errors.append(f"edges to unknown nodes: {', '.join(dangling)}")
        if not any(not node.next for node in self.nodes.values()):
            errors.append("no terminal node (a node with next: [])")
        if not errors:
            seen, todo = {self.start}, deque([self.start])
            while todo:
                for e in self.nodes[todo.popleft()].next:
                    if e.to not in seen:
                        seen.add(e.to)
                        todo.append(e.to)
            if unreachable := [n for n in self.nodes if n not in seen]:
                errors.append(f"unreachable from start: {', '.join(unreachable)}")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def edges(self) -> list[Edge]:
        return [
            Edge(from_=n, to=e.to, label=e.label, minutes=e.minutes,
                 mode=e.mode or self.defaults.mode, optional=e.optional)
            for n, node in self.nodes.items() for e in node.next
        ]
