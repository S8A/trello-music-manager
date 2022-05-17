"""Main module of the program."""

from typing import Any, Dict

import argparse
import dotenv
import os

from trello_music_manager.manager import MusicBoardManager
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


def load_data(
    manager: MusicBoardManager, directory: str, albums_filename: str
) -> Dict[str, Any]:
    """Load artists and albums from the given directory and report results."""
    # Load data and create report
    report = {}
    with cd(directory):
        artists = os.listdir()
        artists.sort()

        artists_albums = {artist: [] for artist in artists}

        for artist in artists_albums:
            with cd(artist):
                albums = read_file_lines_stripped(albums_filename)
                artists_albums[artist] = albums
        report["artists_albums"] = artists_albums

        artists_cards = manager.get_artists_cards()
        artists_cards_names = [card["name"] for card in artists_cards]
        report["artists_cards"] = artists_cards

        report["updated_artists_albums"] = {}
        for artist in artists_cards_names:
            albums = artists_albums.get(artist, [])
            new_albums = manager.update_artist_albums(artist, albums)
            if new_albums:
                report["updated_artists_albums"][artist] = new_albums

        report["new_artists_albums"] = {}
        for artist, albums in artists_albums.items():
            if artist not in artists_cards_names:
                card_id = manager.create_artist_card(artist, albums)
                if card_id:
                    report["new_artists_albums"][artist] = albums

        report["new_linked_cards"] = {}
        for artist in artists_cards_names:
            new_links = manager.create_missing_album_cards(artist)
            if new_links:
                report["new_linked_cards"][artist] = new_links

    # Print report summary
    print(f"Total artists in directory: {len(report['artists_albums'])}")
    print(f"Total artists in Trello list: {len(report['artists_cards'])}")

    updated_artists = report["updated_artists_albums"]
    print(f"Artist cards updated with new albums: {len(updated_artists)}")
    if updated_artists:
        for artist, new_albums in updated_artists.items():
            print(f"\t{artist}\t{len(new_albums)} new albums")

    new_artists = report["new_artists_albums"]
    print(f"New artist cards: {len(new_artists)}")
    if new_artists:
        for artist, albums in new_artists.items():
            print(f"\t{artist}\t({len(albums)} albums)")

    new_linked_artists = report["new_linked_cards"]
    print(f"Artist cards with new linked album cards: {len(new_linked_artists)}")
    if new_linked_artists:
        for artist, new_links in new_linked_artists.items():
            print(f"\t{artist}\t{len(new_links)} new linked album cards")

    # Return report data
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "music.py", description="Manage Trello board of artists and albums."
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

    manager = MusicBoardManager(
        config["TRELLO_API_KEY"],
        config["TRELLO_TOKEN"],
        config["TRELLO_BOARD_ID"],
        config["ARTISTS_LIST"],
        config["ALBUMS_PENDING_LIST"],
        config["ALBUMS_DOING_LIST"],
        config["ALBUMS_DONE_LIST"],
    )

    load_data(manager, args.directory, config["ALBUMS_FILENAME"])
