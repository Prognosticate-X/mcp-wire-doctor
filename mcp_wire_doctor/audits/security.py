"""
Security and Stdio Stream Hygiene rules (CVE-2026 Radar & Stream Sanitation).
"""

from typing import Any, Dict, List, Optional
from .base import AuditCategory, AuditResult, AuditStatus
from ..rpc.transport import StdioTransport


def audit_security_and_stream(transport: StdioTransport) -> List[AuditResult]:
    """Audits stdio channel cleanliness and cache scope leakage risks."""
    results: List[AuditResult] = []

    # 1. Stdio Stream Sanitation (Detect stdout pollution)
    pollutions = transport.stdout_pollutions
    if not pollutions:
        results.append(AuditResult(
            rule_id="SEC-STREAM-001",
            name="Stdio Stream Hygiene",
            category=AuditCategory.SECURITY,
            status=AuditStatus.PASS,
            message="Stdout is clean. All emitted lines conformed to valid JSON-RPC framing."
        ))
    else:
        results.append(AuditResult(
            rule_id="SEC-STREAM-001",
            name="Stdio Stream Hygiene",
            category=AuditCategory.SECURITY,
            status=AuditStatus.FAIL,
            message=(
                f"Stdout pollution detected ({len(pollutions)} non-JSON lines). "
                f"Printing logs or diagnostics directly to stdout breaks MCP client parsing."
            ),
            remediation="Redirect all server logs, warnings, and debug traces to stderr (stderr is the designated log channel).",
            evidence={"sample_pollutions": pollutions[:3]}
        ))

    # 2. Cache Scope Information Disclosure Check
    # (Testing for sensitive tokens declared under global cache scope)
    transport.send_request("resources/list", {}, req_id=30)
    resp, _ = transport.receive_response(timeout=3.0)

    if resp and "result" in resp and "resources" in resp["result"]:
        resources = resp["result"]["resources"]
        leaking_resources = []
        for r in resources:
            if not isinstance(r, dict):
                continue
            uri = r.get("uri", "")
            scope = r.get("cache", {}).get("cacheScope", "global") if isinstance(r.get("cache"), dict) else "global"
            # Flag if session/token keywords appear in global cacheable URIs
            lower_uri = uri.lower()
            if scope == "global" and any(k in lower_uri for k in ["token=", "session=", "key=", "auth="]):
                leaking_resources.append(uri)

        if leaking_resources:
            results.append(AuditResult(
                rule_id="SEC-CACHE-002",
                name="Cache Scope Information Disclosure",
                category=AuditCategory.SECURITY,
                status=AuditStatus.FAIL,
                message="Resource URIs with session/auth tokens declared under global cache scope (CVE-2026-radar risk).",
                remediation="Change resource cacheScope to 'session' or 'user', or redact auth parameters from URIs.",
                evidence=leaking_resources
            ))
        else:
            results.append(AuditResult(
                rule_id="SEC-CACHE-002",
                name="Cache Scope Information Disclosure",
                category=AuditCategory.SECURITY,
                status=AuditStatus.PASS,
                message="No sensitive credentials or session tokens detected in global cache scopes."
            ))

    return results
