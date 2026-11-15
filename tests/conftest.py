"""
Pytest configuration for localfm tests.
"""

import os

import pytest
from django.conf import settings

pytest_plugins = [
    "tests.blackbox.conftest",
]


@pytest.fixture(scope="session")
def django_db_modify_db_settings(*_args, **_kwargs):
    """Modify db settings just before the databases are configured."""
    # project defaults to using localfm specific user which doesn't have create db access.
    # The current local user does have this access, so switch to the local user for auth.
    try:
        user = os.getlogin()
    except Exception:
        user = os.getenv("USER") or "postgres"
    settings.DATABASES["default"]["USER"] = user
