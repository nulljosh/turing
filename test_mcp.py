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


if __name__ == "__main__":
    unittest.main()
