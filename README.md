# Kimi Token Widget

An unofficial, local-only desktop widget and command-line report for token usage across saved [Kimi Code](https://www.kimi.com/code/) sessions.

## Features

- Shows total token usage across all local sessions
- Shows the latest session's token count
- Breaks down regular input, cached input, cache creation, and output tokens
- Includes main-agent and subagent usage
- Refreshes automatically without blocking the interface
- Exports per-session reports as text, JSON, or CSV
- Uses only the Python standard library

## Requirements

- Kimi Code with locally saved sessions
- Python 3.9 or newer
- Tkinter, included with the standard Windows and macOS Python installers

On Linux, install Tkinter with your distribution's package manager if it is not already available. For example, Debian and Ubuntu use `python3-tk`.

## Run the widget

```bash
git clone https://github.com/Cyberkillr013/kimi-token-widget.git
cd kimi-token-widget
python token_widget.py
```

The widget updates every 15 seconds. Drag its title bar to move it, right-click to toggle always-on-top, and use the refresh button to update immediately.

Optional settings:

```bash
python token_widget.py --refresh-seconds 30
python token_widget.py --root /path/to/custom/kimi-code-home
```

## Command-line report

```bash
python token_usage.py
python token_usage.py --format json
python token_usage.py --format csv
```

Save an export with:

```bash
python token_usage.py --format csv > token-usage.csv
```

## Data and privacy

The tools read `sessions/**/agents/*/wire.jsonl` under `KIMI_CODE_HOME`, defaulting to `~/.kimi-code`. They count top-level `usage.record` events and do not count nested usage events again.

All processing stays on your computer. No API key is required and the code makes no network requests. JSON and CSV exports include session titles and working directories, so review exports before sharing them.

The total includes regular input, cached input, cache creation, and output tokens. These token totals do not necessarily correspond directly to subscription-quota percentages. Sessions from other computers are not included unless their local data is supplied separately.

## Compatibility

The parser currently supports the Kimi Code session format, not Claude Code. The project has been tested on Windows; other desktop platforms require a working Tkinter installation but are otherwise untested.

This is an unofficial project and is not affiliated with or endorsed by Moonshot AI.
