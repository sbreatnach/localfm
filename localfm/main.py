import argparse
import logging

import waitress

from .wsgi import application

logger = logging.getLogger("localfm.main")


def run_service():
    parser = argparse.ArgumentParser(description="Starts local FM service")
    parser.add_argument("--port", default=8011, type=int)
    parser.add_argument("--host", default="*")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)

    listen_address = f"{args.host}:{args.port}"
    logger.info("Starting local FM service at %s", listen_address)
    waitress.serve(application, listen=listen_address)


if __name__ == "__main__":
    run_service()
