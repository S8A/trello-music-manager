"""Subcommand functions."""


from typing import Any, Dict, Optional

import os

from trello_music_manager.manager import MusicBoardManager
from trello_music_manager.utils import cd, read_file_lines_stripped


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

    print(f"{artist} ::..")

    album_cards = manager.get_album_cards(artist)

    if not album_cards:
        print("No albums found for the given artist.")
        return None

    for album_card in album_cards:
        album = album_card["name"]
        complete = album_card["_checkitem_state"] == "complete"
        tasks_status = {task: None for task in manager.album_tasks}

        tasks_checklist = manager.get_album_card_tasks_checklist(album_card["id"])
        if not tasks_checklist:
            continue

        tasks_checkitems = manager.get_checkitems(tasks_checklist["id"])
        if not tasks_checkitems:
            continue
            
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
    album_card = manager.get_album_card(artist, album)

    if not album_card:
        print("Album card not found.")
        return None

    album_state = album_card["_checkitem_state"]

    report = {
        "artist": artist,
        "album": album,
        "completed": album_state == "complete",
        "tasks": {},
    }

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
