#!/usr/bin/env python3
"""
A faulty mock MCP server simulating real-world bugs:
1. Prints raw debug logs to stdout (violating JSON-RPC framing)
2. Missing required fields in inputSchema (triggers Claude Code Zod drop #88128)
3. Non-deterministic timestamps in tools list (destroys prompt cache)
"""
import sys
import json
import time

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            msg = json.loads(line.strip())
        except Exception:
            continue
        method = msg.get("method")
        req_id = msg.get("id")

        if method == "initialize":
            # BUG 1: Polluting stdout with a print statement!
            sys.stdout.write("[DEBUG] Server initializing at port 0\n")
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "faulty-mcp-server", "version": "0.1.0"}
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/list":
            # BUG 2: Dynamic timestamp destroying prompt cache & inputSchema type not 'object'
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "broken_tool",
                            "description": f"Query timestamp: {time.time()}",
                            "inputSchema": {
                                "type": "string"  # INVALID: must be "object"
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "resources/list":
            # BUG 3: Sensitive session token in global cache scope
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {
                            "uri": "api://users/current?token=secret123",
                            "name": "User Profile",
                            "cache": {"cacheScope": "global"}
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
