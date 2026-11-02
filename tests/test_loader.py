import pytest

from virtuguide.loader import LoadError, load_tour

GOOD = """
id: t
title: T
start: a
nodes:
  a:
    title: A
    topic: a
    geo: {lat: 1, lon: 2, radius: 10}
    next: [{to: b, label: go}]
  b: {title: B, topic: b, next: []}
"""


def test_examples_load(tour, persona):
    assert len(tour.nodes) == 6
    assert len(tour.edges) == 8
    modes = {(e.from_, e.to): e.mode for e in tour.edges}
    assert modes[("waterfront", "plum-island")] == "drive"
    assert modes[("market-square", "waterfront")] == "walk"
    assert persona.content.length.words == 250


def _load(tmp_path, text):
    p = tmp_path / "t.yaml"
    p.write_text(text)
    return load_tour(p)


def test_minimal_ok(tmp_path):
    assert _load(tmp_path, GOOD).edges[0].label == "go"


@pytest.mark.parametrize("old,new,msg", [
    ("label: go", "lable: go", "lable"),
    ("{to: b, label: go}", "{to: c}", "unknown nodes: a->c"),
    ("start: a", "start: z", "start 'z'"),
    ("next: [{to: b, label: go}]", "next: []", "unreachable from start: b"),
    ("b: {title: B, topic: b, next: []}",
     "b: {title: B, topic: b, next: [{to: a}]}", "no terminal"),
    ("radius: 10", "", "radius"),
])
def test_invalid(tmp_path, old, new, msg):
    assert old in GOOD
    with pytest.raises(LoadError, match=msg):
        _load(tmp_path, GOOD.replace(old, new))
