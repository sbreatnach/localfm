"""
Blackbox testing harness for LocalFM service.
"""


def __getattr__(name: str):
    if name == "PostgresClusterManager":
        from .cluster import PostgresClusterManager

        return PostgresClusterManager
    if name == "CleanDatabase":
        from .database import CleanDatabase

        return CleanDatabase
    if name == "BlackboxClient":
        from .client import BlackboxClient

        return BlackboxClient
    if name in (
        "TestService",
        "ContainerTestService",
        "ProcessTestService",
        "create_test_service",
    ):
        from . import service

        return getattr(service, name)
    if name == "BlackboxTestHarness":
        from .harness import BlackboxTestHarness

        return BlackboxTestHarness
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PostgresClusterManager",
    "CleanDatabase",
    "BlackboxClient",
    "TestService",
    "ContainerTestService",
    "ProcessTestService",
    "create_test_service",
    "BlackboxTestHarness",
]
