"""
Generates rich terminal summaries and GitHub Flavored Markdown audit reports.
"""

import sys
from typing import List
from ..audits.base import AuditSuiteResult, AuditStatus, AuditCategory


def print_cli_report(suite: AuditSuiteResult) -> None:
    """Print clean, high-visibility colored output to terminal."""
    score_color = "\033[1;32m" if suite.score >= 90 else ("\033[1;33m" if suite.score >= 70 else "\033[1;31m")

    print(f"\n\033[1;36m=====================================================\033[0m")
    print(f"\033[1;37m  mcp-wire-doctor: Automated Conformance & Wire Audit\033[0m")
    print(f"\033[1;36m=====================================================\033[0m")
    print(f"  • Target Server:   \033[1;33m{suite.target_command}\033[0m")
    print(f"  • Overall Health:  {score_color}{suite.score}/100\033[0m ({suite.pass_count} passed, {suite.warn_count} warned, {suite.fail_count} failed)\n")

    for res in suite.results:
        if res.status == AuditStatus.PASS:
            icon = "\033[1;32m✓ PASS\033[0m"
        elif res.status == AuditStatus.WARN:
            icon = "\033[1;33m▲ WARN\033[0m"
        else:
            icon = "\033[1;31m✗ FAIL\033[0m"

        print(f"  {icon} \033[1m[{res.rule_id}]\033[0m {res.name} \033[90m({res.category.value})\033[0m")
        print(f"         \033[90m↳ {res.message}\033[0m")
        if res.remediation and res.status != AuditStatus.PASS:
            print(f"         \033[36m💡 Remediation: {res.remediation}\033[0m")
    print("")


def generate_markdown_report(suite: AuditSuiteResult) -> str:
    """Generate structured Markdown document suitable for PR reviews or issue reports."""
    status_badge = "🟢 100% Compliant" if suite.score == 100 else ("🟡 Warnings Detected" if suite.score >= 70 else "🔴 Critical Issues Found")

    lines = [
        f"# MCP Server Conformance & Wire Audit Report",
        "",
        f"> **Target Process**: `{suite.target_command}`  ",
        f"> **Audit Score**: **{suite.score}/100** ({status_badge})  ",
        f"> **Results**: `{suite.pass_count}` Passed, `{suite.warn_count}` Warnings, `{suite.fail_count}` Failed",
        "",
        "## 1. Compliance Matrix",
        "",
        "| Rule ID | Category | Name | Status | Summary |",
        "| :--- | :--- | :--- | :---: | :--- |"
    ]

    for res in suite.results:
        icon = "🟢 PASS" if res.status == AuditStatus.PASS else ("🟡 WARN" if res.status == AuditStatus.WARN else "🔴 FAIL")
        lines.append(f"| `{res.rule_id}` | {res.category.value} | {res.name} | **{icon}** | {res.message} |")

    lines.extend([
        "",
        "## 2. Detailed Findings & Remediation",
        ""
    ])

    non_pass = [r for r in suite.results if r.status != AuditStatus.PASS]
    if not non_pass:
        lines.append("🎉 **No issues detected!** Server demonstrates full compliance with MCP protocol 2026-07-28, Claude Code Zod validator, and deterministic Prompt Caching.")
    else:
        for r in non_pass:
            lines.extend([
                f"### [{r.rule_id}] {r.name}",
                f"- **Status**: `{r.status.value}`",
                f"- **Category**: {r.category.value}",
                f"- **Problem**: {r.message}",
                f"- **Remediation**: `{r.remediation}`" if r.remediation else "",
                ""
            ])

    lines.extend([
        "---",
        "*Generated automatically by [mcp-wire-doctor](https://github.com/Prognosticate-X/mcp-wire-doctor).*"
    ])

    return "\n".join(lines)
