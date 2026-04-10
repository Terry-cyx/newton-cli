"""Test helper: invoke newton-cli via real subprocess so the argv path is exercised."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CliResult:
    code: int
    stdout: str
    stderr: str

    def json(self) -> dict:
        return json.loads(self.stdout)


def run_cli(*args: str, check: bool = False) -> CliResult:
    """Run `python -m newton_cli <args>` and capture the result."""
    proc = subprocess.run(
        [sys.executable, "-m", "newton_cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = CliResult(code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    if check and result.code != 0:
        raise AssertionError(
            f"newton-cli {' '.join(args)} exited {result.code}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result
