import argparse
import logging
import threading
import time

from localfm.core.runtime import register_shutdown_token
from localfm.tracks.library import listen_for_changes
from localfm.wsgi import run_wsgi_server

logger = logging.getLogger("localfm.main")


def run_service():
    parser = argparse.ArgumentParser(description="Starts local FM service")
    parser.add_argument("--port", default=8011, type=int)
    parser.add_argument("--host", default="*")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    shutdown_token = register_shutdown_token()

    library_listen_thread = threading.Thread(
        target=listen_for_changes, args=(shutdown_token,)
    )
    library_listen_thread.start()
    listen_address = f"{args.host}:{args.port}"
    wsgi_thread = threading.Thread(
        target=run_wsgi_server,
        args=(
            shutdown_token,
            listen_address,
        ),
    )
    wsgi_thread.start()

    while wsgi_thread.is_alive() and library_listen_thread.is_alive():
        time.sleep(0.1)
    logger.info("Shutting down gracefully")
    shutdown_token.cancel()
    library_listen_thread.join(timeout=1)
    wsgi_thread.join(timeout=1)


if __name__ == "__main__":
    run_service()
