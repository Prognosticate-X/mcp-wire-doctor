"""
Prompt Cache Determinism Audit: Verifies byte-level wire stability across repeated queries.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional
from .base import AuditCategory, AuditResult, AuditStatus
from ..rpc.transport import StdioTransport


def hash_raw_bytes(text: str) -> str:
    """Compute SHA-256 of raw serialized string."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def audit_cache_determinism(transport: StdioTransport, iterations: int = 3) -> List[AuditResult]:
    """
    Queries tools/list multiple times and checks if raw wire bytes are 100% stable.
    Detects random key ordering or dynamic leakages that invalidate LLM prompt caches.
    """
    results: List[AuditResult] = []
    hashes: List[str] = []
    raw_responses: List[str] = []

    for i in range(iterations):
        transport.send_request("tools/list", {}, req_id="cache_probe")
        parsed, raw = transport.receive_response(timeout=3.0)
        if raw is not None:
            raw_responses.append(raw)
            # Hash the raw line directly since req_id is identical
            hashes.append(hash_raw_bytes(raw))

    if len(hashes) < 2:
        return results

    if all(h == hashes[0] for h in hashes):
        results.append(AuditResult(
            rule_id="CACHE-DET-001",
            name="Tool Schema Wire Determinism",
            category=AuditCategory.PROMPT_CACHE,
            status=AuditStatus.PASS,
            message=f"Tools list serialization is 100% deterministic across {iterations} queries (SHA-256 prefix stable).",
            evidence={"sha256": hashes[0][:16], "iterations": iterations}
        ))
    else:
        results.append(AuditResult(
            rule_id="CACHE-DET-001",
            name="Tool Schema Wire Determinism",
            category=AuditCategory.PROMPT_CACHE,
            status=AuditStatus.FAIL,
            message=(
                "Non-deterministic serialization detected! Tool definitions produced differing raw "
                "byte streams across identical queries. This will destroy client prompt caches (0% hit rate)."
            ),
            remediation="Enforce deterministic dictionary sorting in server JSON serialization before writing to stdout.",
            evidence={"hashes": [h[:16] for h in hashes]}
        ))

    return results
