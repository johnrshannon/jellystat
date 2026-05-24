import sys
from typing import Any

import requests
from requests import Session

from jellystat.config import Config

PAGE_SIZE = 500


class JellyfinClient:
    def __init__(self, config: Config):
        self.base_url = config.server_url
        self.user_id = config.user_id
        self.session = Session()
        self.session.headers.update({"X-Emby-Token": config.api_key})

    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            print(f"Error: could not connect to {self.base_url}")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"Error: server returned {e.response.status_code}")
            sys.exit(1)
        except requests.exceptions.Timeout:
            print("Error: request timed out")
            sys.exit(1)
        return resp.json()

    def get_items(self, params: dict | None = None) -> list[dict]:
        # Handles Jellyfin's StartIndex/TotalRecordCount pagination transparently.
        # Callers always get a flat list regardless of how many pages it took.
        params = dict(params or {})
        params["Limit"] = PAGE_SIZE
        params["StartIndex"] = 0

        items = []
        while True:
            data = self.get("/Items", params=params)
            items.extend(data["Items"])
            if len(items) >= data["TotalRecordCount"]:
                break
            params["StartIndex"] = len(items)

        return items
