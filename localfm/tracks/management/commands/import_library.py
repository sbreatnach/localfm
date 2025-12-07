"""
Imports the entire music library into the tracks DB
"""

# TODO: write the script!
# given a library directory, scan through all MP3s and AACs for track metadata
# then add them all to the DB.
# use tinytag for retrieving metadata
# use a standard recursive search
# parallelise it? Search the root directory, then break the directory listing into chunks
import logging
import os
from pathlib import Path

from django.core.management import BaseCommand
from tinytag import TinyTag

from localfm.tracks.models import Track

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "library_directory", help="Directory defining the music library to import"
        )
        parser.add_argument(
            "--log-level", default="INFO", help="Start of the export date range"
        )

    def handle(
        self,
        library_directory,
        log_level=logging.INFO,
        *args,
        **options,
    ):
        logging.basicConfig(level=log_level)

        root_dir = Path(library_directory)
        base_directories = [
            directory for directory in root_dir.iterdir() if directory.is_dir()
        ]
        for base_directory in base_directories:
            import_from_directory(base_directory)


def import_from_directory(base_directory):
    for current_root, dirs, files in base_directory.walk():
        for name in files:
            file_path = current_root / name
            file_extension = os.path.splitext(name)[1]
            if file_extension in TinyTag.SUPPORTED_FILE_EXTENSIONS:
                tagged_data = TinyTag.get(file_path)
                try:
                    Track.get_or_create_by_tagged_data(tagged_data)
                except Exception as exc:
                    logger.error("Failed to import file %s: %s", file_path, str(exc))
