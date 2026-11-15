"""
Test service runner for localfm Django application.
Supports running dedicated test services as Podman containers or local Python processes.
"""

import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from .database import CleanDatabase

logger = logging.getLogger("localfm.blackbox.service")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_free_port() -> int:
    """Find an available TCP port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


class ServiceStartupError(RuntimeError):
    """Raised when the test service fails to start or pass health check."""

    pass


class TestService(ABC):
    """
    Abstract base class for a dedicated Django test service instance.
    """

    def __init__(
        self,
        db: CleanDatabase,
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        library_dir: Optional[Path] = None,
    ):
        self.db = db
        self.host = host
        self.port = port or find_free_port()
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        if library_dir:
            self.library_dir = library_dir
        else:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="localfm_test_lib_")
            self.library_dir = Path(self._temp_dir.name)
        self._is_running = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @abstractmethod
    def start(self) -> "TestService":
        """Start the test service instance."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop and tear down the test service instance."""
        pass

    @abstractmethod
    def get_logs(self) -> str:
        """Return stdout/stderr logs from the service."""
        pass

    def wait_until_ready(self, timeout: float = 30.0) -> None:
        """Poll the service until it returns HTTP 200 on an endpoint."""
        logger.info("Waiting for test service at %s to be ready...", self.base_url)
        start_time = time.monotonic()
        probe_endpoints = ["/api/v1/artists", "/tracks"]
        last_error = None

        while time.monotonic() - start_time < timeout:
            for endpoint in probe_endpoints:
                try:
                    with httpx.Client(base_url=self.base_url, timeout=2.0) as client:
                        resp = client.get(endpoint)
                        if resp.status_code == 200:
                            logger.info(
                                "Test service at %s is ready (responded 200 on %s)",
                                self.base_url,
                                endpoint,
                            )
                            return
                except Exception as exc:
                    last_error = exc
            time.sleep(0.3)

        logs = self.get_logs()
        raise ServiceStartupError(
            f"Test service at {self.base_url} failed to become ready within {timeout}s: {last_error}\n"
            f"--- Service logs ---\n{logs}"
        )

    def cleanup_resources(self) -> None:
        """Clean up temporary directory."""
        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception as e:
                logger.warning("Error cleaning up temp directory: %s", e)
            self._temp_dir = None

    def __enter__(self) -> "TestService":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class ContainerTestService(TestService):
    """
    Runs the dedicated Django service as a Podman container.
    """

    def __init__(
        self,
        db: CleanDatabase,
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        image: Optional[str] = None,
        library_dir: Optional[Path] = None,
    ):
        super().__init__(db=db, port=port, host=host, library_dir=library_dir)
        self.image = image or os.environ.get(
            "LOCALFM_TEST_SERVICE_IMAGE", "localhost/localfm:latest"
        )
        self.container_name = f"localfm-test-svc-{uuid.uuid4().hex[:8]}"
        self._podman_bin = shutil.which("podman")
        if not self._podman_bin:
            raise RuntimeError("podman executable not found in PATH.")

    def _run_podman(self, *args, check=True) -> subprocess.CompletedProcess:
        cmd = [self._podman_bin, *args]
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
        )

    def start(self) -> "ContainerTestService":
        if self._is_running:
            return self

        logger.info(
            "Starting test service container '%s' on port %d, connected to DB '%s'",
            self.container_name,
            self.port,
            self.db.name,
        )

        localfm_dir = PROJECT_ROOT / "localfm"
        manage_py = PROJECT_ROOT / "manage.py"

        run_args = [
            "run",
            "-d",
            "--name",
            self.container_name,
            "--network",
            self.db.cluster.config.network,
            "-p",
            f"{self.host}:{self.port}:8011",
            "-e",
            f"LOCALFM_DB_HOST={self.db.container_host}",
            "-e",
            f"LOCALFM_DB_PORT={self.db.container_port}",
            "-e",
            f"LOCALFM_DB_NAME={self.db.name}",
            "-e",
            f"LOCALFM_DB_USER={self.db.user}",
            "-e",
            f"LOCALFM_DB_PASSWORD={self.db.password}",
            "-e",
            "DJANGO_SETTINGS_MODULE=localfm.settings",
            "-e",
            "DJANGO_ALLOWED_HOSTS=*",
            "-e",
            "DJANGO_DEBUG=True",
            "-e",
            "DJANGO_SECRET_KEY=blackbox-test-secret-key",
            "-e",
            "LIBRARY_DIRECTORY=/app/test_library",
            "-v",
            f"{localfm_dir}:/app/localfm:ro",
            "-v",
            f"{manage_py}:/app/manage.py:ro",
            "-v",
            f"{self.library_dir}:/app/test_library:rw",
            self.image,
        ]

        res = self._run_podman(*run_args, check=False)
        if res.returncode != 0:
            raise ServiceStartupError(
                f"Failed to start test service container '{self.container_name}': {res.stderr}"
            )

        self._is_running = True
        try:
            self.wait_until_ready()
        except Exception:
            self.stop()
            raise

        return self

    def stop(self) -> None:
        if self._is_running:
            logger.info(
                "Stopping and removing test service container '%s'", self.container_name
            )
            self._run_podman("stop", "-t", "2", self.container_name, check=False)
            self._run_podman("rm", "-f", self.container_name, check=False)
            self._is_running = False
            self.cleanup_resources()

    def get_logs(self) -> str:
        res = self._run_podman("logs", self.container_name, check=False)
        return (res.stdout or "") + (res.stderr or "")


