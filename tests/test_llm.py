import json

import httpx
import pytest

from virtuguide.llm import resolve
from virtuguide.llm.openai_compat import OpenAICompat


def test_resolve_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "box:11434")
    llm = resolve("ollama:qwen3:8b")
    assert llm.model_id == "ollama:qwen3:8b"
    assert llm.model == "qwen3:8b"
    assert str(llm.client.base_url) == "http://box:11434/v1/"


@pytest.mark.parametrize("spec", ["qwen3", "ollama:", "nope:x"])
def test_resolve_rejects(spec):
    with pytest.raises(ValueError):
        resolve(spec)


def test_complete_strips_thinking():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.content))
        content = "<think>hmm</think>\n\nOnce upon a wharf."
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = httpx.Client(base_url="http://x/v1", transport=httpx.MockTransport(handler))
    llm = OpenAICompat("ollama:m", "unused", "m", client=client)
    assert llm.complete("sys", "usr") == "Once upon a wharf."
    assert seen["model"] == "m"
    assert [m["role"] for m in seen["messages"]] == ["system", "user"]
