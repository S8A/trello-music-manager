"""Main module of the program."""

import sys

import argparse
import dotenv

from trello_music_manager.subcommand import load_data, artist_status, album_status
from trello_music_manager.manager import MusicBoardManager, MusicBoardManagerConfigError
from trello_music_manager.utils import cd, read_file_lines_stripped


REQUIRED_CONFIG_VARS = [
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "TRELLO_BOARD_ID",
    "ARTISTS_LIST",
    "ALBUMS_PENDING_LIST",
    "ALBUMS_DOING_LIST",
    "ALBUMS_DONE_LIST",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="trello_music_manager",
        description="Manage Trello board of artists and albums.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="file which contains the required configuration variables"
    )

    subparsers = parser.add_subparsers(
        title="valid subcommands",
        help="subcommand help",
        dest="subcommand",
    )

    load_data_parser = subparsers.add_parser(
        name="load_data",
        description="Load artists and albums from the given directory.",
    )
    load_data_parser.add_argument(
        "directory", help="directory which contains artists' directories"
    )
    load_data_parser.add_argument(
        "--albums-filename",
        default="albums",
        help=(
            "name of text file within each artist directory which lists "
            "that artist's albums"
        )
    )

    status_parser = subparsers.add_parser(
        name="status",
        description="Check the completion status of an artist's album or albums.",
    )
    status_parser.add_argument("artist", help="exact name of the artist")
    status_parser.add_argument("album", nargs="?", help="exact name of the album")

    args = parser.parse_args()

    config = dotenv.dotenv_values(args.env_file)
    for required_variable in REQUIRED_CONFIG_VARS:
        if not config.get(required_variable, None):
            exit(1)

    try:
        manager = MusicBoardManager(
            config["TRELLO_API_KEY"],
            config["TRELLO_TOKEN"],
            config["TRELLO_BOARD_ID"],
            config["ARTISTS_LIST"],
            config["ALBUMS_PENDING_LIST"],
            config["ALBUMS_DOING_LIST"],
            config["ALBUMS_DONE_LIST"],
        )
    except MusicBoardManagerConfigError as e:
        print(e)

    if args.subcommand == "load_data":
        load_data(manager, args.directory, args.albums_filename)
        sys.exit(0)
    elif args.subcommand == "status":
        if args.album:
            report = album_status(manager, args.artist, args.album)
        else:
            report = artist_status(manager, args.artist)
        sys.exit(1 if report is None else 0)
