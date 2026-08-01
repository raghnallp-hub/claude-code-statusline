# Claude Code Statusline

A custom statusline script for [Claude Code](https://claude.ai/claude-code) that displays real-time session information in your terminal.

![Statusline preview](screenshot.png)

## What It Shows

```
🤖 Claude Sonnet 4.6 | 🧠 12% | 💰 $0.04 | ⏱️ 5h ████░░░░░░ 42% resets 2:00PM | 🎙️ Voice
📁 my-project | 📍 ~/code/my-project | 🌳 my-feature | 🌿 main +42 -7
```

| Field | Description |
|---|---|
| 🤖 Model | Active Claude model name |
| 🧠 Context | Context window usage percentage with color thresholds |
| 💰 Cost | Cumulative session cost in USD |
| ⏱️ Rate Limit | 5-hour rate limit usage bar, percentage, and reset time |
| 🎙️ Voice | Shown only when voice mode is currently enabled (read from `~/.claude/settings.json`) |
| 📁 Folder | Repository root directory name |
| 📍 Path | Actual current working directory, with `$HOME` abbreviated to `~` |
| 🌳 Worktree | Active git worktree name |
| 🌿 Branch | Current git branch with lines added/removed |

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) CLI installed
- **Python 3.9+** — Pre-installed on macOS 12.3+ and modern Linux distributions
- `git` — for branch and diff stats (optional; gracefully falls back if not available)

### Python Installation (if needed)

Python 3 is usually pre-installed. If not:

```sh
# macOS
# If not available, install via python.org (no Homebrew needed):
# https://www.python.org/downloads/macos/

# Ubuntu/Debian
sudo apt-get install python3

# Windows
# Use WSL or download from https://www.python.org/downloads/windows/
```

## Setup

**1. Copy the script somewhere accessible:**

```sh
cp statusline-command.py ~/.claude/statusline-command.py
chmod +x ~/.claude/statusline-command.py
```

**2. Add the statusline configuration to `.claude/settings.json`:**

For a **global** setup (applies to all projects), edit `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline-command.py",
    "padding": 0
  }
}
```

For a **project-level** setup, add the same block to `.claude/settings.json` in your project root.

**3. Start Claude Code** — the statusline will appear automatically.

**Note:** On macOS and Linux, the shebang allows you to run directly:
```sh
~/.claude/statusline-command.py < input.json
```

On Windows (native CMD/PowerShell), use explicit invocation:
```powershell
python3 ~/.claude/statusline-command.py < input.json
```

## Customization

The script reads a JSON object from stdin with the following fields:

| Field | Description |
|---|---|
| `model.display_name` | Name of the active model |
| `effort.level` | Effort level (optional; only displayed if present) |
| `context_window.used_percentage` | Context usage as a float (0-100) |
| `cost.total_cost_usd` | Cumulative session cost |
| `rate_limits.five_hour.used_percentage` | 5-hour rate limit usage percentage |
| `rate_limits.five_hour.resets_at` | Unix timestamp when 5-hour limit resets |
| `rate_limits.seven_day.used_percentage` | 7-day rate limit usage percentage (available for optional display) |
| `rate_limits.seven_day.resets_at` | Unix timestamp when 7-day limit resets (available for optional display) |
| `worktree.name` | Active worktree name |
| `worktree.original_cwd` | Current working directory (used to compute repo root and the 📍 path) |

Voice mode state isn't part of the stdin payload — it's a persistent client setting, so the script reads it directly from `~/.claude/settings.json` (`voice.enabled` or the legacy `voiceEnabled` key) each time it runs.

### Context Usage Colors

The 🧠 context percentage displays with color thresholds based on usage:
- White: <30% usage
- 🟡 Yellow: 30-44% usage
- 🟠 Orange: 45-49% usage
- 🟣 Purple: 50-55% usage
- 🔴 Red: ≥55% usage

### Rate Limit Colors

The rate-limit bar uses color thresholds:
- 🟢 Green: <70% usage
- 🟡 Yellow: 70-89% usage  
- 🔴 Red: ≥90% usage

### Editing the Script

Edit `statusline-command.py` to:
- Change context usage color thresholds (lines 173-186)
- Adjust rate-limit color codes (lines 50-54, 56-58)
- Modify bar width (line 24: `width = 10`)
- Change the output format (lines 204-208)
- Add or remove fields from the display
- Enable 7-day limit display (line 211, commented out)
