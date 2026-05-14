# gtm

Go-To-Market SDK + CLI for account research, enrichment, CRM sync, and outreach. Layered architecture: thin CLI → workflow orchestration → single-SDK adapters. Deployable as Modal serverless functions; consumable as an editable Python package or git submodule.

- Package name: `gtm` (entrypoint script: `gtm = cli.main:run`)
- Python: `>=3.13,<3.14`
- Package manager: **`uv` only** (never bare `pip`)
- License: MIT

## Layout

```txt
gtm-sdk/
├── cli/         # Thin command surface (Typer). Parses flags, preflight, calls src/.
├── src/         # Workflow orchestration. Chains libs/ adapters. Modal endpoints register here.
├── libs/        # Single-SDK adapters. One folder per external service. NO cross-lib imports.
├── data-gen/    # Reusable data generation/enrichment pipelines (independent, composable).
├── webhooks/    # Standalone Modal webhook handlers (e.g. GCP raw/ETL exporters).
├── api/
│   ├── specs/   # External API OpenAPI specs (e.g. caldotcom)
│   └── samples/ # Sample payloads (rb2b, caldotcom)
├── tests/       # pytest, importlib mode. Mirrors src/, libs/, cli/.
├── tmp/         # Gitignored scratch. ALL temporary files go here.
├── worktrees/   # Gitignored. All git worktrees under this dir.
├── deploy.py    # Modal deploy entrypoint (must stay at root — avoids `attio` pkg shadowing).
├── pyproject.toml
└── uv.lock
```

### Layer rules (enforced)

- `libs/<x>/` wraps **one** external SDK or API. Idiomatic Python types/functions. **No `libs/<x>` may import from `libs/<y>`.**
- `src/` chains adapters into workflows. Modal `@app.function` / `@modal.fastapi_endpoint` decorators live here.
- `cli/` is Typer-only: parse args → preflight → call into `src/` → render. No business logic.
- `data-gen/` products are independent; do not depend on each other.

Anti-patterns: orchestration inside `libs/`; business logic inside `cli/`; cross-lib imports.

## Adapters (`libs/`)

| Adapter | Purpose |
| --- | --- |
| `apollo` | People + organization enrichment (via `gtm-apollo`) |
| `attio` | CRM: companies, people, notes, attributes, values |
| `browserbase` | Headless browser sessions |
| `caldotcom` | Cal.com bookings/events |
| `dlt` | dltHub filesystem destinations (GCP + local), DestinationType |
| `fathom` | Meeting recordings + transcripts |
| `filesystem` | File utilities for pipeline I/O |
| `gmail` | Gmail URL decoding |
| `granola` | Local Granola export reader |
| `harvest` | LinkedIn lead/profile data via Harvest |
| `linkedin` | LinkedIn member-data helpers |
| `octolens` | Mention monitoring |
| `openai` | Lead extraction via OpenAI |
| `parallel` | Parallel.ai web search / extract / findall |
| `parsers` | Generic parsers |
| `perplexity` | Perplexity API |
| `rb2b` | RB2B website visitor identification |
| `resend` | System/transactional email |
| `telemetry.py` | OTEL tracer init + `emit_cli_event` |

## Orchestration (`src/`)

- `src/app.py` — Modal `App` definition, image build, secret bindings (`apollo`, `attio`, `parallel`), endpoint module registration. **Edit here when adding new Modal endpoints.**
- `src/modal_app.py` — `MODAL_APP` name (env-overridable via `MODAL_APP`, default `elvis-ai-v2`).
- `src/api_keys.py` — API key resolution.
- `src/enrichment.py` — Enrichment workflow.
- `src/accounts/` — `accounts`, `research`, `people`, `batch`, `tasks`, `models`.
- `src/attio/` — `companies`, `people`, `notes`, `deployment_parity`, `http_responses`.
- `src/apollo/` — `organizations`, `people`.
- `src/parallel/` — `extract`, `findall`, `search`.
- `src/{caldotcom,fathom,granola,octolens,rb2b}/` — workflow modules per integration.

## CLI surface

Run via `uv run gtm <group> <command>` (or `uv run python -m cli.main`).

```txt
gtm
├── hello, version
├── accounts                       GTM workflow commands
│   ├── research                   Non-mutating research
│   ├── enrich                     Non-mutating enrichment
│   ├── find-people                Non-mutating people discovery
│   ├── map-account-hierarchy      Non-mutating hierarchy mapping
│   ├── batch-add-people           Batch add (preview/apply)
│   └── batch-add-companies        Batch add (preview/apply)
├── apollo
│   ├── people                     People enrichment + search
│   └── organizations              Org enrichment + search
├── attio
│   ├── people                     Manage people records
│   ├── companies                  Manage company records
│   └── notes                      Manage notes
├── enrichment
│   └── enrich                     Enrich records from LinkedIn (Harvest)
├── gmail
│   └── url                        Gmail URL decoding
├── granola
│   └── export                     Local Granola export
└── parallel
    ├── extract                    Extract content from URLs
    ├── findall                    Discover entities (FindAll)
    └── search                     Search the web
```

