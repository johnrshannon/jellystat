import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import requests
from platformdirs import user_config_dir
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

CONFIG_DIR = Path(user_config_dir("jellystat"))
CONFIG_FILE = CONFIG_DIR / "config.toml"

console = Console()


@dataclass
class Config:
    server_url: str
    api_key: str
    username: str
    user_id: str


def load() -> Config:
    if not CONFIG_FILE.exists():
        console.print("[red]No config found.[/red] Run 'jellystat configure' to get started.")
        sys.exit(1)

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    return Config(
        server_url=data["server_url"].rstrip("/"),  # normalize so appending paths never produces double slashes
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
    console.print(Panel("[bold]jellystat setup[/bold]", expand=False))
    console.print()

    server_url = Prompt.ask("[cyan]Jellyfin server URL[/cyan]").strip().rstrip("/")
    if not server_url.startswith(("http://", "https://")):
        server_url = "http://" + server_url
        console.print(f"  [dim]→ using {server_url}[/dim]")

    api_key = Prompt.ask("[cyan]Jellyfin API key[/cyan]").strip()
    console.print()

    # Direct requests call here to avoid a circular import with client.py,
    # which depends on config. This is the one place that's acceptable.
    headers = {"X-Emby-Token": api_key}
    try:
        with console.status("Connecting to server..."):
            resp = requests.get(f"{server_url}/Users", headers=headers, timeout=10)
            resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        console.print("[red]✗[/red] Could not connect to server.")
        sys.exit(1)
    except requests.exceptions.HTTPError:
        console.print("[red]✗[/red] Server rejected the request — check your API key.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        console.print("[red]✗[/red] Connection timed out.")
        sys.exit(1)

    console.print("[green]Connected.[/green]\n")

    users = resp.json()
    if not users:
        console.print("[red]No users found on this server.[/red]")
        sys.exit(1)

    if len(users) == 1:
        user = users[0]
        console.print(f"Found 1 user: [bold]{user['Name']}[/bold] — selecting automatically.")
    else:
        console.print(f"Found {len(users)} users:")
        for i, u in enumerate(users, 1):
            console.print(f"  [dim]{i}.[/dim] {u['Name']}")
        console.print()
        while True:
            choice = Prompt.ask(f"[cyan]Select a user (1-{len(users)})[/cyan]").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(users):
                user = users[int(choice) - 1]
                break
            console.print("[yellow]Invalid selection, try again.[/yellow]")

    config = Config(
        server_url=server_url,
        api_key=api_key,
        username=user["Name"],
        user_id=user["Id"],
    )
    save(config)

    console.print()
    console.print(Panel(
        f"[green]All set![/green] Logged in as [bold]{user['Name']}[/bold]\n"
        f"[dim]Config saved to {CONFIG_FILE}[/dim]",
        expand=False,
    ))
