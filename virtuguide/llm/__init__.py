import os
from typing import Protocol


class LLM(Protocol):
    model_id: str

    def complete(self, system: str, user: str) -> str: ...


def resolve(spec: str) -> LLM:
    """Build an LLM from 'provider:model', e.g. 'ollama:qwen3:8b'.

    The full spec string is the model_id hashed into text cache keys.
    """
    provider, sep, model = spec.partition(":")
    if not sep or not model:
        raise ValueError(f"model must be 'provider:model', got {spec!r}")
    if provider == "ollama":
        from virtuguide.llm.openai_compat import OpenAICompat

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if "://" not in host:
            host = f"http://{host}"
        return OpenAICompat(spec, f"{host.rstrip('/')}/v1", model)
    raise ValueError(f"unknown LLM provider {provider!r} (known: ollama)")
