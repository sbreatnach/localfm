import functools
import signal


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