CLI helpers: `cli/json_encoder.py`, `cli/json_validation.py`. CLI emits OTEL events (`cli.usage_error` on exit code 2).

## Install

### As an editable submodule (preferred when consumed from another repo)

```bash
git submodule add git@github.com:elviskahoro/gtm.git gtm-sdk
```

In the parent `pyproject.toml`:

```toml
[tool.uv.sources]
gtm = { path = "gtm-sdk", editable = true }
```

Then `uv sync`. All `cli`, `src`, `libs` packages become importable.

### Standalone

```bash
git clone --recurse-submodules git@github.com:elviskahoro/gtm.git
cd gtm
uv sync
```

## Common commands

```bash
uv sync                          # install/lock deps
uv run gtm --help                # CLI help
uv run gtm <group> <cmd> --help  # subcommand help
uv run pytest                    # full test suite (importlib mode)
uv run pytest tests/cli          # subset
trunk check --all                # lint + typecheck (ruff, etc.)
```

## Modal deployment

```bash
uv run modal deploy deploy.py
```

- `deploy.py` lives at the repo root **on purpose** — moving it under `src/` causes `src/attio/` to shadow the pip `attio` package.
- App name resolves from `MODAL_APP` env var; falls back to `elvis-ai-v2`.
- Image is debian_slim + Python 3.13 with a pinned subset of deps and local `libs/` + `src/` mounted via `add_local_python_source`.
- Secrets used: `apollo`, `attio`, `parallel` (Modal `Secret.from_name`).
- Free tier cap: **8 web endpoints** total. Parallel endpoints are gated behind a plan upgrade.
- Endpoint modules are imported in `src/app.py` for decorator registration — when adding a new endpoint module, add the import there.

Build env vars baked into the image: `AI_BUILD_GIT_SHA`, `AI_DEPLOYED_AT`.

## Webhooks

Standalone Modal apps under `webhooks/`:

- `export_to_gcp_raw.py` — raw payload sink to GCS (bucket `dlthub-devx-test-bucket`, secret `devx-gcp-202605111323`).
- `export_to_gcp_etl.py` — ETL variant.

Deploy each independently with `modal deploy webhooks/<file>.py`.

## Telemetry

OTEL traces emitted from `libs/telemetry.py`. Activated only when one of:

- `HYPERDX_API_KEY` — direct HyperDX ingestion (auto-prefixes `Bearer`).
- `HYPERDX_OTLP_ENDPOINT` — overrides the HyperDX endpoint (default `https://in-otel.hyperdx.io/v1/traces`).
- `OTEL_EXPORTER_OTLP_ENDPOINT` — custom OTEL collector.

If none set → tracer is a no-op. CLI calls `init_tracer()` at startup and emits `cli.usage_error` events on Typer exit code 2.

## Conventions

- **Temp files**: `tmp/` only. Never alongside source.
- **Branches**: `agent/<slug>` for agent-created branches. Never `claude/*`.
- **Worktrees**: under `worktrees/<branch-name>`. Never use `.git/modules/*` paths as user-facing worktrees.
- **Commits**: never add AI co-author trailers (`Co-Authored-By: Claude/Oz/...`). Human authors only.
- **Documentation**: live in code (docstrings, README per major module, CHANGELOG entries). Do **not** create summary/investigation `.md` files.
- **Path anchoring in scripts**: anchor file I/O on `Path(__file__).resolve().parent`, never the CWD — `uv run path/to/script.py` does not chdir.

## Testing

- `pytest` with `--import-mode=importlib` (already in `pyproject.toml`).
- Layout mirrors source: `tests/cli/`, `tests/libs/`, `tests/src/`, `tests/integration/`.
- Integration smoke: `tests/integration/test_gtm_remote_smoke.py`.
- `S101` (assert) is allowed in `tests/**` (ruff per-file ignore).

## Agent guidance

When adding functionality:

1. **External SDK call?** → New file in `libs/<service>/`. Wrap one SDK only. No cross-lib imports.
2. **Multi-step flow / Modal endpoint?** → `src/<service>/`. Register module import in `src/app.py` if it defines endpoints.
3. **User-facing command?** → `cli/<group>/`. Typer subapp. Call into `src/`. Wire into `cli/main.py` via `app.add_typer(...)`.
4. **Standalone data product?** → `data-gen/<product>/`. Self-contained.
5. **Webhook handler?** → `webhooks/<name>.py`. Independent Modal app.

See `AGENTS.md` (symlinked from `CLAUDE.md`) for the authoritative version of these rules.
