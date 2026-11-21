"""
Blackbox test harness coordinator for LocalFM.
"""

import logging
from pathlib import Path
from typing import Optional

from .client import BlackboxClient
from tests.shared.cluster import PostgresClusterConfig, PostgresClusterManager
from tests.shared.database import CleanDatabase
from .service import TestService, create_test_service

logger = logging.getLogger("localfm.blackbox.harness")


class BlackboxTestHarness:
    """
    Coordinates the blackbox testing environment:
    - Ensures the shared PostgreSQL DB cluster is running via Podman.
    - Creates an isolated clean database for the test run.
    - Starts a unique test service instance dedicated to this run.
    - Provides a client to execute blackbox HTTP requests.
    - Automatically tears down the unique test service and clean database on completion.
    """

    def __init__(
        self,
        cluster: Optional[PostgresClusterManager] = None,
        cluster_config: Optional[PostgresClusterConfig] = None,
        service_type: Optional[str] = None,
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        library_dir: Optional[Path] = None,
    ):
        self.cluster = cluster or PostgresClusterManager(config=cluster_config)
        self.db = CleanDatabase(cluster=self.cluster)
        self.service_type = service_type
        self.port = port
        self.host = host
        self.library_dir = library_dir

        self.service: Optional[TestService] = None
        self.client: Optional[BlackboxClient] = None
        self._is_started = False

    @property
    def base_url(self) -> str:
        if not self.service:
            raise RuntimeError("Harness has not been started yet.")
        return self.service.base_url

    @property
    def db_name(self) -> str:
        return self.db.name

    def start(self) -> "BlackboxTestHarness":
        """
        Start the blackbox test harness:
        1. Ensure the shared PostgreSQL cluster container is up.
        2. Create the clean test database.
        3. Launch the unique test service.
        4. Initialize the HTTP test client.
        """
        if self._is_started:
            return self

        logger.info("Initializing blackbox testing harness...")
        # 1. Ensure shared postgres cluster container is running
        self.cluster.start_cluster()

        # 2. Create clean test database on the shared cluster
        self.db.create()

        # 3. Create and start unique test service instance
        self.service = create_test_service(
            db=self.db,
            service_type=self.service_type,
            port=self.port,
            host=self.host,
            library_dir=self.library_dir,
        )
        self.service.start()

        # 4. Instantiate client
        self.client = BlackboxClient(base_url=self.service.base_url)
        self._is_started = True
        logger.info(
            "Blackbox harness ready. Service running at %s, connected to database '%s'",
            self.service.base_url,
            self.db.name,
        )
        return self

    def stop(self) -> None:
        """
        Tear down the test service and drop the clean test database.
        Note: The shared PostgreSQL cluster container remains running for reuse.
        """
        if not self._is_started:
            return

        logger.info("Tearing down blackbox harness...")
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.warning("Error closing test client: %s", e)
            self.client = None

        if self.service:
            try:
                self.service.stop()
            except Exception as e:
                logger.warning("Error stopping test service: %s", e)

        if self.db:
            try:
                self.db.drop()
            except Exception as e:
                logger.warning("Error dropping test database: %s", e)

        self._is_started = False
        logger.info("Blackbox harness teardown complete.")

    def get_db_connection(self):
        """Get an active psycopg connection to the test database for assertion purposes."""
        return self.db.get_connection()

    def __enter__(self) -> "BlackboxTestHarness":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
