# Talnaspor

Auditable question answering over official Icelandic statistics.

## Goals

- Retrieve observations from Statistics Iceland's PX-Web API.
- Validate statistical queries against official table metadata.
- Report periods, units and provenance.
- Reject unsupported or ambiguous queries rather than invent answers.

## Development

Python 3.11 or later.

Install [uv](https://docs.astral.sh/uv/) and use the Makefile for common tasks:

```sh
make sync          # Install the project and development tools from uv.lock
make run           # Start the API at http://127.0.0.1:8000 (docs at /docs)
make evaluate      # Ask the evaluation questions live; write evaluation/results.md
make check         # Check the lockfile, lint, formatting, types, and tests
make format        # Format Python code
make typecheck     # Type-check source and tests with mypy
make test          # Run tests
make build         # Create source and wheel distributions in dist/
make clean         # Remove generated artifacts and caches; preserve .venv
make distclean     # Also remove .venv; run make sync to start again
```

Ask a question once the API is running:

```sh
curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' \
     -d '{"question": "Hver er verðbólgan núna?"}'
```

Run `make` or `make help` for every target. For example, use
`make test PYTEST_ARGS='-q -k query'` to pass pytest options. `UV` and
`RUFF_ARGS` and `MYPY_ARGS` can also be overridden on the command line.

`make clean` works without Python or uv, including after a failed build. It
removes Python bytecode, tool caches, package metadata, build outputs, and
coverage reports. It preserves virtual environments, Git metadata, source,
documentation, `uv.lock`, and `.env`. `make clean-venv` removes only `.venv`.
Cleanup does not clear uv's shared download cache or follow symlinks.

The project is under active development for Gagnaþon 2026.
