"""
Protocol Specification Conformance Rules (2026-07-28).
"""

from typing import Any, Dict, List, Optional
from .base import AuditCategory, AuditResult, AuditStatus
from ..rpc.transport import StdioTransport
from ..rpc.protocol import build_initialize_params, LATEST_PROTOCOL_VERSION


def audit_spec_conformance(transport: StdioTransport) -> List[AuditResult]:
    """Runs standard MCP protocol conformance checks."""
    results: List[AuditResult] = []

    # 1. Initialize Handshake
    transport.send_request("initialize", build_initialize_params(), req_id=1)
    init_resp, raw_init = transport.receive_response(timeout=4.0)

    if not init_resp:
        results.append(AuditResult(
            rule_id="MCP-SPEC-001",
            name="Initialize Handshake",
            category=AuditCategory.SPEC,
            status=AuditStatus.FAIL,
            message="Server failed to respond to 'initialize' request within 4.0s.",
            remediation="Ensure the server implements the MCP JSON-RPC 'initialize' handler and writes to stdout."
        ))
        return results

    if "error" in init_resp:
        results.append(AuditResult(
            rule_id="MCP-SPEC-001",
            name="Initialize Handshake",
            category=AuditCategory.SPEC,
            status=AuditStatus.FAIL,
            message=f"Server returned error on 'initialize': {init_resp['error']}",
            remediation="Fix initialization failure in server code."
        ))
        return results

    init_res = init_resp.get("result", {})
    proto_ver = init_res.get("protocolVersion")
    capabilities = init_res.get("capabilities", {})
    server_info = init_res.get("serverInfo", {})

    has_valid_info = bool(server_info.get("name"))
    if has_valid_info and proto_ver:
        results.append(AuditResult(
            rule_id="MCP-SPEC-001",
            name="Initialize Handshake",
            category=AuditCategory.SPEC,
            status=AuditStatus.PASS,
            message=f"Server initialized successfully as '{server_info.get('name')} v{server_info.get('version')}' (Protocol: {proto_ver}).",
            evidence={"serverInfo": server_info, "protocolVersion": proto_ver}
        ))
    else:
        results.append(AuditResult(
            rule_id="MCP-SPEC-001",
            name="Initialize Handshake",
            category=AuditCategory.SPEC,
            status=AuditStatus.WARN,
            message=f"Server returned partial initialization result (missing name or protocolVersion).",
            remediation="Include 'serverInfo.name' and 'protocolVersion' in initialize response.",
            evidence=init_res
        ))

    # Send notifications/initialized
    transport.send_notification("notifications/initialized")

    # 2. Ping Check
    transport.send_request("ping", {}, req_id=2)
    ping_resp, _ = transport.receive_response(timeout=2.0)
    if ping_resp and "result" in ping_resp:
        results.append(AuditResult(
            rule_id="MCP-SPEC-002",
            name="Ping Health Check",
            category=AuditCategory.SPEC,
            status=AuditStatus.PASS,
            message="Server correctly responded to 'ping' request."
        ))
    else:
        results.append(AuditResult(
            rule_id="MCP-SPEC-002",
            name="Ping Health Check",
            category=AuditCategory.SPEC,
            status=AuditStatus.WARN,
            message="Server does not implement or failed to respond to 'ping'.",
            remediation="Implement standard 'ping' handler returning empty result '{}'."
        ))

    # 3. Tools List Check
    if "tools" in capabilities:
        transport.send_request("tools/list", {}, req_id=3)
        tools_resp, _ = transport.receive_response(timeout=4.0)
        if tools_resp and "result" in tools_resp and "tools" in tools_resp["result"]:
            tools = tools_resp["result"]["tools"]
            valid = all(isinstance(t, dict) and "name" in t and "inputSchema" in t for t in tools)
            if valid:
                results.append(AuditResult(
                    rule_id="MCP-SPEC-003",
                    name="Tools List Conformance",
                    category=AuditCategory.SPEC,
                    status=AuditStatus.PASS,
                    message=f"Server declared {len(tools)} compliant tools.",
                    evidence={"tool_count": len(tools), "tool_names": [t["name"] for t in tools]}
                ))
            else:
                results.append(AuditResult(
                    rule_id="MCP-SPEC-003",
                    name="Tools List Conformance",
                    category=AuditCategory.SPEC,
                    status=AuditStatus.FAIL,
                    message="One or more tools in 'tools/list' missing required 'name' or 'inputSchema'.",
                    remediation="Ensure all tools provide string 'name' and object 'inputSchema'."
                ))
        else:
            results.append(AuditResult(
                rule_id="MCP-SPEC-003",
                name="Tools List Conformance",
                category=AuditCategory.SPEC,
                status=AuditStatus.FAIL,
                message="Server declared 'tools' capability but failed to respond to 'tools/list'.",
                remediation="Implement 'tools/list' handler returning a list of tools."
            ))

    return results