class ProcessTestService(TestService):
    """
    Runs the dedicated Django service as a local Python subprocess.
    """

    def __init__(
        self,
        db: CleanDatabase,
        port: Optional[int] = None,
        host: str = "127.0.0.1",
        library_dir: Optional[Path] = None,
    ):
        super().__init__(db=db, port=port, host=host, library_dir=library_dir)
        self._proc: Optional[subprocess.Popen] = None
        self._log_file: Optional[tempfile.NamedTemporaryFile] = None

    def start(self) -> "ProcessTestService":
        if self._is_running:
            return self

        logger.info(
            "Starting test service process on port %d, connected to DB '%s'",
            self.port,
            self.db.name,
        )

        env = os.environ.copy()
        env.update(
            {
                "LOCALFM_DB_HOST": self.db.host,
                "LOCALFM_DB_PORT": str(self.db.port),
                "LOCALFM_DB_NAME": self.db.name,
                "LOCALFM_DB_USER": self.db.user,
                "LOCALFM_DB_PASSWORD": self.db.password,
                "DJANGO_SETTINGS_MODULE": "localfm.settings",
                "DJANGO_ALLOWED_HOSTS": "*",
                "DJANGO_DEBUG": "True",
                "DJANGO_SECRET_KEY": "blackbox-test-secret-key",
                "LIBRARY_DIRECTORY": str(self.library_dir),
            }
        )

        self._log_file = tempfile.NamedTemporaryFile(
            prefix=f"localfm_svc_{self.port}_", suffix=".log", delete=False
        )

        cmd = [
            sys.executable,
            "-m",
            "localfm.main",
            "--port",
            str(self.port),
            "--host",
            self.host,
        ]

        self._proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
        )
        self._is_running = True

        try:
            self.wait_until_ready()
        except Exception:
            self.stop()
            raise

        return self

    def stop(self) -> None:
        if self._is_running and self._proc:
            logger.info("Stopping test service process (PID %d)", self._proc.pid)
            try:
                self._proc.send_signal(signal.SIGTERM)
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Process did not exit after SIGTERM, sending SIGKILL"
                    )
                    self._proc.kill()
                    self._proc.wait(timeout=2)
            except Exception as e:
                logger.warning("Error stopping process %d: %s", self._proc.pid, e)
            finally:
                self._proc = None
                self._is_running = False
                if self._log_file:
                    try:
                        self._log_file.close()
                    except Exception:
                        pass
                self.cleanup_resources()

    def get_logs(self) -> str:
        if self._log_file:
            try:
                with open(self._log_file.name, "r") as f:
                    return f.read()
            except Exception as e:
                return f"<Error reading log file {self._log_file.name}: {e}>"
        return "<No log file>"


def create_test_service(
    db: CleanDatabase,
    service_type: Optional[str] = None,
    port: Optional[int] = None,
    host: str = "127.0.0.1",
    library_dir: Optional[Path] = None,
) -> TestService:
    """
    Factory function to instantiate a dedicated test service.
    Defaults to container mode, or process mode if configured.
    """
    resolved_type = (
        service_type or os.environ.get("LOCALFM_TEST_SERVICE_TYPE", "container")
    ).lower()

    if resolved_type == "auto":
        # Auto-detect: if podman is installed, prefer container mode; otherwise process mode
        if shutil.which("podman"):
            resolved_type = "container"
        else:
            resolved_type = "process"

    if resolved_type == "container":
        return ContainerTestService(
            db=db, port=port, host=host, library_dir=library_dir
        )
    elif resolved_type == "process":
        return ProcessTestService(db=db, port=port, host=host, library_dir=library_dir)
    else:
        raise ValueError(
            f"Unknown test service type '{resolved_type}'. Expected 'container', 'process', or 'auto'."
        )
