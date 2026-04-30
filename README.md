# gtm

**gtm** is Go-To-Market infrastructure for account research and outreach. It provides composable adapters for Apollo, Attio, Gmail, Granola, and Parallel web search, orchestrated through a CLI and deployed as serverless functions on Modal.

## Install as a submodule

Add gtm to your project as an editable Git submodule:

```bash
git submodule add git@github.com:elviskahoro/gtm.git gtm
cd gtm
uv sync
```

## CLI usage

Run the gtm CLI locally for testing and one-off tasks:

```bash
# See all available commands
uv run gtm --help

# Research an account by ID
uv run gtm accounts research --account-id <id>

# Add a contact to Attio
uv run gtm attio people add <email>
```

## Modal deployment

Deploy gtm functions to Modal for scheduled and serverless execution:

```bash
cd gtm
uv run modal deploy deploy.py
```

The deployment respects the `MODAL_APP` environment variable. If set, functions deploy under that app name; otherwise they use the app name defined in `deploy.py`.

## Telemetry

gtm emits OpenTelemetry traces when configured. Set any of these environment variables:

- `HYPERDX_API_KEY` — enables direct HyperDX ingestion
- `HYPERDX_OTLP_ENDPOINT` — HyperDX OTLP endpoint (defaults to `https://in-otel.hyperdx.io/v1/traces` when `HYPERDX_API_KEY` is set, optional)
- `OTEL_EXPORTER_OTLP_ENDPOINT` — sends traces to a custom OpenTelemetry collector

If none are set, telemetry is disabled and no traces are emitted.

## Contributing

Forks welcome. Layer your own skills, projects, and design artifacts on top by consuming gtm as a submodule in your own repository.

## License

MIT. See [LICENSE](./LICENSE).
