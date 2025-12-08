set dotenv-load

gnu-bootstrap:
    /usr/lib/postgresql/17/bin/initdb -D ./deployment/local/pgdata -E 'UTF-8' --lc-collate='en_IE.UTF-8' --lc-ctype='en_IE.UTF-8'

win-run-all:
    mprocs -c mprocs.win.yaml

gnu-run-all:
    mprocs -c mprocs.gnu.yaml

run-command +ARGS:
    uv run python -m manage {{ARGS}}

clean:
    psql -h 127.0.0.1 --port 5532 -f ./deployment/local/db-init.sql postgres

migrate:
    uv run python -m manage migrate

generate-migrations *ARGS:
    uv run python -m manage makemigrations {{ARGS}}

lint:
    uv run isort .
    uv run ruff format .
