import logging

from django.conf import settings
from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

from localfm.core.runtime import CancellationToken

logger = logging.getLogger(__name__)


def listen_for_changes(shutdown_token: CancellationToken):
    logger.info("Listening for library changes at %s", settings.MUSIC_LIBRARY_DIRECTORY)
    event_handler = LoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, settings.MUSIC_LIBRARY_DIRECTORY, recursive=True)
    observer.start()
    try:
        while observer.is_alive() and not shutdown_token.is_canceled():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
