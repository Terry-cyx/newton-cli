"""Test the `newton-cli run-script` subcommand contract.

run-script is the B-route escape hatch: when a Newton example needs per-step
Python (custom @wp.kernel, torch policy, autograd loop), the agent writes a
small script and the CLI invokes it in a subprocess with structured output.

Contract:
  - exits 0 if the script exits 0
  - exits 3 (newton_runtime_error) if the script exits non-zero
  - exits 5 (timeout) if the script doesn't finish in --timeout seconds
  - exits 2 (user error) if --script doesn't exist
  - --json emits {"schema":"newton-cli/v1","data":{exit_code, duration_s, ...}}
  - injects env var NEWTON_CLI_ARTIFACT_DIR and lists files written there
"""

from __future__ import annotations

import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests._cli import run_cli


def _write_script(body: str) -> Path:
    """Write a tempfile script and return its path."""
    fd, name = tempfile.mkstemp(suffix=".py", prefix="newton_cli_test_")
    os.close(fd)
    Path(name).write_text(textwrap.dedent(body))
    return Path(name)


class TestRunScriptHappyPath(unittest.TestCase):
    def test_exit_zero_success(self):
        script = _write_script("""
            import sys
            print("hello from script")
            sys.exit(0)
        """)
        try:
            r = run_cli("run-script", str(script), "--json")
            self.assertEqual(r.code, 0, msg=f"stderr={r.stderr}")
            data = r.json()["data"]
            self.assertEqual(data["exit_code"], 0)
            self.assertIn("hello from script", "\n".join(data.get("stdout_lines", [])))
            self.assertIn("duration_s", data)
        finally:
            script.unlink(missing_ok=True)

    def test_artifact_dir_collected(self):
        script = _write_script("""
            import os
            from pathlib import Path
            d = Path(os.environ["NEWTON_CLI_ARTIFACT_DIR"])
            (d / "result.txt").write_text("ok")
            (d / "result.npz").write_bytes(b"\\x00\\x01\\x02")
        """)
        try:
            r = run_cli("run-script", str(script), "--json")
            self.assertEqual(r.code, 0, msg=f"stderr={r.stderr}")
            artifacts = r.json()["data"]["artifacts"]
            names = sorted(Path(a["path"]).name for a in artifacts)
            self.assertIn("result.txt", names)
            self.assertIn("result.npz", names)
        finally:
            script.unlink(missing_ok=True)


class TestRunScriptFailures(unittest.TestCase):
    def test_script_nonzero_exit_maps_to_runtime_error(self):
        script = _write_script("""
            import sys
            sys.exit(7)
        """)
        try:
            r = run_cli("run-script", str(script), "--json")
            self.assertEqual(r.code, 3)
            self.assertEqual(r.json()["data"]["exit_code"], 7)
        finally:
            script.unlink(missing_ok=True)

    def test_script_exception_propagates_in_stderr(self):
        script = _write_script("""
            raise RuntimeError("boom from script")
        """)
        try:
            r = run_cli("run-script", str(script), "--json")
            self.assertEqual(r.code, 3)
            stderr_blob = "\n".join(r.json()["data"].get("stderr_lines", []))
            self.assertIn("boom from script", stderr_blob)
        finally:
            script.unlink(missing_ok=True)

    def test_missing_script_file_user_error(self):
        r = run_cli("run-script", "Z:\\does\\not\\exist.py", "--json")
        self.assertEqual(r.code, 2)
        envelope = json.loads(r.stderr)
        self.assertEqual(envelope["error"]["code"], "user_error")

    def test_timeout_kills_script(self):
        script = _write_script("""
            import time
            time.sleep(30)
        """)
        try:
            r = run_cli("run-script", str(script), "--timeout", "1", "--json")
            self.assertEqual(r.code, 5)
            envelope = json.loads(r.stderr)
            self.assertEqual(envelope["error"]["code"], "timeout")
        finally:
            script.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
