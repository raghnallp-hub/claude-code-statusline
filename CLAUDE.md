# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A cross-platform custom statusline script for Claude Code that displays real-time session information in the terminal. Implemented in Python 3 for reliability, security, and zero external dependencies (no package managers required).

The implementation reads JSON from stdin (provided by Claude Code) and produces a two-line formatted display with model info, context usage, session cost, rate limits, workspace info, and git status.

## Architecture

### Data Flow

```
Claude Code → JSON stdin → Python json decoder → safely_get() validation → 
format_rate_limit() & make_bar() formatters → subprocess git calls → printf output
```

### Core Components

**`safely_get(obj, *keys, default=None)`** — Safe nested dictionary navigation
- Prevents KeyError, TypeError, AttributeError on malformed input
- Returns default value instead of crashing
- Example: `safely_get(data, "rate_limits", "five_hour", "used_percentage")`

**`make_bar(percentage)`** — Generates a 10-character usage bar
- Input: float percentage (any value, clamped to 0-100)
- Output: `████░░░░░░` filled/empty blocks
- Robust to invalid input (negative, >100%, non-numeric)

**`format_rate_limit(percentage, reset_ts, label)`** — Formats rate-limit display with color
- Calculates color based on thresholds: green <70%, yellow 70-89%, red ≥90%
- Converts Unix timestamp to local time (e.g., "2:30PM")
- Handles timezone differences (macOS `date -r` vs Linux `date -d`)
- Returns None/empty string if input invalid (graceful degradation)

**`get_git_info()`** — Retrieves git branch and diff stats
- Uses subprocess to call `git` (safe argument passing, no shell injection)
- Returns branch name with colored diff stats: `main +5 ~3` (5 added, 3 modified)
- Falls back to "no branch" if not in repo or git unavailable
- Subprocess calls: `git rev-parse`, `git branch`, `git diff --cached`, `git diff`

**`get_voice_enabled()`** — Reads voice mode state
- Voice mode is a persistent client setting, not part of the stdin payload, so this reads `~/.claude/settings.json` directly (`voice.enabled`, falling back to the legacy `voiceEnabled` key)
- Returns `False` on any error (missing file, malformed JSON, etc.)

**`format_cwd(cwd)`** — Formats the actual working directory
- Abbreviates `$HOME` to `~`
- Returns "unknown" if `cwd` is missing or Path() operations fail

**`main()`** — Orchestrates input parsing and output formatting
- Reads JSON from stdin, validates it's a dict
- Extracts fields with `safely_get()` (all validations happen here)
- Truncates all string fields to 100 chars (prevents DoS via long strings)
- Formats two-line output (line 1: model/cost/effort/context; line 2: dir/worktree/branch)
- Exits with code 1 on JSON parse error or invalid structure

### Two-Line Output Format

**Line 1 (Session State):**
- Without effort: `🤖 Model | 🧠 45% | 💰 $0.12 | ⏱️ 5h ████░░░░░░ 65% resets 2:30PM`
- With effort: `🤖 Model | 💪 high | 🧠 45% | 💰 $0.12 | ⏱️ 5h ████░░░░░░ 65% resets 2:30PM`
- With voice mode on, ` | 🎙️ Voice` is appended; omitted entirely when off

**Context Usage Color Thresholds (🧠):**
- White: <30% | Yellow: 30-44% | Orange: 45-49% | Purple: 50-55% | Red: ≥55%

**Line 2 (Workspace):**
- `📍 ~/code/my-project | 🌳 my-feature | 🌿 main +5 ~3` (green +, yellow ~)
- The 🌳 worktree segment only appears when `worktree.name` (a `--worktree` session) or `workspace.git_worktree` (a linked `git worktree add` checkout) is present in the payload — omitted otherwise to keep the line short

## Security & Robustness

### Vulnerabilities Tested & Mitigated

**52 comprehensive tests** (see `test_statusline.py`):
- ✅ Shell injection attempts → Treated as literal strings
- ✅ Python code injection → Not executed
- ✅ Oversized inputs (10KB+ model names, 1MB+ JSON) → Truncated/handled
- ✅ Invalid types (string instead of number) → Converted or defaulted
- ✅ Unicode/ANSI escape codes → Displayed safely without execution
- ✅ Timestamps (negative, far-future, invalid) → Handled gracefully
- ✅ Extreme values (Infinity, -50%, 150%) → Clamped or displayed

**Defense mechanisms:**
1. **JSON parsing is bulletproof** — Python's `json` module, not regex hacks
2. **No shell execution on user input** — subprocess calls use split args, not shell
3. **No dynamic code generation** — f-strings only, no eval/exec
4. **Type safety** — `safely_get()` validates before operations
5. **String truncation** — All user-facing strings capped at 100 chars
6. **Timeout protection** — Completes in <5 seconds even with 1MB+ input
7. **Memory safe** — No memory leaks or infinite loops under stress

