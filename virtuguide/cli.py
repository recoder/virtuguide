from pathlib import Path
from typing import Annotated

import typer

from virtuguide.cache import Cache
from virtuguide.llm import LLM, resolve
from virtuguide.loader import LoadError, load_persona, load_tour
from virtuguide.pipeline import EXT, STAGE, run
from virtuguide.pipeline import plan as plan_jobs

app = typer.Typer(no_args_is_help=True)


def _load(fn, path):
    try:
        return fn(path)
    except LoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e


def _llm(spec: str) -> LLM:
    try:
        return resolve(spec)
    except ValueError as e:
        raise typer.BadParameter(str(e), param_hint="--model") from e


Model = Annotated[str, typer.Option(help="provider:model, e.g. ollama:qwen3:8b")]


@app.command()
def validate(
    tours: Annotated[list[Path], typer.Option("--tour", "-t")] = [],  # noqa: B006
    personas: Annotated[list[Path], typer.Option("--persona", "-p")] = [],  # noqa: B006
) -> None:
    """Validate tour and persona YAML files."""
    if not tours and not personas:
        raise typer.BadParameter("give at least one --tour or --persona")
    failed = False
    for fn, paths in ((load_tour, tours), (load_persona, personas)):
        for p in paths:
            try:
                fn(p)
                typer.echo(f"ok  {p}")
            except LoadError as e:
                typer.echo(f"ERR {e}", err=True)
                failed = True
    if failed:
        raise typer.Exit(1)


@app.command()
def plan(
    tour: Path,
    persona: Path,
    model: Model,
    cache: Path = Path("cache"),
) -> None:
    """Show text jobs that `generate` would run and what is already cached."""
    _llm(model)
    jobs = plan_jobs(_load(load_tour, tour), _load(load_persona, persona), model, Cache(cache))
    for j in jobs:
        typer.echo(f"{'cached' if j.cached else 'miss  '}  {j.kind:6}  {j.id}")
    misses = [j for j in jobs if not j.cached]
    # shortcut: words only, no $ estimate; add per-model pricing with real adapters
    typer.echo(f"\n{len(jobs)} jobs, {len(misses)} to generate, "
               f"~{sum(j.words for j in misses)} output words")


@app.command()
def generate(tour: Path, persona: Path, model: Model, cache: Path = Path("cache")) -> None:
    """Generate missing story and bridge texts into the cache."""
    llm, store = _llm(model), Cache(cache)
    jobs = plan_jobs(_load(load_tour, tour), _load(load_persona, persona), model, store)
    misses = [j for j in jobs if not j.cached]
    typer.echo(f"{len(misses)} of {len(jobs)} to generate with {model}")
    run(misses, llm, store)
    for j in jobs:
        typer.echo(f"{j.kind:6}  {j.id:30}  {store.path(STAGE, j.key, EXT)}")
