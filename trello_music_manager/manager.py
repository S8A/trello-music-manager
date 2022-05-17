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

    def get_artists_cards(self) -> List[Dict[str, Any]]:
        """Get a list of all cards in the artists' list."""
        url = "https://api.trello.com/1/lists/{id}/cards"
        artists_list_id = self.artists_list.get("id", "")
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

    def get_artist_albums_checklist(self, artist: str) -> Optional[Dict[str, Any]]:
        """Get the artist's albums checklist."""
        artist_card = self.get_artist_card(artist)

        if artist_card:
            checklists = []
            checklists_url = "https://api.trello.com/1/cards/{id}/checklists"
            response = self.make_request(
                checklists_url.format(id=artist_card["id"]), "GET"
            )

            if response.status_code == 200:
                checklists = json.loads(response.text)

            for checklist in checklists:
                if "name" in checklist and checklist["name"] == "Albums":
                    return checklist

    def get_artist_albums_checkitems(
        self, artist: str, albums_checklist_id: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get the items of the given artist's card's albums checklist."""
        if not albums_checklist_id:
            albums_checklist = self.get_artist_albums_checklist(artist)
            return self.get_artist_albums_checkitems(artist, albums_checklist["id"])

        checkitems_url = "https://api.trello.com/1/checklists/{id}/checkItems"
        response = self.make_request(
            checkitems_url.format(id=albums_checklist_id), "GET"
        )

        if response.status_code == 200:
            return json.loads(response.text)

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
    ) -> List[str]:
        """Add the given items to the specified checklist"""
        added_items_responses = []
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
                added_items_responses.append(response.text)
        return added_items_responses

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

    def create_artist_card(
        self, artist: str, albums: List[str], pos: str = "bottom"
    ) -> Optional[str]:
        """Create a new card for the given artist with a checklist for their albums."""
        card = self.create_card(self.artists_list["id"], artist, pos=pos)

        if not card:
            return None

        checklist = self.create_checklist(card["id"], "Albums")

        if not checklist:
            self.delete_card(card["id"])
            return None

        albums_checkitems = []
        for album in albums:
            album_card = self.create_album_card(artist, album)
            if album_card and "shortUrl" in album_card:
                albums_checkitems.append(album_card["shortUrl"])
            else:
                albums_checkitems.append(album)

        self.add_items_to_checklist(checklist["id"], albums_checkitems)

        return card["id"]

    def update_artist_albums(
        self, artist: str, albums: List[str]
    ) -> Optional[List[str]]:
        """Add the given albums that aren't already on the artist's albums checklist."""
        if not albums:
            return None

        albums_checklist = self.get_artist_albums_checklist(artist)

        if albums_checklist:
            albums_checkitems = self.get_artist_albums_checkitems(
                artist, albums_checklist_id=albums_checklist["id"]
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

            return self.add_items_to_checklist(albums_checklist["id"], new_albums)

    def create_album_card(
        self, artist: str, album: str, pos: str = "bottom"
    ) -> Optional[Dict[str, Any]]:
        """Create a card for the given album in the pending list."""
        artist_card = self.get_artist_card(artist)

        if not artist_card:
            return None

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
            "url": artist_card["shortUrl"],
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

    def create_missing_album_cards(self, artist: str) -> List[str]:
        """Create missing linked cards for the artists' albums."""
        albums_checklist = self.get_artist_albums_checklist(artist)

        if albums_checklist:
            artist_card_id = albums_checklist.get("idCard", "")

            albums_checkitems = self.get_artist_albums_checkitems(
                artist, albums_checklist_id=albums_checklist["id"]
            )

            new_links = []
            url = "https://api.trello.com/1/cards/{id}/checkItem/{idCheckItem}"
            for checkitem in albums_checkitems:
                checkitem_id = checkitem.get("id", "")
                name = checkitem["name"]
                if not name.startswith("http"):
                    album_card = self.create_album_card(artist, name)
                    if album_card and "shortUrl" in album_card:
                        query = {
                            "name": album_card["shortUrl"],
                        }

                        response = self.make_request(
                            url.format(id=artist_card_id, idCheckItem=checkitem_id),
                            "PUT",
                            query_params=query,
                        )

                        if response.status_code == 200:
                            new_links.append(response.text)

            return new_links