**Test Results:** All 52 tests pass with 0 vulnerabilities found.

## Development & Testing

### Quick Test

```sh
# Test with sample JSON
python3 statusline-command.py <<'EOF'
{
  "model": {"display_name": "Claude Sonnet 4.6"},
  "effort": {"level": "high"},
  "context_window": {"used_percentage": 45.5},
  "cost": {"total_cost_usd": 0.12},
  "rate_limits": {
    "five_hour": {"used_percentage": 65, "resets_at": 1717584000}
  },
  "cwd": "/tmp",
  "workspace": {"current_dir": "/tmp"},
  "worktree": {"name": "my-feature", "path": "/tmp/.claude/worktrees/my-feature", "branch": "worktree-my-feature", "original_cwd": "/tmp/project", "original_branch": "main"}
}
EOF
```

### Run Full Test Suite

```sh
# Run all 52 tests
python3 test_statusline.py

# Run with pytest for prettier output
python3 -m pytest test_statusline.py -v

# Run only security tests
python3 -m pytest test_statusline.py -k "injection" -v
```

**Test categories:**
- Edge cases: empty input, null, malformed JSON
- Type errors: wrong types in fields, graceful degradation
- Extreme values: huge numbers, Infinity, scientific notation
- Oversized input: 10KB+ names, 1MB+ payloads
- Security: shell/code injection, format strings
- Stress: timeout protection, memory safety

See `QA_TEST_REPORT.md` for detailed findings.

## Customization

### Easy Edits

**Color scheme** (lines 44-46, 55-58):
```python
GREEN = "\033[32m"   # Green ANSI code
YELLOW = "\033[33m"  # Yellow ANSI code
RED = "\033[31m"     # Red ANSI code
```

**Context usage color thresholds** (lines 177-186):
```python
if pct_value >= 55:
    color = "\033[31m"      # RED — Change 55 to adjust threshold
elif pct_value >= 50:
    color = "\033[35m"      # PURPLE
elif pct_value >= 45:
    color = "\033[38;5;208m"  # ORANGE
elif pct_value >= 30:
    color = "\033[33m"      # YELLOW
```

**Rate-limit color thresholds** (lines 50-54):
```python
if pct >= 90:
    color = RED      # Change 90 to 85 for earlier red
elif pct >= 70:      # Change 70 threshold
    color = YELLOW
```

**Bar width** (line 24):
```python
width = 10  # Change to 20 for wider bar: ██████████░░░░░░░░░░
```

**Output format** (lines 175-186):
- Modify f-strings to add/remove fields
- Line 1: `line1 = f"..."`
- Line 2: `line2 = f"..."`

**Enable 7-day rate limit** (line 189, currently commented):
```python
# Uncomment to show 7-day alongside 5-hour:
# rate_limit_str += format_rate_limit(rl_7d_pct, rl_7d_reset, "7d")
```

## Dependencies

- **Python 3.9+** — Pre-installed on macOS 12.3+, Ubuntu 20.04+, and most modern systems
- **git** — For branch and diff stats (optional; falls back to "no branch" if missing)
- Standard library only: `json`, `sys`, `subprocess`, `os`, `datetime`, `pathlib`

**No external package managers required** — works on Intel macOS, Apple Silicon, Linux (any distro), and Windows (WSL).

## Input Schema

The JSON input from Claude Code provides:
- `model.display_name` (string) — Active model name
- `effort.level` (string, optional) — Effort level if set
- `context_window.used_percentage` (number) — Context usage 0-100
- `cost.total_cost_usd` (number) — Cumulative session cost
- `rate_limits.five_hour.used_percentage` (number) — 5-hour limit percentage
- `rate_limits.five_hour.resets_at` (number) — Unix timestamp of reset time
- `rate_limits.seven_day.used_percentage` (number) — 7-day limit (optional display)
- `rate_limits.seven_day.resets_at` (number) — 7-day reset timestamp
- `cwd` / `workspace.current_dir` (string) — Current working directory path
- `worktree.name` (string, optional) — Present only during `--worktree` sessions
- `workspace.git_worktree` (string, optional) — Present only inside a linked `git worktree add` checkout

All fields are optional; missing fields trigger safe defaults. Voice mode is deliberately *not* one of these fields — it's read out-of-band from `~/.claude/settings.json` since it's a client setting rather than session data.

See the [official statusline docs](https://code.claude.com/docs/en/statusline) for the full, authoritative schema — this project's assumptions about field names should be checked against it whenever Claude Code changes what it sends (this is what caused the 📁/🌳 fields to show "unknown"/"no worktree" before the schema was corrected against a real captured payload).

## Installation

Copy to `~/.claude/statusline-command.py` and configure in `.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline-command.py",
    "padding": 0
  }
}
```

Or run directly on macOS/Linux with shebang:
```sh
chmod +x ~/.claude/statusline-command.py
~/.claude/statusline-command.py < input.json
```
