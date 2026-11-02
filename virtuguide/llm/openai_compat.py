import re

import httpx

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class OpenAICompat:
    """Chat completions over any OpenAI-compatible endpoint (Ollama, OpenAI)."""

    def __init__(self, model_id: str, base_url: str, model: str, api_key: str | None = None,
                 client: httpx.Client | None = None, timeout: float = 600):
        self.model_id = model_id
        self.model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = client or httpx.Client(base_url=base_url, headers=headers, timeout=timeout)

    def complete(self, system: str, user: str) -> str:
        r = self.client.post("/chat/completions", json={
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        })
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"] or ""
        # reasoning models (qwen3, deepseek-r1) may inline their thinking
        text = _THINK.sub("", text).strip()
        if not text:
            raise RuntimeError(f"{self.model_id}: empty completion")
        return text
