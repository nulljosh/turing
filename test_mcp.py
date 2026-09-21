"""The MCP server answers a real client conversation. Runs headless, no model, no app."""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def talk(*messages):
    """Send messages to a fresh server process and return its replies."""
    p = subprocess.run([sys.executable, os.path.join(HERE, "mcp_server.py")], input="\n".join(json.dumps(m) for m in messages) + "\n",
                       capture_output=True, text=True, timeout=60, env={**os.environ, "SAMANTHA_HEADLESS": "1"})
    return [json.loads(line) for line in p.stdout.splitlines()]


class McpTests(unittest.TestCase):
    """initialize, list, call, and the ways a call can go wrong."""

    def test_conversation(self):
        """Conversation."""
        r = talk({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
                 {"jsonrpc": "2.0", "method": "notifications/initialized"},
                 {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                 {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "calculate", "arguments": {"expression": "17*23"}}},
                 {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "run_shortcut", "arguments": {"name": "x"}}},
                 {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}},
                 {"jsonrpc": "2.0", "id": 6, "method": "bogus"})
        self.assertEqual([x["id"] for x in r], [1, 2, 3, 4, 5, 6])  # the notification got no reply
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-03-26")
        names = [t["name"] for t in r[1]["result"]["tools"]]
        self.assertIn("calculate", names)
        self.assertGreater(len(names), 50)
        for hidden in ("run_shortcut", "copy_to_clipboard", "sleep_display"):
            self.assertNotIn(hidden, names)
        calc = [t for t in r[1]["result"]["tools"] if t["name"] == "calculate"][0]
        self.assertEqual(calc["inputSchema"]["required"], ["expression"])
        self.assertEqual(r[2]["result"], {"content": [{"type": "text", "text": "391"}], "isError": False})
        self.assertTrue(r[3]["result"]["isError"] and r[4]["result"]["isError"])
        self.assertEqual(r[5]["error"]["code"], -32601)

    def test_garbage_does_not_kill_the_server(self):
        """Garbage does not kill the server."""
        p = subprocess.run([sys.executable, os.path.join(HERE, "mcp_server.py")], input='not json\n{"jsonrpc":"2.0","id":1,"method":"ping"}\n',
                           capture_output=True, text=True, timeout=60)
        replies = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["result"], {})


class ClientTests(unittest.TestCase):
    """She calls MCP servers too: here she calls her own, which is the whole loop in one test."""

    def setUp(self):
        """A config with one server, her own mcp_server.py, and the client pointed at it."""
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.cfg = os.path.join(self.dir, "mcp.json")
        json.dump({"servers": {"samantha": [sys.executable, os.path.join(HERE, "mcp_server.py")], "broken": ["/nonexistent/server"]}}, open(self.cfg, "w"))
        os.environ["SAMANTHA_MCP_CONFIG"] = self.cfg
        os.environ["SAMANTHA_HEADLESS"] = "1"
        sys.path.insert(0, HERE)
        import tools_util
        self.u = tools_util

    def tearDown(self):
        """Forget the temporary config."""
        os.environ.pop("SAMANTHA_MCP_CONFIG", None)

    def test_lists_the_servers_tools(self):
        """list_mcp_tools shows her own server's tools and says which server is unavailable."""
        out = self.u.list_mcp_tools()
        self.assertIn("samantha: ", out)
        self.assertIn("open_app", out)
        self.assertRegex(out, r"and \d+ more")  # the list stops at 30 tools
        self.assertIn("broken: unavailable", out)

    def test_calls_a_tool(self):
        """A call goes out over MCP and the text comes back."""
        self.assertEqual(self.u.call_mcp_tool('samantha calculate {"expression": "17*23"}'), "391")

    def test_the_ways_a_call_fails(self):
        """A missing server, bad JSON, a hidden tool, a dead server and a missing tool each answer in words."""
        self.assertIn("do not have an MCP server called nope", self.u.call_mcp_tool("nope calculate {}"))
        self.assertIn("not a JSON object", self.u.call_mcp_tool("samantha calculate [1]"))
        self.assertIn("No tool named run_shortcut", self.u.call_mcp_tool('samantha run_shortcut {"name": "x"}'))
        self.assertIn("broken said no", self.u.call_mcp_tool("broken calculate {}"))
        self.assertTrue(self.u.call_mcp_tool("samantha").startswith("Say it like"))

    def test_no_config_says_so(self):
        """With no config file she says how to add one."""
        os.environ["SAMANTHA_MCP_CONFIG"] = os.path.join(self.dir, "missing.json")
        self.assertIn("No MCP servers configured", self.u.list_mcp_tools())

    def test_it_is_a_write_and_hidden(self):
        """Calling someone else's tool asks first and never reaches a model."""
        import tools
        self.assertIn("call_mcp_tool", tools.WRITES)
        self.assertIn("call_mcp_tool", tools.NOT_FOR_MODELS)


if __name__ == "__main__":
    unittest.main()
