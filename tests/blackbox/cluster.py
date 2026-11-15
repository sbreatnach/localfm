"""
Manages the shared PostgreSQL DB cluster container in Podman.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import psycopg

logger = logging.getLogger("localfm.blackbox.cluster")


@dataclass
class PostgresClusterConfig:
    container_name: str = os.environ.get(
        "LOCALFM_TEST_PG_CONTAINER", "localfm-test-postgres"
    )
    image: str = os.environ.get(
        "LOCALFM_TEST_PG_IMAGE", "docker.io/library/postgres:17-alpine"
    )
    network: str = os.environ.get("LOCALFM_TEST_NETWORK", "localfm-test-net")
    host: str = os.environ.get("LOCALFM_TEST_DB_HOST", "127.0.0.1")
    port: int = int(os.environ.get("LOCALFM_TEST_DB_PORT", "5533"))
    user: str = os.environ.get("LOCALFM_TEST_DB_USER", "localfm")
    password: str = os.environ.get("LOCALFM_TEST_DB_PASSWORD", "localfm")
    admin_db: str = os.environ.get("LOCALFM_TEST_ADMIN_DB", "postgres")
    container_internal_port: int = 5432


class PostgresClusterManager:
    """
    Manages the lifecycle of a shared PostgreSQL container in Podman.
    Provides methods to start/stop the cluster and create/drop isolated test databases.
    """

    def __init__(self, config: Optional[PostgresClusterConfig] = None):
        self.config = config or PostgresClusterConfig()
        self._podman_bin = shutil.which("podman")
        if not self._podman_bin:
            raise RuntimeError(
                "podman executable not found in PATH. Podman is required to run the shared test DB cluster."
            )

    @property
    def admin_connection_url(self) -> str:
        return (
            f"postgresql://{self.config.user}:{self.config.password}@"
            f"{self.config.host}:{self.config.port}/{self.config.admin_db}"
        )

    def _run_podman(self, *args, check=True) -> subprocess.CompletedProcess:
        cmd = [self._podman_bin, *args]
        logger.debug("Running: %s", " ".join(cmd))
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
        )

    def ensure_network(self) -> None:
        """Ensure the podman network exists for test containers."""
        res = self._run_podman("network", "exists", self.config.network, check=False)
        if res.returncode != 0:
            logger.info("Creating Podman network '%s'", self.config.network)
            self._run_podman("network", "create", self.config.network)

    def container_exists(self) -> bool:
        """Check if the postgres container exists in Podman."""
        res = self._run_podman(
            "container", "exists", self.config.container_name, check=False
        )
        return res.returncode == 0

    def is_container_running(self) -> bool:
        """Check if the postgres container is running."""
        res = self._run_podman(
            "inspect",
            "--format",
            "{{.State.Status}}",
            self.config.container_name,
            check=False,
        )
        if res.returncode != 0:
            return False
        return res.stdout.strip() == "running"

    def start_cluster(self, timeout: float = 30.0) -> None:
        """
        Ensure the shared PostgreSQL DB cluster container is running and ready.
        Reuses existing running container if available.
        """
        if self.is_container_running():
            logger.info(
                "Shared PostgreSQL container '%s' is already running",
                self.config.container_name,
            )
            self.wait_until_ready(timeout=timeout)
            return

        self.ensure_network()

        if self.container_exists():
            logger.info(
                "Starting existing stopped PostgreSQL container '%s'",
                self.config.container_name,
            )
            self._run_podman("start", self.config.container_name)
        else:
            logger.info(
                "Launching new shared PostgreSQL container '%s' on port %d",
                self.config.container_name,
                self.config.port,
            )
            self._run_podman(
                "run",
                "-d",
                "--name",
                self.config.container_name,
                "--network",
                self.config.network,
                "-p",
                f"{self.config.host}:{self.config.port}:{self.config.container_internal_port}",
                "-e",
                f"POSTGRES_USER={self.config.user}",
                "-e",
                f"POSTGRES_PASSWORD={self.config.password}",
                "-e",
                f"POSTGRES_DB={self.config.admin_db}",
                self.config.image,
            )

        self.wait_until_ready(timeout=timeout)

    def stop_cluster(self, timeout: int = 5) -> None:
        """Stop the shared PostgreSQL container."""
        if self.is_container_running():
            logger.info(
                "Stopping PostgreSQL container '%s'", self.config.container_name
            )
            self._run_podman(
                "stop", "-t", str(timeout), self.config.container_name, check=False
            )

    def remove_cluster(self) -> None:
        """Force-remove the shared PostgreSQL container."""
        if self.container_exists():
            logger.info(
                "Removing PostgreSQL container '%s'", self.config.container_name
            )
            self._run_podman("rm", "-f", self.config.container_name, check=False)

    def wait_until_ready(self, timeout: float = 30.0) -> None:
        """Poll the PostgreSQL container until it accepts client connections."""
        start_time = time.monotonic()
        last_err = None
        while time.monotonic() - start_time < timeout:
            try:
                with psycopg.connect(
                    self.admin_connection_url, connect_timeout=2
                ) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                        cur.fetchone()
                logger.debug(
                    "PostgreSQL cluster '%s' is ready", self.config.container_name
                )
                return
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        raise TimeoutError(
            f"PostgreSQL container '{self.config.container_name}' failed to become ready within {timeout}s: {last_err}"
        )

    def get_admin_connection(self) -> psycopg.Connection:
        """Return an autocommit connection to the admin database."""
        return psycopg.connect(self.admin_connection_url, autocommit=True)

    def _validate_dbname(self, db_name: str) -> None:
        if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
            raise ValueError(
                f"Invalid database name '{db_name}'. Only alphanumeric characters and underscores are allowed."
            )

    def create_database(self, db_name: str) -> None:
        """Create a new clean database on the shared PostgreSQL cluster."""
        self._validate_dbname(db_name)
        logger.info("Creating clean test database '%s'", db_name)
        with self.get_admin_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'CREATE DATABASE "{db_name}" OWNER "{self.config.user}";')

    def drop_database(self, db_name: str) -> None:
        """Drop a database on the shared PostgreSQL cluster, terminating existing connections."""
        self._validate_dbname(db_name)
        logger.info("Dropping test database '%s'", db_name)
        with self.get_admin_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid();
                    """,
                    (db_name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE);')

    def list_databases(self) -> list[str]:
        """List all non-template databases in the cluster."""
        with self.get_admin_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT datname FROM pg_database WHERE datistemplate = false;"
                )
                rows = cur.fetchall()
                return [row[0] for row in rows]

    def database_exists(self, db_name: str) -> bool:
        """Check whether a specific database exists in the cluster."""
        return db_name in self.list_databases()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    mgr = PostgresClusterManager()

    if action == "start":
        mgr.start_cluster()
        print(
            f"PostgreSQL cluster '{mgr.config.container_name}' started and ready on port {mgr.config.port}."
        )
    elif action == "stop":
        mgr.stop_cluster()
        print(f"PostgreSQL cluster '{mgr.config.container_name}' stopped.")
    elif action == "rm":
        mgr.remove_cluster()
        print(f"PostgreSQL cluster '{mgr.config.container_name}' removed.")
    elif action == "status":
        running = mgr.is_container_running()
        print(
            f"PostgreSQL cluster '{mgr.config.container_name}': {'RUNNING' if running else 'STOPPED'}"
        )
        if running:
            print("Databases:", mgr.list_databases())
    else:
        print(f"Unknown action: {action}. Available: start, stop, rm, status")
        sys.exit(1)
