"""
Base audit types, status codes, and aggregator.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class AuditStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


class AuditCategory(str, Enum):
    SPEC = "Protocol Spec (2026-07-28)"
    CLAUDE_CODE = "Claude Code (v2.1+) Compatibility"
    PROMPT_CACHE = "Prompt Cache Determinism"
    SECURITY = "Security & Stream Hygiene"


class AuditResult:
    """Individual test case finding."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        category: AuditCategory,
        status: AuditStatus,
        message: str,
        remediation: Optional[str] = None,
        evidence: Optional[Any] = None
    ):
        self.rule_id = rule_id
        self.name = name
        self.category = category
        self.status = status
        self.message = message
        self.remediation = remediation
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "remediation": self.remediation,
            "evidence": self.evidence
        }


class AuditSuiteResult:
    """Aggregates all results for an MCP server audit run."""

    def __init__(self, target_command: str):
        self.target_command = target_command
        self.results: List[AuditResult] = []

    def add(self, result: AuditResult) -> None:
        self.results.append(result)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == AuditStatus.PASS)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == AuditStatus.WARN)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == AuditStatus.FAIL)

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def score(self) -> int:
        """Score from 0 to 100."""
        if not self.results:
            return 100
        # Fail = 0 pts, Warn = 50 pts, Pass = 100 pts
        points = sum(100 if r.status == AuditStatus.PASS else (50 if r.status == AuditStatus.WARN else 0) for r in self.results)
        return int(points / len(self.results))
