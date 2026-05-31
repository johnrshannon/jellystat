import csv
import json
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def display(items: list[dict], columns: list[tuple[str, str]], fmt: str = "table", footer: dict | None = None) -> None:
    if not items:
        console.print("[dim]No results.[/dim]")
        return

    if fmt == "json":
        _json(items)
    elif fmt == "csv":
        _csv(items, columns)
    else:
        _table(items, columns, footer=footer)


def display_kv(pairs: list[tuple[str, str]], fmt: str = "table") -> None:
    if fmt == "json":
        print(json.dumps(dict(pairs), indent=2))
    elif fmt == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["Field", "Value"])
        for k, v in pairs:
            writer.writerow([k, v])
    else:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold")
        table.add_column()
        for k, v in pairs:
            table.add_row(k, str(v) if v is not None else "")
        console.print(table)


def add_output_args(parser) -> None:
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table", metavar="FORMAT")
    parser.add_argument("--limit", type=int, metavar="N")


def add_library_args(parser) -> None:
    parser.add_argument("--library", metavar="TEXT", action="append", help="only include this library")
    parser.add_argument("--exclude-library", metavar="TEXT", action="append", dest="exclude_library", help="exclude this library")


def _table(items: list[dict], columns: list[tuple[str, str]], footer: dict | None = None) -> None:
    table = Table(show_header=True, header_style="bold", row_styles=["", "dim"], show_footer=bool(footer), footer_style="bold")

    for col in columns:
        header = col[0]
        justify = col[2] if len(col) > 2 else "left"
        footer_val = footer.get(col[1], "") if footer else ""
        table.add_column(header, justify=justify, footer=footer_val)

    for item in items:
        table.add_row(*[_val(item.get(col[1])) for col in columns])

    console.print(table)


def _json(items: list[dict]) -> None:
    print(json.dumps(items, indent=2))


def _csv(items: list[dict], columns: list[tuple[str, str]]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow([col[0] for col in columns])
    for item in items:
        writer.writerow([_val(item.get(col[1])) for col in columns])


def _val(v) -> str:
    # Coerce None cleanly without letting 0 or False become empty string
    return "" if v is None else str(v)
