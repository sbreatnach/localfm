import argparse
import logging
import os
import pprint
import sys
import pylast
from datetime import datetime, UTC, timedelta
from dateutil.parser import parse as date_parse
from pylast import PlayedTrack

logger = logging.getLogger(__name__)


def main():
    cur_datetime = datetime.now(tz=UTC)
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--log-level", default="INFO", help="Start of the export date range"
    )
    arg_parser.add_argument("--start-datetime", help="Start of the export date range")
    arg_parser.add_argument("--end-datetime", help="End of the export date range")
    arg_parser.add_argument(
        "--lastfm-api-key",
        default=os.environ.get("LASTFM_API_KEY"),
        help="API key for Last.fm",
    )
    arg_parser.add_argument(
        "--lastfm-api-secret",
        default=os.environ.get("LASTFM_API_SECRET"),
        help="API secret for Last.fm",
    )
    arg_parser.add_argument(
        "--lastfm-username",
        default=os.environ.get("LASTFM_USERNAME"),
        help="Username for Last.fm",
    )
    arg_parser.add_argument(
        "--lastfm-password",
        default=os.environ.get("LASTFM_PASSWORD"),
        help="Password for Last.fm",
    )
    args = arg_parser.parse_args()
    logging.basicConfig(level=args.log_level)

    start_datetime = (
        date_parse(args.start_datetime)
        if args.start_datetime
        else (cur_datetime - timedelta(hours=1))
    )
    end_datetime = date_parse(args.end_datetime) if args.end_datetime else cur_datetime
    if end_datetime < start_datetime:
        logger.error("Invalid date range specified")
        sys.exit(1)
    if not all(
        {
            args.lastfm_api_key,
            args.lastfm_api_secret,
            args.lastfm_username,
            args.lastfm_password,
        }
    ):
        logger.error("Missing required authentication data")
        sys.exit(2)

    network = pylast.LastFMNetwork(
        api_key=args.lastfm_api_key,
        api_secret=args.lastfm_api_secret,
        username=args.lastfm_username,
        password_hash=pylast.md5(args.lastfm_password),
    )
    user = network.get_authenticated_user()
    track_data: list[PlayedTrack] = user.get_recent_tracks(
        limit=None,
        time_from=int(start_datetime.timestamp()),
        time_to=int(end_datetime.timestamp()),
    )
    # TODO: pass this data into a DB for use elsewhere
    pprint.pprint(track_data)


if __name__ == "__main__":
    main()
