# LocalFM

My personal music nexus.

## Local deployment

### Windows

```shell
scoop install postgresql

# initialise the DB data dir
d:\scoop\apps\postgresql\current\bin\initdb.exe -D D:\scoop\persist\postgresql\18.1\data -E 'UTF-8' --lc-collate='English_Ireland.UTF-8' --lc-ctype='English_Ireland.UTF-8'
```

### Fedora Linux

```shell
sudo dnf install postgresql-server just caddy
cargo binstall mprocs

/usr/lib/postgresql/17/bin/initdb -D ./deployment/local/pgdata -E 'UTF-8' --lc-collate='en_IE.UTF-8' --lc-ctype='en_IE.UTF-8'
```

### Debian Linux

```shell
sudo apt install postgresql-server

/usr/lib/postgresql/17/bin/initdb -D ./deployment/local/pgdata -E 'UTF-8' --lc-collate='en_IE.UTF-8' --lc-ctype='en_IE.UTF-8'
```

### Podman

```shell
podman build -t localfm .
podman run --rm -e LIBRARY_DIRECTORY=/Music -v ${HOME}/Music:/Music -it localfm 
```

## Commands

### Bootstrap

```shell
just run-command collectstatic
just gnu-run-all
just clean
```

### Import library

Ensure that `LIBRARY_DIRECTORY` is valid for the environment before running.

```shell
just run-command import_library
```

## Import scrobbles

All LastFM credentials need to be injected via env vars beforehand

```shell
just run-command import_scrobbles
```

## Blackbox Testing

LocalFM includes an end-to-end blackbox testing harness that tests the service externally over HTTP.

### How It Works

1. **Shared PostgreSQL DB Cluster**: A dedicated PostgreSQL container (`localfm-test-postgres`) runs in Podman on a dedicated port (`5533` by default) attached to a Podman network (`localfm-test-net`). The cluster container is shared across test runs and started automatically if not running.
2. **Clean Test Database**: For each test run, the harness dynamically creates a fresh, clean database (e.g., `localfm_test_<unique_id>`) on the shared PostgreSQL cluster.
3. **Dedicated Test Service**: A unique test service instance is launched specifically for the test run, pointed at the clean database with its own dynamic port and isolated music directory. The harness automatically runs migrations and waits for the HTTP endpoint to become healthy.
4. **Automatic Teardown**: Upon test run completion, the dedicated test service is cleanly shut down and the test database is dropped (`WITH (FORCE)`).

### Running Tests

```shell
# Run all blackbox tests
just test-blackbox

# Or run directly via pytest
uv run pytest tests/blackbox
```

### Shared Cluster Management

You can inspect or control the shared test PostgreSQL cluster container using Just or the CLI:

```shell
just test-cluster-status
just test-cluster-start
just test-cluster-stop
```

### Configuration

The harness can be configured via environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `LOCALFM_TEST_SERVICE_TYPE` | Service runner: `container`, `process`, or `auto` | `container` |
| `LOCALFM_TEST_DB_PORT` | Mapped host port for shared PostgreSQL container | `5533` |
| `LOCALFM_TEST_PG_CONTAINER` | Podman container name for PostgreSQL cluster | `localfm-test-postgres` |
| `LOCALFM_TEST_PG_IMAGE` | PostgreSQL container image | `docker.io/library/postgres:17-alpine` |
| `LOCALFM_TEST_NETWORK` | Podman network for test containers | `localfm-test-net` |

# TODO

Configure systemd service in homelab.
Make the daily library import use a date range based on last success.
Send notification (how?) when scrobbles fail to import to DB.
  Perhaps a section in the web UI?
Re-import library files on library file change.
Make the server reload on project file change - SIGHUP support?
Auto-fix MP3/AAC metadata when import fails
  Just re-save the metadata
  Or fork the metadata lib to correctly read the older metadata format
  Or force a re-save of the entire music library
