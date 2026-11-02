from typing import Protocol


class LLM(Protocol):
    model_id: str

    def complete(self, system: str, user: str) -> str: ...
