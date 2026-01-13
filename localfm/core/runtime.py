import functools
import logging
import signal

from waitress.server import create_server

logger = logging.getLogger(__name__)


class CancellationToken:
    def __init__(self):
        self._is_canceled = False

    def is_canceled(self):
        return self._is_canceled

    def cancel(self):
        self._is_canceled = True


def signal_handler(cancellation_token: CancellationToken, sig, frame):
    cancellation_token.cancel()


def register_shutdown_token():
    shutdown_token = CancellationToken()
    signal.signal(signal.SIGINT, functools.partial(signal_handler, shutdown_token))
    signal.signal(signal.SIGTERM, functools.partial(signal_handler, shutdown_token))
    return shutdown_token


def run_wsgi_server(shutdown_token: CancellationToken, application, listen_address):
    logger.info("Starting WSGI service at %s", listen_address)
    server = create_server(application, listen=listen_address)
    try:
        while server.map and not shutdown_token.is_canceled():
            server.asyncore.poll(1.0, map=server.map)
    finally:
        server.close()
