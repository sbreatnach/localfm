import logging
import os

from django.conf import settings
from tinytag import TinyTag
from watchdog.events import DirModifiedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from localfm.core.runtime import CancellationToken
from localfm.tracks.models import Track

logger = logging.getLogger(__name__)


def import_file(file_path: str):
    file_extension = os.path.splitext(file_path)[1]
    if file_extension in TinyTag.SUPPORTED_FILE_EXTENSIONS:
        tagged_data = TinyTag.get(file_path)
        try:
            Track.get_or_create_by_tagged_data(file_path, tagged_data)
        except Exception as exc:
            logger.error("Failed to import file %s: %s", file_path, str(exc))


class LibraryEventHandler(FileSystemEventHandler):
    """
    Update localfm state as appropriate when library data changes.
    """

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        super().on_modified(event)
        # update the library to account for any music file changes
        # ignore any files other than mp3 or aac
        if not event.is_directory:
            import_file(event.src_path)


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
