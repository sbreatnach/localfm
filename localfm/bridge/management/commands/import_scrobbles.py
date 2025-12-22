import json
import logging
import os
import pprint
import random
import sys
import time
from collections import namedtuple
from datetime import UTC, datetime, timedelta

import pylast
from dateutil.parser import parse as date_parse
from django.core.management import BaseCommand
from django.db import transaction
from pylast import PlayedTrack, User

from localfm.tracks.models import Track, TrackPlay

logger = logging.getLogger(__name__)


Scrobble = namedtuple("Scrobble", "artist_name, album_name, track_name, occurred_on")


class ScrobbleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def save_scrobble(scrobble: Scrobble) -> bool:
    logger.debug("Importing track with scrobble %s", scrobble)
    persisted_track = Track.get_by_identifier(
        scrobble.track_name,
        artist_name=scrobble.artist_name,
        album_name=scrobble.album_name,
    )
    if persisted_track is None:
        logger.warning("Unable to find track: %s", scrobble)
        return False
    with transaction.atomic():
        _, created = TrackPlay.objects.get_or_create(
            track=persisted_track,
            occurred_on=scrobble.occurred_on,
        )
        if created:
            persisted_track.play_count += 1
            persisted_track.save()
    return True


def load_lastfm_scrobbles(user: User, start_datetime, end_datetime) -> list[Scrobble]:
    logger.info("Importing scrobbles for range %s to %s", start_datetime, end_datetime)
    track_data: list[PlayedTrack] = user.get_recent_tracks(
        limit=None,
        time_from=int(start_datetime.timestamp()),
        time_to=int(end_datetime.timestamp()),
    )
    logger.info("Found %d tracks", len(track_data))
    logger.debug("Track data:\n%s", pprint.pformat(track_data))

    # convert the tracks to scrobbles
    scrobbles = []
    for played_track in track_data:
        track = played_track.track
        artist = track.get_artist()
        album_name = played_track.album
        if album_name is None:
            album = track.get_album()
            album_name = album.get_name() if album else None
        if album_name == "Untitled Album":
            album_name = ""
        timestamp = int(played_track.timestamp) if played_track.timestamp else None
        occurred_on = (
            datetime.fromtimestamp(timestamp).replace(tzinfo=UTC) if timestamp else None
        )
        scrobbles.append(
            Scrobble(
                artist_name=artist.get_name() if artist else None,
                album_name=album_name,
                track_name=track.get_title(),
                occurred_on=occurred_on,
            )
        )
    return scrobbles


def load_from_file(scrobbles_file, **kwargs) -> list[Scrobble]:
    scrobbles = []
    with open(scrobbles_file, "r", encoding="utf-8") as handle:
        raw_scrobbles = json.load(handle)
        for raw_scrobble in raw_scrobbles:
            raw_scrobble[3] = datetime.fromisoformat(raw_scrobble[3])
            scrobbles.append(Scrobble(*raw_scrobble))
    return scrobbles


def load_from_lastfm(
    lastfm_api_key=None,
    lastfm_api_secret=None,
    lastfm_username=None,
    lastfm_password=None,
    start_datetime=None,
    end_datetime=None,
    hour_delta=24,
    chunk_jitter=60,
    **kwargs,
) -> list[Scrobble]:
    cur_datetime = datetime.now(tz=UTC)
    start_datetime = (
        date_parse(start_datetime)
        if start_datetime
        else (cur_datetime - timedelta(hours=24))
    )
    end_datetime = date_parse(end_datetime) if end_datetime else cur_datetime
    if end_datetime < start_datetime:
        logger.error("Invalid date range specified")
        sys.exit(1)
    if not all(
        {
            lastfm_api_key,
            lastfm_api_secret,
            lastfm_username,
            lastfm_password,
        }
    ):
        logger.error("Missing required access data")
        sys.exit(2)

    network = pylast.LastFMNetwork(
        api_key=lastfm_api_key,
        api_secret=lastfm_api_secret,
        username=lastfm_username,
        password_hash=pylast.md5(lastfm_password),
    )
    user = network.get_authenticated_user()

    # chunk the date range so we don't attempt to import too large a track listing;
    # we're not going to support parallel requests because that could fall
    # foul of rate limiting
    chunk_delta = timedelta(hours=hour_delta)
    scrobbles = []
    next_start_datetime = start_datetime
    while next_start_datetime < end_datetime:
        next_end_datetime = next_start_datetime + chunk_delta
        if next_end_datetime >= end_datetime:
            next_end_datetime = end_datetime

        scrobbles.extend(
            load_lastfm_scrobbles(user, next_start_datetime, next_end_datetime)
        )

        next_start_datetime = next_end_datetime
        if chunk_jitter > 0 and next_start_datetime < end_datetime:
            wait_period = random.randint(
                chunk_jitter // 5, chunk_jitter + chunk_jitter // 5
            )
            logger.info("Waiting %s seconds before next request", wait_period)
            time.sleep(wait_period)

    return scrobbles


def save_scrobbles_to_file(file_path, scrobbles):
    output_file = file_path.format(dated=datetime.now().strftime("%Y%m%dT%H%M%S"))
    with open(output_file, "w", encoding="utf-8") as handle:
        json.dump(
            scrobbles, handle, cls=ScrobbleEncoder, ensure_ascii=False, indent="\t"
        )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            help="source of the scrobbles to import",
        )
        parser.add_argument(
            "target",
            default="database",
            help="target where the scrobbles will be saved",
        )
        parser.add_argument(
            "--log-level", default="INFO", help="Log level for the script"
        )
        parser.add_argument("--start-datetime", help="Start of the export date range")
        parser.add_argument("--end-datetime", help="End of the export date range")
        parser.add_argument(
            "--hour-delta",
            help="Number of hours between each chunk imported",
            default=24,
            type=int,
        )
        parser.add_argument(
            "--chunk-jitter",
            help="Number of approximate seconds between each chunk import",
            default=60,
            type=int,
        )
        parser.add_argument(
            "--lastfm-api-key",
            default=os.environ.get("LASTFM_API_KEY"),
            help="API key for Last.fm",
        )
        parser.add_argument(
            "--lastfm-api-secret",
            default=os.environ.get("LASTFM_API_SECRET"),
            help="API secret for Last.fm",
        )
        parser.add_argument(
            "--lastfm-username",
            default=os.environ.get("LASTFM_USERNAME"),
            help="Username for Last.fm",
        )
        parser.add_argument(
            "--lastfm-password",
            default=os.environ.get("LASTFM_PASSWORD"),
            help="Password for Last.fm",
        )

    def handle(
        self,
        source,
        target="database",
        log_level=logging.INFO,
        failed_scrobbles_file="failed_scrobbles_{dated}.json",
        *args,
        **import_kwargs,
    ):
        logging.basicConfig(level=log_level)
        if source == "lastfm":
            scrobbles = load_from_lastfm(**import_kwargs)
        else:
            scrobbles = load_from_file(source, **import_kwargs)

        if target == "database":
            failed_scrobbles = []
            for scrobble in scrobbles:
                if not save_scrobble(scrobble):
                    failed_scrobbles.append(scrobble)
            if failed_scrobbles:
                save_scrobbles_to_file(failed_scrobbles_file, failed_scrobbles)
        else:
            save_scrobbles_to_file(target, scrobbles)
