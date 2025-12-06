set dotenv-load

win-run-all:
    mprocs -c mprocs.win.yaml

run-command +ARGS:
    uv run python -m manage {{ARGS}}

migrate:
    uv run python -m manage migrate

generate-migrations *ARGS:
    uv run python -m manage makemigrations {{ARGS}}

lint:
    uv run isort .
    uv run ruff format .
