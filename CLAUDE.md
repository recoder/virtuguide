# virtuguide

Personalized audio tour guides. YAML tour graph + persona -> LLM-written stories -> TTS audio -> static bundle -> offline PWA player.

Owner uses it for family trips in New England (towns, museums, Boston Freedom Trail). Entertainment, not education: occasional historical looseness is acceptable. Possible later: friends use it, maybe commercial.

## Core architecture

Python library first, thin CLI on top. No runtime backend: the player is a static PWA reading a pre-rendered bundle. Never call an LLM or TTS while the user is walking.

```
virtuguide/
  models/      # pydantic v2: Tour, Node, Edge, Persona, Script, Manifest
  loader.py    # YAML -> validated models
  llm/         # LLM protocol; openai_compat.py (Ollama + OpenAI), anthropic.py
  tts/         # TTS protocol; adapters (kokoro first, openai second); chunk + stitch
  prompts/     # pure functions assembling story / bridge prompts
  cache.py     # content-addressed file store
  pipeline.py  # plan(tour, persona) -> jobs; run(jobs) -> artifacts
  bundle.py    # artifacts -> manifest.json + files
  cli.py       # typer
player/        # static PWA (no Python), reads the bundle
tours/
personas/
cache/
dist/
tests/
```

### Principles

1. **Plan/execute split.** `plan()` is pure: returns jobs with cache keys and cached/miss status. `run()` executes misses. Enables `--dry-run`, cost estimates, trivial tests.
2. **Stages talk through the cache and bundle, not in-memory objects.** `generate` (text) and `speak` (audio) are separate commands; prompt iteration must never touch audio.
3. **Adapters are small Protocols resolved by a registry from persona config.** The pipeline never imports a concrete engine.
4. **Scripts are engine-neutral.** The LLM emits plain text, paragraphs, and at most `[pause]`. Never engine-specific markup (SSML, audio tags). Each TTS adapter renders the neutral script into its own dialect. Style is a neutral description string that adapters map as they can.
5. **Chunking/stitching lives in the pipeline, not adapters.** Split at paragraph boundaries to respect engine limits, synthesize, stitch with ffmpeg (shell out, don't wrap).
6. **Text and audio caches are keyed separately** so changing voice/engine never regenerates text.
7. **Make errors hard to make.** pydantic `extra="forbid"` everywhere, validate at load time, fail loudly, no silent defaults for anything that changes output.
8. **A future service/editor just imports `pipeline.plan/run`.** The CLI contains no logic the library lacks.

### Cache keys

- Story text: `hash(tour_id, node_id, node.topic, node.notes, persona.content, language, llm.model_id)`
- Bridge text (per edge): `hash(tour_id, from, to, edge.label, edge.minutes, both topics, persona.content, language, llm.model_id)`
- Audio: `hash(script_text, engine, voice, persona.tts.style, persona.tts.speed)`
- Layout: `cache/<stage>/<hash>.<ext>` + `<hash>.json` sidecar recording the inputs. Plain files, no SQLite (inspectable, diffable).

### Non-linear routes

Tours are directed graphs (cycles legal, player must never assume a DAG). Node stories are **self-contained**. Continuity comes from a short **bridge** generated per edge (A->B), which sees only the two topics + edge label/minutes, never the full stories, so it works from any path. Optional callbacks ("if you've visited X") are a possible later feature as conditional snippets.

## Stack and conventions

- Python 3.12+, uv, pydantic v2, typer, httpx, pytest, ruff.
- Sync code; thread pool for LLM/TTS calls. No asyncio.
- Concise, idiomatic Python. Type hints everywhere. Prefer small pure functions and dataclass/pydantic models over class hierarchies.
- Tests use a deterministic `FakeLLM` and `FakeTTS`; no network in tests.
- Secrets via env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`); never in YAML.
- LLM: one OpenAI-compatible adapter covers Ollama and OpenAI; a second covers Anthropic. No LiteLLM.
- Small local models (Ollama) are for debugging plumbing only; tune prompts on the model that will ship.

## Schemas

Full examples are in the appendix. Extract them to `personas/dry-historian.yaml` and `tours/newburyport.yaml` as the first step.

**Persona**: `id`, `name`, `language`, `content` (prompt, audience, length, bridge_length; hashed into text keys), `tts` (style, speed, ordered `voices` fallback list of `{engine, voice}`; hashed into audio keys only).

**Tour**: `id`, `title`, `start`, `defaults`, `nodes` mapping. Node: `title`, `topic`, optional `geo {lat, lon, radius}`, optional `notes` (free text injected as "prefer these facts"), optional `optional: true`, `next` list of edges `{to, label?, minutes?, mode?, optional?}`. Edges are written inline in nodes; the loader flattens them.

Topic strings are written in English; output language comes from the persona (the LLM translates concepts, keeps proper nouns in original form).

### Loader validation (beyond types)

- Every `to` and `start` resolves to a node.
- Every node reachable from `start`.
- At least one terminal node (`next: []`).
- `geo` optional per tour, but `radius` required wherever `geo` is present.
- Unknown keys are errors (typo like `lable:` must fail).
- Museum tours: same schema, `kind: museum` hint to the generator, `room:` field instead of `geo`. Defer until a test museum tour exists.

## CLI surface

`validate`, `plan` (what would run, what's cached, rough cost), `generate` (text), `speak` (audio), `bakeoff story.md --engines a,b,c` (render one story through several engines into a folder for listening), `bundle` (assemble for the player).

## Bundle contract (draft)

`dist/<tour>/<persona>/manifest.json` is the **only** interface between Python and the PWA. Include `"schema": 1` from day one. Contains: tour id/title, start, nodes (id, title, text path, audio path, geo), edges (from, to, label, minutes, optional, bridge text/audio paths), persona id/language, and attribution/credits if any. Plus the `.md` and `.opus`/`.mp3` files. Keep it flat and versioned; the PWA must refuse unknown major schema versions.

## Roadmap

- **P0, content quality (start here):** models, loader + validation, LLM protocol with Ollama and one cloud adapter, prompt assembly, cache, `validate`/`plan`/`generate`, markdown output. Tests with FakeLLM. Done when `generate` on the Newburyport example yields stories worth reading aloud.
- **P1, audio:** TTS protocol, kokoro + one cloud adapter, chunk/stitch, `speak`, `bakeoff`, `bundle` + manifest v1.
- **P2, player:** static PWA: graph navigation ("you are here, next options"), audio playback, text view, offline service worker, Media Session API lock-screen controls. Target is Android Chrome; verify background audio with the screen off early, this is the main risk.
- **P3, family beta:** real trips, feedback on pacing and story length.
- **P4, geo:** `watchPosition` in the PWA for "near next node" hints (arm only the next 1-2 nodes; GPS in dense areas is 10-30 m; keep a manual "next" button). Decide then whether a native app is needed. Freedom Trail: store the trail as a GPX polyline and snap to it instead of using a routing engine.
- **P5, editor:** AI-assisted tour authoring (LLM proposes the graph from a place name, human edits).

## Out of scope for now

Accounts, payments, live LLM/TTS at runtime, native mobile, background geolocation, grounding via structured `sources:`. If it goes public: check TTS voice licenses per voice, Wikipedia CC BY-SA attribution, OSM/ODbL and tile-server terms, and trademark issues around "Freedom Trail".

## Open questions

- Language: English-only, or Russian tours too? Decides TTS shortlist (verify Russian coverage of local models early).
- Final shipping LLM: Anthropic vs OpenAI (decide after P0 prompt tuning).
- Which two TTS engines for the first bake-off (proposal: Kokoro local + OpenAI cloud).

---

## Appendix A: `personas/dry-historian.yaml`

```yaml
id: dry-historian
name: The Dry Historian
language: en-US              # drives the text AND the TTS voice choice
content:                     # hashed into the text cache key
  prompt: |
    You are a local guide with deep knowledge and a dry wit. You tell stories,
    not lectures: open with a hook, include one surprising detail, and end on
    an image or a punchline. No bullet points, no headings, no stage directions.
    Write for the ear: short sentences, concrete nouns, numbers spelled out.
  audience: adults and teenagers, walking, no map in hand
  length: {words: 250, tolerance: 0.2}
  bridge_length: {words: 60}
tts:                         # NOT hashed into text; hashed into audio key
  style: warm, dry-witted storyteller, unhurried
  speed: 1.0
  voices:                    # fallback order
    - {engine: openai, voice: onyx}
    - {engine: kokoro, voice: am_michael}
```

## Appendix B: `tours/newburyport.yaml`

Coordinates are approximate placeholders; verify on a map.

```yaml
id: newburyport
title: Newburyport, MA
start: market-square
defaults: {mode: walk}

nodes:
  market-square:
    title: Market Square
    topic: The brick commercial heart of a once-rich shipping town, and the urban-renewal fight that nearly flattened it
    geo: {lat: 42.8113, lon: -70.8773, radius: 40}
    next:
      - {to: waterfront,   label: Down to the river,          minutes: 3}
      - {to: high-street,  label: Up the hill to the mansions, minutes: 8}
      - {to: custom-house, label: The maritime museum,        minutes: 4}

  waterfront:
    title: Waterfront Park
    topic: What the harbor looked like when it was full of ships
    geo: {lat: 42.8120, lon: -70.8800, radius: 60}
    notes: Boardwalk views toward the Merrimack mouth.   # injected as preferred facts
    next:
      - {to: custom-house, minutes: 5}
      - {to: plum-island,  label: Drive to the beach, mode: drive, minutes: 15, optional: true}

  custom-house:
    title: Custom House Maritime Museum
    topic: Clipper ships, customs duty, and why this building exists
    geo: {lat: 42.8118, lon: -70.8764, radius: 30}
    next:
      - {to: market-square, minutes: 4}
      - {to: high-street,   minutes: 9}

  high-street:
    title: High Street
    topic: Federal-era captains' houses as a display of money
    geo: {lat: 42.8085, lon: -70.8730, radius: 80}
    next:
      - {to: old-hill, minutes: 10}

  old-hill:
    title: Old Hill Burying Ground
    topic: Gravestones as local history, and what they say about who got remembered
    geo: {lat: 42.8070, lon: -70.8690, radius: 50}
    next: []                  # terminal

  plum-island:
    title: Plum Island
    topic: Barrier island, salt marsh, birds
    geo: {lat: 42.7900, lon: -70.8030, radius: 300}
    optional: true
    next: []
```
