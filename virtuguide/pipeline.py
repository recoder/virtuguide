from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal

from virtuguide import cache as cache_mod
from virtuguide.cache import Cache
from virtuguide.llm import LLM
from virtuguide.models import Persona, Tour
from virtuguide.prompts import bridge_prompt, story_prompt

STAGE, EXT = "text", "md"


@dataclass(frozen=True)
class Job:
    kind: Literal["story", "bridge"]
    id: str
    key: str
    inputs: dict[str, Any]
    cached: bool
    system: str
    user: str
    words: int


def plan(tour: Tour, persona: Persona, model_id: str, cache: Cache) -> list[Job]:
    base = {"tour_id": tour.id, "persona": persona.content.model_dump(),
            "language": persona.language, "model_id": model_id}
    jobs = []
    for nid, node in tour.nodes.items():
        inputs = base | {"node_id": nid, "topic": node.topic, "notes": node.notes}
        jobs.append(_job("story", nid, inputs, cache, *story_prompt(tour, nid, persona),
                         persona.content.length.words))
    for e in tour.edges:
        inputs = base | {"from": e.from_, "to": e.to, "label": e.label, "minutes": e.minutes,
                         "from_topic": tour.nodes[e.from_].topic,
                         "to_topic": tour.nodes[e.to].topic}
        jobs.append(_job("bridge", f"{e.from_}->{e.to}", inputs, cache,
                         *bridge_prompt(tour, e, persona), persona.content.bridge_length.words))
    return jobs


def _job(kind, id, inputs, cache: Cache, system, user, words) -> Job:
    k = cache_mod.key(**inputs)
    return Job(kind, id, k, inputs, cache.has(STAGE, k, EXT), system, user, words)


def run(jobs: list[Job], llm: LLM, cache: Cache, workers: int = 4) -> None:
    def one(job: Job) -> None:
        if job.inputs["model_id"] != llm.model_id:
            raise ValueError(f"job planned for {job.inputs['model_id']!r}, llm is {llm.model_id!r}")
        cache.write(STAGE, job.key, EXT, llm.complete(job.system, job.user), job.inputs)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, [j for j in jobs if not j.cached]))
