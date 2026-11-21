"""
Helpers for bootstrapping an isolated Django database for integration tests.
"""

from contextlib import contextmanager

from django.conf import settings
from django.core import management
from django.db import connections

from .cluster import PostgresClusterManager
from .database import CleanDatabase


@contextmanager
def migrated_database(cluster: PostgresClusterManager):
    """
    Create an isolated database on the shared PostgreSQL cluster, point Django at
    it, and apply all migrations. Restores the previous Django database settings
    and drops the database on exit.
    """
    db = CleanDatabase(cluster=cluster)
    db.create()

    previous = dict(settings.DATABASES["default"])
    settings.DATABASES["default"].update(
        {
            "HOST": db.host,
            "PORT": db.port,
            "NAME": db.name,
            "USER": db.user,
            "PASSWORD": db.password,
        }
    )
    connections.close_all()

    try:
        management.call_command("migrate", no_input=True, verbosity=0)
        yield db
    finally:
        connections.close_all()
        settings.DATABASES["default"].update(previous)
        db.drop()
