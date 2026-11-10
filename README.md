# Kimi Token Widget

An unofficial, local-only desktop widget and command-line report for token usage across saved [Kimi Code](https://www.kimi.com/code/) sessions.

## Features

- A minimal desktop widget with only an animated moon-cat virtual pet and the all-session token total
- Breathing, bobbing, random blinking, and eyes that follow the mouse pointer
- Happy, surprised, excited, playful, snack-loving, and sleepy expressions
- Floating hearts when petted, star eyes during play, a bouncing ball, snacks, and animated “Zzz” symbols
- Automatic sleep after 45 seconds without interaction, with wake-up on hover or activity
- Gentle wandering near its current spot, with an option to turn wandering off
- Includes main-agent and subagent usage
- Refreshes automatically without blocking the interface
- Draws and animates everything with Tkinter, with no image assets or extra dependencies
- Exports detailed per-session reports as text, JSON, or CSV
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

The token count updates every 15 seconds.

Interactions:

- Hover over the avatar to excite or wake it
- Click the avatar to pet it
- Drag anywhere to move the widget and surprise the pet
- Double-click the avatar to refresh and trigger its excited reaction
- Right-click to give a snack, play together, toggle sleep, toggle always-on-top or wandering, refresh, or close
- Press `Esc` to close

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
