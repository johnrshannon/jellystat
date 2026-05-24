import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import requests
from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("jellystat"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    server_url: str
    api_key: str
    username: str
    user_id: str


def load() -> Config:
    if not CONFIG_FILE.exists():
        print("No config found. Run 'jellystat configure' to get started.")
        sys.exit(1)

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    return Config(
        server_url=data["server_url"].rstrip("/"),
        api_key=data["api_key"],
        username=data["username"],
        user_id=data["user_id"],
    )


def save(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(f'server_url = "{config.server_url}"\n')
        f.write(f'api_key = "{config.api_key}"\n')
        f.write(f'username = "{config.username}"\n')
        f.write(f'user_id = "{config.user_id}"\n')


def run_wizard() -> None:
    print()
    server_url = input("Jellyfin server URL: ").strip().rstrip("/")
    api_key = input("Jellyfin API key: ").strip()

    print("\nConnecting to server...", end=" ", flush=True)

    # Direct requests call here to avoid a circular import with client.py,
    # which depends on config. This is the one place that's acceptable.
    headers = {"X-Emby-Token": api_key}
    try:
        resp = requests.get(f"{server_url}/Users", headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("failed (could not connect)")
        sys.exit(1)
    except requests.exceptions.HTTPError:
        print("failed (check your API key)")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("timed out")
        sys.exit(1)

    print("OK")

    users = resp.json()
    if not users:
        print("No users found on this server.")
        sys.exit(1)

    if len(users) == 1:
        user = users[0]
        print(f"Found 1 user: {user['Name']}")
        print(f"Using {user['Name']} automatically.")
    else:
        print(f"\nFound {len(users)} users:")
        for i, u in enumerate(users, 1):
            print(f"  {i}. {u['Name']}")
        print()
        while True:
            choice = input(f"Select a user (1-{len(users)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(users):
                user = users[int(choice) - 1]
                break
            print("Invalid selection, try again.")

    config = Config(
        server_url=server_url,
        api_key=api_key,
        username=user["Name"],
        user_id=user["Id"],
    )
    save(config)
    print(f"\nConfig saved to {CONFIG_FILE}")
