"""
WSGI config for localfm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import logging
import os

from waitress import create_server

from localfm.core.runtime import CancellationToken

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "localfm.settings")

logger = logging.getLogger(__name__)


def run_wsgi_server(application, shutdown_token: CancellationToken, listen_address):
    logger.info("Starting WSGI service at %s", listen_address)
    server = create_server(application, listen=listen_address)
    try:
        while server.map and not shutdown_token.is_canceled():
            server.asyncore.poll(1.0, map=server.map)
    finally:
        server.close()
