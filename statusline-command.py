#!/usr/bin/env python3
"""
Claude Code Statusline Script
Cross-platform JSON statusline for Claude Code
Works on macOS, Linux, Windows (with WSL or python command)
"""
import json
import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path


def safely_get(obj, *keys, default=None):
    """Safely navigate nested dictionaries, returning default on any error."""
    try:
        for key in keys:
            if not isinstance(obj, dict):
                return default
            obj = obj.get(key)
            if obj is None:
                return default
        return obj
    except (TypeError, AttributeError, KeyError):
        return default


def make_bar(percentage):
    """Generate a 10-character usage bar with filled (█) and empty (░) blocks."""
    try:
        pct = float(percentage) if percentage else 0
        pct = max(0, min(100, pct))  # Clamp to 0-100
    except (ValueError, TypeError):
        pct = 0

    width = 10
    filled = int(pct * width / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_rate_limit(percentage, reset_ts, label):
    """Format rate-limit info with color thresholds (green <70%, yellow 70-89%, red ≥90%)."""
    if percentage is None or reset_ts is None:
        return None

    try:
        pct = float(percentage)
        pct = max(0, min(100, pct))  # Clamp to 0-100
        ts = int(float(reset_ts))
    except (ValueError, TypeError):
        return None

    # Color codes
    if pct >= 90:
        color = "\033[31m"  # RED
    elif pct >= 70:
        color = "\033[33m"  # YELLOW
    else:
        color = "\033[32m"  # GREEN
    reset = "\033[0m"

    # Format reset time
    try:
        reset_dt = datetime.fromtimestamp(ts)
        reset_time = reset_dt.strftime("%-I:%M%p").lstrip("0")  # Remove leading zero
    except (ValueError, OSError):
        reset_time = "unknown"

    bar = make_bar(pct)
    return f"{color}{label} {bar} {pct:.0f}% resets {reset_time}{reset}"


def get_git_info():
    """Get current git branch and diff stats."""
    try:
        # Check if in git repo
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        # Get branch name
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except subprocess.CalledProcessError:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()

        # Get staged changes
        staged_output = subprocess.check_output(
            ["git", "diff", "--cached", "--numstat"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        staged = len(staged_output.strip().split('\n')) if staged_output.strip() else 0

        # Get modified changes
        modified_output = subprocess.check_output(
            ["git", "diff", "--numstat"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        modified = len(modified_output.strip().split('\n')) if modified_output.strip() else 0

        git_str = branch
        if staged > 0:
            git_str += f" \033[32m+{staged}\033[0m"
        if modified > 0:
            git_str += f" \033[33m~{modified}\033[0m"

        return git_str
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no branch"


def get_voice_enabled():
    """Check whether voice mode is currently enabled via Claude Code's global settings.json."""
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        with open(settings_path) as f:
            settings = json.load(f)
        if not isinstance(settings, dict):
            return False
        return bool(
            safely_get(settings, "voice", "enabled", default=False)
            or settings.get("voiceEnabled", False)
        )
    except Exception:
        return False


def format_cwd(cwd):
    """Format the actual working directory, abbreviating the home dir to ~."""
    try:
        if not cwd:
            return "unknown"
        home = str(Path.home())
        cwd_str = str(cwd)
        if cwd_str == home:
            cwd_str = "~"
        elif cwd_str.startswith(home + os.sep):
            cwd_str = "~" + cwd_str[len(home):]
        return cwd_str[:100]
    except Exception:
        return "unknown"


def main():
    """Parse JSON from stdin and output formatted statusline."""
    try:
        # Read and parse JSON from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            sys.exit(1)

        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            sys.exit(1)

        if not isinstance(data, dict):
            sys.exit(1)

        # Extract fields safely
        model = safely_get(data, "model", "display_name", default="Unknown Model")
        # Sanitize: ensure it's a string and limit length
        model = str(model)[:100] if model else "Unknown Model"

        effort = safely_get(data, "effort", "level", default=None)
        effort = str(effort)[:50] if effort else None

        used_pct = safely_get(data, "context_window", "used_percentage")
        try:
            pct_value = float(used_pct) if used_pct is not None else 0
            pct_str = f"{pct_value:.0f}%"

            # Color based on context usage: yellow 30-44%, orange 45-49%, purple 50-55%, red 55%+
            if pct_value >= 55:
                color = "\033[31m"      # RED
            elif pct_value >= 50:
                color = "\033[35m"      # PURPLE
            elif pct_value >= 45:
                color = "\033[38;5;208m"  # ORANGE (256-color)
            elif pct_value >= 30:
                color = "\033[33m"      # YELLOW
            else:
                color = ""              # No color
            reset = "\033[0m"
            used_display = f"{color}{pct_str}{reset}" if color else pct_str
        except (ValueError, TypeError):
            used_display = "0%"

        total_cost = safely_get(data, "cost", "total_cost_usd")
        try:
            cost_display = f"${float(total_cost):.2f}" if total_cost else "$0.00"
        except (ValueError, TypeError):
            cost_display = "$0.00"

        # worktree.name: Claude Code `--worktree` sessions.
        # workspace.git_worktree: any linked `git worktree add` checkout.
        # Absent in the common case (no worktree in play) -- omit the segment then.
        worktree = (
            safely_get(data, "worktree", "name", default=None)
            or safely_get(data, "workspace", "git_worktree", default=None)
        )
        worktree_str = str(worktree)[:100] if worktree else None

        current_dir = safely_get(data, "workspace", "current_dir", default=None) or safely_get(
            data, "cwd", default=None
        )

        rl_5h_pct = safely_get(data, "rate_limits", "five_hour", "used_percentage")
        rl_5h_reset = safely_get(data, "rate_limits", "five_hour", "resets_at")

        # Format rate limit
        rate_limit_str = format_rate_limit(rl_5h_pct, rl_5h_reset, "5h") or ""

        # Get git info
        git_str = get_git_info()

        # Get actual working directory (abbreviated)
        cwd_display = format_cwd(current_dir)

        # Get voice mode indicator
        voice_segment = " | 🎙️ Voice" if get_voice_enabled() else ""

        # Build output
        if effort:
            line1 = f"🤖 {model} | 💪 {effort} | 🧠 {used_display} | 💰 {cost_display} | ⏱️ {rate_limit_str}{voice_segment}"
        else:
            line1 = f"🤖 {model} | 🧠 {used_display} | 💰 {cost_display} | ⏱️ {rate_limit_str}{voice_segment}"

        worktree_segment = f" | 🌳 {worktree_str}" if worktree_str else ""
        line2 = f"📍 {cwd_display}{worktree_segment} | 🌿 {git_str}"

        print(line1)
        print(line2)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
