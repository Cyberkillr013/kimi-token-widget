import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TOKEN_FIELDS = ("inputOther", "inputCacheRead", "inputCacheCreation", "output")


def empty_usage():
    return {field: 0 for field in TOKEN_FIELDS}


def timestamp_ms(value):
    if value is None:
        return 0
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return 0
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
    if isinstance(value, (int, float)):
        return int(value * 1000) if value < 100_000_000_000 else int(value)
    return 0


def format_time(value):
    milliseconds = timestamp_ms(value)
    if not milliseconds:
        return "unknown"
    return datetime.fromtimestamp(milliseconds / 1000).astimezone().strftime("%Y-%m-%d %H:%M")


def read_metadata(session_dir):
    try:
        with (session_dir / "state.json").open(encoding="utf-8") as handle:
            metadata = json.load(handle)
        return metadata if isinstance(metadata, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def token_amount(value):
    if isinstance(value, bool):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def collect_session(session_dir):
    metadata = read_metadata(session_dir)
    session = {
        "sessionId": session_dir.name,
        "title": str(metadata.get("title") or "(no title)"),
        "workDir": str(metadata.get("workDir") or metadata.get("cwd") or ""),
        "createdAt": metadata.get("createdAt"),
        "updatedAt": metadata.get("updatedAt"),
        "usageRecords": 0,
        "models": set(),
        "usage": empty_usage(),
    }
    last_usage_at = 0

    for wire_path in session_dir.glob("agents/*/wire.jsonl"):
        try:
            handle = wire_path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict) or event.get("type") != "usage.record":
                    continue
                usage = event.get("usage")
                if not isinstance(usage, dict):
                    continue
                session["usageRecords"] += 1
                for field in TOKEN_FIELDS:
                    session["usage"][field] += token_amount(usage.get(field))
                if isinstance(event.get("model"), str):
                    session["models"].add(event["model"])
                last_usage_at = max(last_usage_at, timestamp_ms(event.get("time")))

    session["models"] = sorted(session["models"])
    session["lastUsageAt"] = last_usage_at or None
    session["totalTokens"] = sum(session["usage"].values())
    session["sortTime"] = max(
        timestamp_ms(session["updatedAt"]),
        timestamp_ms(session["createdAt"]),
        last_usage_at,
    )
    return session


def collect_sessions(root):
    sessions_root = root / "sessions"
    sessions = []
    if not sessions_root.is_dir():
        return sessions
    for session_dir in sessions_root.glob("*/*"):
        if session_dir.is_dir():
            sessions.append(collect_session(session_dir))
    return sorted(sessions, key=lambda session: session["sortTime"], reverse=True)


def serializable_session(session):
    return {key: value for key, value in session.items() if key != "sortTime"}


def summarize(sessions):
    usage = empty_usage()
    for session in sessions:
        for field in TOKEN_FIELDS:
            usage[field] += session["usage"][field]
    return {
        "sessions": len(sessions),
        "sessionsWithUsage": sum(session["usageRecords"] > 0 for session in sessions),
        "usageRecords": sum(session["usageRecords"] for session in sessions),
        "usage": usage,
        "totalTokens": sum(usage.values()),
    }


def print_table(sessions, summary):
    rows = []
    for session in sessions:
        short_id = session["sessionId"].removeprefix("session_")[:8]
        title = " ".join(session["title"].split())
        if len(title) > 42:
            title = title[:41] + "…"
        rows.append([
            short_id,
            format_time(session["updatedAt"] or session["lastUsageAt"]),
            f"{session['usage']['inputOther']:,}",
            f"{session['usage']['inputCacheRead']:,}",
            f"{session['usage']['inputCacheCreation']:,}",
            f"{session['usage']['output']:,}",
            f"{session['totalTokens']:,}",
            title,
        ])

    headers = ["SESSION", "UPDATED", "INPUT", "CACHE READ", "CACHE WRITE", "OUTPUT", "TOTAL", "TITLE"]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row[:-1]):
            widths[index] = max(widths[index], len(value))

    def format_row(row):
        cells = []
        for index, value in enumerate(row[:-1]):
            cells.append(value.rjust(widths[index]) if 2 <= index <= 6 else value.ljust(widths[index]))
        cells.append(row[-1])
        return "  ".join(cells)

    print(f"Kimi Code sessions: {summary['sessions']} ({summary['sessionsWithUsage']} with recorded usage)")
    print(format_row(headers))
    print(format_row(["-" * width for width in widths] + ["-" * 5]))
    for row in rows:
        print(format_row(row))

    totals = summary["usage"]
    print(
        "\nAll sessions: "
        f"input {totals['inputOther']:,} | "
        f"cache read {totals['inputCacheRead']:,} | "
        f"cache write {totals['inputCacheCreation']:,} | "
        f"output {totals['output']:,} | "
        f"total {summary['totalTokens']:,}"
    )
    print("Total includes regular input, cached input, cache creation, and output tokens.")


def print_csv(sessions):
    writer = csv.writer(sys.stdout)
    writer.writerow([
        "session_id",
        "title",
        "work_dir",
        "created_at",
        "updated_at",
        "usage_records",
        "models",
        "input_other",
        "input_cache_read",
        "input_cache_creation",
        "output",
        "total_tokens",
    ])
    for session in sessions:
        writer.writerow([
            session["sessionId"],
            session["title"],
            session["workDir"],
            session["createdAt"],
            session["updatedAt"],
            session["usageRecords"],
            ";".join(session["models"]),
            *(session["usage"][field] for field in TOKEN_FIELDS),
            session["totalTokens"],
        ])


def main():
    parser = argparse.ArgumentParser(description="Report exact token usage for each saved Kimi Code session.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("KIMI_CODE_HOME", Path.home() / ".kimi-code")),
        help="Kimi Code data directory (default: KIMI_CODE_HOME or ~/.kimi-code)",
    )
    parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    args = parser.parse_args()

    sessions = collect_sessions(args.root.expanduser())
    summary = summarize(sessions)
    if args.format == "json":
        json.dump(
            {"summary": summary, "sessions": [serializable_session(session) for session in sessions]},
            sys.stdout,
            indent=2,
        )
        print()
    elif args.format == "csv":
        print_csv(sessions)
    else:
        print_table(sessions, summary)


if __name__ == "__main__":
    main()
