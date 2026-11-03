"""
Model Context Protocol (MCP) message builders and schemas across protocol revisions.
"""

from typing import Any, Dict, List, Optional

LATEST_PROTOCOL_VERSION = "2026-07-28"
LEGACY_PROTOCOL_VERSION = "2024-11-05"


def build_initialize_params(
    client_name: str = "mcp-wire-doctor",
    client_version: str = "1.0.0",
    protocol_version: str = LATEST_PROTOCOL_VERSION
) -> Dict[str, Any]:
    """Constructs a compliant initialize params payload."""
    return {
        "protocolVersion": protocol_version,
        "capabilities": {
            "roots": {"listChanged": True},
            "sampling": {}
        },
        "clientInfo": {
            "name": client_name,
            "version": client_version
        }
    }
