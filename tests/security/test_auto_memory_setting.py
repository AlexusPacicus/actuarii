"""Claude Code's auto memory is off in this repository (ADR-010): .claude/settings.json pins autoMemoryEnabled to false.

The agent's memory is .claude/memory/, governed by receipts and versioned by git. The auto memory in
~/.claude/projects/ has neither, and Claude Code tells the agent to write there unless the setting turns it off.
"""
import json
from pathlib import Path

SETTINGS = Path(__file__).resolve().parents[2] / ".claude" / "settings.json"


def test_the_project_settings_turn_the_auto_memory_off():
    assert json.loads(SETTINGS.read_text(encoding="utf-8")).get("autoMemoryEnabled") is False
