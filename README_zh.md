# mcp-wire-doctor 🩺

[![CI](https://github.com/Prognosticate-X/mcp-wire-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/Prognosticate-X/mcp-wire-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0-success.svg)](pyproject.toml)

> **零依赖的 Model Context Protocol (MCP) 线路级规范合规性、客户端兼容性与安全审计工具。**  
> 专门解决 Claude Code 静默丢弃工具问题（[anthropics/claude-code#88128](https://github.com/anthropics/claude-code/issues/88128)）、防止 Schema 序列化乱序击穿大模型 Prompt Cache（[anomalyco/opencode#23571](https://github.com/anomalyco/opencode/issues/23571)）以及排查跨租户缓存泄露风险（[Danyw24/mcp-radar#162](https://github.com/Danyw24/mcp-radar/issues/162)）。

[English (US)](README.md) | [中文说明 (Chinese)](README_zh.md)

---

## ⚡ 为什么需要 `mcp-wire-doctor`？

随着 **Model Context Protocol (MCP)** 生态在多语言（Python FastMCP、Rust `rmcp`、TypeScript SDK、Go SDK）中极速普及，服务端在实现过程中常出现隐秘的“线路级（Wire-level）”缺陷。这些问题在本地单测中极难发现，却会在真实客户端中引发灾难性后果：

```
                    [ MCP Server Stdio 标准输入输出流 ]
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
   [ 静默丢弃全部工具 ]             [ 提示词缓存命中率归零 ]        [ JSON-RPC 帧被毁 ]
Claude Code 客户端 Zod 校验器       工具参数字典无序迭代，每次重连    在代码中随手 print() 调试日志
因缺少可选字段或类型不符，静默       输出的字节哈希发生变化，导致      直接输出到 stdout，导致所有
抛弃所有工具（Issue #88128）。      Prompt Cache 彻底失效。         客户端 JSON 解析器崩溃。
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                         [ 🩺 mcp-wire-doctor ]
                     端到端黑盒自动化线路级诊断体检
```

### 核心排查与审计领域：
1. **Claude Code (v2.1+) 客户端 Zod 校验陷阱（[#88128](https://github.com/anthropics/claude-code/issues/88128)）**：Claude Code 在客户端对 `tools/list` 启用了极其严苛的 Zod 校验。当服务端未严格遵循类型定义时，Claude Code 会在重试 4 次后**直接静默丢弃该 Server 的全部工具，且对用户与大模型完全无报错**。
2. **Prompt Cache 非确定性破坏（[#23571](https://github.com/anomalyco/opencode/issues/23571)）**：如果服务端在多次返回同一工具定义时，内部字典 key 顺序随机变动，会导致下游大模型的 Prompt Cache 前缀失效，产生高达 10 倍的 Token 额外开销与高额延迟。
3. **Stdio 标准输出污染**：使用 `print()` 或 `console.log()` 直接输出到 stdout（而非标准的 stderr），破坏以换行符分隔的 JSON-RPC 协议帧。
4. **缓存作用域信息泄露（[CVE-2026 Radar](https://github.com/Danyw24/mcp-radar/issues/162)）**：检测是否在 `global` 缓存作用域下声明了包含用户凭证、Token 或会话标识符的 URI。

---

## 🛠️ 自动化体检项目矩阵

| 规则编号 | 规则分类 | 项目名称 | 审计内容 |
| :--- | :--- | :--- | :--- |
| `MCP-SPEC-001` | 协议规范 | **Initialize 握手** | 验证 JSON-RPC 2.0 initialize 响应、protocolVersion 协商（`2026-07-28`）与 serverInfo。 |
| `MCP-SPEC-002` | 协议规范 | **Ping 健康检查** | 验证标准 ping 请求在超时时间内的合规响应。 |
| `MCP-SPEC-003` | 协议规范 | **Tools List 合规性** | 审计工具声明结构的完整性（`name`、`inputSchema` 结构）。 |
| `CLAUDE-ZOD-001`| 兼容性 | **Claude Code Zod 模拟**| 精确模拟 Claude Code 客户端校验逻辑，提前捕获静默丢工具缺陷。 |
| `CACHE-DET-001` | 提示词缓存 | **线路级确定性验证** | 连续多次查询工具集，比对 SHA-256 哈希，确保字节级 100% 稳定。 |
| `SEC-STREAM-001`| 安全与流卫生 | **Stdio 输出流清洁度** | 确保 stdout 中未混入任何非 JSON 日志行。 |
| `SEC-CACHE-002` | 安全与凭证 | **缓存作用域泄露风险** | 检测全局缓存资源中是否混入敏感鉴权参数。 |

---

## 🚀 快速上手

### 1. 免安装直接运行
基于 Python 3.9+ 标准库构建，无需安装任何第三方库：

```bash
git clone https://github.com/Prognosticate-X/mcp-wire-doctor.git
cd mcp-wire-doctor
./bin/mcp-wire-doctor --help
```

### 2. 体检任意 MCP 服务
只需将命令传入 `--command`：

```bash
# 审计 Python 编写的 MCP 服务：
./bin/mcp-wire-doctor audit --command "python3 server.py"

# 审计 Node / NPX 服务：
./bin/mcp-wire-doctor audit --command "npx -y @modelcontextprotocol/server-everything"

# 输出完整 Markdown 报告供 PR 审查：
./bin/mcp-wire-doctor audit --command "python3 server.py" --out audit_report.md
```

### 3. 终端诊断反馈演示
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

## 🔄 CI/CD 持续集成

可在 GitHub Actions 中加入质量门禁，防止低兼容性代码合并进主分支：

```yaml
- name: Audit MCP Server Conformance
  run: |
    python -m mcp_wire_doctor.cli audit --command "python src/server.py" --fail-on-error
```

---

## 🧪 运行单元测试

```bash
python3 -m unittest discover -s tests -v
```

---

## 📄 许可证

MIT © 2026 Prognosticate X
