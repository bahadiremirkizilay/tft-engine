"""Claude Code PreToolUse hook: never skip the repo's pre-commit checks.

Blocks shell commands that bypass the git hook (--no-verify, commit -n, or a changed
core.hooksPath). Reads the tool call as JSON on stdin; exit code 2 blocks it.
"""

import json
import re
import sys

BYPASS = [
    (r"--no-verify", "--no-verify"),
    (r"\bgit\b[^;&|\n]*\bcommit\b[^;&|\n]*\s-n(\s|$)", "commit -n"),
    # changing the hooks folder (reading it with --get is fine)
    (r"\bgit\b[^;&|\n]*\bconfig\b(?![^;&|\n]*--get)[^;&|\n]*core\.hooksPath", "core.hooksPath"),
    (r"\bgit\s+-c\s*core\.hooksPath", "core.hooksPath"),
]


def main() -> int:
    try:
        call = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = str(call.get("tool_input", {}).get("command", ""))
    for pattern, what in BYPASS:
        if re.search(pattern, command):
            print(
                f"Blocked: this command bypasses the repo's pre-commit checks ({what}). "
                "Fix the failing check instead; the owner can change hooks by hand.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
