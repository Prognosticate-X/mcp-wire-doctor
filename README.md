# mcp-wire-doctor 🩺

[![CI](https://github.com/Prognosticate-X/mcp-wire-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/Prognosticate-X/mcp-wire-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0-success.svg)](pyproject.toml)

> **Zero-dependency wire-level conformance, compatibility, and security auditor for Model Context Protocol (MCP) servers and clients.**  
> Built to eliminate silent tool drops in Claude Code ([anthropics/claude-code#88128](https://github.com/anthropics/claude-code/issues/88128)), protect LLM prompt cache hit rates ([anomalyco/opencode#23571](https://github.com/anomalyco/opencode/issues/23571)), and audit cross-tenant cache disclosure risks ([Danyw24/mcp-radar#162](https://github.com/Danyw24/mcp-radar/issues/162)).

[English (US)](README.md) | [中文说明 (Chinese)](README_zh.md)

---

## ⚡ Why `mcp-wire-doctor`?

As the **Model Context Protocol (MCP)** ecosystem rapidly evolves across languages (Python FastMCP, Rust `rmcp`, TypeScript SDK, Go SDK), server implementations frequently trigger subtle wire-level failures that are completely invisible in local unit tests:

```
                  [ MCP Server Stdio Wire Stream ]
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
[ SILENT TOOL DROPS ]    [ CACHE HIT DESTROYED ]    [ STREAMS BROKEN ]
Claude Code v2.1 Zod     Non-deterministic dict     Raw print() statements
rejects optional fields  serialization shifts       emitted to stdout break
or non-object schemas    bytes across queries;      JSON-RPC framing for
([issue #88128]).        prompt cache drops to 0%.  all MCP clients.
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 ▼
                     [ 🩺 mcp-wire-doctor ]
               Automated Black-Box Diagnostic Battery
```

### Critical Problem Areas Audited:
1. **Claude Code (v2.1+) Client Zod Traps ([#88128](https://github.com/anthropics/claude-code/issues/88128))**: Claude Code applies strict client-side Zod validators to `tools/list`. If optional fields are omitted or `inputSchema` is improperly typed, Claude Code retries 4 times with exponential backoff and **silently drops the server's tools without surfacing an error to the user or model**.
2. **Prompt Cache Non-Determinism ([#23571](https://github.com/anomalyco/opencode/issues/23571))**: If dictionary keys in tool schemas iterate non-deterministically across re-queries, the LLM prompt cache prefix changes every time the agent reconnects, forcing full re-tokenization and 10x cost inflation.
3. **Stdio Stream Pollution**: Direct calls to `print()` or `console.log()` writing to `stdout` instead of `stderr` corrupt line-delimited JSON-RPC framing.
4. **Cache Scope Information Disclosure ([CVE-2026 Radar](https://github.com/Danyw24/mcp-radar/issues/162))**: Detects session tokens or user authentication credentials declared under `global` cache scopes.

---

## 🛠️ The Audit Battery

`mcp-wire-doctor` runs an automated black-box battery over your server's stdio transport:

| Rule ID | Category | Name | Diagnostic Description |
| :--- | :--- | :--- | :--- |
| `MCP-SPEC-001` | Protocol Spec | **Initialize Handshake** | Validates JSON-RPC 2.0 initialize response, protocolVersion negotiation (`2026-07-28`), and serverInfo. |
| `MCP-SPEC-002` | Protocol Spec | **Ping Health Check** | Verifies standard ping request response within timeout. |
| `MCP-SPEC-003` | Protocol Spec | **Tools List Conformance** | Audits tool declaration completeness (`name`, `inputSchema`). |
| `CLAUDE-ZOD-001`| Client Compat | **Claude Code Zod Check** | Simulates Claude Code 2.1's exact client-side Zod validator to detect silent tool drops. |
| `CACHE-DET-001` | Prompt Cache | **Wire Determinism** | Runs sequential queries to ensure bit-for-bit SHA-256 stability of tool schemas. |
| `SEC-STREAM-001`| Security | **Stdio Stream Hygiene** | Verifies zero non-JSON lines polluted the stdout stream. |
| `SEC-CACHE-002` | Security | **Cache Scope Disclosure** | Audits declared resources against credential leakage in global cache scopes. |

---

## 🚀 Quick Start

### 1. Zero-Install Execution
Runs directly using Python 3.9+ standard library without any dependencies:

```bash
git clone https://github.com/Prognosticate-X/mcp-wire-doctor.git
cd mcp-wire-doctor
./bin/mcp-wire-doctor --help
```

### 2. Audit Any MCP Server
Point `mcp-wire-doctor` to your server's start command:

```bash
# Audit a Python MCP server:
./bin/mcp-wire-doctor audit --command "python3 server.py"

# Audit a Node / NPX server:
./bin/mcp-wire-doctor audit --command "npx -y @modelcontextprotocol/server-everything"

# Generate a GitHub Markdown report for PR reviews:
./bin/mcp-wire-doctor audit --command "python3 server.py" --out audit_report.md
```

### 3. Sample Terminal Output
```text
=====================================================
  mcp-wire-doctor: Automated Conformance & Wire Audit
=====================================================
  • Target Server:   python3 server.py
  • Overall Health:  100/100 (7 passed, 0 warned, 0 failed)

  ✓ PASS [MCP-SPEC-001] Initialize Handshake (Protocol Spec (2026-07-28))
         ↳ Server initialized successfully as 'production-mcp v1.0.0' (Protocol: 2026-07-28).
  ✓ PASS [MCP-SPEC-002] Ping Health Check (Protocol Spec (2026-07-28))
         ↳ Server correctly responded to 'ping' request.
  ✓ PASS [MCP-SPEC-003] Tools List Conformance (Protocol Spec (2026-07-28))
         ↳ Server declared 4 compliant tools.
  ✓ PASS [CLAUDE-ZOD-001] Claude Code Tool Schema Validation (Claude Code (v2.1+) Compatibility)
         ↳ All 4 tools fully conform to Claude Code's Zod validator. No silent tool dropping will occur.
  ✓ PASS [CACHE-DET-001] Tool Schema Wire Determinism (Prompt Cache Determinism)
         ↳ Tools list serialization is 100% deterministic across 3 queries (SHA-256 prefix stable).
  ✓ PASS [SEC-STREAM-001] Stdio Stream Hygiene (Security & Stream Hygiene)
         ↳ Stdout is clean. All emitted lines conformed to valid JSON-RPC framing.
  ✓ PASS [SEC-CACHE-002] Cache Scope Information Disclosure (Security & Stream Hygiene)
         ↳ No sensitive credentials or session tokens detected in global cache scopes.
```

---

## 🔄 CI/CD Integration

Prevent regressions from reaching production by running `mcp-wire-doctor` in GitHub Actions:

```yaml
- name: Audit MCP Server Conformance
  run: |
    python -m mcp_wire_doctor.cli audit --command "python src/server.py" --fail-on-error
```

---

## 🧪 Testing

Run the zero-dependency test suite:

```bash
python3 -m unittest discover -s tests -v
```

---

## 📄 License

MIT © 2026 Prognosticate X
