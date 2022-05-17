"""Module for the Trello music board manager itself."""
from typing import Any, Dict, List, Optional

import json
import requests


class MusicBoardManagerConfigError(Exception):
    """Raised when the Trello music board manager is improperly configured."""

    def __init__(self, message):
        """Create a MusicBoardManagerConfigError with the given message."""
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.__class__}: {self.message}"


class MusicBoardManager:
    """Object that manages the music board using the Trello API."""

    def __init__(
        self,
        api_key: str,
        token: str,
        board_id: str,
        artists_list_name: str,
        albums_pending_list_name: str,
        albums_doing_list_name: str,
        albums_done_list_name: str
    ):
        self.api_key = api_key
        self.token = token
        self.board_id = board_id
        self.artists_list_name = artists_list_name
        self.albums_pending_list_name = albums_pending_list_name
        self.albums_doing_list_name = albums_doing_list_name
        self.albums_done_list_name = albums_done_list_name

        self.headers = {
           "Accept": "application/json",
        }

        self.lists = self.get_board_lists()

    @property
    def artists_list(self) -> Optional[Dict[str, Any]]:
        """Get Trello list which holds artists' cards."""
        return self.lists.get("artists", None)

    @property
    def albums_pending_list(self) -> Optional[Dict[str, Any]]:
        """Get Trello list which holds albums that are pending."""
        return self.lists.get("albums_pending", None)

    @property
    def albums_doing_list(self) -> Optional[Dict[str, Any]]:
        """Get Trello list which holds albums that are in progress."""
        return self.lists.get("albums_doing", None)

    @property
    def albums_done_list(self) -> Optional[Dict[str, Any]]:
        """Get Trello list which holds albums that are done."""
        return self.lists.get("albums_done", None)

    def get_board_lists(self) -> Dict[str, Dict[str, Any]]:
        """Get lists of the Trello music board."""
        url = "https://api.trello.com/1/boards/{id}/lists"
        response = self.make_request(url.format(id=self.board_id), "GET")
        status = response.status_code
        if status != 200:
            raise MusicBoardManagerConfigError(
                f"Request of music board's lists failed with status code {status}."
            )

        lists = {
            "artists": None,
            "albums_pending": None,
            "albums_doing": None,
            "albums_done": None,
        }

        for trello_list in json.loads(response.text):
            if trello_list["name"] == self.artists_list_name:
                lists["artists"] = trello_list

            if trello_list["name"] == self.albums_pending_list_name:
                lists["albums_pending"] = trello_list

            if trello_list["name"] == self.albums_doing_list_name:
                lists["albums_doing"] = trello_list

            if trello_list["name"] == self.albums_done_list_name:
                lists["albums_done"] = trello_list

        for k, v in lists.items():
            if not v:
                raise MusicBoardManagerConfigError(f"Could not find {k} board.")

        return lists

    def get_artists_cards(self) -> List[Dict[str, Any]]:
        """Get a list of all cards in the artists' list."""
        url = "https://api.trello.com/1/lists/{id}/cards"
        artists_list_id = self.artists_list["id"]
        response = self.make_request(url.format(id=artists_list_id), "GET")
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return []

    def get_artist_card(self, artist: str) -> Optional[Dict[str, Any]]:
        """Get the card of the given artist, if any"""
        artists_cards = self.get_artists_cards()
        artist_card = None
        for card in artists_cards:
            if "name" in card and card["name"] == artist:
                artist_card = card
        return artist_card

    def get_artist_card_albums_checklist(
        self, artist_card_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the artist's albums checklist."""
        checklists_url = "https://api.trello.com/1/cards/{id}/checklists"
        response = self.make_request(checklists_url.format(id=artist_card_id), "GET")

        if response.status_code == 200:
            checklists = json.loads(response.text)
            for checklist in checklists:
                if "name" in checklist and checklist["name"] == "Albums":
                    return checklist

    def get_artist_card_albums_checkitems(
        self, albums_checklist_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get the items of the given artist's card's albums checklist."""
        checkitems_url = "https://api.trello.com/1/checklists/{id}/checkItems"
        response = self.make_request(
            checkitems_url.format(id=albums_checklist_id), "GET"
        )

        if response.status_code == 200:
            return json.loads(response.text)

    def create_artist_card(
        self, artist: str, albums: List[str], pos: str = "bottom"
    ) -> Optional[Dict[str, Any]]:
        """Create a new card for the given artist with a checklist for their albums."""
        card = self.create_card(self.artists_list["id"], artist, pos=pos)

        if not card:
            return None

        checklist = self.create_checklist(card["id"], "Albums")

        if not checklist:
            self.delete_card(card["id"])
            return None

        if albums:
            albums_checklist_items = []
            for album in albums:
                album_card = self.create_album_card(album, card["shortUrl"])
                if album_card and "shortUrl" in album_card:
                    albums_checklist_items.append(album_card["shortUrl"])
                else:
                    albums_checklist_items.append(album)

            self.add_items_to_checklist(checklist["id"], albums_checklist_items)

        return card

    def add_new_albums_artist_card(
        self, artist_card_id: str, artist_card_short_url: str, albums: List[str]
    ) -> Optional[List[str]]:
        """Add the given albums that aren't already on the artist's albums checklist."""
        if not albums:
            return None

        albums_checklist = self.get_artist_card_albums_checklist(artist_card_id)

        if albums_checklist:
            albums_checkitems = self.get_artist_card_albums_checkitems(
                albums_checklist["id"]
            )

            current_albums = []
            for checkitem in albums_checkitems:
                name = checkitem["name"]
                if name.startswith("http"):
                    card_id = name.split("/")[-1]
                    card = self.get_card(card_id)
                    if card:
                        current_albums.append(card["name"])
                else:
                    current_albums.append(name)

            new_albums = [album for album in albums if album not in current_albums]

            new_albums_items = []
            for album in new_albums:
                album_card = self.create_album_card(album, artist_card_short_url)
                if album_card:
                    new_albums_items.append(album_card["shortUrl"])
                else:
                    new_albums_items.append(album)

            return self.add_items_to_checklist(albums_checklist["id"], new_albums_items)

    def create_album_card(
        self, album: str, artist_card_short_url: str, pos: str = "bottom"
    ) -> Optional[Dict[str, Any]]:
        """Create a card for the given album in the pending list."""
        album_card = self.create_card(self.albums_pending_list["id"], album, pos=pos)

        if not album_card:
            return None

        checklist = self.create_checklist(album_card["id"], "Tasks")

        if not checklist:
            self.delete_card(album_card["id"])
            return None

        tasks = [
            "Download",
            "Add metadata",
            "Transfer to phone",
            "Listen",
        ]
        added_items = self.add_items_to_checklist(checklist["id"], tasks)

        if len(added_items) != len(tasks):
            self.delete_card(album_card["id"])
            return None

        attachments_url = "https://api.trello.com/1/cards/{id}/attachments"
        attachments_query = {
            "url": artist_card_short_url,
        }
        attachments_response = self.make_request(
            attachments_url.format(id=album_card["id"]),
            "POST",
            query_params=attachments_query,
        )

        if attachments_response.status_code != 200:
            self.delete_card(album_card["id"])
            return None

        return album_card

    def create_linked_album_cards(
        self, artist_card_id: str, artist_card_short_url: str
    ) -> List[Dict[str, Any]]:
        """Create linked cards for the artists' albums that are not linked already."""
        albums_checklist = self.get_artist_card_albums_checklist(artist_card_id)

        if albums_checklist:
            albums_checkitems = self.get_artist_card_albums_checkitems(
                albums_checklist["id"]
            )

            updated_checkitems = []
            for checkitem in albums_checkitems:
                album_name = checkitem["name"]
                if not album_name.startswith("http"):
                    album_card = self.create_album_card(
                        album_name, artist_card_short_url
                    )
                    if album_card and "shortUrl" in album_card:
                        updated_checkitem = self.update_checkitem(
                            artist_card_id,
                            checkitem["id"],
                            name=album_card["shortUrl"],
                            state="incomplete",
                        )

                        if updated_checkitem:
                            updated_checkitems.append(updated_checkitem)

            return updated_checkitems

    def create_card(
        self, list_id: str, name: str, pos: str = "bottom"
    ) -> Optional[Dict[str, Any]]:
        """Create a card on the specified list."""
        url = "https://api.trello.com/1/cards"
        query = {
            "idList": list_id,
            "name": name,
            "pos": pos,
        }
        response = self.make_request(url, "POST", query_params=query)
        if response.status_code == 200:
            return json.loads(response.text)

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get the card by its ID."""
        url = "https://api.trello.com/1/cards/{id}"
        response = self.make_request(url.format(id=card_id), "GET")
        if response.status_code == 200:
            return json.loads(response.text)

    def delete_card(self, card_id: str) -> bool:
        """Delete the card with the given ID."""
        url = "https://api.trello.com/1/cards/{id}"
        response = self.make_request(url.format(id=card_id), "DELETE")
        return response.status_code == 200

    def create_checklist(
        self, card_id: str, name: str, pos: str = "bottom"
    ) -> Optional[Dict[str, Any]]:
        """Create a checklist on the specified card."""
        url = "https://api.trello.com/1/checklists"
        query = {
            "idCard": card_id,
            "name": name,
            "pos": pos,
        }
        response = self.make_request(url, "POST", query_params=query)
        if response.status_code == 200:
            return json.loads(response.text)

    def add_items_to_checklist(
        self, checklist_id: str, items: List[str], pos: str = "bottom"
    ) -> List[Dict[str, Any]]:
        """Add the given items to the specified checklist"""
        added_checkitems = []
        url = "https://api.trello.com/1/checklists/{id}/checkItems"
        for item in items:
            query = {
                "name": item,
                "pos": pos
            }
            response = self.make_request(
                url.format(id=checklist_id), "POST", query_params=query
            )

            if response.status_code == 200:
                added_checkitems.append(json.loads(response.text))
        return added_checkitems

    def update_checkitem(
        self,
        card_id: str,
        checkitem_id: str,
        name: Optional[str] = None,
        state: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a checkitem's name and/or state."""
        if not name and not state:
            return None

        url = "https://api.trello.com/1/cards/{id}/checkItem/{idCheckItem}"

        query = {}
        if name:
            query["name"] = name
        if state:
            query["state"] = state

        response = self.make_request(
            url.format(id=card_id, idCheckItem=checkitem_id), "PUT", query_params=query,
        )

        if response.status_code == 200:
            return json.loads(response.text)

    def make_request(
        self, url: str, method: str, query_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Make a JSON API request with the given parameters."""
        params = {
            "key": self.api_key,
            "token": self.token,
        }
        if query_params:
            for k, v in query_params.items():
                params[k] = v

        return requests.request(method, url, headers=self.headers, params=params)
