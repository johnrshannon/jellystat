from jellystat import output
from jellystat.client import JellyfinClient


def register(subparsers):
    p = subparsers.add_parser("server", help="Server metadata commands")
    sub = p.add_subparsers(dest="server_command")

    sub.add_parser("info", help="Server name, version, OS, uptime")
    sub.add_parser("sessions", help="Active playback sessions")
    sub.add_parser("storage", help="Storage breakdown by library")
    sub.add_parser("users", help="User accounts and activity")
    sub.add_parser("devices", help="All devices that have connected")
    sub.add_parser("plugins", help="Installed plugins")
    sub.add_parser("tasks", help="Scheduled tasks and last run status")

    for name in ("info", "sessions", "storage", "users", "devices", "plugins", "tasks"):
        output.add_output_args(sub._name_parser_map[name])


def handle(args, client: JellyfinClient):
    cmd = args.server_command
    if cmd == "info":
        _info(args, client)
    elif cmd == "sessions":
        _sessions(args, client)
    elif cmd == "storage":
        _storage(args, client)
    elif cmd == "users":
        _users(args, client)
    elif cmd == "devices":
        _devices(args, client)
    elif cmd == "plugins":
        _plugins(args, client)
    elif cmd == "tasks":
        _tasks(args, client)
    else:
        import argparse
        argparse.ArgumentParser(prog="jellystat server").print_help()


def _info(args, client: JellyfinClient):
    data = client.get("/System/Info")
    pairs = [
        ("Server name",  data.get("ServerName", "")),
        ("Version",      data.get("Version", "")),
        ("OS",           data.get("OperatingSystem", "")),
        ("Architecture", data.get("SystemArchitecture", "")),
        ("Local URL",    data.get("LocalAddress", "")),
    ]
    output.display_kv(pairs, args.format)


def _sessions(args, client: JellyfinClient):
    data = client.get("/Sessions")
    rows = []
    for s in data:
        now_playing = s.get("NowPlayingItem")
        rows.append({
            "User":       s.get("UserName", ""),
            "Device":     s.get("DeviceName", ""),
            "Client":     s.get("Client", ""),
            "Playing":    now_playing.get("Name", "") if now_playing else "",
            "Transcoding": "yes" if s.get("TranscodingInfo") else "",
        })

    if args.limit:
        rows = rows[:args.limit]

    output.display(rows, [
        ("User", "User"),
        ("Device", "Device"),
        ("Client", "Client"),
        ("Playing", "Playing"),
        ("Transcoding", "Transcoding"),
    ], args.format)


def _storage(args, client: JellyfinClient):
    libraries = client.get("/Library/MediaFolders")
    rows = []
    for lib in libraries.get("Items", []):
        # Fetch just enough to get the total count without pulling all items
        result = client.get("/Items", params={
            "ParentId": lib["Id"],
            "Recursive": "true",
            "Limit": 1,
        })
        rows.append({
            "Library": lib.get("Name", ""),
            "Type":    lib.get("CollectionType", "").replace("_", " ").title(),
            "Items":   result.get("TotalRecordCount", 0),
        })

    output.display(rows, [("Library", "Library"), ("Type", "Type"), ("Items", "Items")], args.format)


def _users(args, client: JellyfinClient):
    data = client.get("/Users")
    rows = []
    for u in data:
        policy = u.get("Policy", {})
        last_activity = u.get("LastActivityDate", "")
        rows.append({
            "Username":  u.get("Name", ""),
            "Admin":     "yes" if policy.get("IsAdministrator") else "",
            "Last seen": last_activity[:10] if last_activity else "never",
        })

    if args.limit:
        rows = rows[:args.limit]

    output.display(rows, [("Username", "Username"), ("Admin", "Admin"), ("Last seen", "Last seen")], args.format)


def _devices(args, client: JellyfinClient):
    data = client.get("/Devices")
    rows = []
    for d in data.get("Items", []):
        last_activity = d.get("DateLastActivity", "")
        rows.append({
            "Device":    d.get("Name", ""),
            "Client":    d.get("AppName", ""),
            "Last user": d.get("LastUserName", ""),
            "Last seen": last_activity[:10] if last_activity else "",
        })

    if args.limit:
        rows = rows[:args.limit]

    output.display(rows, [
        ("Device", "Device"),
        ("Client", "Client"),
        ("Last user", "Last user"),
        ("Last seen", "Last seen"),
    ], args.format)


def _plugins(args, client: JellyfinClient):
    data = client.get("/Plugins")
    rows = [{"Name": p.get("Name", ""), "Version": p.get("Version", ""), "Status": p.get("Status", "")} for p in data]

    if args.limit:
        rows = rows[:args.limit]

    output.display(rows, [("Name", "Name"), ("Version", "Version"), ("Status", "Status")], args.format)


def _tasks(args, client: JellyfinClient):
    data = client.get("/ScheduledTasks")
    rows = []
    for t in data:
        last = t.get("LastExecutionResult", {}) or {}
        next_run = t.get("NextExecutionTicks")
        rows.append({
            "Task":      t.get("Name", ""),
            "Last run":  last.get("EndTimeUtc", "")[:10] if last.get("EndTimeUtc") else "never",
            "Status":    last.get("Status", ""),
        })

    if args.limit:
        rows = rows[:args.limit]

    output.display(rows, [("Task", "Task"), ("Last run", "Last run"), ("Status", "Status")], args.format)
