#!/usr/bin/env python3
"""
A 100% compliant mock MCP server over stdio.
Responds to initialize, ping, tools/list with deterministic keys and valid schemas.
"""
import sys
import json

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        msg = json.loads(line.strip())
        method = msg.get("method")
        req_id = msg.get("id")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "perfect-mcp-server", "version": "1.0.0"}
                }
            }
            sys.stdout.write(json.dumps(resp, sort_keys=True) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            sys.stdout.write(json.dumps(resp, sort_keys=True) + "\n")
            sys.stdout.flush()

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "calculate_hash",
                            "description": "Calculates cryptographic hash of a string",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"input": {"type": "string"}},
                                "required": ["input"]
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(resp, sort_keys=True) + "\n")
            sys.stdout.flush()

        elif method == "resources/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
            sys.stdout.write(json.dumps(resp, sort_keys=True) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
