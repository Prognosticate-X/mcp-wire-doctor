"""
CLI entry point for mcp-wire-doctor.
"""

import argparse
import json
import sys
from typing import Optional

from .rpc.transport import StdioTransport
from .audits.base import AuditSuiteResult, AuditStatus
from .audits.spec import audit_spec_conformance
from .audits.zod_compat import audit_claude_code_compatibility
from .audits.determinism import audit_cache_determinism
from .audits.security import audit_security_and_stream
from .reporter.markdown import print_cli_report, generate_markdown_report


def run_full_audit(command: str) -> AuditSuiteResult:
    """Spawns server and executes all test suites sequentially."""
    transport = StdioTransport(command)
    suite = AuditSuiteResult(command)

    try:
        transport.start()

        # 1. Spec Conformance
        for r in audit_spec_conformance(transport):
            suite.add(r)

        # 2. Claude Code Zod Compatibility
        for r in audit_claude_code_compatibility(transport):
            suite.add(r)

        # 3. Prompt Cache Determinism
        for r in audit_cache_determinism(transport):
            suite.add(r)

        # 4. Security & Stdio Stream Hygiene
        for r in audit_security_and_stream(transport):
            suite.add(r)

    finally:
        transport.close()

    return suite


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-wire-doctor",
        description="Automated wire-level conformance, compatibility, and security auditor for MCP servers."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. Audit
    audit_parser = subparsers.add_parser("audit", help="Audit an MCP server process over stdio")
    audit_parser.add_argument("--command", "-c", type=str, required=True, help="Command to run the MCP server (e.g. 'python server.py' or 'node server.js')")
    audit_parser.add_argument("--out", "-o", type=str, default=None, help="Save markdown audit report to file")
    audit_parser.add_argument("--json", action="store_true", help="Output audit results as raw JSON")
    audit_parser.add_argument("--fail-on-error", action="store_true", default=True, help="Exit with non-zero exit code if failures are found")

    args = parser.parse_args()

    if args.subcommand == "audit":
        suite = run_full_audit(args.command)

        if args.json:
            data = {
                "target_command": suite.target_command,
                "score": suite.score,
                "pass_count": suite.pass_count,
                "warn_count": suite.warn_count,
                "fail_count": suite.fail_count,
                "results": [r.to_dict() for r in suite.results]
            }
            print(json.dumps(data, indent=2))
        else:
            print_cli_report(suite)

        if args.out:
            md = generate_markdown_report(suite)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Report saved to: {args.out}", file=sys.stderr)

        if args.fail_on_error and suite.fail_count > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
