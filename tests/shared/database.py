"""
Clean test database manager for isolated test runs.
"""

import logging
import uuid
from typing import Optional

import psycopg

from .cluster import PostgresClusterManager

logger = logging.getLogger("localfm.shared.database")


def generate_test_db_name() -> str:
    """Generate a unique database name for a test run."""
    return f"localfm_test_{uuid.uuid4().hex[:10]}"


class CleanDatabase:
    """
    Represents an isolated, clean test database created on the shared PostgreSQL cluster.
    Automatically drops the database upon context exit or teardown.
    """

    def __init__(
        self,
        cluster: Optional[PostgresClusterManager] = None,
        db_name: Optional[str] = None,
    ):
        self.cluster = cluster or PostgresClusterManager()
        self.name = db_name or generate_test_db_name()
        self._is_created = False

    @property
    def host(self) -> str:
        return self.cluster.config.host

    @property
    def port(self) -> int:
        return self.cluster.config.port

    @property
    def user(self) -> str:
        return self.cluster.config.user

    @property
    def password(self) -> str:
        return self.cluster.config.password

    @property
    def container_host(self) -> str:
        return self.cluster.config.container_name

    @property
    def container_port(self) -> int:
        return self.cluster.config.container_internal_port

    @property
    def connection_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    def create(self) -> "CleanDatabase":
        """Create the database on the shared PostgreSQL cluster."""
        if not self._is_created:
            self.cluster.create_database(self.name)
            self._is_created = True
        return self

    def drop(self) -> None:
        """Drop the test database from the shared PostgreSQL cluster."""
        if self._is_created:
            try:
                self.cluster.drop_database(self.name)
            except Exception as e:
                logger.warning("Failed to drop test database '%s': %s", self.name, e)
            finally:
                self._is_created = False

    def get_connection(self) -> psycopg.Connection:
        """Get an active psycopg connection to this test database."""
        return psycopg.connect(self.connection_url, autocommit=True)

    def __enter__(self) -> "CleanDatabase":
        return self.create()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.drop()

    def __repr__(self) -> str:
        return f"<CleanDatabase name='{self.name}' host='{self.host}:{self.port}'>"
