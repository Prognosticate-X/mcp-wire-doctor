import unittest
from mcp_wire_doctor.audits.zod_compat import simulate_claude_code_tool_validator


class TestZodCompat(unittest.TestCase):
    def test_valid_tool_passes(self):
        valid_tool = {
            "name": "read_file",
            "description": "Reads a file",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
        errors = simulate_claude_code_tool_validator(valid_tool)
        self.assertEqual(len(errors), 0)

    def test_invalid_input_schema_type(self):
        broken_tool = {
            "name": "broken_tool",
            "inputSchema": {
                "type": "string"
            }
        }
        errors = simulate_claude_code_tool_validator(broken_tool)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("must be 'object'" in e for e in errors))

    def test_invalid_cache_scope(self):
        tool_with_bad_scope = {
            "name": "cached_tool",
            "inputSchema": {"type": "object"},
            "cache": {"cacheScope": "invalid_scope"}
        }
        errors = simulate_claude_code_tool_validator(tool_with_bad_scope)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("must be one of" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
