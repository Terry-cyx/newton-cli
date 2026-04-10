"""Phase 0 acceptance tests: introspection commands.

Each test invokes newton-cli via subprocess and asserts the contract documented
in prompts/cli_anything_bootstrap.md and CLAUDE.md.
"""

from __future__ import annotations

import unittest

from tests._cli import run_cli

SCHEMA = "newton-cli/v1"


class TestVersion(unittest.TestCase):
    def test_version_human_exits_zero(self):
        r = run_cli("version")
        self.assertEqual(r.code, 0, msg=r.stderr)
        self.assertIn("newton", r.stdout.lower())

    def test_version_json_envelope(self):
        r = run_cli("version", "--json", check=True)
        payload = r.json()
        self.assertEqual(payload["schema"], SCHEMA)
        data = payload["data"]
        self.assertIn("newton", data)
        self.assertIn("warp", data)
        self.assertIn("python", data)
        self.assertIn("newton_cli", data)


class TestDevicesList(unittest.TestCase):
    def test_devices_list_json(self):
        r = run_cli("devices", "list", "--json", check=True)
        payload = r.json()
        self.assertEqual(payload["schema"], SCHEMA)
        devices = payload["data"]["devices"]
        self.assertIsInstance(devices, list)
        self.assertGreaterEqual(len(devices), 1)
        # Every device entry has at least these keys.
        for d in devices:
            self.assertIn("name", d)
            self.assertIn("kind", d)  # 'cpu' or 'cuda'
        # CPU is always present.
        self.assertTrue(any(d["kind"] == "cpu" for d in devices))


class TestApiList(unittest.TestCase):
    def test_api_list_all_modules(self):
        r = run_cli("api", "list", "--json", check=True)
        payload = r.json()
        self.assertEqual(payload["schema"], SCHEMA)
        symbols = payload["data"]["symbols"]
        self.assertIsInstance(symbols, list)
        # ModelBuilder is the canonical public symbol everyone uses.
        names = {(s["module"], s["name"]) for s in symbols}
        self.assertIn(("newton", "ModelBuilder"), names)
        self.assertIn(("newton", "Model"), names)
        self.assertIn(("newton", "State"), names)

    def test_api_list_module_filter(self):
        r = run_cli("api", "list", "--module", "newton.geometry", "--json", check=True)
        payload = r.json()
        symbols = payload["data"]["symbols"]
        self.assertTrue(symbols, "newton.geometry should expose at least one symbol")
        for s in symbols:
            self.assertEqual(s["module"], "newton.geometry")

    def test_api_list_rejects_private_module(self):
        r = run_cli("api", "list", "--module", "newton._src", "--json")
        self.assertEqual(r.code, 2)
        err = run_cli("api", "list", "--module", "newton._src", "--json").stderr
        self.assertIn("_src", err)


class TestApiDescribe(unittest.TestCase):
    def test_describe_modelbuilder(self):
        r = run_cli("api", "describe", "ModelBuilder", "--json", check=True)
        payload = r.json()
        data = payload["data"]
        self.assertEqual(data["name"], "ModelBuilder")
        self.assertEqual(data["module"], "newton")
        self.assertIn("doc", data)

    def test_describe_dotted_path(self):
        r = run_cli("api", "describe", "geometry.GeoType", "--json", check=True)
        payload = r.json()
        self.assertEqual(payload["data"]["name"], "GeoType")

    def test_describe_unknown_symbol(self):
        r = run_cli("api", "describe", "ThisDoesNotExist", "--json")
        self.assertEqual(r.code, 2, msg=r.stdout + r.stderr)

    def test_describe_refuses_private(self):
        r = run_cli("api", "describe", "_src.sim.SomePrivate", "--json")
        self.assertEqual(r.code, 2)


class TestExamplesList(unittest.TestCase):
    def test_examples_list_contains_basic_pendulum(self):
        r = run_cli("examples", "list", "--json", check=True)
        payload = r.json()
        examples = payload["data"]["examples"]
        names = {e["name"] for e in examples}
        self.assertIn("basic_pendulum", names)
        self.assertIn("basic_shapes", names)


class TestExamplesDescribe(unittest.TestCase):
    def test_describe_basic_pendulum(self):
        r = run_cli("examples", "describe", "basic_pendulum", "--json", check=True)
        payload = r.json()
        data = payload["data"]
        self.assertEqual(data["name"], "basic_pendulum")
        self.assertIn("doc", data)
        self.assertIn("flags", data)
        flag_names = {f["name"] for f in data["flags"]}
        self.assertIn("--num-frames", flag_names)

    def test_describe_unknown_example(self):
        r = run_cli("examples", "describe", "definitely_not_an_example", "--json")
        self.assertEqual(r.code, 2)


class TestExitCodeContract(unittest.TestCase):
    def test_unknown_top_level_command(self):
        r = run_cli("not-a-command")
        self.assertEqual(r.code, 2)


if __name__ == "__main__":
    unittest.main()
