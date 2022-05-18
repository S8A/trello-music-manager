"""Main module of the program."""

import sys

import argparse
import dotenv

from trello_music_manager.subcommand import (
    album_status,
    artist_status,
    complete_tasks,
    delete_album,
    load_data,
    reset_tasks,
)
from trello_music_manager.manager import MusicBoardManager, MusicBoardManagerConfigError


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

    complete_tasks_parser = subparsers.add_parser(
        name="complete_tasks",
        description="Mark tasks of an artist's album as complete.",
    )
    complete_tasks_parser.add_argument("artist", help="exact name of the artist")
    complete_tasks_parser.add_argument("album", help="exact name of the album")
    complete_tasks_parser.add_argument(
        "tasks", nargs="*", metavar="task", help="tasks to mark as complete"
    )

    reset_tasks_parser = subparsers.add_parser(
        name="reset_tasks",
        description="Mark all tasks of an artist's album as incomplete.",
    )
    reset_tasks_parser.add_argument("artist", help="exact name of the artist")
    reset_tasks_parser.add_argument("album", help="exact name of the album")

    delete_album_parser = subparsers.add_parser(
        name="delete_album",
        description="Delete an artist's album.",
    )
    delete_album_parser.add_argument("artist", help="exact name of the artist")
    delete_album_parser.add_argument("album", help="exact name of the album")

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
    elif args.subcommand == "complete_tasks":
        report = complete_tasks(manager, args.artist, args.album, args.tasks)
        sys.exit(1 if report is None else 0)
    elif args.subcommand == "reset_tasks":
        success = reset_tasks(manager, args.artist, args.album)
        sys.exit(0 if success else 1)
    elif args.subcommand == "delete_album":
        success = delete_album(manager, args.artist, args.album)
        sys.exit(0 if success else 1)
