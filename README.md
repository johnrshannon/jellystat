# jellystat

CLI tool for querying a Jellyfin media server. Two layers: server metadata and library queries with filtering, sorting, and a few analytics commands.

---

## Requirements

- Python 3.10+
- A Jellyfin server with API access

---

## Installation

```
pip install git+https://github.com/johnrshannon/jellystat
```

For local development:

```
git clone https://github.com/johnrshannon/jellystat
cd jellystat
pip install -e .
```

> **Windows:** If `jellystat` isn't found after install, add Python's Scripts folder to your PATH: `C:\Users\<you>\AppData\Local\Programs\Python\Python3x\Scripts\`

---

## Configuration

Run once after installing:

```
jellystat configure
```

You'll be prompted for your server URL and API key. To get an API key: Jellyfin dashboard > API Keys > Add. If your server has multiple users, the wizard will ask which one to use for watch history and play data.

Config is written to the platform-appropriate location:

| OS      | Path                                                   |
|---------|--------------------------------------------------------|
| Linux   | `~/.config/jellystat/config.toml`                      |
| macOS   | `~/Library/Application Support/jellystat/config.toml` |
| Windows | `C:\Users\<you>\AppData\Roaming\jellystat\config.toml` |

---

## Commands

### Server

```
jellystat server info        Server name, version, OS, uptime
jellystat server sessions    Active playback sessions
jellystat server storage     Storage breakdown by library
jellystat server users       User accounts and activity
jellystat server devices     All devices that have connected
jellystat server plugins     Installed plugins
jellystat server tasks       Scheduled tasks and last run status
```

### Library

```
jellystat movies    Query all movies
jellystat shows     Query all TV shows
```

These query by content type across all libraries, regardless of how your libraries are named or organized.

Both support:

```
--min-rating / --max-rating FLOAT
--after / --before N
--genre TEXT
--min-runtime / --max-runtime N
--watched / --unwatched
--min-plays N
--has-trailer
--has-extras
--missing TEXT           overview, rating, genre, trailer, year
--resolution TEXT        4k, 1080p, 720p, 480p
--min-size / --max-size N
--sort TEXT              title, rating, year, added, runtime
--desc
```

Shows also support:

```
--status [ended|continuing]
--min-seasons / --max-seasons N
--sort seasons
```

### Analytics

```
jellystat stats        Aggregate counts, runtime, storage, genre and decade breakdown
                       --type [movies|shows|all]

jellystat forgotten    Items added a while ago that haven't been watched
                       --type [movies|shows|all]
                       --days N    Minimum days since added (default: 180)

jellystat rewatched    Items watched more than once
                       --type [movies|shows|all]
                       --min-plays N    (default: 2)
```

---

## Output

All commands accept `--format [table|json|csv]`. Default is `table`. JSON output is suitable for piping to `jq`.

```
jellystat movies --min-rating 7.5 --after 2000 --format json | jq '.[].Title'
```

Use `--limit N` on any command to cap results.
