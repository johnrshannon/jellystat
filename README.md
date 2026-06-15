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

> **macOS:** If pip refuses with an "externally managed environment" error, add `--break-system-packages` to the install command. This is a Python packaging convention that protects system-managed environments. The flag tells pip you're intentionally installing outside a virtualenv.

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

#### movies

Defaults to a library named "Movies". Use `--library` to query a different one.

```
--title TEXT             filter by title (case-insensitive substring)
--title-exact TEXT       filter by exact title (case-insensitive)
--min-rating FLOAT
--max-rating FLOAT
--after N                released after this year
--before N               released before this year
--genre TEXT
--resolution TEXT        4k, 1080p, 720p, 480p
--min-runtime N
--max-runtime N
--min-size N             minimum file size in MB
--max-size N             maximum file size in MB
--watched / --unwatched
--min-plays N
--has-trailer
--has-extras
--missing TEXT           overview, rating, genre, trailer, year
--sort TEXT              title, rating, year, added, runtime, filesize
--desc
--limit N
--library TEXT           repeatable
--exclude-library TEXT   repeatable
--columns TEXT           comma-separated: title, year, rating, runtime, genres, resolution, size
--summary                print total runtime and count instead of a table
--format table|json|csv
```

#### shows

Queries all TV libraries by default.

```
--title TEXT             filter by title (case-insensitive substring)
--title-exact TEXT       filter by exact title (case-insensitive)
--min-rating FLOAT
--max-rating FLOAT
--after N                first aired after this year
--before N               first aired before this year
--genre TEXT
--status ended|continuing
--min-seasons N
--max-seasons N
--resolution TEXT        4k, 1080p, 720p, 480p (matches if any episode is that resolution)
--watched / --unwatched
--missing TEXT           overview, rating, genre, year
--sort TEXT              title, rating, year, added, seasons, size, runtime
--desc
--limit N
--library TEXT           repeatable
--exclude-library TEXT   repeatable
--columns TEXT           comma-separated: title, year, rating, status, seasons, genres, size, resolution, runtime
--summary                print total runtime, episodes, seasons, and show count instead of a table
--format table|json|csv
```

`--library` and `--exclude-library` are useful when you have multiple libraries of the same content type. Both flags can be repeated.

```
jellystat movies --exclude-library "MMA" --exclude-library "Comedy"
jellystat movies --library "Movies" --columns title,year,rating
```

#### seasons

Storage and episode count broken down by season for a single show.

```
jellystat seasons "show name"
```

### Analytics

```
jellystat stats        Aggregate counts, runtime, storage, genre and decade breakdown
                       --type [movies|shows|all]
                       --library / --exclude-library TEXT

jellystat forgotten    Items added a while ago that haven't been watched
                       --type [movies|shows|all]
                       --days N    Minimum days since added (default: 180)
                       --library / --exclude-library TEXT

jellystat rewatched    Items watched more than once
                       --type [movies|shows|all]
                       --min-plays N    (default: 2)
                       --library / --exclude-library TEXT

jellystat recently-added    Items added in the last N days, sorted by date
                            --type [movies|shows|all]
                            --days N    Look back window (default: 30)
                            --library / --exclude-library TEXT
```

---

## Examples

How much content do you have?

```
jellystat movies --summary
jellystat shows --summary
jellystat movies --library MMA --summary
```

Longest shows by total runtime:

```
jellystat shows --sort runtime --desc --limit 10 --columns title,runtime
```

What 4K content haven't you watched yet?

```
jellystat movies --resolution 4k --unwatched
jellystat shows --resolution 4k --unwatched
```

Highest rated films you haven't seen:

```
jellystat movies --min-rating 8.0 --unwatched --sort rating --desc
```

Everything added in the last two weeks:

```
jellystat recently-added --days 14
```

Shows you've started but the library doesn't know you finished (useful for finding things you dropped):

```
jellystat forgotten --type shows
```

All movies in a specific library:

```
jellystat movies --library "MMA" --sort rating --desc
```

Runtime of a specific show:

```
jellystat shows --title-exact "The Sopranos" --summary
```

Storage breakdown by season for a specific show:

```
jellystat seasons "breaking bad"
```

Everything you've watched more than once:

```
jellystat rewatched --type movies
```

---

## Output

All commands accept `--format [table|json|csv]`. Default is `table`. JSON output is suitable for piping to `jq`.

```
jellystat movies --min-rating 7.5 --after 2000 --format json | jq '.[].Title'
```

Use `--limit N` on any command to cap results.
