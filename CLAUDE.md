# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Permifrost

Permifrost is a Python CLI tool that manages Snowflake user and role permissions declaratively. It reads a YAML specification file and generates/executes `GRANT` and `REVOKE` statements to bring a Snowflake account's permission state in line with the spec.

**This repository is a fork by Gemma Analytics of the original Permifrost project at [https://gitlab.com/gitlab-data/permifrost](https://gitlab.com/gitlab-data/permifrost).** The fork is published as the [`gemma.permifrost`](https://pypi.org/project/gemma.permifrost/) package on PyPI and is used in tandem with [tundri](https://github.com/Gemma-Analytics/tundri), which handles object-level DDL (CREATE/DROP/ALTER) before Permifrost runs permission grants.

## Development Commands

```bash
# Install dev dependencies
pip install -e '.[dev]'

# Or via Docker
make permifrost      # Opens a shell in a container with Permifrost installed

# Run CLI
permifrost run <spec_file> --dry         # Dry run (no changes)
permifrost run <spec_file>               # Execute grants/revokes
permifrost spec-test <spec_file>         # Validate spec file only

# Tests
pytest -x -v --disable-pytest-warnings   # All tests
make test                                 # Run tests via Docker

# Linting
make local-lint      # Black + isort + mypy + flake8 (auto-fix)
make local-show-lint # Show lint results without fixing

# Type checking
mypy src/permifrost/ --ignore-missing-imports
```

## Architecture

### Module Overview

| Module | Purpose |
|--------|---------|
| `src/permifrost/cli/cli.py` | Click CLI entry point (`permifrost` command group) |
| `src/permifrost/cli/permissions.py` | `run` and `spec-test` subcommands |
| `src/permifrost/snowflake_spec_loader.py` | Parse YAML spec into permission objects |
| `src/permifrost/spec_file_loader.py` | Load and validate YAML spec files |
| `src/permifrost/snowflake_connector.py` | Snowflake connection management |
| `src/permifrost/snowflake_grants.py` | Generate and execute GRANT/REVOKE statements |
| `src/permifrost/snowflake_permission.py` | Permission model and comparison logic |
| `src/permifrost/entities.py` | Dataclasses for roles, users, databases, schemas, warehouses |
| `src/permifrost/spec_schemas/` | Cerberus YAML validation schemas |

### Execution Flow

1. Load and validate the YAML spec file
2. Connect to Snowflake using env var credentials
3. Inspect current grants on the account
4. Compare desired vs. actual permission state
5. Generate GRANT/REVOKE statements for the diff
6. Execute statements (unless `--dry`)

## Environment Variables

```
PERMISSION_BOT_ACCOUNT=<account-id>
PERMISSION_BOT_USER=PERMIFROST
PERMISSION_BOT_PASSWORD=<password>
PERMISSION_BOT_ROLE=SECURITYADMIN
PERMISSION_BOT_DATABASE=PERMIFROST
PERMISSION_BOT_WAREHOUSE=ADMIN
```

## Key Files

- `pyproject.toml` — package metadata, dependencies, entry point (`gemma.permifrost`)
- `VERSION` — current package version
- `GEMMA_RELEASE.md` — release process for publishing to PyPI
- `CHANGELOG.md` — version history
- `CONTRIBUTING.md` — contribution guidelines

## Release Process

Releases are managed manually using `bumpversion` and `twine`. See `GEMMA_RELEASE.md` for full details.

```bash
# Bump version
bumpversion patch   # or minor / major

# Build and publish
python -m build
twine upload dist/*
```

## Conventions

- Source code lives under `src/permifrost/`
- Tests live under `tests/`
- Use `pip install -e '.[dev]'` for local development (not `uv`)
- Docker-based workflow is available via `make` targets for a fully isolated environment
- Never commit directly to `main` — always create a feature branch and open a PR
