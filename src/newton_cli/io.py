"""Output / error envelope helpers shared by every subcommand.

Stable contract:
  - --json mode emits {"schema":"newton-cli/v1","data":...} on stdout
  - error mode emits {"schema":"newton-cli/v1","error":{...}} on stderr
  - human mode emits free-form text on stdout / stderr

Exit codes:
  0  ok
  2  user / argument error
  3  Newton or Warp runtime error
  4  missing optional dependency
"""

from __future__ import annotations

import json
import sys
from typing import Any, NoReturn

from newton_cli import SCHEMA

EXIT_OK = 0
EXIT_USER_ERROR = 2
EXIT_RUNTIME_ERROR = 3
EXIT_MISSING_DEP = 4
EXIT_TIMEOUT = 5


def emit(data: Any, *, json_mode: bool, human: str | None = None) -> None:
    """Emit a successful result.

    Args:
        data: payload placed under the `data` key in JSON mode
        json_mode: whether the user passed --json
        human: optional human-readable rendering; defaults to repr(data)
    """
    if json_mode:
        sys.stdout.write(json.dumps({"schema": SCHEMA, "data": data}, default=str))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(human if human is not None else repr(data))
        if not (human or "").endswith("\n"):
            sys.stdout.write("\n")
    sys.stdout.flush()


def fail(
    code: int,
    message: str,
    *,
    hint: str | None = None,
    json_mode: bool = False,
    error_code: str | None = None,
) -> NoReturn:
    """Emit an error envelope and exit with the given code."""
    if json_mode:
        envelope = {
            "schema": SCHEMA,
            "error": {
                "code": error_code or _default_error_code(code),
                "message": message,
            },
        }
        if hint:
            envelope["error"]["hint"] = hint
        sys.stderr.write(json.dumps(envelope))
        sys.stderr.write("\n")
    else:
        sys.stderr.write(f"error: {message}\n")
        if hint:
            sys.stderr.write(f"hint: {hint}\n")
    sys.stderr.flush()
    sys.exit(code)


def _default_error_code(exit_code: int) -> str:
    return {
        EXIT_USER_ERROR: "user_error",
        EXIT_RUNTIME_ERROR: "runtime_error",
        EXIT_MISSING_DEP: "missing_dependency",
        EXIT_TIMEOUT: "timeout",
    }.get(exit_code, "error")
