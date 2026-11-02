import pytest
from conftest import FakeLLM

from virtuguide.cache import Cache
from virtuguide.pipeline import plan, run


def keys(jobs):
    return {j.id: j.key for j in jobs}


def test_plan_run_replan(tour, persona, tmp_path):
    cache = Cache(tmp_path)
    jobs = plan(tour, persona, "fake", cache)
    assert sum(j.kind == "story" for j in jobs) == 6
    assert sum(j.kind == "bridge" for j in jobs) == 8
    assert not any(j.cached for j in jobs)

    llm = FakeLLM()
    run(jobs, llm, cache)
    assert llm.calls == 14
    again = plan(tour, persona, "fake", cache)
    assert all(j.cached for j in again)
    run(again, llm, cache)
    assert llm.calls == 14
    j = jobs[0]
    assert cache.read("text", j.key, "md").startswith("story ")
    assert cache.path("text", j.key, "json").exists()


def test_key_sensitivity(tour, persona, tmp_path):
    cache = Cache(tmp_path)
    base = keys(plan(tour, persona, "m", cache))

    tts = persona.model_copy(update={"tts": persona.tts.model_copy(update={"speed": 1.5})})
    assert keys(plan(tour, tts, "m", cache)) == base

    content = persona.content.model_copy(update={"prompt": "different"})
    changed = keys(plan(tour, persona.model_copy(update={"content": content}), "m", cache))
    assert all(changed[k] != base[k] for k in base)

    other_model = keys(plan(tour, persona, "m2", cache))
    assert all(other_model[k] != base[k] for k in base)


def test_notes_only_affect_own_story(tour, persona, tmp_path):
    cache = Cache(tmp_path)
    base = keys(plan(tour, persona, "m", cache))
    node = tour.nodes["waterfront"].model_copy(update={"notes": "new facts"})
    t2 = tour.model_copy(update={"nodes": tour.nodes | {"waterfront": node}})
    diff = {k for k, v in keys(plan(t2, persona, "m", cache)).items() if v != base[k]}
    assert diff == {"waterfront"}


def test_run_rejects_model_mismatch(tour, persona, tmp_path):
    cache = Cache(tmp_path)
    with pytest.raises(ValueError, match="planned for"):
        run(plan(tour, persona, "a", cache), FakeLLM("b"), cache)
