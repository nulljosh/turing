#!/usr/bin/env python3
"""Samantha's hands over MCP, so any assistant can use them.

A stdio MCP server: newline-delimited JSON-RPC on stdin and stdout, standard library
only. It serves every tool in tools.TOOLS except the ones that fire a side effect
nobody asked to see (NOT_FOR_MODELS: running a Shortcut, writing the clipboard,
blanking the screen). Those stay behind her own command line until the harness can
ask first. Point a client at it, for example in Claude Code:

    claude mcp add samantha -- python3 /path/to/turing/mcp_server.py
"""
import json
import sys

import tools

PROTOCOL = "2024-11-05"


def _tools():
    """The tools a client may call, in MCP's shape."""
    out = []
    for name, fn in tools.TOOLS.items():
        if name in tools.NOT_FOR_MODELS:
            continue
        schema = tools._schema(fn)["function"]
        out.append({"name": name, "description": schema["description"], "inputSchema": schema["parameters"]})
    return out


def call(name, arguments):
    """Run one tool and return MCP's result object. Errors come back as text with isError set, never as a crash."""
    fn = tools.TOOLS.get(name)
    if not fn or name in tools.NOT_FOR_MODELS:
        return {"content": [{"type": "text", "text": f"No tool named {name}."}], "isError": True}
    takes = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    try:
        text = str(fn(**{k: str(v) for k, v in (arguments or {}).items() if k in takes}))
    except Exception as e:
        return {"content": [{"type": "text", "text": f"{name} failed: {e}"}], "isError": True}
    return {"content": [{"type": "text", "text": text}], "isError": False}


def handle(msg):
    """One JSON-RPC message in, the reply out (None for a notification)."""
    method, ident = msg.get("method"), msg.get("id")
    if ident is None:
        return None
    if method == "initialize":
        result = {"protocolVersion": (msg.get("params") or {}).get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
                  "serverInfo": {"name": "samantha", "version": open(tools.os.path.join(tools.os.path.dirname(tools.os.path.abspath(__file__)), "VERSION")).read().strip()}}
    elif method == "tools/list":
        result = {"tools": _tools()}
    elif method == "tools/call":
        p = msg.get("params") or {}
        result = call(p.get("name", ""), p.get("arguments"))
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"Unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def main():
    """Read requests until stdin closes."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
