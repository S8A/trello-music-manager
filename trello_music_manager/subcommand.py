"""Subcommand functions."""


from typing import Any, Dict, List, Optional

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


def complete_tasks(
    manager: MusicBoardManager, artist: str, album: str, tasks: List[str]
) -> Optional[Dict[str, Any]]:
    """Mark the specified album's tasks as complete."""
    if not tasks:
        return complete_tasks(manager, artist, album, manager.album_tasks)

    for task in tasks:
        if task not in manager.album_tasks:
            print(f"Invalid task: {task}")
            return None

    album_card = manager.get_album_card(artist, album)
    if not album_card:
        print("Album card not found.")
        return None

    print(f"{artist} \u2013 {album} ::..")

    tasks_checklist = manager.get_album_card_tasks_checklist(album_card["id"])
    if not tasks_checklist:
        print("Tasks checklist not found.")
        return None

    tasks_checkitems = manager.get_checkitems(tasks_checklist["id"])
    if not tasks_checkitems:
        print("No tasks found.")
        return None

    tasks_completed = {task: False for task in manager.album_tasks}
    for task_checkitem in tasks_checkitems:
        task = task_checkitem["name"]
        complete = task_checkitem["state"] == "complete"
        if task in tasks and not complete:
            updated_checkitem = manager.update_checkitem(
                album_card["id"], task_checkitem["id"], state="complete"
            )
            if not updated_checkitem:
                print(f"Could not mark task as complete: {task}")
                return None
            tasks_completed[task] = True
        else:
            tasks_completed[task] = complete

    report = {
        "artist": artist,
        "album": album,
        "completed": False,
        "tasks": tasks_completed,
    }

    if all(tasks_completed.values()):
        if album_card["idList"] != manager.albums_done_list["id"]:
            moved_card = manager.move_card(
                album_card["id"], manager.albums_done_list["id"], pos="top"
            )
            if not moved_card:
                print(
                    f"Could not move album card to '{manager.albums_done_list_name}'."
                )
        if album_card["_checkitem_state"] != "complete":
            updated_checkitem = manager.update_checkitem(
                album_card["_artist_card_id"],
                album_card["_checkitem_id"],
                state="complete",
            )
            if not updated_checkitem:
                print("Could not mark album as complete in artist card.")

        report["completed"] = True

        print("\u2713 All tasks completed.")
    elif any(tasks_completed.values()):
        if album_card["idList"] != manager.albums_doing_list["id"]:
            moved_card = manager.move_card(
                album_card["id"], manager.albums_doing_list["id"], pos="top"
            )
            if not moved_card:
                print(
                    f"Could not move album card to '{manager.albums_doing_list_name}'."
                )
        if album_card["_checkitem_state"] != "incomplete":
            updated_checkitem = manager.update_checkitem(
                album_card["_artist_card_id"],
                album_card["_checkitem_id"],
                state="incomplete",
            )
            if not updated_checkitem:
                print("Could not mark album as incomplete in artist card.")

        report["completed"] = False
        for task, completed in tasks_completed.items():
            print("[", "\u2713" if completed else " ", "]", sep="", end=" ")
            print(task)

    print()

    return report


def reset_tasks(manager: MusicBoardManager, artist: str, album: str) -> bool:
    """Reset all the album's tasks' status to incomplete."""
    album_card = manager.get_album_card(artist, album)
    if not album_card:
        print("Album card not found.")
        return False

    print(f"{artist} \u2013 {album} ::..")

    tasks_checklist = manager.get_album_card_tasks_checklist(album_card["id"])
    if not tasks_checklist:
        print("Tasks checklist not found.")
        return False

    tasks_checkitems = manager.get_checkitems(tasks_checklist["id"])
    if not tasks_checkitems:
        print("No tasks found.")
        return False

    for task_checkitem in tasks_checkitems:
        task = task_checkitem["name"]
        complete = task_checkitem["state"] == "complete"
        if task in manager.album_tasks and complete:
            updated_checkitem = manager.update_checkitem(
                album_card["id"], task_checkitem["id"], state="incomplete"
            )
            if not updated_checkitem:
                print(f"Could not mark task as incomplete: {task}")
                return False

    if album_card["idList"] != manager.albums_pending_list["id"]:
        moved_card = manager.move_card(
            album_card["id"], manager.albums_pending_list["id"], pos="top"
        )
        if not moved_card:
            print(f"Could not move album card to '{manager.albums_pending_list_name}'.")
            return False
    if album_card["_checkitem_state"] != "incomplete":
        updated_checkitem = manager.update_checkitem(
            album_card["_artist_card_id"],
            album_card["_checkitem_id"],
            state="incomplete",
        )
        if not updated_checkitem:
            print("Could not mark album as incomplete in artist card.")
            return False

    print("\u2713 Successfully reset album tasks.")
    print()
    return True

def delete_album(manager: MusicBoardManager, artist: str, album: str) -> bool:
    """Delete the specified album."""
    album_card = manager.get_album_card(artist, album)
    if not album_card:
        print("Album card not found.")
        return False

    print(f"{artist} \u2013 {album} ::..")

    deleted_album_card = manager.delete_card(album_card["id"])
    if not deleted_album_card:
        print("Could not delete album card.")
        return False

    deleted_album_checkitem = manager.delete_checkitem(
        album_card["_artist_card_id"], album_card["_checkitem_id"]
    )
    if not deleted_album_checkitem:
        print("Could not delete album from artist card.")
        return False

    print("\u2713 Successfully deleted album.")
    print()

    return True
