import logging
import os
import pprint
import sys
from datetime import UTC, datetime, timedelta

import pylast
from dateutil.parser import parse as date_parse
from django.core.management import BaseCommand
from django.db import transaction
from pylast import PlayedTrack

from localfm.tracks.models import Track, TrackPlay

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--log-level", default="INFO", help="Log level for the script"
        )
        parser.add_argument("--start-datetime", help="Start of the export date range")
        parser.add_argument("--end-datetime", help="End of the export date range")
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
        lastfm_api_key=None,
        lastfm_api_secret=None,
        lastfm_username=None,
        lastfm_password=None,
        start_datetime=None,
        end_datetime=None,
        log_level=logging.INFO,
        *args,
        **options,
    ):
        logging.basicConfig(level=log_level)

        cur_datetime = datetime.now(tz=UTC)
        start_datetime = (
            date_parse(start_datetime)
            if start_datetime
            else (cur_datetime - timedelta(hours=1))
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
        track_data: list[PlayedTrack] = user.get_recent_tracks(
            limit=None,
            time_from=int(start_datetime.timestamp()),
            time_to=int(end_datetime.timestamp()),
        )
        logger.info("Found %d tracks", len(track_data))
        logger.debug("Track data:\n%s", pprint.pformat(track_data))

        # persist the play count into local DB
        for played_track in track_data:
            track = played_track.track
            artist = track.get_artist()
            album_name = played_track.album
            if album_name is None:
                album = track.get_album()
                album_name = album.get_name() if album else None
            identifier_args = dict(
                track_name=track.get_title(),
                artist_name=artist.get_name() if artist else None,
                album_name=album_name,
            )
            timestamp = int(played_track.timestamp) if played_track.timestamp else None
            occurred_on = (
                datetime.fromtimestamp(timestamp).replace(tzinfo=UTC)
                if timestamp
                else None
            )
            logger.debug("Importing track with args %s played at %s", identifier_args, occurred_on)
            persisted_track = Track.get_by_identifier(**identifier_args)
            if persisted_track is None:
                logger.warning("Unable to find track: %s", played_track)
                continue
            with transaction.atomic():
                persisted_track.play_count += 1
                persisted_track.save()
                TrackPlay.objects.create(
                    track=persisted_track,
                    occurred_on=occurred_on,
                )
