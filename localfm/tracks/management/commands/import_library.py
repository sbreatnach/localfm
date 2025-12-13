"""
Imports the entire music library into the tracks DB
"""
import time
from concurrent.futures import ThreadPoolExecutor
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
            "--log-level", default="INFO", help="Log level for the script"
        )
        parser.add_argument(
            "--parallel-workers", type=int, default=5, help="Number of parallel processes for importing"
        )
        parser.add_argument(
            "--name-filter", help="Filter to specific directories by name"
        )

    def handle(
        self,
        library_directory,
        log_level=logging.INFO,
        parallel_workers=5,
        name_filter=None,
        *args,
        **options,
    ):
        logging.basicConfig(level=log_level)

        root_dir = Path(library_directory)
        base_directories = [
            directory for directory in root_dir.iterdir() if directory.is_dir() and is_filtered(directory.name, name_filter=name_filter)
        ]
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            _results = [result for result in executor.map(import_from_directory, base_directories)]
        logger.info(f"Imported tracks in %s seconds", time.time() - start_time)


def is_filtered(name, name_filter=None):
    if name_filter:
        return name_filter in name
    return name


def import_from_directory(base_directory):
    logger.debug("Importing from directory: %s", base_directory)
    for current_root, dirs, files in base_directory.walk():
        for name in files:
            file_path = current_root / name
            file_extension = os.path.splitext(name)[1]
            if file_extension in TinyTag.SUPPORTED_FILE_EXTENSIONS:
                tagged_data = TinyTag.get(file_path)
                try:
                    Track.get_or_create_by_tagged_data(file_path, tagged_data)
                except Exception as exc:
                    logger.error("Failed to import file %s: %s", file_path, str(exc))
