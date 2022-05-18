"""Main module of the program."""

import sys
from typing import Any, Dict, Optional

import argparse
import dotenv
import os

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


def load_data(
    manager: MusicBoardManager, directory: str, albums_filename: str
) -> Dict[str, Any]:
    """Load artists and albums from the given directory and report results."""
    with cd(directory):
        artists = os.listdir()
        artists.sort()

        artists_albums = {}
        for artist in artists:
            with cd(artist):
                albums = read_file_lines_stripped(albums_filename)
                artists_albums[artist] = albums

        artists_cards = {card["name"]: card for card in manager.get_artists_cards()}

        new_artists_cards = {}
        new_artists_albums_checkitems = {}

        for artist, albums in artists_albums.items():
            if artist not in artists_cards:
                card = manager.create_artist_card(artist, albums)
                if card:
                    new_artists_cards[artist] = card
            else:
                artist_card = artists_cards[artist]
                new_albums_checkitems = manager.add_new_albums_artist_card(
                    artist_card["id"], artist_card["shortUrl"], albums
                )
                if new_albums_checkitems:
                    new_artists_albums_checkitems[artist] = new_albums_checkitems

        linked_albums_checkitems = {}
        for artist in artists:
            if artist in new_artists_cards:
                card = new_artists_cards[artist]
            elif artist in artists_cards:
                card = artists_cards[artist]
            else:
                continue

            new_linked_checkitems = manager.create_linked_album_cards(
                card["id"], card["shortUrl"]
            )
            if new_linked_checkitems:
                linked_albums_checkitems[artist] = new_linked_checkitems

    print("Load data: Summary ::..")
    print(f"Total artists in directory: {len(artists_albums)}")
    print(f"Total artists already in Trello: {len(artists_cards)}")

    print(f"New artist cards: {len(new_artists_cards)}")
    if new_artists_cards:
        for artist in new_artists_cards:
            print(f"\t{artist}")

    print(f"Artist cards updated with new albums: {len(new_artists_albums_checkitems)}")
    if new_artists_albums_checkitems:
        for artist, checkitems in new_artists_albums_checkitems.items():
            print(f"\t{artist}\t{len(checkitems)} new albums")

    print(f"Artist cards with new linked album cards: {len(linked_albums_checkitems)}")
    if linked_albums_checkitems:
        for artist, checkitems in linked_albums_checkitems.items():
            print(f"\t{artist}\t{len(checkitems)} new linked album cards")

    report = {
        "new_artists_cards": new_artists_cards,
        "new_artists_albums_checkitems": new_artists_albums_checkitems,
        "linked_albums_checkitems": linked_albums_checkitems,
    }

    return report


def artist_status(manager: MusicBoardManager, artist: str) -> Optional[Dict[str, Any]]:
    """Show the status of the artist's albums."""
    report = {
        "artist": artist,
        "albums": {},
    }

    artist_card = manager.get_artist_card(artist)
    if not artist_card:
        print("Artist not found.")
        return None
    
    print(f"{artist} ::..")

    albums_checklist = manager.get_artist_card_albums_checklist(artist_card["id"])
    if not albums_checklist:
        print("Albums checklist not found.")
        return None

    albums_checkitems = manager.get_checkitems(albums_checklist["id"])
    if not albums_checkitems:
        print("No albums found.")
        return None
    
    for checkitem in albums_checkitems:
        complete = checkitem["state"] == "complete"
        name = checkitem["name"]
        album = name
        tasks_status = {task: None for task in manager.album_tasks}

        if name.startswith("http"):
            album_card_id = name.split("/")[-1]
            album_card = manager.get_card(album_card_id)
            if not album_card:
                continue

            album = album_card["name"]

            tasks_checklist = manager.get_album_card_tasks_checklist(album_card_id)
            if not tasks_checklist:
                continue

            tasks_checkitems = manager.get_checkitems(tasks_checklist["id"])
            if tasks_checkitems:
                for task_checkitem in tasks_checkitems:
                    task = task_checkitem["name"]
                    if task in tasks_status:
                        tasks_status[task] = task_checkitem["state"] == "complete"

        report["albums"][album] = {
            "completed": complete,
            "tasks": tasks_status
        }

        print("[", "\u2713" if complete else " ", "]", sep="", end="  |  ")
        for task, task_complete in tasks_status.items():
            if task_complete is None:
                complete_mark = "?"
            else:
                complete_mark = "\u2713" if task_complete else "_"
            print(complete_mark, sep="", end=" ")
        print(end=" |  ")
        print(album)

    print()
    print(
        "Columns: Album completion status, album tasks' completion status, album title"
    )
    print("Tasks in order:", ", ".join(manager.album_tasks), sep=" ")
    print()

    return report


def album_status(
    manager: MusicBoardManager, artist: str, album: str
) -> Optional[Dict[str, Any]]:
    """Show the status of an artist's album."""
    report = {
        "artist": artist,
        "album": album,
        "completed": None,
        "tasks": {},
    }

    artist_card = manager.get_artist_card(artist)
    if not artist_card:
        print("Artist not found.")
        return None

    albums_checklist = manager.get_artist_card_albums_checklist(artist_card["id"])
    if not albums_checklist:
        print("Albums checklist not found.")
        return None

    albums_checkitems = manager.get_checkitems(albums_checklist["id"])
    if not albums_checkitems:
        print("No albums found.")
        return None
    
    album_card = None
    album_state = "?"
    for checkitem in albums_checkitems:
        name = checkitem["name"]

        if not name.startswith("http"):
            print("Album card not linked.")
            return None

        album_card_id = name.split("/")[-1]
        card = manager.get_card(album_card_id)
        if not card:
            continue

        if card["name"] == album:
            album_card = card
            album_state = checkitem["state"]
            break
    
    if not album_card:
        print("Album not found.")
        return None

    report["completed"] = album_state == "complete"

    print(f"{artist} \u2013 {album} ::..")
    print()
    print(f"State: {album_state}")
    print()

    tasks_checklist = manager.get_album_card_tasks_checklist(album_card["id"])
    if not tasks_checklist:
        print("Tasks checklist not found.")
        return None

    print("Tasks:")
    tasks_checkitems = manager.get_checkitems(tasks_checklist["id"])
    if not tasks_checkitems:
        print("No tasks found.")
        return None
        
    for task_checkitem in tasks_checkitems:
        task = task_checkitem["name"]
        complete = task_checkitem["state"] == "complete"
        if task in manager.album_tasks:
            report["tasks"][task] = complete
            print("[", "\u2713" if complete else " ", "]", sep="", end=" ")
            print(task)
    print()

    return report


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
