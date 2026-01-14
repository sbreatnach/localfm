import logging

from django.conf import settings
from watchdog.events import DirModifiedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from localfm.core.runtime import CancellationToken

logger = logging.getLogger(__name__)


class LibraryEventHandler(FileSystemEventHandler):
    """
    Update localfm state as appropriate when library data changes.
    """

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        super().on_modified(event)

        # TODO: update the library to account for any music file changes
        # ignore any files other than mp3 or aac
        # if the music file is new or has changed, attempt to import it
        # should it be done sync or async? Unclear what the process model
        # for watchdog library is and how it varies by platform.
        what = "directory" if event.is_directory else "file"
        logger.info("Modified %s: %s", what, event.src_path)


def listen_for_changes(shutdown_token: CancellationToken):
    logger.info("Listening for library changes at %s", settings.MUSIC_LIBRARY_DIRECTORY)
    event_handler = LibraryEventHandler()
    observer = Observer()
    observer.schedule(event_handler, settings.MUSIC_LIBRARY_DIRECTORY, recursive=True)
    observer.start()
    try:
        while observer.is_alive() and not shutdown_token.is_canceled():
            observer.join(0.1)
    finally:
        observer.stop()
        observer.join()
