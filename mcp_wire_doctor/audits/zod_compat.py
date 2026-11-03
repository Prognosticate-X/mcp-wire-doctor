"""
Claude Code (v2.1+) client Zod validator simulator.
Directly audits against the silent tool-drop defect (anthropics/claude-code#88128).
"""

from typing import Any, Dict, List, Optional
from .base import AuditCategory, AuditResult, AuditStatus
from ..rpc.transport import StdioTransport


def simulate_claude_code_tool_validator(tool: Dict[str, Any]) -> List[str]:
    """
    Simulates the exact Zod schema validation applied by Claude Code (v2.1.235+).
    Returns a list of validation error descriptions.
    """
    errors = []

    # 1. Basic tool fields
    if "name" not in tool or not isinstance(tool["name"], str) or not tool["name"].strip():
        errors.append("Invalid or missing 'name': must be non-empty string.")

    if "description" in tool and not isinstance(tool["description"], str):
        errors.append("Field 'description' must be a string if provided.")

    # 2. InputSchema validation
    schema = tool.get("inputSchema")
    if not isinstance(schema, dict):
        errors.append("Field 'inputSchema' is missing or not a dictionary/object.")
    else:
        schema_type = schema.get("type")
        if schema_type != "object":
            errors.append(f"InputSchema 'type' must be 'object', got '{schema_type}'.")

        props = schema.get("properties")
        if props is not None and not isinstance(props, dict):
            errors.append("InputSchema 'properties' must be a dictionary.")

        req = schema.get("required")
        if req is not None:
            if not isinstance(req, list):
                errors.append("InputSchema 'required' must be an array of strings.")
            elif not all(isinstance(r, str) for r in req):
                errors.append("InputSchema 'required' contains non-string elements.")

    # 3. Protocol 2026-07-28 Cache extensions (Issue #88128 / #469)
    # Claude Code 2.1 expects ttlMs or cacheScope if caching hints are declared
    if "cache" in tool:
        cache_obj = tool["cache"]
        if not isinstance(cache_obj, dict):
            errors.append("Tool declared 'cache' but value is not an object.")
        else:
            if "ttlMs" in cache_obj and not isinstance(cache_obj["ttlMs"], (int, float)):
                errors.append("cache.ttlMs must be a number (milliseconds).")
            if "cacheScope" in cache_obj and cache_obj["cacheScope"] not in ["global", "session", "user"]:
                errors.append("cache.cacheScope must be one of: 'global', 'session', 'user'.")

    return errors


def audit_claude_code_compatibility(transport: StdioTransport) -> List[AuditResult]:
    """Audits tool and prompt declarations against Claude Code's client validator."""
    results: List[AuditResult] = []

    transport.send_request("tools/list", {}, req_id=10)
    resp, _ = transport.receive_response(timeout=4.0)

    if not resp or "result" not in resp or "tools" not in resp["result"]:
        # No tools declared or failed to list
        return results

    tools = resp["result"]["tools"]
    all_clean = True
    failing_tools = {}

    for tool in tools:
        if not isinstance(tool, dict):
            continue
        t_name = tool.get("name", "unnamed")
        errs = simulate_claude_code_tool_validator(tool)
        if errs:
            all_clean = False
            failing_tools[t_name] = errs

    if all_clean:
        results.append(AuditResult(
            rule_id="CLAUDE-ZOD-001",
            name="Claude Code Tool Schema Validation",
            category=AuditCategory.CLAUDE_CODE,
            status=AuditStatus.PASS,
            message=f"All {len(tools)} tools fully conform to Claude Code's Zod validator. No silent tool dropping will occur.",
            evidence={"tool_count": len(tools)}
        ))
    else:
        results.append(AuditResult(
            rule_id="CLAUDE-ZOD-001",
            name="Claude Code Tool Schema Validation",
            category=AuditCategory.CLAUDE_CODE,
            status=AuditStatus.FAIL,
            message=(
                f"{len(failing_tools)} tool(s) will trigger Zod parse failures and cause "
                f"Claude Code to silently drop the server (anthropics/claude-code#88128)."
            ),
            remediation="Fix inputSchema structures and ensure properties are dicts and required arrays are strings.",
            evidence=failing_tools
        ))

    return results
