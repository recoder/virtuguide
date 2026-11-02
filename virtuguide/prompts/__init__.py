"""Pure prompt assembly. Output contract: plain text, paragraphs, at most [pause]."""

from virtuguide.models import Edge, Persona, Tour

FORMAT_RULES = (
    "Output plain text only: paragraphs separated by blank lines. "
    "The only allowed markup is [pause] for a beat of silence. "
    "No headings, lists, SSML, or stage directions."
)


def _system(persona: Persona, words: int | str) -> str:
    c = persona.content
    return (
        f"{c.prompt.strip()}\n\n"
        f"Audience: {c.audience}.\n"
        f"Write in language {persona.language}; keep proper nouns in their original form.\n"
        f"Length: about {words} words.\n"
        f"{FORMAT_RULES}"
    )


def story_prompt(tour: Tour, node_id: str, persona: Persona) -> tuple[str, str]:
    node = tour.nodes[node_id]
    c = persona.content
    words = f"{c.length.words} (+/- {int(c.length.tolerance * 100)}%)"
    user = f"Tour: {tour.title}\nStop: {node.title}\nTopic: {node.topic}\n"
    if node.notes:
        user += f"Prefer these facts: {node.notes}\n"
    user += "Tell the story for this stop. It must stand alone: listeners may arrive from anywhere."
    return _system(persona, words), user


def bridge_prompt(tour: Tour, edge: Edge, persona: Persona) -> tuple[str, str]:
    a, b = tour.nodes[edge.from_], tour.nodes[edge.to]
    user = (
        f"Tour: {tour.title}\n"
        f"Leaving: {a.title} ({a.topic})\n"
        f"Heading to: {b.title} ({b.topic})\n"
        f"Way: {edge.mode}"
        + (f", about {edge.minutes:g} minutes" if edge.minutes is not None else "")
        + (f", '{edge.label}'" if edge.label else "")
        + "\nWrite a short transition for the trip: wrap up the first place in a line, "
        "tease the next. Don't retell either story."
    )
    return _system(persona, persona.content.bridge_length.words), user
