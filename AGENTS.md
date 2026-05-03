# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Code Placement Rules

Use these boundaries when adding or refactoring code:

- `libs/` = reusable domain logic and adapters. Single-SDK adapters for external services (Attio, Apollo, Gmail) belong here. Keep modules composable and callable from multiple contexts.
- `src/` = workflow orchestration. Any multi-step flow that chains operations, coordinates side effects, or runs pipeline logic belongs here.
- `cli/` = thin command surface only. Parse flags, perform preflight, call `src/` workflows, and render output/errors.

Anti-patterns:

- Do not add workflow orchestration directly in `libs/`.
- Do not make `cli/` command files own business logic.

Migration note:

- For all new work, follow this boundary. When touching legacy paths, prefer moving orchestration into `src/` incrementally.

## Package Management (uv)

**Always use `uv` as the package manager. Never use bare `pip`, `pip3`, or `python3 -m pip`.**

Common commands:

- `uv sync` — install dependencies from `pyproject.toml` and `uv.lock`
- `uv pip install <package>` — add a dependency (updates lock file)
- `uv run <command>` — run a command within the uv environment
- `uv python pin 3.x` — manage Python version for the project

Why: `uv` maintains a lock file (`uv.lock`) that ensures deterministic, reproducible environments across machines and CI. Bare `pip` bypasses this guarantee and can lead to environment drift.

## Testing

Run tests with pytest:

```bash
uv run pytest
```

pytest is configured to use importlib mode. Tests live in the `tests/` directory and follow the same module structure as `src/` and `libs/`.

## Temporary Files

All temporary files created during tool runs (intermediate outputs, scratch data, cached results, etc.) **must** be written to the `tmp/` directory at the project root. This directory is gitignored and cleaned up between runs. Never write temporary files to the project root or alongside source code.

## Documentation Placement

**Do NOT create summary or investigation documents.** Documentation should be live in the code itself.

Instead of creating summary `.md` files:

- **Add docstrings** to functions, classes, and modules that explain the "why" (not just the "what")
- **Add comments** in complex sections to document decisions and gotchas
- **Update module-level documentation** (docstrings at the top of files) when adding features
- **Keep README.md** files for each major module with setup/usage instructions
- **Use CHANGELOG.md** entries when making significant changes
- **Store architectural decisions** in design artifacts, not as loose summary documents

If you finish a task and need to communicate what was done, output the summary as text in your response—don't create `.md` files for it.

## Git Branch Naming

Always use the `agent/` prefix for branches created by AI agents (e.g., `agent/add-email-validation`). Never use `claude/` or other provider-specific prefixes.
## Git Worktrees

When creating git worktrees for this repository, always create them under `worktrees/` at the repository root unless the user explicitly requests a different location.

Before creating a worktree:

- Ensure `worktrees/` exists or create it
- Ensure `worktrees/` is ignored by git
- Use paths like `worktrees/<branch-name>`

Do not rely on git internal module paths such as `.git/modules/...` as user-facing worktree locations.
