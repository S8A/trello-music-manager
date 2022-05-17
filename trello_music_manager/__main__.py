"""Main module of the program."""

from typing import Any, Dict

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
    "ALBUMS_FILENAME",
]


def load_data(manager: MusicBoardManager, directory: str, albums_filename: str) -> None:
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="trello_music_manager",
        description="Manage Trello board of artists and albums.",
    )
    parser.add_argument(
        "directory", help="Directory with artists' directories."
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="File which contains the required configuration variables."
    )
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

    load_data(manager, args.directory, config["ALBUMS_FILENAME"])
